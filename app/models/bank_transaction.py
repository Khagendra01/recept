from sqlalchemy import Column, Integer, String, DateTime, Float, Text, Boolean
from sqlalchemy.sql import func
from app.db.base_class import Base

class BankTransaction(Base):
    __tablename__ = "bank_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)  # No FK constraint
    upload_batch_id = Column(String(255), nullable=True, index=True)  # Group by CSV upload
    
    # Bank transaction details
    date = Column(DateTime, nullable=True)
    description = Column(Text, nullable=True)
    amount = Column(Float, nullable=True)
    balance = Column(Float, nullable=True)
    transaction_type = Column(String(50), nullable=True)  # debit, credit
    reference_number = Column(String(255), nullable=True)
    
    # Categorization
    category = Column(String(100), nullable=True)
    merchant_name = Column(String(255), nullable=True)  # Cleaned/normalized
    
    # Matching status
    is_matched = Column(Boolean, default=False)
    matched_transaction_id = Column(Integer, nullable=True)  # Links to transactions table
    match_confidence = Column(Float, nullable=True)  # 0-1 confidence score
    match_type = Column(String(50), nullable=True)  # exact, approximate, manual
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
