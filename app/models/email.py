from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.sql import func
from app.db.base_class import Base

class Email(Base):
    __tablename__ = "emails"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)  # No FK constraint
    
    # Gmail metadata
    gmail_message_id = Column(String(255), unique=True, index=True, nullable=False)
    gmail_thread_id = Column(String(255), nullable=True)
    gmail_history_id = Column(String(255), nullable=True)
    
    # Email content
    subject = Column(String(500), nullable=True)
    sender = Column(String(255), nullable=True)
    snippet = Column(Text, nullable=True)
    body_text = Column(Text, nullable=True)
    body_html = Column(Text, nullable=True)
    received_date = Column(DateTime, nullable=True)
    
    # Processing status
    has_attachments = Column(Boolean, default=False)
    has_pdf_receipts = Column(Boolean, default=False)
    is_processed = Column(Boolean, default=False)
    processing_status = Column(String(50), default="pending")  # pending, processing, completed, failed
    processing_error = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
