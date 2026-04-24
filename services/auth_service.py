# services/auth_service.py
"""Сервис авторизации"""
from datetime import datetime, timedelta
from typing import Optional, Dict
import uuid
from models import User
from database import DatabaseManager

class Session:
    def __init__(self, user: User, session_id: str, expires_at: datetime):
        self.user = user
        self.session_id = session_id
        self.expires_at = expires_at
    
    def is_valid(self) -> bool:
        return datetime.utcnow() < self.expires_at and self.user.is_active
    
    def to_dict(self) -> dict:
        return {
            'session_id': self.session_id,
            'user': self.user.to_dict(),
            'expires_at': self.expires_at.isoformat()
        }

class AuthService:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.sessions: Dict[str, Session] = {}
        self.session_duration = timedelta(hours=8)
    
    def login(self, login: str, password: str) -> Optional[Session]:
        user = self.db.authenticate_user(login, password)
        if not user:
            return None
        
        session_id = str(uuid.uuid4())
        expires_at = datetime.utcnow() + self.session_duration
        session = Session(user, session_id, expires_at)
        self.sessions[session_id] = session
        
        self.db.log_audit(user_id=user.id, action='login', entity_type='user', entity_id=user.id)
        return session
    
    def logout(self, session_id: str):
        if session_id in self.sessions:
            session = self.sessions[session_id]
            self.db.log_audit(user_id=session.user.id, action='logout', entity_type='user', entity_id=session.user.id)
            del self.sessions[session_id]
    
    def get_session(self, session_id: str) -> Optional[Session]:
        session = self.sessions.get(session_id)
        if session and not session.is_valid():
            del self.sessions[session_id]
            return None
        return session
    
    def get_current_user(self, session_id: str) -> Optional[User]:
        session = self.get_session(session_id)
        return session.user if session else None
    
    def has_role(self, session_id: str, required_roles: list) -> bool:
        user = self.get_current_user(session_id)
        if not user:
            return False
        return user.role in required_roles
