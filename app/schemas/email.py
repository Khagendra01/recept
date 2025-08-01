from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class EmailBase(BaseModel):
    subject: Optional[str] = None
    sender: Optional[str] = None
    snippet: Optional[str] = None

class EmailCreate(EmailBase):
    user_id: int
    gmail_message_id: str
    gmail_thread_id: Optional[str] = None
    gmail_history_id: Optional[str] = None
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    received_date: Optional[datetime] = None
    has_attachments: Optional[bool] = None
    has_pdf_receipts: Optional[bool] = None

class EmailUpdate(BaseModel):
    processing_status: Optional[str] = None
    is_processed: Optional[bool] = None
    processing_error: Optional[str] = None
    has_attachments: Optional[bool] = None
    has_pdf_receipts: Optional[bool] = None

class EmailInDBBase(EmailBase):
    id: int
    user_id: int
    gmail_message_id: str
    gmail_thread_id: Optional[str] = None
    gmail_history_id: Optional[str] = None
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    received_date: Optional[datetime] = None
    has_attachments: bool
    has_pdf_receipts: bool
    is_processed: bool
    processing_status: str
    processing_error: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class Email(EmailInDBBase):
    pass

class EmailList(BaseModel):
    emails: List[Email]
    total: int
    page: int
    size: int
    pages: int
