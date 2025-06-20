"""
Unit tests for authentication system
===================================
"""
import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, mock_open

from app.core.auth import User, UserManager, SessionManager


class TestUser:
    """User sınıfı testleri"""
    
    @pytest.mark.unit
    def test_user_creation(self):
        """User oluşturma testi"""
        user_data = {
            'user_id': 1,
            'username': 'test_user',
            'full_name': 'Test User',
            'email': 'test@example.com',
            'role': 'operator',
            'warehouse_id': 0,
            'is_active': True,
            'created_at': '2025-01-01T00:00:00'
        }
        
        user = User(**user_data)
        
        assert user.username == 'test_user'
        assert user.full_name == 'Test User'
        assert user.role == 'operator'
        assert user.is_active is True
    
    @pytest.mark.unit
    def test_user_to_dict(self):
        """User to_dict testi"""
        user = User(
            user_id=1,
            username='test',
            full_name='Test User',
            email='test@example.com',
            role='admin',
            warehouse_id=0,
            is_active=True,
            created_at='2025-01-01'
        )
        
        user_dict = user.to_dict()
        
        assert isinstance(user_dict, dict)
        assert user_dict['username'] == 'test'
        assert user_dict['role'] == 'admin'
    
    @pytest.mark.unit
    def test_user_from_dict(self):
        """User from_dict testi"""
        user_data = {
            'user_id': 1,
            'username': 'test',
            'full_name': 'Test User',
            'email': 'test@example.com',
            'role': 'scanner',
            'warehouse_id': 1,
            'is_active': True,
            'created_at': '2025-01-01'
        }
        
        user = User.from_dict(user_data)
        
        assert user.username == 'test'
        assert user.warehouse_id == 1


class TestUserManager:
    """UserManager sınıfı testleri"""
    
    @pytest.mark.unit
    def test_user_manager_initialization(self):
        """UserManager başlatma testi"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            manager = UserManager(temp_path)
            
            # Default users oluşturulmalı
            assert len(manager.users) >= 3
            assert 'admin' in manager.users
            assert 'operator' in manager.users
            assert 'scanner' in manager.users
            
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    @pytest.mark.unit
    def test_get_user(self):
        """Kullanıcı alma testi"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            manager = UserManager(temp_path)
            
            # Mevcut kullanıcı
            admin_user = manager.get_user('admin')
            assert admin_user is not None
            assert admin_user.username == 'admin'
            assert admin_user.role == 'admin'
            
            # Olmayan kullanıcı
            non_existent = manager.get_user('nonexistent')
            assert non_existent is None
            
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    @pytest.mark.unit
    def test_authenticate_valid_user(self):
        """Geçerli kullanıcı doğrulama testi"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            manager = UserManager(temp_path)
            
            user = manager.authenticate('admin')
            
            assert user is not None
            assert user.username == 'admin'
            assert user.last_login is not None
            
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    @pytest.mark.unit
    def test_authenticate_invalid_user(self):
        """Geçersiz kullanıcı doğrulama testi"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            manager = UserManager(temp_path)
            
            # Olmayan kullanıcı
            user = manager.authenticate('nonexistent')
            assert user is None
            
            # Deaktif kullanıcı
            manager.deactivate_user('admin')
            user = manager.authenticate('admin')
            assert user is None
            
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    @pytest.mark.unit
    def test_add_user(self):
        """Kullanıcı ekleme testi"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            manager = UserManager(temp_path)
            initial_count = len(manager.users)
            
            new_user_data = {
                'username': 'new_user',
                'full_name': 'New User',
                'email': 'new@example.com',
                'role': 'operator',
                'warehouse_id': 1
            }
            
            user = manager.add_user(new_user_data)
            
            assert user.username == 'new_user'
            assert user.user_id > 0
            assert len(manager.users) == initial_count + 1
            assert 'new_user' in manager.users
            
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    @pytest.mark.unit
    def test_update_user(self):
        """Kullanıcı güncelleme testi"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            manager = UserManager(temp_path)
            
            # Mevcut kullanıcıyı güncelle
            result = manager.update_user('admin', {'full_name': 'Updated Admin'})
            assert result is True
            
            updated_user = manager.get_user('admin')
            assert updated_user.full_name == 'Updated Admin'
            
            # Olmayan kullanıcıyı güncelleme
            result = manager.update_user('nonexistent', {'full_name': 'Test'})
            assert result is False
            
        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestSessionManager:
    """SessionManager sınıfı testleri"""
    
    @pytest.mark.unit
    def test_session_manager_initialization(self):
        """SessionManager başlatma testi"""
        session_manager = SessionManager()
        
        assert session_manager.current_user is None
        assert session_manager.session_start is None
        assert not session_manager.is_authenticated()
    
    @pytest.mark.unit
    def test_successful_login(self):
        """Başarılı giriş testi"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            session_manager = SessionManager()
            session_manager.user_manager = UserManager(temp_path)
            
            result = session_manager.login('admin')
            
            assert result is True
            assert session_manager.is_authenticated()
            assert session_manager.current_user is not None
            assert session_manager.current_user.username == 'admin'
            assert session_manager.session_start is not None
            
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    @pytest.mark.unit
    def test_failed_login(self):
        """Başarısız giriş testi"""
        session_manager = SessionManager()
        
        result = session_manager.login('nonexistent')
        
        assert result is False
        assert not session_manager.is_authenticated()
        assert session_manager.current_user is None
    
    @pytest.mark.unit
    def test_logout(self):
        """Çıkış testi"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            session_manager = SessionManager()
            session_manager.user_manager = UserManager(temp_path)
            
            # Önce giriş yap
            session_manager.login('admin')
            assert session_manager.is_authenticated()
            
            # Çıkış yap
            session_manager.logout()
            assert not session_manager.is_authenticated()
            assert session_manager.current_user is None
            assert session_manager.session_start is None
            
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    @pytest.mark.unit
    def test_role_permissions(self):
        """Rol yetkileri testi"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            session_manager = SessionManager()
            session_manager.user_manager = UserManager(temp_path)
            
            # Admin yetkisi
            session_manager.login('admin')
            assert session_manager.has_role('admin')
            assert session_manager.has_permission('scan')
            assert session_manager.has_permission('print')
            
            # Operator yetkisi
            session_manager.login('operator')
            assert session_manager.has_role('operator')
            assert session_manager.has_permission('scan')
            assert session_manager.has_permission('print')
            
            # Scanner yetkisi
            session_manager.login('scanner')
            assert session_manager.has_role('scanner')
            assert session_manager.has_permission('scan')
            assert not session_manager.has_permission('print')
            
        finally:
            Path(temp_path).unlink(missing_ok=True)