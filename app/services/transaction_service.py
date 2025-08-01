from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_, func
from datetime import datetime, timedelta, timezone
from math import ceil

from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate, TransactionUpdate, TransactionList

class TransactionService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_transaction(self, transaction_create: TransactionCreate) -> Transaction:
        """Create new transaction"""
        db_transaction = Transaction(**transaction_create.model_dump())
        self.db.add(db_transaction)
        self.db.commit()
        self.db.refresh(db_transaction)
        return db_transaction
    
    def get_transaction(self, transaction_id: int) -> Optional[Transaction]:
        """Get transaction by ID"""
        return self.db.query(Transaction).filter(Transaction.id == transaction_id).first()
    
    def update_transaction(self, transaction_id: int, transaction_update: TransactionUpdate) -> Optional[Transaction]:
        """Update transaction"""
        db_transaction = self.get_transaction(transaction_id)
        if not db_transaction:
            return None
        
        update_data = transaction_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_transaction, field, value)
        
        self.db.commit()
        self.db.refresh(db_transaction)
        return db_transaction
    
    def delete_transaction(self, transaction_id: int) -> bool:
        """Delete transaction"""
        db_transaction = self.get_transaction(transaction_id)
        if not db_transaction:
            return False
        
        self.db.delete(db_transaction)
        self.db.commit()
        return True
    
    def get_user_transactions(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        category: str = None,
        date_from: datetime = None,
        date_to: datetime = None,
        search: str = None,
        processed_only: bool = True
    ) -> TransactionList:
        """Get transactions for a user with filtering"""
        
        query = self.db.query(Transaction).filter(Transaction.user_id == user_id)
        
        if processed_only:
            query = query.filter(Transaction.is_processed == True)
        
        if category:
            query = query.filter(Transaction.category == category)
        
        if date_from:
            query = query.filter(Transaction.transaction_date >= date_from)
        
        if date_to:
            query = query.filter(Transaction.transaction_date <= date_to)
        
        if search:
            search_filter = or_(
                Transaction.merchant_name.ilike(f"%{search}%"),
                Transaction.description.ilike(f"%{search}%"),
                Transaction.email_subject.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)
        
        # Get total count
        total = query.count()
        
        # Get paginated results
        transactions = (
            query
            .order_by(desc(Transaction.transaction_date), desc(Transaction.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
        
        pages = ceil(total / limit) if limit > 0 else 1
        page = (skip // limit) + 1 if limit > 0 else 1
        
        return TransactionList(
            transactions=transactions,
            total=total,
            page=page,
            size=limit,
            pages=pages
        )
    
    def get_recent_transactions(self, user_id: int, limit: int = 15) -> List[Transaction]:
        """Get recent transactions for dashboard"""
        return (
            self.db.query(Transaction)
            .filter(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.is_processed == True
                )
            )
            .order_by(desc(Transaction.transaction_date), desc(Transaction.created_at))
            .limit(limit)
            .all()
        )
    
    def get_transaction_summary(self, user_id: int) -> Dict[str, Any]:
        """Get transaction summary statistics"""
        # Total transactions
        total_transactions = (
            self.db.query(Transaction)
            .filter(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.is_processed == True
                )
            )
            .count()
        )
        
        # Total amount
        total_amount = (
            self.db.query(func.sum(Transaction.amount))
            .filter(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.is_processed == True,
                    Transaction.amount.isnot(None)
                )
            )
            .scalar() or 0
        )
        
        # This month's transactions
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        month_transactions = (
            self.db.query(Transaction)
            .filter(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.is_processed == True,
                    Transaction.transaction_date >= month_start
                )
            )
            .count()
        )
        
        month_amount = (
            self.db.query(func.sum(Transaction.amount))
            .filter(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.is_processed == True,
                    Transaction.transaction_date >= month_start,
                    Transaction.amount.isnot(None)
                )
            )
            .scalar() or 0
        )
        
        # Category breakdown
        category_stats = (
            self.db.query(
                Transaction.category,
                func.count(Transaction.id).label('count'),
                func.sum(Transaction.amount).label('total')
            )
            .filter(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.is_processed == True,
                    Transaction.category.isnot(None)
                )
            )
            .group_by(Transaction.category)
            .all()
        )
        
        categories = [{
            'category': stat.category,
            'count': stat.count,
            'total': float(stat.total or 0)
        } for stat in category_stats]
        
        return {
            'total_transactions': total_transactions,
            'total_amount': float(total_amount),
            'month_transactions': month_transactions,
            'month_amount': float(month_amount),
            'categories': categories
        }
    
    def get_categories(self, user_id: int) -> List[str]:
        """Get unique categories for user"""
        categories = (
            self.db.query(Transaction.category)
            .filter(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.category.isnot(None)
                )
            )
            .distinct()
            .all()
        )
        
        return [cat.category for cat in categories if cat.category]
    
    def count_user_transactions(self, user_id: int) -> int:
        """Count total transactions for user"""
        return (
            self.db.query(Transaction)
            .filter(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.is_processed == True
                )
            )
            .count()
        )
