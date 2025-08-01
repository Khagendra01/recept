from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.api.deps import get_db, get_current_user
from app.schemas.transaction import (
    Transaction, 
    TransactionCreate, 
    TransactionUpdate, 
    TransactionList,
    TransactionSummary
)
from app.services.transaction_service import TransactionService
from app.models.user import User

router = APIRouter()

@router.get("/", response_model=TransactionList)
def get_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    category: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> TransactionList:
    """Get user's transactions with filtering and pagination"""
    transaction_service = TransactionService(db)
    
    return transaction_service.get_user_transactions(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        category=category,
        date_from=date_from,
        date_to=date_to,
        search=search
    )

@router.get("/recent")
def get_recent_transactions(
    limit: int = Query(15, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[TransactionSummary]:
    """Get recent transactions for dashboard"""
    transaction_service = TransactionService(db)
    
    transactions = transaction_service.get_recent_transactions(
        user_id=current_user.id,
        limit=limit
    )
    
    # Convert to summary format
    return [
        TransactionSummary(
            id=tx.id,
            merchant_name=tx.merchant_name,
            amount=tx.amount,
            currency=tx.currency,
            transaction_date=tx.transaction_date,
            category=tx.category,
            email_snippet=tx.email_snippet,
            created_at=tx.created_at
        )
        for tx in transactions
    ]

@router.get("/summary")
def get_transaction_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get transaction summary statistics"""
    transaction_service = TransactionService(db)
    
    return transaction_service.get_transaction_summary(current_user.id)

@router.get("/categories")
def get_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[str]:
    """Get unique categories for user"""
    transaction_service = TransactionService(db)
    
    return transaction_service.get_categories(current_user.id)

@router.get("/{transaction_id}", response_model=Transaction)
def get_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Transaction:
    """Get specific transaction"""
    transaction_service = TransactionService(db)
    
    transaction = transaction_service.get_transaction(transaction_id)
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    # Check if transaction belongs to current user
    if transaction.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this transaction"
        )
    
    return transaction

@router.put("/{transaction_id}", response_model=Transaction)
def update_transaction(
    transaction_id: int,
    transaction_update: TransactionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Transaction:
    """Update transaction"""
    transaction_service = TransactionService(db)
    
    # Check if transaction exists and belongs to user
    existing_transaction = transaction_service.get_transaction(transaction_id)
    
    if not existing_transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    if existing_transaction.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this transaction"
        )
    
    # Update transaction
    updated_transaction = transaction_service.update_transaction(
        transaction_id, transaction_update
    )
    
    if not updated_transaction:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update transaction"
        )
    
    return updated_transaction

@router.delete("/{transaction_id}")
def delete_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """Delete transaction"""
    transaction_service = TransactionService(db)
    
    # Check if transaction exists and belongs to user
    existing_transaction = transaction_service.get_transaction(transaction_id)
    
    if not existing_transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    if existing_transaction.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this transaction"
        )
    
    # Delete transaction
    success = transaction_service.delete_transaction(transaction_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete transaction"
        )
    
    return {"message": "Transaction deleted successfully"}
