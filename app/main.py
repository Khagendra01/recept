import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine

from app.api.v1.api import api_router
from app.core.config import settings
from app.db.session import engine
from app.db.base import Base

# Create tables
Base.metadata.create_all(bind=engine)

# For Vercel deployment, we'll disable background tasks in production
if settings.DEBUG:
    from app.services.background_tasks import background_service
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        print("Starting up Receipt Processing API...")
        
        # Start background email polling
        task = asyncio.create_task(background_service.start_email_polling())
        
        yield
        
        # Shutdown
        print("Shutting down Receipt Processing API...")
        background_service.stop_email_polling()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="AI-powered receipt processing and bank statement comparison API",
        version="1.0.0",
        lifespan=lifespan
    )
else:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="AI-powered receipt processing and bank statement comparison API",
        version="1.0.0"
    )

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {
        "message": "Receipt Processing API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
def health_check():
    import datetime
    return {
        "status": "healthy",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
    }

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.DEBUG else "An unexpected error occurred"
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=settings.DEBUG
    )
