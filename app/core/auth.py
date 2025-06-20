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

# SQL tabanlı user management'ı import et
try:
    from app.core.user_db import DatabaseUserManager, User
    USE_DATABASE = True
    logger.info("Using SQL database for user management")
except Exception as e:
    logger.warning(f"Database user management not available, using file-based: {e}")
    USE_DATABASE = False
    
    # Fallback: File-based user management (eski sistem)
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
            """User'ı dictionary'ye çevir"""
            return asdict(self)
        
        @classmethod
        def from_dict(cls, data: Dict) -> 'User':
            """Dictionary'den User oluştur"""
            return cls(**data)


class UserManager:
    """Kullanıcı yönetimi sınıfı - SQL veya dosya tabanlı"""
    
    def __init__(self, users_file: str = "users.json"):
        if USE_DATABASE:
            self._db_manager = DatabaseUserManager()
            logger.info("Initialized SQL database user manager")
        else:
            # Fallback to file-based system
            self.users_file = Path(users_file)
            self.users: Dict[str, User] = {}
            self._load_users()
            self._create_default_users()
            logger.info("Initialized file-based user manager")
    
    def _load_users(self):
        """Kullanıcıları dosyadan yükle (sadece file-based sistemde)"""
        if USE_DATABASE:
            return
            
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
        """Kullanıcıları dosyaya kaydet (sadece file-based sistemde)"""
        if USE_DATABASE:
            return
            
        try:
            users_data = {username: user.to_dict() for username, user in self.users.items()}
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(users_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(self.users)} users to {self.users_file}")
        except Exception as e:
            logger.error(f"Error saving users: {e}")
    
    def _create_default_users(self):
        """Varsayılan kullanıcıları oluştur (sadece file-based sistemde)"""
        if USE_DATABASE:
            return
            
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
                    "full_name": "Barkod Okuyucu",
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
            logger.info("Created default users: admin, operator, scanner")
    
    def get_user(self, username: str) -> Optional[User]:
        """Kullanıcı al"""
        if USE_DATABASE:
            return self._db_manager.get_user(username)
        else:
            return self.users.get(username)
    
    def authenticate(self, username: str, password: str = None) -> Optional[User]:
        """Kullanıcı doğrula"""
        if USE_DATABASE:
            return self._db_manager.authenticate(username, password)
        else:
            # File-based authentication (password olmadan)
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
        if USE_DATABASE:
            return self._db_manager.get_all_users()
        else:
            return list(self.users.values())
    
    def add_user(self, user_data: Dict) -> User:
        """Yeni kullanıcı ekle"""
        if USE_DATABASE:
            return self._db_manager.create_user(user_data)
        else:
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
        if USE_DATABASE:
            return self._db_manager.update_user(username, updates)
        else:
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
    
    def change_password(self, username: str, new_password: str) -> bool:
        """Kullanıcı şifresini değiştir (sadece database sisteminde)"""
        if USE_DATABASE:
            return self._db_manager.change_password(username, new_password)
        else:
            logger.warning("Password change not supported in file-based system")
            return False


class SessionManager:
    """Session yönetimi sınıfı"""
    
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
            
            # Logger context'ini güncelle (circular import olmadan)
            try:
                from app.core.logger import WMSLogger
                for logger_instance in WMSLogger._loggers.values():
                    for handler in logger_instance.handlers:
                        for filter_obj in handler.filters:
                            if hasattr(filter_obj, 'set_user_context'):
                                filter_obj.set_user_context(user.username, str(user.user_id))
            except:
                pass  # Logger context set edilemezse önemli değil
            
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
        """Kullanıcının belirtilen rolü var mı"""
        if not self.is_authenticated():
            return False
        return self.current_user.role == role
    
    def has_permission(self, permission: str) -> bool:
        """Kullanıcının belirtilen yetkisi var mı"""
        if not self.is_authenticated():
            return False
        
        role = self.current_user.role
        
        # Admin her şeyi yapabilir
        if role == "admin":
            return True
        
        # Operator scan ve print yapabilir
        if role == "operator":
            return permission in ["scan", "print", "manage_orders"]
        
        # Scanner sadece scan yapabilir
        if role == "scanner":
            return permission == "scan"
        
        return False


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Global session manager'ı al"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


def get_current_user() -> Optional[Dict]:
    """Mevcut kullanıcıyı dictionary olarak al (backward compatibility)"""
    session_manager = get_session_manager()
    user = session_manager.get_current_user()
    if user:
        return user.to_dict()
    return None


def get_current_user_object() -> Optional[User]:
    """Mevcut kullanıcıyı User object olarak al"""
    session_manager = get_session_manager()
    return session_manager.get_current_user()


def is_authenticated() -> bool:
    """Kullanıcı giriş yapmış mı"""
    session_manager = get_session_manager()
    return session_manager.is_authenticated()


def has_permission(permission: str) -> bool:
    """Mevcut kullanıcının belirtilen yetkisi var mı"""
    session_manager = get_session_manager()
    return session_manager.has_permission(permission)