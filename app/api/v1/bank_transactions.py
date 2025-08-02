from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.api.deps import get_db, get_current_user
from app.schemas.bank_transaction import (
    BankTransactionList, 
    CSVUploadResponse,
    ComparisonResult
)
from app.services.bank_transaction_service import BankTransactionService
from app.models.user import User

router = APIRouter()

@router.get("/", response_model=BankTransactionList)
def get_bank_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    batch_id: str = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> BankTransactionList:
    """Get user's bank transactions"""
    bank_service = BankTransactionService(db)
    
    return bank_service.get_user_bank_transactions(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        batch_id=batch_id
    )

@router.post("/upload-csv", response_model=CSVUploadResponse)
async def upload_bank_statement_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> CSVUploadResponse:
    """Upload bank statement CSV file"""
    
    # Validate file type
    if not file.filename.lower().endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are allowed"
        )
    
    # Check file size (10MB limit)
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    content = await file.read()
    
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size too large. Maximum 10MB allowed."
        )
    
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file uploaded"
        )
    
    bank_service = BankTransactionService(db)
    
    try:
        result = await bank_service.process_csv_upload(
            user_id=current_user.id,
            csv_content=content
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process CSV file: {str(e)}"
        )

@router.get("/compare", response_model=ComparisonResult)
def compare_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ComparisonResult:
    """Compare ledger transactions with bank transactions"""
    bank_service = BankTransactionService(db)
    
    try:
        result = bank_service.compare_transactions(current_user.id)
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare transactions: {str(e)}"
        )

@router.post("/detect-duplicates")
def detect_and_merge_duplicates(
    batch_id: str = Query(None, description="Optional batch ID to limit duplicate detection to specific upload"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Detect and merge duplicate transactions using AI-powered analysis"""
    bank_service = BankTransactionService(db)
    
    try:
        result = bank_service.detect_and_merge_duplicates(
            user_id=current_user.id,
            batch_id=batch_id
        )
        
        return {
            "message": "Duplicate detection completed successfully",
            "summary": result["summary"],
            "merged_transactions": result["merged_transactions"]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detect and merge duplicates: {str(e)}"
        )

@router.get("/compare-improved", response_model=ComparisonResult)
def compare_transactions_improved(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ComparisonResult:
    """Compare ledger transactions with bank transactions using improved matching"""
    bank_service = BankTransactionService(db)
    
    try:
        result = bank_service.improved_match_transactions(current_user.id)
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare transactions: {str(e)}"
        )

@router.post("/sample-data", response_model=CSVUploadResponse)
def generate_sample_ledger_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> CSVUploadResponse:
    """Generate sample ledger transactions for dashboard demonstration"""
    bank_service = BankTransactionService(db)
    
    try:
        result = bank_service.generate_sample_bank_transactions(current_user.id)
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate sample data: {str(e)}"
        )

@router.post("/sample-comparison", response_model=ComparisonResult)
def generate_sample_comparison_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ComparisonResult:
    """Generate sample comparison data with 8-10 transactions where 3 should match"""
    bank_service = BankTransactionService(db)
    
    try:
        result = bank_service.generate_sample_comparison_data(current_user.id)
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate sample comparison data: {str(e)}"
        )

@router.get("/batches")
def get_upload_batches(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get upload batches for user"""
    bank_service = BankTransactionService(db)
    
    try:
        # Get all bank transactions for user
        transactions = bank_service.get_user_bank_transactions(
            user_id=current_user.id,
            skip=0,
            limit=1000
        )
        
        # Group by batch_id
        batches = {}
        for tx in transactions.transactions:
            batch_id = tx.upload_batch_id
            if batch_id not in batches:
                batches[batch_id] = {
                    "batch_id": batch_id,
                    "count": 0,
                    "total_amount": 0,
                    "date_range": {"start": None, "end": None}
                }
            
            batches[batch_id]["count"] += 1
            if tx.amount:
                batches[batch_id]["total_amount"] += tx.amount
            
            if tx.date:
                if not batches[batch_id]["date_range"]["start"] or tx.date < batches[batch_id]["date_range"]["start"]:
                    batches[batch_id]["date_range"]["start"] = tx.date
                if not batches[batch_id]["date_range"]["end"] or tx.date > batches[batch_id]["date_range"]["end"]:
                    batches[batch_id]["date_range"]["end"] = tx.date
        
        return {
            "batches": list(batches.values()),
            "total_batches": len(batches)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get upload batches: {str(e)}"
        )
