import base64
import email
import io
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import PyPDF2
import pdfplumber

from app.core.config import settings
from app.models.user import User
from app.models.email import Email
from app.schemas.email import EmailCreate, EmailUpdate
from app.services.user_service import UserService
from app.services.email_service import EmailService
from app.services.openai_service import OpenAIService

class GmailService:
    def __init__(self, db: Session):
        self.db = db
        self.user_service = UserService(db)
        self.email_service = EmailService(db)
        self.openai_service = OpenAIService(db)
    
    def _get_gmail_service(self, user: User):
        """Get authenticated Gmail service"""
        if not user.gmail_access_token:
            raise Exception("User has no Gmail access token")
        
        credentials = Credentials(
            token=user.gmail_access_token,
            refresh_token=user.gmail_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
        )
        
        # Check if token is expired and refresh if needed
        if credentials.expired and credentials.refresh_token:
            try:
                from google.auth.transport.requests import Request
                credentials.refresh(Request())
                
                # Update user with new token
                from app.services.user_service import UserService
                from app.schemas.user import UserUpdate
                user_service = UserService(self.db)
                user_service.update_user(
                    user.id,
                    UserUpdate(
                        gmail_access_token=credentials.token,
                        gmail_token_expiry=credentials.expiry,
                    )
                )
                
                # Update the user object for this session
                user.gmail_access_token = credentials.token
                user.gmail_token_expiry = credentials.expiry
                
                print(f"Refreshed Gmail token for user {user.id}")
            except Exception as e:
                print(f"Failed to refresh Gmail token for user {user.id}: {e}")
                raise Exception("Gmail token refresh failed")
        
        return build('gmail', 'v1', credentials=credentials)
    
    async def fetch_recent_emails(self, user: User, max_results: int = 10) -> List[Dict[str, Any]]:
        """Fetch recent emails for initial sync"""
        try:
            service = self._get_gmail_service(user)
            
            # Query for emails that might contain receipts
            query = 'has:attachment (receipt OR invoice OR "thank you for your purchase" OR "order confirmation")'
            
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            processed_emails = []
            
            for message in messages:
                email_data = await self._process_email_message(service, message['id'], user.id)
                if email_data:
                    processed_emails.append(email_data)
            
            # Update user's last sync time
            from app.schemas.user import UserUpdate
            self.user_service.update_user(
                user.id,
                UserUpdate(last_gmail_sync=datetime.now(timezone.utc))
            )
            
            return processed_emails
            
        except Exception as e:
            raise Exception(f"Failed to fetch emails: {str(e)}")
    
    async def poll_new_emails(self, user: User) -> List[Dict[str, Any]]:
        """Poll for new emails since last sync"""
        try:
            service = self._get_gmail_service(user)
            
            # Use history API for incremental sync if we have a history ID
            if user.gmail_history_id:
                return await self._fetch_new_emails_by_history(service, user)
            else:
                # Fallback to date-based query
                return await self._fetch_new_emails_by_date(service, user)
                
        except Exception as e:
            print(f"Error polling emails for user {user.id}: {e}")
            return []
    
    async def _fetch_new_emails_by_history(self, service, user: User) -> List[Dict[str, Any]]:
        """Fetch new emails using Gmail History API"""
        try:
            history = service.users().history().list(
                userId='me',
                startHistoryId=user.gmail_history_id,
                historyTypes=['messageAdded']
            ).execute()
            
            processed_emails = []
            
            if 'history' in history:
                for record in history['history']:
                    if 'messagesAdded' in record:
                        for msg_added in record['messagesAdded']:
                            message_id = msg_added['message']['id']
                            
                            # Check if we already processed this email
                            if not self.email_service.get_email_by_gmail_id(message_id):
                                email_data = await self._process_email_message(
                                    service, message_id, user.id
                                )
                                if email_data:
                                    processed_emails.append(email_data)
            
            # Update history ID
            if 'historyId' in history:
                self.user_service.update_user(
                    user.id,
                    UserUpdate(gmail_history_id=history['historyId'])
                )
            
            return processed_emails
            
        except Exception as e:
            print(f"Error fetching by history: {e}")
            return []
    
    async def _fetch_new_emails_by_date(self, service, user: User) -> List[Dict[str, Any]]:
        """Fetch new emails by date (fallback method)"""
        try:
            # Get emails from last sync or last 24 hours
            if user.last_gmail_sync:
                since_date = user.last_gmail_sync
            else:
                # Use timedelta to properly subtract 1 day
                since_date = datetime.now(timezone.utc) - timedelta(days=1)
            
            query_date = since_date.strftime('%Y/%m/%d')
            
            query = f'has:attachment after:{query_date} (receipt OR invoice OR "thank you for your purchase" OR "order confirmation")'
            
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=settings.MAX_EMAILS_PER_POLL
            ).execute()
            
            messages = results.get('messages', [])
            processed_emails = []
            
            for message in messages:
                # Check if we already processed this email
                if not self.email_service.get_email_by_gmail_id(message['id']):
                    email_data = await self._process_email_message(service, message['id'], user.id)
                    if email_data:
                        processed_emails.append(email_data)
            
            return processed_emails
            
        except Exception as e:
            print(f"Error fetching by date: {e}")
            return []
    
    async def _process_email_message(self, service, message_id: str, user_id: int) -> Optional[Dict[str, Any]]:
        """Process a single email message"""
        try:
            message = service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            # Extract email metadata
            headers = {h['name']: h['value'] for h in message['payload'].get('headers', [])}
            
            email_data = EmailCreate(
                user_id=user_id,
                gmail_message_id=message_id,
                gmail_thread_id=message.get('threadId'),
                gmail_history_id=message.get('historyId'),
                subject=headers.get('Subject', ''),
                sender=headers.get('From', ''),
                snippet=message.get('snippet', ''),
                received_date=self._parse_date(headers.get('Date')),
            )
            
            # Extract email body
            body_text, body_html = self._extract_email_body(message['payload'])
            email_data.body_text = body_text
            email_data.body_html = body_html
            
            # Check for attachments
            attachments, pdf_attachments = self._extract_attachments(service, message_id, message['payload'])
            email_data.has_attachments = len(attachments) > 0
            email_data.has_pdf_receipts = len(pdf_attachments) > 0
            
            # Save email to database
            db_email = self.email_service.create_email(email_data)
            
            # Process PDF receipts if any
            if pdf_attachments:
                await self._process_pdf_receipts(pdf_attachments, db_email)
            
            return {
                'email_id': db_email.id,
                'subject': db_email.subject,
                'sender': db_email.sender,
                'has_receipts': db_email.has_pdf_receipts,
                'processed': db_email.is_processed
            }
            
        except Exception as e:
            print(f"Error processing email {message_id}: {e}")
            return None
    
    def _extract_email_body(self, payload: Dict[str, Any]) -> Tuple[str, str]:
        """Extract text and HTML body from email payload"""
        body_text = ""
        body_html = ""
        
        def extract_parts(part):
            nonlocal body_text, body_html
            
            if part.get('mimeType') == 'text/plain':
                data = part['body'].get('data')
                if data:
                    body_text = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            elif part.get('mimeType') == 'text/html':
                data = part['body'].get('data')
                if data:
                    body_html = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            elif 'parts' in part:
                for subpart in part['parts']:
                    extract_parts(subpart)
        
        extract_parts(payload)
        return body_text, body_html
    
    def _extract_attachments(self, service, message_id: str, payload: Dict[str, Any]) -> Tuple[List[Dict], List[Dict]]:
        """Extract all attachments and filter PDF receipts"""
        attachments = []
        pdf_attachments = []
        
        def extract_attachment_parts(part):
            if 'filename' in part and part['filename']:
                attachment_id = part['body'].get('attachmentId')
                if attachment_id:
                    attachment_data = service.users().messages().attachments().get(
                        userId='me',
                        messageId=message_id,
                        id=attachment_id
                    ).execute()
                    
                    attachment = {
                        'filename': part['filename'],
                        'mimeType': part.get('mimeType', ''),
                        'size': part['body'].get('size', 0),
                        'data': attachment_data['data']
                    }
                    attachments.append(attachment)
                    
                    # Check if it's a PDF
                    if part.get('mimeType') == 'application/pdf' or part['filename'].lower().endswith('.pdf'):
                        pdf_attachments.append(attachment)
            
            # Recursively check parts
            if 'parts' in part:
                for subpart in part['parts']:
                    extract_attachment_parts(subpart)
        
        extract_attachment_parts(payload)
        return attachments, pdf_attachments
    
    async def _process_pdf_receipts(self, pdf_attachments: List[Dict], db_email: Email):
        """Process PDF receipts using OpenAI"""
        for pdf_attachment in pdf_attachments:
            try:
                # Decode PDF data
                pdf_data = base64.urlsafe_b64decode(pdf_attachment['data'])
                
                # Extract text from PDF
                pdf_text = self._extract_pdf_text(pdf_data)
                
                if pdf_text:
                    # Use OpenAI to extract transaction data
                    await self.openai_service.process_receipt_pdf(
                        pdf_text=pdf_text,
                        email=db_email,
                        filename=pdf_attachment['filename']
                    )
                    
            except Exception as e:
                print(f"Error processing PDF {pdf_attachment['filename']}: {e}")
                # Update email with processing error
                self.email_service.update_email(
                    db_email.id,
                    EmailUpdate(
                        processing_status="failed",
                        processing_error=f"PDF processing failed: {str(e)}"
                    )
                )
    
    def _extract_pdf_text(self, pdf_data: bytes) -> str:
        """Extract text from PDF using pdfplumber and PyPDF2"""
        text = ""
        
        try:
            # Try pdfplumber first (better for structured data)
            with pdfplumber.open(io.BytesIO(pdf_data)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                        
        except Exception:
            try:
                # Fallback to PyPDF2
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_data))
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            except Exception as e:
                print(f"Failed to extract PDF text: {e}")
                return ""
        
        return text.strip()
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse email date string to datetime"""
        if not date_str:
            return None
        
        try:
            # Parse RFC 2822 date format
            parsed = email.utils.parsedate_tz(date_str)
            if parsed:
                timestamp = email.utils.mktime_tz(parsed)
                return datetime.fromtimestamp(timestamp, tz=timezone.utc)
        except Exception:
            pass
        
        return None
