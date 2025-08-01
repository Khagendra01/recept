from fastapi import APIRouter

from app.api.v1 import auth, transactions, bank_transactions, emails

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
api_router.include_router(bank_transactions.router, prefix="/bank-transactions", tags=["bank-transactions"])
api_router.include_router(emails.router, prefix="/emails", tags=["emails"])
