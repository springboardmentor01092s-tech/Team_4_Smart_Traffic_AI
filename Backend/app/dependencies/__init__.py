"""
app/dependencies/__init__.py
"""
from app.dependencies.auth import get_current_user, require_role

__all__ = ["get_current_user", "require_role"]
