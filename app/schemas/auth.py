from pydantic import BaseModel
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

class GoogleAuthRequest(BaseModel):
    code: str
    state: Optional[str] = None

class GoogleAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict
    gmail_connected: bool = False

class GmailConnectionStatus(BaseModel):
    connected: bool
    last_sync: Optional[str] = None
    total_emails: int = 0
    total_transactions: int = 0
