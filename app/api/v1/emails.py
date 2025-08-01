from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.api.deps import get_db, get_current_user
from app.schemas.email import Email, EmailList
from app.services.email_service import EmailService
from app.models.user import User

router = APIRouter()

@router.get("/", response_model=EmailList)
def get_emails(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    processed_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> EmailList:
    """Get user's emails with pagination"""
    email_service = EmailService(db)
    
    emails = email_service.get_user_emails(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        processed_only=processed_only
    )
    
    total = email_service.count_user_emails(current_user.id)
    pages = (total + limit - 1) // limit if limit > 0 else 1
    page = (skip // limit) + 1 if limit > 0 else 1
    
    return EmailList(
        emails=emails,
        total=total,
        page=page,
        size=limit,
        pages=pages
    )

@router.get("/notifications")
def get_recent_notifications(
    limit: int = Query(5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Get recent email notifications for navbar"""
    email_service = EmailService(db)
    
    notifications = email_service.get_recent_notifications(
        user_id=current_user.id,
        limit=limit
    )
    
    return [
        {
            "id": email.id,
            "subject": email.subject,
            "sender": email.sender,
            "snippet": email.snippet,
            "received_date": email.received_date,
            "has_pdf_receipts": email.has_pdf_receipts,
            "is_processed": email.is_processed,
            "processing_status": email.processing_status
        }
        for email in notifications
    ]

@router.get("/stats")
def get_email_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get email processing statistics"""
    from app.models.email import Email
    from sqlalchemy import func, and_
    
    # Total emails
    total_emails = (
        db.query(Email)
        .filter(Email.user_id == current_user.id)
        .count()
    )
    
    # Emails with receipts
    emails_with_receipts = (
        db.query(Email)
        .filter(
            and_(
                Email.user_id == current_user.id,
                Email.has_pdf_receipts == True
            )
        )
        .count()
    )
    
    # Processed emails
    processed_emails = (
        db.query(Email)
        .filter(
            and_(
                Email.user_id == current_user.id,
                Email.is_processed == True
            )
        )
        .count()
    )
    
    # Pending emails
    pending_emails = (
        db.query(Email)
        .filter(
            and_(
                Email.user_id == current_user.id,
                Email.has_pdf_receipts == True,
                Email.is_processed == False,
                Email.processing_status == "pending"
            )
        )
        .count()
    )
    
    # Failed emails
    failed_emails = (
        db.query(Email)
        .filter(
            and_(
                Email.user_id == current_user.id,
                Email.processing_status == "failed"
            )
        )
        .count()
    )
    
    return {
        "total_emails": total_emails,
        "emails_with_receipts": emails_with_receipts,
        "processed_emails": processed_emails,
        "pending_emails": pending_emails,
        "failed_emails": failed_emails,
        "processing_rate": (
            (processed_emails / max(emails_with_receipts, 1)) * 100
            if emails_with_receipts > 0 else 0
        )
    }

@router.get("/{email_id}", response_model=Email)
def get_email(
    email_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Email:
    """Get specific email"""
    email_service = EmailService(db)
    
    email = email_service.get_email(email_id)
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found"
        )
    
    # Check if email belongs to current user
    if email.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this email"
        )
    
    return email
