from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.mongodb import connect_to_mongo, close_mongo_connection
from app.core.database import engine, Base
import app.db.models # Ensure models are loaded
from app.api.v1.api import api_router
import logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup sequence: Connect to databases safely
    logger.info("Starting up CityFlowX Backend...")
    try:
        connect_to_mongo()
    except Exception as e:
        logger.warning(f"MongoDB connection skipped or failed: {e}")
    try:
        # Create DB tables (users, etc.) in Supabase PostgreSQL
        Base.metadata.create_all(bind=engine)
        logger.info("Supabase PostgreSQL tables created/verified successfully.")
    except Exception as e:
        logger.warning(f"PostgreSQL table creation skipped or failed: {e}")
    yield
    # Shutdown sequence
    logger.info("Shutting down CityFlowX Backend...")
    try:
        close_mongo_connection()
    except Exception as e:
        logger.warning(f"Error closing MongoDB connection: {e}")

app = FastAPI(
    title="CityFlowX AI",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    description="CityFlowX - Smart City Urban Traffic AI & Autonomous Signal Control",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for dev flexibility
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {
        "message": "Welcome to CityFlowX API",
        "docs": "/docs",
        "version": "1.0.0"
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "CityFlowX AI",
        "api_version": settings.API_V1_STR
    }
