from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
from contextlib import asynccontextmanager

from app.config import settings
from app.database import create_tables
from app.routers import banks, fd_plans, excel_upload


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    print("Starting FD Management Application...")
    
    # Create upload directory if it doesn't exist
    upload_dir = settings.upload_folder
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir, exist_ok=True)
    
    # Create database tables
    try:
        create_tables()
        print("Database tables created successfully")
    except Exception as e:
        print(f"Error creating database tables: {e}")
    
    yield
    
    # Shutdown
    print("Shutting down FD Management Application...")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Fixed Deposit Management System with Bank Onboarding and Excel Upload",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled exceptions"""
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.detail,
                "error_type": "HTTPException"
            }
        )
    
    # Log the error for debugging
    print(f"Unhandled exception: {exc}")
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "error_type": "InternalServerError"
        }
    )


# Include routers
app.include_router(banks.router, prefix="/api")
app.include_router(fd_plans.router, prefix="/api")
app.include_router(excel_upload.router, prefix="/api")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with application information"""
    return {
        "success": True,
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "endpoints": {
            "banks": "/api/banks",
            "fd_plans": "/api/fd-plans",
            "excel_upload": "/api/excel"
        }
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "success": True,
        "status": "healthy",
        "version": settings.app_version
    }


# API info endpoint
@app.get("/api/info")
async def api_info():
    """API information endpoint"""
    return {
        "success": True,
        "message": "FD Management API",
        "version": settings.app_version,
        "features": [
            "Bank onboarding and management",
            "FD plan creation with conditional interest rates",
            "Excel upload for bulk FD plan creation",
            "Interest calculation based on withdrawal timing",
            "Comprehensive validation and error handling"
        ],
        "database": "PostgreSQL",
        "supported_file_formats": settings.allowed_file_extensions
    }


# Serve static files (for frontend if needed)
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )