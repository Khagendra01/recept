import asyncio
from typing import List
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

from app.db.session import SessionLocal
from app.models.user import User
from app.services.gmail_service import GmailService
from app.services.auth_service import AuthService
from app.core.config import settings

class BackgroundTaskService:
    """Service for handling background tasks like email polling"""
    
    def __init__(self):
        self.is_running = False
        self.poll_interval = settings.EMAIL_POLL_INTERVAL
    
    async def start_email_polling(self):
        """Start the email polling background task"""
        if self.is_running:
            return
        
        self.is_running = True
        print(f"Starting email polling with {self.poll_interval}s interval")
        
        while self.is_running:
            try:
                await self._poll_all_users_emails()
            except Exception as e:
                print(f"Error in email polling: {e}")
            
            # Wait for next poll
            await asyncio.sleep(self.poll_interval)
    
    def stop_email_polling(self):
        """Stop the email polling background task"""
        self.is_running = False
        print("Stopped email polling")
    
    async def _poll_all_users_emails(self):
        """Poll emails for all users with Gmail access"""
        db = SessionLocal()
        try:
            # Get all users with Gmail access tokens
            users = (
                db.query(User)
                .filter(
                    User.is_active == True,
                    User.gmail_access_token.isnot(None)
                )
                .all()
            )
            
            print(f"Polling emails for {len(users)} users")
            
            for user in users:
                try:
                    # Proactively refresh token before making API calls
                    auth_service = AuthService(db)
                    
                    # Ensure user has a valid Gmail token
                    if not auth_service.ensure_valid_gmail_token(user):
                        print(f"User {user.id} has no valid Gmail token, skipping...")
                        continue
                    
                    await self._poll_user_emails(db, user)
                except Exception as e:
                    print(f"Error polling emails for user {user.id}: {e}")
                    
                    # Try to refresh token if it's expired (fallback)
                    auth_service = AuthService(db)
                    refreshed_token = auth_service.refresh_gmail_token(user)
                    
                    if refreshed_token:
                        print(f"Refreshed token for user {user.id}, retrying...")
                        try:
                            await self._poll_user_emails(db, user)
                        except Exception as retry_e:
                            print(f"Retry failed for user {user.id}: {retry_e}")
                    else:
                        print(f"Could not refresh token for user {user.id}")
        
        finally:
            db.close()
    
    async def _poll_user_emails(self, db: Session, user: User):
        """Poll emails for a specific user"""
        gmail_service = GmailService(db)
        
        # Check if we should poll this user (don't poll too frequently)
        if user.last_gmail_sync:
            # Ensure both datetimes are timezone-aware for comparison
            current_time = datetime.now(timezone.utc)
            last_sync = user.last_gmail_sync
            
            # If last_gmail_sync is timezone-naive, assume it's UTC
            if last_sync.tzinfo is None:
                last_sync = last_sync.replace(tzinfo=timezone.utc)
            
            time_since_sync = current_time - last_sync
            if time_since_sync < timedelta(minutes=5):  # Minimum 5 minutes between syncs
                return
        
        # Poll for new emails
        new_emails = await gmail_service.poll_new_emails(user)
        
        if new_emails:
            print(f"Found {len(new_emails)} new emails for user {user.id}")
            
            # Update user's last sync time
            from app.services.user_service import UserService
            from app.schemas.user import UserUpdate
            user_service = UserService(db)
            user_service.update_user(
                user.id,
                UserUpdate(last_gmail_sync=datetime.now(timezone.utc))
            )
        
        return new_emails
    
    async def process_pending_receipts(self):
        """Process any pending receipt extractions"""
        db = SessionLocal()
        try:
            from app.services.email_service import EmailService
            from app.services.openai_service import OpenAIService
            
            email_service = EmailService(db)
            openai_service = OpenAIService(db)
            
            # Get pending emails with PDF receipts
            pending_emails = email_service.get_pending_emails()
            
            print(f"Processing {len(pending_emails)} pending receipts")
            
            for email in pending_emails:
                try:
                    # Note: This would require access to the original PDF
                    # In a real implementation, you'd store PDFs locally
                    # For now, we'll skip this
                    pass
                except Exception as e:
                    print(f"Error processing receipt for email {email.id}: {e}")
        
        finally:
            db.close()
    
    async def check_users_without_gmail_tokens(self):
        """Check for users without Gmail tokens and log them"""
        db = SessionLocal()
        try:
            # Get users without Gmail tokens
            users_without_tokens = (
                db.query(User)
                .filter(
                    User.is_active == True,
                    User.gmail_access_token.is_(None)
                )
                .all()
            )
            
            if users_without_tokens:
                print(f"Found {len(users_without_tokens)} users without Gmail tokens:")
                for user in users_without_tokens:
                    print(f"  - User {user.id}: {user.email} (Google ID: {user.google_id})")
            
            return users_without_tokens
        
        finally:
            db.close()

# Global instance
background_service = BackgroundTaskService()
