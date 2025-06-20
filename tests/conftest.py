"""
Test configuration and fixtures
===============================
"""
import os
import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import tempfile


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Test ortamını hazırlar - her test session'ında bir kez çalışır"""
    # Test için environment variables ayarla
    test_env = {
        "LOGO_SQL_SERVER": "test_server,1433",
        "LOGO_SQL_DB": "test_db",
        "LOGO_SQL_USER": "test_user", 
        "LOGO_SQL_PASSWORD": "test_password",
        "LOGO_COMPANY_NR": "999",
        "LOGO_PERIOD_NR": "01"
    }
    
    for key, value in test_env.items():
        os.environ[key] = value
    
    yield
    
    # Cleanup
    for key in test_env.keys():
        if key in os.environ:
            del os.environ[key]


@pytest.fixture
def mock_db_connection():
    """Mock database connection fixture"""
    with patch('app.dao.logo.get_conn') as mock_conn:
        mock_context = Mock()
        mock_conn.return_value.__enter__ = Mock(return_value=mock_context)
        mock_conn.return_value.__exit__ = Mock(return_value=None)
        yield mock_context


@pytest.fixture
def mock_db_cursor():
    """Mock database cursor fixture"""
    cursor = Mock()
    cursor.fetchone.return_value = None
    cursor.fetchall.return_value = []
    cursor.description = [["id"], ["name"], ["value"]]
    return cursor


@pytest.fixture
def sample_order_data():
    """Sample order data for testing"""
    return {
        "order_no": "TEST001",
        "customer": "Test Customer",
        "status": 1,
        "order_lines": [
            {
                "item_code": "ITEM001",
                "qty_ordered": 10,
                "qty_scanned": 5,
                "warehouse_id": 0
            },
            {
                "item_code": "ITEM002", 
                "qty_ordered": 20,
                "qty_scanned": 0,
                "warehouse_id": 1
            }
        ]
    }


@pytest.fixture
def temp_config_file():
    """Geçici config dosyası oluşturur"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config_data = {
            "ui": {
                "theme": "light",
                "font_pt": 10
            },
            "db": {
                "retry": 3
            }
        }
        import json
        json.dump(config_data, f)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    os.unlink(temp_path)


@pytest.fixture
def mock_settings():
    """Mock settings fixture"""
    with patch('app.settings.get') as mock_get:
        mock_get.side_effect = lambda key, default=None: {
            "ui.theme": "light",
            "ui.font_pt": 10,
            "ui.sounds.enabled": True,
            "ui.sounds.volume": 0.9,
            "db.retry": 3,
            "db.heartbeat": 10
        }.get(key, default)
        yield mock_get


@pytest.fixture
def mock_toast():
    """Mock toast notifications"""
    with patch('app.toast.show') as mock_show:
        yield mock_show


@pytest.fixture
def mock_sound_effects():
    """Mock sound effects"""
    with patch('app.ui.pages.scanner_page.snd_ok') as mock_ok, \
         patch('app.ui.pages.scanner_page.snd_err') as mock_err, \
         patch('app.ui.pages.scanner_page.snd_dupe') as mock_dupe:
        yield {
            'ok': mock_ok,
            'err': mock_err, 
            'dupe': mock_dupe
        }


# Test Helpers
class TestDataFactory:
    """Test data factory"""
    
    @staticmethod
    def create_order(order_no="TEST001", customer="Test Customer", status=1):
        return {
            "order_no": order_no,
            "customer": customer,
            "status": status,
            "created_at": "2025-01-01"
        }
    
    @staticmethod
    def create_order_line(item_code="ITEM001", qty_ordered=10, qty_scanned=0):
        return {
            "item_code": item_code,
            "qty_ordered": qty_ordered,
            "qty_scanned": qty_scanned,
            "warehouse_id": 0
        }
    
    @staticmethod
    def create_barcode_data(barcode="123456", item_code="ITEM001", multiplier=1):
        return {
            "barcode": barcode,
            "item_code": item_code,
            "multiplier": multiplier,
            "warehouse_id": 0
        }