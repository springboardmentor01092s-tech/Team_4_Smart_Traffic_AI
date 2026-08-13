from fastapi import APIRouter
from app.api.v1 import traffic, auth

api_router = APIRouter()
api_router.include_router(traffic.router, prefix="/traffic", tags=["traffic"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
