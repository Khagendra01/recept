from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class TransactionBase(BaseModel):
    merchant_name: Optional[str] = None
    amount: Optional[float] = None
    currency: str = "USD"
    transaction_date: Optional[datetime] = None
    category: Optional[str] = None
    description: Optional[str] = None

class TransactionCreate(TransactionBase):
    user_id: int
    email_id: Optional[int] = None
    email_subject: Optional[str] = None
    email_snippet: Optional[str] = None
    pdf_file_path: Optional[str] = None
    extraction_confidence: Optional[float] = None
    raw_extracted_data: Optional[str] = None
    is_processed: bool = False

class TransactionUpdate(BaseModel):
    merchant_name: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    transaction_date: Optional[datetime] = None
    category: Optional[str] = None
    description: Optional[str] = None

class TransactionInDBBase(TransactionBase):
    id: int
    user_id: int
    email_id: Optional[int] = None
    email_subject: Optional[str] = None
    email_snippet: Optional[str] = None
    pdf_file_path: Optional[str] = None
    extraction_confidence: Optional[float] = None
    is_processed: bool
    processing_error: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class Transaction(TransactionInDBBase):
    pass

class TransactionSummary(BaseModel):
    """Summary for dashboard display"""
    id: int
    merchant_name: Optional[str]
    amount: Optional[float]
    currency: str
    transaction_date: Optional[datetime]
    category: Optional[str]
    email_snippet: Optional[str]
    created_at: datetime

class TransactionList(BaseModel):
    transactions: List[Transaction]
    total: int
    page: int
    size: int
    pages: int

# AI Extraction schemas
class ReceiptData(BaseModel):
    """Structured data extracted from receipt using OpenAI"""
    merchant_name: Optional[str] = Field(description="Name of the merchant/store")
    amount: Optional[float] = Field(description="Total transaction amount")
    currency: Optional[str] = Field(description="Currency code (e.g., USD, EUR)")
    transaction_date: Optional[str] = Field(description="Date of transaction (YYYY-MM-DD format)")
    category: Optional[str] = Field(description="Category of purchase (e.g., food, travel, shopping)")
    description: Optional[str] = Field(description="Brief description of the purchase")
    tax_amount: Optional[float] = Field(description="Tax amount if available")
    payment_method: Optional[str] = Field(description="Payment method used")
    confidence: Optional[float] = Field(description="Confidence score 0-1")
