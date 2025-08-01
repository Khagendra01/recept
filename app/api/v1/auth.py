from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.api.deps import get_db, get_current_user
from app.schemas.auth import GoogleAuthRequest, GoogleAuthResponse, GmailConnectionStatus
from app.services.auth_service import AuthService, _used_codes
from app.services.gmail_service import GmailService
from app.services.transaction_service import TransactionService
from app.services.email_service import EmailService
from app.models.user import User
from app.core.config import settings

router = APIRouter()

@router.get("/debug/gmail-status")
def debug_gmail_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Debug endpoint to check user's Gmail token status"""
    return {
        "user_id": current_user.id,
        "email": current_user.email,
        "has_gmail_access_token": bool(current_user.gmail_access_token),
        "has_gmail_refresh_token": bool(current_user.gmail_refresh_token),
        "gmail_token_expiry": current_user.gmail_token_expiry.isoformat() if current_user.gmail_token_expiry else None,
        "last_gmail_sync": current_user.last_gmail_sync.isoformat() if current_user.last_gmail_sync else None,
        "google_id": current_user.google_id,
        "access_token_length": len(current_user.gmail_access_token) if current_user.gmail_access_token else 0,
        "refresh_token_length": len(current_user.gmail_refresh_token) if current_user.gmail_refresh_token else 0,
    }

@router.post("/debug/clear-used-codes")
def clear_used_codes() -> Dict[str, str]:
    """Clear the used codes cache (for testing)"""
    global _used_codes
    _used_codes.clear()
    return {"message": "Used codes cache cleared"}

@router.post("/debug/check-users-without-gmail")
async def check_users_without_gmail() -> Dict[str, Any]:
    """Check for users without Gmail tokens (for debugging)"""
    from app.services.background_tasks import background_service
    
    users_without_tokens = await background_service.check_users_without_gmail_tokens()
    
    return {
        "message": f"Found {len(users_without_tokens)} users without Gmail tokens",
        "users": [
            {
                "id": user.id,
                "email": user.email,
                "google_id": user.google_id,
                "created_at": user.created_at.isoformat() if user.created_at else None
            }
            for user in users_without_tokens
        ]
    }

@router.get("/google/url")
def get_google_auth_url(
    redirect_uri: str = None,
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """Get Google OAuth2 authorization URL"""
    auth_service = AuthService(db)
    
    try:
        authorization_url, state = auth_service.get_authorization_url(redirect_uri)
        return {
            "authorization_url": authorization_url,
            "state": state
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate authorization URL: {str(e)}"
        )

@router.post("/google/callback")
async def google_auth_callback(
    auth_request: GoogleAuthRequest,
    db: Session = Depends(get_db)
) -> GoogleAuthResponse:
    """Handle Google OAuth2 callback"""
    auth_service = AuthService(db)
    
    try:
        # Use the same redirect URI that was used when generating the auth URL
        result = await auth_service.exchange_code_for_tokens(
            code=auth_request.code,
            redirect_uri=settings.google_redirect_uri
        )
        
        return GoogleAuthResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Authentication failed: {str(e)}"
        )

@router.get("/me")
def get_current_user_info(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get current user information"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "picture": current_user.picture,
        "gmail_connected": bool(current_user.gmail_access_token),
        "created_at": current_user.created_at,
        "last_gmail_sync": current_user.last_gmail_sync
    }

@router.get("/gmail/status")
def get_gmail_connection_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> GmailConnectionStatus:
    """Get Gmail connection status and stats"""
    auth_service = AuthService(db)
    email_service = EmailService(db)
    transaction_service = TransactionService(db)
    
    # Check if user has valid Gmail tokens
    gmail_connected = auth_service.ensure_valid_gmail_token(current_user)
    
    total_emails = email_service.count_user_emails(current_user.id)
    total_transactions = transaction_service.count_user_transactions(current_user.id)
    
    return GmailConnectionStatus(
        connected=gmail_connected,
        last_sync=current_user.last_gmail_sync.isoformat() if current_user.last_gmail_sync else None,
        total_emails=total_emails,
        total_transactions=total_transactions
    )

@router.get("/gmail/auth-url")
def get_gmail_auth_url(
    redirect_uri: str = None,
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """Get Google OAuth2 authorization URL specifically for Gmail access"""
    auth_service = AuthService(db)
    
    try:
        authorization_url, state = auth_service.get_authorization_url(redirect_uri)
        return {
            "authorization_url": authorization_url,
            "state": state
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate authorization URL: {str(e)}"
        )

@router.post("/gmail/sync")
async def trigger_gmail_sync(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Manually trigger Gmail sync"""
    auth_service = AuthService(db)
    
    # Check if user has valid Gmail tokens
    if not auth_service.ensure_valid_gmail_token(current_user):
        # Try to get a fresh auth URL for the user
        try:
            auth_url, state = auth_service.get_authorization_url()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Gmail not connected. Please sign in again to grant Gmail access.",
                    "auth_url": auth_url,
                    "needs_reauth": True
                }
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Gmail not connected. Please sign in again to grant Gmail access."
            )
    
    gmail_service = GmailService(db)
    
    try:
        # Fetch recent emails for first-time sync or manual sync
        emails = await gmail_service.fetch_recent_emails(current_user, max_results=10)
        
        # Update last sync time
        from datetime import datetime
        current_user.last_gmail_sync = datetime.utcnow()
        db.commit()
        
        return {
            "success": True,
            "message": f"Synced {len(emails)} emails",
            "emails_processed": len(emails)
        }
        
    except Exception as e:
        # If the error is related to expired/invalid tokens, suggest re-authentication
        if "invalid_grant" in str(e) or "token" in str(e).lower():
            try:
                auth_url, state = auth_service.get_authorization_url()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "Gmail access has expired. Please sign in again to refresh your access.",
                        "auth_url": auth_url,
                        "needs_reauth": True
                    }
                )
            except Exception as auth_e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Gmail access has expired. Please sign in again to refresh your access."
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Gmail sync failed: {str(e)}"
            )

@router.post("/logout")
def logout(
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Logout user (client-side token removal)"""
    return {"message": "Logged out successfully"}
