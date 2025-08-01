from sqlalchemy import Column, Integer, String, DateTime, Float, Text, Boolean
from sqlalchemy.sql import func
from app.db.base_class import Base

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)  # No FK constraint
    email_id = Column(Integer, nullable=True, index=True)  # Links to email table
    
    # Transaction details
    merchant_name = Column(String(255), nullable=True)
    amount = Column(Float, nullable=True)
    currency = Column(String(10), default="USD")
    transaction_date = Column(DateTime, nullable=True)
    category = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    
    # Receipt/Email metadata
    email_subject = Column(String(500), nullable=True)
    email_snippet = Column(Text, nullable=True)
    pdf_file_path = Column(String(500), nullable=True)
    
    # AI extraction metadata
    extraction_confidence = Column(Float, nullable=True)  # 0-1 confidence score
    raw_extracted_data = Column(Text, nullable=True)  # JSON string of raw AI response
    
    # Processing status
    is_processed = Column(Boolean, default=False)
    processing_error = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
