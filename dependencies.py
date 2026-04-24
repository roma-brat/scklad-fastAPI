"""
Dependencies для FastAPI роутов
"""
from fastapi import Request
from database import DatabaseManager
from models import User


def get_db(request: Request) -> DatabaseManager:
    """Получение экземпляра DatabaseManager из приложения"""
    from main import db_manager
    return db_manager


def get_current_user(request: Request, db: DatabaseManager = None) -> dict | None:
    """Получение текущего пользователя из cookie (возвращает dict)"""
    if db is None:
        db = get_db(request)
    
    user_id = request.cookies.get("session_id")
    if not user_id:
        return None
    
    try:
        user = db.get_user_by_id(int(user_id))
        if not user:
            return None
        
        # Преобразуем ORM объект в dict чтобы избежать DetachedInstanceError
        return {
            "id": user.id,
            "username": user.username,
            "login": user.login,
            "role": str(user.role),
            "workstation": user.workstation,
            "workstations": user.workstations,
            "is_active": user.is_active,
        }
    except (ValueError, TypeError, Exception):
        return None
