"""
Test utilities and helpers
==========================
"""
import os
import tempfile
import shutil
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import Mock, patch


class DatabaseMockHelper:
    """Veritabanı mock yardımcısı"""
    
    @staticmethod
    def create_mock_cursor(fetchone_result=None, fetchall_result=None):
        """Mock cursor oluşturur"""
        cursor = Mock()
        cursor.fetchone.return_value = fetchone_result
        cursor.fetchall.return_value = fetchall_result or []
        cursor.description = [["id"], ["name"], ["value"]]
        return cursor
    
    @staticmethod
    def create_mock_connection(cursor=None):
        """Mock connection oluşturur"""
        connection = Mock()
        connection.execute.return_value = cursor or DatabaseMockHelper.create_mock_cursor()
        return connection


class FileSystemTestHelper:
    """Dosya sistemi test yardımcısı"""
    
    @staticmethod
    @contextmanager
    def temporary_directory():
        """Geçici dizin oluşturur"""
        temp_dir = tempfile.mkdtemp()
        try:
            yield Path(temp_dir)
        finally:
            shutil.rmtree(temp_dir)
    
    @staticmethod
    @contextmanager
    def temporary_config_file(config_data):
        """Geçici config dosyası oluşturur"""
        import json
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name
        
        try:
            yield Path(temp_path)
        finally:
            os.unlink(temp_path)


class EnvironmentTestHelper:
    """Environment variable test yardımcısı"""
    
    @staticmethod
    @contextmanager
    def temporary_env_vars(**env_vars):
        """Geçici environment variables ayarlar"""
        original_values = {}
        
        # Mevcut değerleri sakla ve yenilerini ayarla
        for key, value in env_vars.items():
            original_values[key] = os.environ.get(key)
            os.environ[key] = value
        
        try:
            yield
        finally:
            # Orijinal değerleri geri yükle
            for key, original_value in original_values.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value


class UITestHelper:
    """UI test yardımcısı"""
    
    @staticmethod
    def create_mock_widget():
        """Mock QWidget oluşturur"""
        widget = Mock()
        widget.setEnabled = Mock()
        widget.setText = Mock()
        widget.text = Mock(return_value="")
        widget.clear = Mock()
        return widget
    
    @staticmethod
    def create_mock_table():
        """Mock QTableWidget oluşturur"""
        table = Mock()
        table.setRowCount = Mock()
        table.setColumnCount = Mock()
        table.setItem = Mock()
        table.item = Mock()
        table.rowCount = Mock(return_value=0)
        return table


class DataTestHelper:
    """Test verileri yardımcısı"""
    
    @staticmethod
    def create_sample_order(order_no="TEST001", **kwargs):
        """Örnek sipariş verisi oluşturur"""
        default_order = {
            "order_no": order_no,
            "customer": "Test Customer",
            "status": 1,
            "created_at": "2025-01-01",
            "warehouse_id": 0
        }
        default_order.update(kwargs)
        return default_order
    
    @staticmethod
    def create_sample_order_lines(count=3):
        """Örnek sipariş satırları oluşturur"""
        lines = []
        for i in range(count):
            lines.append({
                "item_code": f"ITEM{i+1:03d}",
                "qty_ordered": (i + 1) * 10,
                "qty_scanned": (i + 1) * 5,
                "warehouse_id": i % 2
            })
        return lines
    
    @staticmethod
    def create_sample_barcode_data():
        """Örnek barkod verisi oluşturur"""
        return {
            "barcode": "1234567890123",
            "item_code": "ITEM001",
            "multiplier": 1.0,
            "warehouse_id": 0
        }


class AssertionHelper:
    """Assertion yardımcıları"""
    
    @staticmethod
    def assert_dict_contains(actual_dict, expected_subset):
        """Dictionary'nin belirli key-value'ları içerdiğini kontrol eder"""
        for key, expected_value in expected_subset.items():
            assert key in actual_dict, f"Key '{key}' not found in dict"
            assert actual_dict[key] == expected_value, \
                f"Expected {key}={expected_value}, got {actual_dict[key]}"
    
    @staticmethod
    def assert_called_with_sql_containing(mock_execute, sql_fragment):
        """Mock execute'un belirli SQL fragment'ı içeren çağrı aldığını kontrol eder"""
        assert mock_execute.called, "execute() was not called"
        
        for call in mock_execute.call_args_list:
            sql_query = call[0][0]  # İlk argument SQL query
            if sql_fragment.upper() in sql_query.upper():
                return True
        
        raise AssertionError(f"No execute() call found containing '{sql_fragment}'")


# Test kategorileri için marker'lar
def slow_test(func):
    """Yavaş test marker'ı"""
    return pytest.mark.slow(func)


def database_test(func):
    """Veritabanı test marker'ı"""
    return pytest.mark.database(func)


def ui_test(func):
    """UI test marker'ı"""
    return pytest.mark.ui(func)