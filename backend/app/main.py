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
        # Create DB tables (civilians, traffic_controllers, users) in Supabase PostgreSQL
        Base.metadata.create_all(bind=engine)
        logger.info("Supabase PostgreSQL tables created/verified successfully.")
        
        # Pre-seed default Traffic Controller account & setup Google Auth DB trigger
        from app.core.database import SessionLocal
        from app.api.v1.auth import init_default_controller
        from setup_trigger import setup_trigger
        
        db = SessionLocal()
        try:
            init_default_controller(db)
            logger.info("Default Traffic Controller pre-seeded into database.")
        finally:
            db.close()
            
        try:
            setup_trigger()
            logger.info("Supabase auth.users -> public.civilians database trigger verified.")
        except Exception as trigger_err:
            logger.warning(f"Trigger setup note: {trigger_err}")
    except Exception as e:
        logger.warning(f"PostgreSQL table creation/seeding skipped or failed: {e}")
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
