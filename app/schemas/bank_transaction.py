from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class BankTransactionBase(BaseModel):
    date: Optional[datetime] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    balance: Optional[float] = None
    transaction_type: Optional[str] = None
    reference_number: Optional[str] = None

class BankTransactionCreate(BankTransactionBase):
    user_id: int
    upload_batch_id: Optional[str] = None

class BankTransactionUpdate(BaseModel):
    category: Optional[str] = None
    merchant_name: Optional[str] = None
    is_matched: Optional[bool] = None
    matched_transaction_id: Optional[int] = None
    match_confidence: Optional[float] = None
    match_type: Optional[str] = None

class BankTransactionInDBBase(BankTransactionBase):
    id: int
    user_id: int
    upload_batch_id: Optional[str] = None
    category: Optional[str] = None
    merchant_name: Optional[str] = None
    is_matched: bool
    matched_transaction_id: Optional[int] = None
    match_confidence: Optional[float] = None
    match_type: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class BankTransaction(BankTransactionInDBBase):
    pass

class BankTransactionList(BaseModel):
    transactions: List[BankTransaction]
    total: int
    page: int
    size: int
    pages: int

# CSV Upload schemas
class CSVUploadResponse(BaseModel):
    batch_id: str
    total_transactions: int
    successful_imports: int
    failed_imports: int
    errors: List[str] = []

# Comparison schemas
class TransactionMatch(BaseModel):
    ledger_transaction: Optional['Transaction'] = None
    bank_transaction: Optional[BankTransaction] = None
    match_type: str  # "matched", "ledger_only", "bank_only"
    confidence: Optional[float] = None

class ComparisonResult(BaseModel):
    matched: List[TransactionMatch]
    ledger_only: List[TransactionMatch]
    bank_only: List[TransactionMatch]
    summary: dict

# Import Transaction here to avoid circular import
from app.schemas.transaction import Transaction
TransactionMatch.model_rebuild()
