import json
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from openai import OpenAI
from datetime import datetime
import re

from app.core.config import settings
from app.models.email import Email
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate, ReceiptData
from app.services.transaction_service import TransactionService
from app.services.email_service import EmailService

class OpenAIService:
    def __init__(self, db: Session):
        self.db = db
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.transaction_service = TransactionService(db)
        self.email_service = EmailService(db)
    
    def _parse_date_string(self, date_str: str) -> Optional[str]:
        """Parse various date formats and return YYYY-MM-DD format"""
        if not date_str:
            return None
            
        # Common date patterns
        patterns = [
            r'(\d{1,2})/(\d{1,2})/(\d{4})',  # 8/1/2025
            r'(\d{4})-(\d{1,2})-(\d{1,2})',  # 2025-08-01
            r'(\d{1,2})-(\d{1,2})-(\d{4})',  # 08-01-2025
        ]
        
        for pattern in patterns:
            match = re.search(pattern, date_str)
            if match:
                if len(match.groups()) == 3:
                    if len(match.group(1)) == 4:  # YYYY-MM-DD format
                        year, month, day = match.groups()
                    else:  # MM/DD/YYYY or MM-DD-YYYY format
                        month, day, year = match.groups()
                    
                    # Ensure month and day are zero-padded
                    month = month.zfill(2)
                    day = day.zfill(2)
                    
                    return f"{year}-{month}-{day}"
        
        return None
    
    async def process_receipt_pdf(self, pdf_text: str, email: Email, filename: str) -> Optional[Transaction]:
        """Process PDF receipt text using OpenAI to extract structured data"""
        try:
            # Update email status to processing
            self.email_service.update_email(
                email.id,
                {'processing_status': 'processing'}
            )
            
            # Log the receipt processing attempt
            print(f"Processing receipt: {filename}")
            print(f"Email subject: {email.subject}")
            print(f"Text length: {len(pdf_text)} characters")
            
            # Extract structured data using OpenAI
            receipt_data = await self._extract_receipt_data(pdf_text)
            
            if receipt_data:
                print(f"Successfully extracted data for {filename}")
                print(f"Merchant: {receipt_data.merchant_name}")
                print(f"Amount: {receipt_data.amount}")
                print(f"Category: {receipt_data.category}")
                
                # Create transaction from extracted data
                transaction = await self._create_transaction_from_receipt(
                    receipt_data, email, filename
                )
                
                # Update email status to completed
                self.email_service.update_email(
                    email.id,
                    {
                        'is_processed': True,
                        'processing_status': 'completed'
                    }
                )
                
                return transaction
            else:
                print(f"Failed to extract data from {filename}")
                # Update email status to failed
                self.email_service.update_email(
                    email.id,
                    {
                        'processing_status': 'failed',
                        'processing_error': 'Failed to extract data from receipt - AI extraction returned null'
                    }
                )
                
        except Exception as e:
            print(f"Error processing receipt {filename}: {e}")
            print(f"Email subject: {email.subject}")
            print(f"Error type: {type(e).__name__}")
            
            # Update email status to failed
            self.email_service.update_email(
                email.id,
                {
                    'processing_status': 'failed',
                    'processing_error': f"Processing error: {str(e)}"
                }
            )
            
        return None
    
    async def _extract_receipt_data(self, pdf_text: str) -> Optional[ReceiptData]:
        """Use OpenAI to extract structured data from receipt text"""
        try:
            # Prepare the prompt for structured extraction
            prompt = self._create_extraction_prompt(pdf_text)
            
            response = self.client.chat.completions.create(
                model="gpt-4-1106-preview",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at extracting structured transaction data from receipts. Return only valid JSON without any markdown formatting or code blocks."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            # Parse the response
            content = response.choices[0].message.content
            
            # Try to extract JSON from markdown code blocks if present
            json_content = content
            if content.startswith('```json'):
                # Extract JSON from markdown code block
                json_content = content.replace('```json', '').replace('```', '').strip()
            elif content.startswith('```'):
                # Extract JSON from generic code block
                json_content = content.replace('```', '').strip()
            
            # Try to parse JSON response
            try:
                extracted_data = json.loads(json_content)
                
                # Validate and create ReceiptData object
                receipt_data = ReceiptData(**extracted_data)
                return receipt_data
                
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Failed to parse OpenAI response as JSON: {e}")
                print(f"Response content: {content}")
                return None
                
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return None
    
    def _create_extraction_prompt(self, pdf_text: str) -> str:
        """Create prompt for OpenAI to extract receipt data"""
        return f"""
Extract transaction information from the following receipt text and return it as JSON.

Receipt Text:
{pdf_text}

Please extract the following information and return as JSON:
{{
    "merchant_name": "Name of the store/merchant",
    "amount": 0.00,
    "currency": "USD",
    "transaction_date": "YYYY-MM-DD",
    "category": "Category (e.g., food, travel, shopping, gas, entertainment)",
    "description": "Brief description of the purchase",
    "tax_amount": 0.00,
    "payment_method": "Payment method if available",
    "confidence": 0.95
}}

Special Instructions for Ride-Sharing Receipts (Uber, Lyft, etc.):
- For Uber receipts: Look for "UBER" or "Uber" in the text
- For ride-sharing: Category should be "travel"
- Description should include trip details if available (e.g., "Uber ride from X to Y")
- Look for trip fare, service fee, and total amount
- Date format: Convert any date format to YYYY-MM-DD (e.g., "8/1/2025" becomes "2025-08-01")

Guidelines:
- Use null for missing information
- Amount should be the total transaction amount as a number
- Date should be in YYYY-MM-DD format
- Confidence should be between 0 and 1 based on how clear the information is
- Category should be one of: food, travel, shopping, gas, entertainment, healthcare, utilities, other
- Extract the most relevant information even if some fields are missing
- If the text doesn't appear to be a receipt, set confidence to 0
- For ride-sharing services, prioritize travel category and include service details in description

Return only the JSON, no additional text.
"""
    
    async def _create_transaction_from_receipt(
        self, 
        receipt_data: ReceiptData, 
        email: Email, 
        filename: str
    ) -> Transaction:
        """Create transaction record from extracted receipt data"""
        
        # Parse transaction date with improved parsing
        transaction_date = None
        if receipt_data.transaction_date:
            # First try the improved date parsing
            parsed_date = self._parse_date_string(receipt_data.transaction_date)
            if parsed_date:
                try:
                    transaction_date = datetime.strptime(parsed_date, "%Y-%m-%d")
                except ValueError:
                    pass
            else:
                # Fallback to original parsing
                try:
                    transaction_date = datetime.strptime(receipt_data.transaction_date, "%Y-%m-%d")
                except ValueError:
                    pass
        
        # Special handling for Uber receipts
        merchant_name = receipt_data.merchant_name
        category = receipt_data.category
        description = receipt_data.description
        
        # If it's an Uber receipt, ensure proper categorization
        if merchant_name and "uber" in merchant_name.lower():
            category = "travel"
            if not description or "uber" not in description.lower():
                description = f"Uber ride - {description or 'Transportation service'}"
        
        # Create transaction
        transaction_create = TransactionCreate(
            user_id=email.user_id,
            email_id=email.id,
            merchant_name=merchant_name,
            amount=receipt_data.amount,
            currency=receipt_data.currency or "USD",
            transaction_date=transaction_date,
            category=category,
            description=description,
            email_subject=email.subject,
            email_snippet=email.snippet,
            pdf_file_path=filename,
            extraction_confidence=receipt_data.confidence,
            raw_extracted_data=json.dumps(receipt_data.model_dump()),
            is_processed=True
        )
        
        return self.transaction_service.create_transaction(transaction_create)
    
    async def reprocess_failed_receipts(self, user_id: int = None) -> int:
        """Reprocess failed receipt extractions"""
        # Get emails with failed processing
        failed_emails = (
            self.db.query(Email)
            .filter(
                Email.processing_status == "failed",
                Email.has_pdf_receipts == True
            )
        )
        
        if user_id:
            failed_emails = failed_emails.filter(Email.user_id == user_id)
        
        failed_emails = failed_emails.all()
        
        reprocessed_count = 0
        
        for email in failed_emails:
            try:
                # Note: This would require re-downloading the PDF from Gmail
                # For now, we'll skip this implementation
                # In a real system, you'd store the PDF files locally
                pass
            except Exception as e:
                print(f"Error reprocessing email {email.id}: {e}")
        
        return reprocessed_count
    
    async def reprocess_uber_receipts(self, user_id: int = None) -> int:
        """Specifically reprocess failed Uber receipts with enhanced handling"""
        # Get emails with failed processing that might be Uber receipts
        failed_emails = (
            self.db.query(Email)
            .filter(
                Email.processing_status == "failed",
                Email.has_pdf_receipts == True
            )
        )
        
        if user_id:
            failed_emails = failed_emails.filter(Email.user_id == user_id)
        
        failed_emails = failed_emails.all()
        
        uber_receipts = []
        for email in failed_emails:
            # Check if this might be an Uber receipt based on subject or sender
            if (email.subject and "uber" in email.subject.lower()) or \
               (email.sender and "uber" in email.sender.lower()):
                uber_receipts.append(email)
        
        print(f"Found {len(uber_receipts)} failed Uber receipts to reprocess")
        
        reprocessed_count = 0
        for email in uber_receipts:
            try:
                print(f"Attempting to reprocess Uber receipt: {email.subject}")
                # Note: This would require re-downloading the PDF from Gmail
                # For now, we'll skip this implementation
                # In a real system, you'd store the PDF files locally
                pass
            except Exception as e:
                print(f"Error reprocessing Uber receipt {email.id}: {e}")
        
        return reprocessed_count
