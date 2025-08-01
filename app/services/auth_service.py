from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
import httpx
from datetime import datetime, timedelta
import hashlib

from app.core.config import settings
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.services.user_service import UserService

# Simple cache to prevent code reuse
_used_codes = set()

class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_service = UserService(db)
        
    def create_google_flow(self, redirect_uri: str = None) -> Flow:
        """Create Google OAuth2 flow"""
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=[
                "openid",
                "https://www.googleapis.com/auth/userinfo.email",
                "https://www.googleapis.com/auth/userinfo.profile",
                "https://www.googleapis.com/auth/gmail.readonly",
            ],
        )
        
        flow.redirect_uri = redirect_uri or settings.google_redirect_uri
        return flow
    
    def get_authorization_url(self, redirect_uri: str = None) -> tuple[str, str]:
        """Get Google OAuth2 authorization URL"""
        flow = self.create_google_flow(redirect_uri)
        authorization_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent"  # Force consent to get refresh token
        )
        return authorization_url, state
    
    async def exchange_code_for_tokens(self, code: str, redirect_uri: str = None) -> Dict[str, Any]:
        """Exchange authorization code for tokens"""
        print(f"DEBUG: Exchanging code with redirect_uri: {redirect_uri}")
        
        # Check if code has already been used
        code_hash = hashlib.md5(code.encode()).hexdigest()
        if code_hash in _used_codes:
            raise Exception("Authorization code has already been used. Please try signing in again.")
        
        flow = self.create_google_flow(redirect_uri)
        
        try:
            print(f"DEBUG: Flow redirect_uri: {flow.redirect_uri}")
            
            # Exchange the authorization code for tokens
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
            # Mark code as used
            _used_codes.add(code_hash)
            
            print(f"DEBUG: Successfully got credentials, token type: {type(credentials.token)}")
            
            # Get user info from Google
            user_info = await self._get_google_user_info(credentials.token)
            print(f"DEBUG: Got user info: {user_info.get('email', 'No email')}")
            
            # Create or update user
            user = await self._create_or_update_user(
                user_info, credentials
            )
            
            # Create our app's access token
            access_token = create_access_token(subject=user.id)
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "picture": user.picture,
                },
                "gmail_connected": bool(user.gmail_access_token)
            }
            
        except Exception as e:
            print(f"DEBUG: Error in exchange_code_for_tokens: {str(e)}")
            # Don't expose internal errors to the client
            if "invalid_grant" in str(e):
                raise Exception("Authorization code has expired or is invalid. Please try signing in again.")
            elif "scope" in str(e).lower():
                raise Exception("OAuth scope mismatch. Please try signing in again.")
            else:
                raise Exception(f"Authentication failed: {str(e)}")
    
    async def _get_google_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user info from Google API"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response.status_code != 200:
                raise Exception("Failed to get user info from Google")
                
            return response.json()
    
    async def _create_or_update_user(
        self, user_info: Dict[str, Any], credentials: Credentials
    ) -> User:
        """Create or update user with Google info"""
        existing_user = self.user_service.get_user_by_google_id(user_info["id"])
        
        if existing_user:
            # Update existing user
            update_data = {
                "name": user_info.get("name"),
                "picture": user_info.get("picture"),
                "gmail_access_token": credentials.token,
                "gmail_refresh_token": credentials.refresh_token,
                "gmail_token_expiry": credentials.expiry,
            }
            return self.user_service.update_user(existing_user.id, UserUpdate(**update_data))
        else:
            # Create new user
            user_data = UserCreate(
                email=user_info["email"],
                google_id=user_info["id"],
                name=user_info.get("name"),
                picture=user_info.get("picture"),
            )
            user = self.user_service.create_user(user_data)
            
            # Update with Gmail tokens
            update_data = {
                "gmail_access_token": credentials.token,
                "gmail_refresh_token": credentials.refresh_token,
                "gmail_token_expiry": credentials.expiry,
            }
            return self.user_service.update_user(user.id, UserUpdate(**update_data))
    
    def refresh_gmail_token(self, user: User) -> Optional[str]:
        """Refresh Gmail access token using refresh token"""
        if not user.gmail_refresh_token:
            return None
            
        try:
            credentials = Credentials(
                token=user.gmail_access_token,
                refresh_token=user.gmail_refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
            )
            
            if credentials.expired:
                credentials.refresh(Request())
                
                # Update user with new token
                self.user_service.update_user(
                    user.id,
                    UserUpdate(
                        gmail_access_token=credentials.token,
                        gmail_token_expiry=credentials.expiry,
                    )
                )
                
                return credentials.token
                
            return user.gmail_access_token
            
        except Exception as e:
            print(f"Failed to refresh Gmail token: {e}")
            return None
    
    def is_gmail_token_expired(self, user: User) -> bool:
        """Check if Gmail access token is expired"""
        if not user.gmail_token_expiry:
            return True
        return datetime.utcnow() >= user.gmail_token_expiry
    
    def ensure_valid_gmail_token(self, user: User) -> bool:
        """Ensure user has a valid Gmail token, refresh if needed"""
        if not user.gmail_access_token:
            return False
        
        if self.is_gmail_token_expired(user):
            refreshed_token = self.refresh_gmail_token(user)
            return refreshed_token is not None
        
        return True
    
    def get_user_by_token(self, token: str) -> Optional[User]:
        """Get user by JWT token"""
        from app.core.security import verify_token
        
        user_id = verify_token(token)
        if not user_id:
            return None
            
        return self.user_service.get_user(int(user_id))
