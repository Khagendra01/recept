from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from datetime import datetime

from app.models.email import Email
from app.schemas.email import EmailCreate, EmailUpdate

class EmailService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_email(self, email_create: EmailCreate) -> Email:
        """Create new email record"""
        db_email = Email(**email_create.model_dump())
        self.db.add(db_email)
        self.db.commit()
        self.db.refresh(db_email)
        return db_email
    
    def get_email(self, email_id: int) -> Optional[Email]:
        """Get email by ID"""
        return self.db.query(Email).filter(Email.id == email_id).first()
    
    def get_email_by_gmail_id(self, gmail_message_id: str) -> Optional[Email]:
        """Get email by Gmail message ID"""
        return self.db.query(Email).filter(Email.gmail_message_id == gmail_message_id).first()
    
    def update_email(self, email_id: int, email_update: EmailUpdate) -> Optional[Email]:
        """Update email"""
        db_email = self.get_email(email_id)
        if not db_email:
            return None
        
        # Handle both dict and Pydantic model inputs
        if isinstance(email_update, dict):
            update_data = email_update
        else:
            update_data = email_update.model_dump(exclude_unset=True)
            
        for field, value in update_data.items():
            setattr(db_email, field, value)
        
        self.db.commit()
        self.db.refresh(db_email)
        return db_email
    
    def get_user_emails(
        self, 
        user_id: int, 
        skip: int = 0, 
        limit: int = 100,
        processed_only: bool = False
    ) -> List[Email]:
        """Get emails for a user"""
        query = self.db.query(Email).filter(Email.user_id == user_id)
        
        if processed_only:
            query = query.filter(Email.is_processed == True)
        
        return (
            query
            .order_by(desc(Email.received_date))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_pending_emails(self, user_id: int = None) -> List[Email]:
        """Get emails pending processing"""
        query = self.db.query(Email).filter(
            and_(
                Email.is_processed == False,
                Email.has_pdf_receipts == True,
                Email.processing_status == "pending"
            )
        )
        
        if user_id:
            query = query.filter(Email.user_id == user_id)
        
        return query.order_by(Email.received_date).all()
    
    def count_user_emails(self, user_id: int) -> int:
        """Count total emails for user"""
        return self.db.query(Email).filter(Email.user_id == user_id).count()
    
    def get_recent_notifications(self, user_id: int, limit: int = 5) -> List[Email]:
        """Get recent email notifications"""
        return (
            self.db.query(Email)
            .filter(
                and_(
                    Email.user_id == user_id,
                    Email.has_pdf_receipts == True
                )
            )
            .order_by(desc(Email.created_at))
            .limit(limit)
            .all()
        )
