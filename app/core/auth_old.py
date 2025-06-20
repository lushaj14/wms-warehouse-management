"""
Kullanıcı Authentication ve Session Yönetimi
===========================================
"""
import hashlib
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict

from app.core.logger import get_logger
from app.core.exceptions import (
    AuthenticationException, InvalidUserException, InactiveUserException,
    FileSystemException, ValidationException
)

logger = get_logger(__name__)


@dataclass
class User:
    """Kullanıcı veri sınıfı"""
    user_id: int
    username: str
    full_name: str
    email: str
    role: str
    warehouse_id: int
    is_active: bool
    created_at: str
    last_login: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'User':
        return cls(**data)


class UserManager:
    """Kullanıcı yönetimi sınıfı"""
    
    def __init__(self, users_file: str = "users.json"):
        self.users_file = Path(users_file)
        self.users: Dict[str, User] = {}
        self._load_users()
        self._create_default_users()
    
    def _load_users(self):
        """Kullanıcıları dosyadan yükle"""
        if self.users_file.exists():
            try:
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    users_data = json.load(f)
                    for username, user_data in users_data.items():
                        self.users[username] = User.from_dict(user_data)
                logger.info(f"Loaded {len(self.users)} users from {self.users_file}")
            except Exception as e:
                logger.error(f"Error loading users: {e}")
    
    def _save_users(self):
        """Kullanıcıları dosyaya kaydet"""
        try:
            users_data = {username: user.to_dict() for username, user in self.users.items()}
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(users_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(self.users)} users to {self.users_file}")
        except Exception as e:
            logger.error(f"Error saving users: {e}")
    
    def _create_default_users(self):
        """Varsayılan kullanıcıları oluştur"""
        if not self.users:
            default_users = [
                {
                    "user_id": 1,
                    "username": "admin",
                    "full_name": "Sistem Yöneticisi",
                    "email": "admin@company.com",
                    "role": "admin",
                    "warehouse_id": 0,
                    "is_active": True,
                    "created_at": datetime.now().isoformat()
                },
                {
                    "user_id": 2,
                    "username": "operator",
                    "full_name": "Depo Operatörü",
                    "email": "operator@company.com",
                    "role": "operator",
                    "warehouse_id": 0,
                    "is_active": True,
                    "created_at": datetime.now().isoformat()
                },
                {
                    "user_id": 3,
                    "username": "scanner",
                    "full_name": "Barkod Tarayıcı",
                    "email": "scanner@company.com",
                    "role": "scanner",
                    "warehouse_id": 0,
                    "is_active": True,
                    "created_at": datetime.now().isoformat()
                }
            ]
            
            for user_data in default_users:
                user = User(**user_data)
                self.users[user.username] = user
            
            self._save_users()
            logger.info("Created default users")
    
    def get_user(self, username: str) -> Optional[User]:
        """Kullanıcı al"""
        return self.users.get(username)
    
    def authenticate(self, username: str, password: str = None) -> Optional[User]:
        """Kullanıcı doğrula (şimdilik password kontrolü yok)"""
        if not username or not username.strip():
            raise ValidationException("Kullanıcı adı boş olamaz", field="username")
        
        user = self.get_user(username)
        if not user:
            raise InvalidUserException(username)
        
        if not user.is_active:
            raise InactiveUserException(username)
        
        # Şimdilik basit authentication - production'da gerçek password kontrolü yapılmalı
        user.last_login = datetime.now().isoformat()
        self._save_users()
        logger.info(f"User authenticated: {username}")
        return user
    
    def get_all_users(self) -> List[User]:
        """Tüm kullanıcıları al"""
        return list(self.users.values())
    
    def add_user(self, user_data: Dict) -> User:
        """Yeni kullanıcı ekle"""
        user_data['user_id'] = max([u.user_id for u in self.users.values()], default=0) + 1
        user_data['created_at'] = datetime.now().isoformat()
        user_data['is_active'] = True
        
        user = User(**user_data)
        self.users[user.username] = user
        self._save_users()
        
        logger.info(f"New user added: {user.username}")
        return user
    
    def update_user(self, username: str, updates: Dict) -> bool:
        """Kullanıcı güncelle"""
        if username in self.users:
            user = self.users[username]
            for key, value in updates.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            self._save_users()
            logger.info(f"User updated: {username}")
            return True
        return False
    
    def deactivate_user(self, username: str) -> bool:
        """Kullanıcıyı deaktive et"""
        return self.update_user(username, {'is_active': False})


class SessionManager:
    """Session yönetimi"""
    
    def __init__(self):
        self.current_user: Optional[User] = None
        self.session_start: Optional[datetime] = None
        self.user_manager = UserManager()
    
    def login(self, username: str, password: str = None) -> bool:
        """Kullanıcı girişi"""
        try:
            user = self.user_manager.authenticate(username, password)
            self.current_user = user
            self.session_start = datetime.now()
            
            # Session bilgilerini logla
            from app.core.logger import log_user_action
            log_user_action(
                "LOGIN",
                f"User logged in successfully",
                username=user.username,
                user_id=user.user_id,
                role=user.role,
                warehouse_id=user.warehouse_id
            )
            return True
        except (AuthenticationException, ValidationException):
            # Bu exception'lar UI katmanında handle edilecek
            raise
        except Exception as e:
            # Beklenmeyen exception'ı wrap et
            logger.exception(f"Unexpected error during login: {str(e)}")
            raise AuthenticationException(
                f"Giriş sırasında beklenmeyen hata: {str(e)}",
                original_exception=e
            )
    
    def logout(self):
        """Kullanıcı çıkışı"""
        if self.current_user:
            from app.core.logger import log_user_action
            log_user_action(
                "LOGOUT",
                f"User logged out",
                session_duration=str(datetime.now() - self.session_start) if self.session_start else "unknown"
            )
            
            self.current_user = None
            self.session_start = None
    
    def get_current_user(self) -> Optional[User]:
        """Mevcut kullanıcıyı al"""
        return self.current_user
    
    def is_authenticated(self) -> bool:
        """Kullanıcı giriş yapmış mı"""
        return self.current_user is not None
    
    def has_role(self, role: str) -> bool:
        """Kullanıcının belirli rolü var mı"""
        return self.current_user and self.current_user.role == role
    
    def has_permission(self, permission: str) -> bool:
        """Kullanıcının belirli yetkisi var mı"""
        if not self.current_user:
            return False
        
        # Role-based permissions
        role_permissions = {
            'admin': ['all'],
            'operator': ['scan', 'print', 'view_orders', 'complete_orders'],
            'scanner': ['scan', 'view_orders']
        }
        
        user_permissions = role_permissions.get(self.current_user.role, [])
        return 'all' in user_permissions or permission in user_permissions


# Global session manager
_session_manager = SessionManager()


def get_session_manager() -> SessionManager:
    """Session manager'ı al"""
    return _session_manager


def get_current_user() -> Optional[Dict]:
    """Mevcut kullanıcıyı dict olarak al (logging için)"""
    user = _session_manager.get_current_user()
    return user.to_dict() if user else None


def require_login(func):
    """Login gerektiren fonksiyonlar için decorator"""
    def wrapper(*args, **kwargs):
        if not _session_manager.is_authenticated():
            raise PermissionError("Login required")
        return func(*args, **kwargs)
    return wrapper


def require_permission(permission: str):
    """Belirli yetki gerektiren fonksiyonlar için decorator"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not _session_manager.has_permission(permission):
                raise PermissionError(f"Permission required: {permission}")
            return func(*args, **kwargs)
        return wrapper
    return decorator