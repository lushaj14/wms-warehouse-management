"""
SQL Database User Management
===========================

Kullanıcı yönetimi için SQL Server tablosu ve işlemleri.
"""

import hashlib
import json
from datetime import datetime
from typing import Dict, Optional, List
from dataclasses import dataclass

from app.dao.logo import get_conn, exec_sql, fetch_one, fetch_all
from app.core.logger import get_logger
from app.core.exceptions import (
    DatabaseException, InvalidUserException, InactiveUserException,
    ValidationException
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
    password_hash: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """User'ı dictionary'ye çevir (password_hash hariç)"""
        data = {
            'user_id': self.user_id,
            'username': self.username,
            'full_name': self.full_name,
            'email': self.email,
            'role': self.role,
            'warehouse_id': self.warehouse_id,
            'is_active': self.is_active,
            'created_at': self.created_at,
            'last_login': self.last_login
        }
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'User':
        """Dictionary'den User oluştur"""
        return cls(**data)


class DatabaseUserManager:
    """SQL Database tabanlı kullanıcı yönetimi"""
    
    def __init__(self):
        self.table_name = "WMS_USERS"
        self._ensure_table_exists()
        self._create_default_admin()
    
    def _ensure_table_exists(self):
        """WMS_USERS tablosunu oluştur (yoksa)"""
        create_table_sql = f"""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='{self.table_name}' AND xtype='U')
        CREATE TABLE {self.table_name} (
            user_id INT IDENTITY(1,1) PRIMARY KEY,
            username NVARCHAR(50) UNIQUE NOT NULL,
            full_name NVARCHAR(100) NOT NULL,
            email NVARCHAR(100),
            password_hash NVARCHAR(255) NOT NULL,
            role NVARCHAR(20) NOT NULL DEFAULT 'operator',
            warehouse_id INT NOT NULL DEFAULT 0,
            is_active BIT NOT NULL DEFAULT 1,
            created_at DATETIME NOT NULL DEFAULT GETDATE(),
            last_login DATETIME NULL,
            updated_at DATETIME NULL
        )
        """
        
        try:
            exec_sql(create_table_sql)
            logger.info(f"Table {self.table_name} checked/created successfully")
        except Exception as e:
            logger.error(f"Error creating table {self.table_name}: {e}")
            raise DatabaseException(f"Kullanıcı tablosu oluşturulamadı: {str(e)}")
    
    def _create_default_admin(self):
        """Varsayılan admin kullanıcısını oluştur"""
        try:
            # Admin kullanıcısı var mı kontrol et
            admin_exists = self.get_user("admin")
            if admin_exists:
                logger.info("Admin user already exists")
                return
            
            # Admin kullanıcısını oluştur
            admin_data = {
                "username": "admin",
                "full_name": "Sistem Yöneticisi",
                "email": "admin@company.com",
                "password": "hakan14",
                "role": "admin",
                "warehouse_id": 0
            }
            
            self.create_user(admin_data)
            logger.info("Default admin user created with username: admin, password: hakan14")
            
        except Exception as e:
            logger.error(f"Error creating default admin user: {e}")
    
    def _hash_password(self, password: str) -> str:
        """Şifreyi hash'le"""
        # SHA-256 kullanıyoruz (production'da bcrypt kullanılmalı)
        return hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Şifreyi doğrula"""
        return self._hash_password(password) == password_hash
    
    def get_user(self, username: str) -> Optional[User]:
        """Kullanıcıyı username ile al"""
        if not username:
            return None
        
        try:
            sql = f"""
            SELECT user_id, username, full_name, email, role, warehouse_id, 
                   is_active, created_at, last_login, password_hash
            FROM {self.table_name}
            WHERE username = ?
            """
            
            row = fetch_one(sql, username)
            if row:
                user_data = {
                    'user_id': row['user_id'],
                    'username': row['username'],
                    'full_name': row['full_name'],
                    'email': row['email'],
                    'role': row['role'],
                    'warehouse_id': row['warehouse_id'],
                    'is_active': bool(row['is_active']),
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                    'last_login': row['last_login'].isoformat() if row['last_login'] else None,
                    'password_hash': row['password_hash']
                }
                return User(**user_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting user {username}: {e}")
            raise DatabaseException(f"Kullanıcı bilgisi alınamadı: {str(e)}")
    
    def authenticate(self, username: str, password: str = None) -> Optional[User]:
        """Kullanıcı doğrula"""
        if not username or not username.strip():
            raise ValidationException("Kullanıcı adı boş olamaz", field="username")
        
        user = self.get_user(username)
        if not user:
            raise InvalidUserException(username)
        
        if not user.is_active:
            raise InactiveUserException(username)
        
        # Şifre kontrolü (verilmişse)
        if password and user.password_hash:
            if not self._verify_password(password, user.password_hash):
                raise InvalidUserException(username)
        
        # Last login güncelle
        self.update_last_login(username)
        
        logger.info(f"User authenticated: {username}")
        return user
    
    def create_user(self, user_data: Dict) -> User:
        """Yeni kullanıcı oluştur"""
        required_fields = ['username', 'full_name', 'password']
        for field in required_fields:
            if not user_data.get(field):
                raise ValidationException(f"{field} alanı gerekli", field=field)
        
        # Kullanıcı zaten var mı kontrol et
        if self.get_user(user_data['username']):
            raise ValidationException(f"Kullanıcı adı '{user_data['username']}' zaten mevcut")
        
        try:
            password_hash = self._hash_password(user_data['password'])
            
            sql = f"""
            INSERT INTO {self.table_name} 
            (username, full_name, email, password_hash, role, warehouse_id, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            
            params = (
                user_data['username'],
                user_data['full_name'],
                user_data.get('email', ''),
                password_hash,
                user_data.get('role', 'operator'),
                user_data.get('warehouse_id', 0),
                user_data.get('is_active', True)
            )
            
            exec_sql(sql, *params)
            
            # Oluşturulan kullanıcıyı getir
            new_user = self.get_user(user_data['username'])
            logger.info(f"New user created: {user_data['username']}")
            return new_user
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise DatabaseException(f"Kullanıcı oluşturulamadı: {str(e)}")
    
    def update_user(self, username: str, updates: Dict) -> bool:
        """Kullanıcı güncelle"""
        if not self.get_user(username):
            return False
        
        try:
            # Güncellenebilir alanlar
            allowed_fields = ['full_name', 'email', 'role', 'warehouse_id', 'is_active']
            update_parts = []
            params = []
            
            for field, value in updates.items():
                if field in allowed_fields:
                    update_parts.append(f"{field} = ?")
                    params.append(value)
                elif field == 'password':
                    update_parts.append("password_hash = ?")
                    params.append(self._hash_password(value))
            
            if not update_parts:
                return False
            
            update_parts.append("updated_at = GETDATE()")
            params.append(username)
            
            sql = f"""
            UPDATE {self.table_name}
            SET {', '.join(update_parts)}
            WHERE username = ?
            """
            
            exec_sql(sql, *params)
            logger.info(f"User updated: {username}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating user {username}: {e}")
            raise DatabaseException(f"Kullanıcı güncellenemedi: {str(e)}")
    
    def update_last_login(self, username: str) -> bool:
        """Last login zamanını güncelle"""
        try:
            sql = f"""
            UPDATE {self.table_name}
            SET last_login = GETDATE()
            WHERE username = ?
            """
            
            exec_sql(sql, username)
            return True
            
        except Exception as e:
            logger.error(f"Error updating last login for {username}: {e}")
            return False
    
    def get_all_users(self) -> List[User]:
        """Tüm kullanıcıları al"""
        try:
            sql = f"""
            SELECT user_id, username, full_name, email, role, warehouse_id, 
                   is_active, created_at, last_login
            FROM {self.table_name}
            ORDER BY created_at
            """
            
            rows = fetch_all(sql)
            users = []
            
            for row in rows:
                user_data = {
                    'user_id': row['user_id'],
                    'username': row['username'],
                    'full_name': row['full_name'],
                    'email': row['email'],
                    'role': row['role'],
                    'warehouse_id': row['warehouse_id'],
                    'is_active': bool(row['is_active']),
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                    'last_login': row['last_login'].isoformat() if row['last_login'] else None
                }
                users.append(User(**user_data))
            
            return users
            
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            raise DatabaseException(f"Kullanıcı listesi alınamadı: {str(e)}")
    
    def deactivate_user(self, username: str) -> bool:
        """Kullanıcıyı deaktive et"""
        return self.update_user(username, {'is_active': False})
    
    def activate_user(self, username: str) -> bool:
        """Kullanıcıyı aktive et"""
        return self.update_user(username, {'is_active': True})
    
    def change_password(self, username: str, new_password: str) -> bool:
        """Kullanıcı şifresini değiştir"""
        if not new_password or len(new_password) < 4:
            raise ValidationException("Şifre en az 4 karakter olmalı", field="password")
        
        return self.update_user(username, {'password': new_password})
    
    def delete_user(self, username: str) -> bool:
        """Kullanıcıyı sil (dikkatli kullanın!)"""
        if username == "admin":
            raise ValidationException("Admin kullanıcısı silinemez")
        
        try:
            sql = f"DELETE FROM {self.table_name} WHERE username = ?"
            exec_sql(sql, username)
            logger.info(f"User deleted: {username}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting user {username}: {e}")
            raise DatabaseException(f"Kullanıcı silinemedi: {str(e)}")