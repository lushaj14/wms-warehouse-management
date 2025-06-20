"""
Unit tests for DAO layer
========================
"""
import pytest
from unittest.mock import patch, Mock
import pyodbc

from app.dao.logo import (
    _t, fetch_one, exec_sql, lookup_barcode,
    MAX_RETRY, RETRY_WAIT
)
from app.constants import DEFAULT_COMPANY_NR, DEFAULT_PERIOD_NR


class TestTableNameGeneration:
    """Tablo adı üretimi testleri"""
    
    def test_table_name_with_period(self):
        """Period'lu tablo adı testi"""
        result = _t("ORDERS")
        expected = f"LG_{DEFAULT_COMPANY_NR}_{DEFAULT_PERIOD_NR}_ORDERS"
        assert result == expected
    
    def test_table_name_without_period(self):
        """Period'suz tablo adı testi"""
        result = _t("COMPANIES", period_dependent=False)
        expected = f"LG_{DEFAULT_COMPANY_NR}_COMPANIES"
        assert result == expected


class TestDatabaseOperations:
    """Veritabanı operasyon testleri"""
    
    @pytest.mark.unit
    def test_fetch_one_success(self, mock_db_connection, mock_db_cursor):
        """Başarılı fetch_one testi"""
        # Mock setup
        mock_db_connection.execute.return_value = mock_db_cursor
        mock_db_cursor.fetchone.return_value = ("value1", "value2", "value3")
        
        # Test
        result = fetch_one("SELECT * FROM test_table")
        
        # Assertions
        assert result is not None
        assert isinstance(result, dict)
        mock_db_connection.execute.assert_called_once_with("SELECT * FROM test_table")
    
    @pytest.mark.unit
    def test_fetch_one_no_result(self, mock_db_connection, mock_db_cursor):
        """Sonuç bulunamayan fetch_one testi"""
        # Mock setup
        mock_db_connection.execute.return_value = mock_db_cursor
        mock_db_cursor.fetchone.return_value = None
        
        # Test
        result = fetch_one("SELECT * FROM empty_table")
        
        # Assertions
        assert result is None
    
    @pytest.mark.unit
    def test_exec_sql_success(self, mock_db_connection):
        """Başarılı exec_sql testi"""
        # Test
        exec_sql("INSERT INTO test_table VALUES (?, ?)", "value1", "value2")
        
        # Assertions
        mock_db_connection.execute.assert_called_once_with(
            "INSERT INTO test_table VALUES (?, ?)", "value1", "value2"
        )
    
    @pytest.mark.unit
    def test_database_retry_mechanism(self):
        """Veritabanı retry mekanizması testi"""
        with patch('app.dao.logo.pyodbc.connect') as mock_connect:
            # İlk 2 deneme başarısız, 3. başarılı
            mock_connect.side_effect = [
                pyodbc.Error("Connection failed"),
                pyodbc.Error("Connection failed"), 
                Mock()  # Başarılı connection
            ]
            
            with patch('app.dao.logo.time.sleep'):  # Sleep'i mock'la
                from app.dao.logo import get_conn
                
                # Test - retry mekanizması çalışmalı
                with get_conn() as conn:
                    assert conn is not None
                
                # 3 deneme yapılmalı
                assert mock_connect.call_count == 3


class TestBarcodeOperations:
    """Barkod operasyon testleri"""
    
    @pytest.mark.unit
    def test_lookup_barcode_found(self, mock_db_connection, mock_db_cursor):
        """Barkod bulundu testi"""
        # Mock setup
        mock_db_connection.execute.return_value = mock_db_cursor
        mock_db_cursor.fetchone.return_value = ("ITEM001", 2.5)  # item_code, multiplier
        mock_db_cursor.description = [["item_code"], ["multiplier"]]
        
        # Test
        result = lookup_barcode("123456")
        
        # Assertions
        assert result is not None
        assert isinstance(result, dict)
    
    @pytest.mark.unit
    def test_lookup_barcode_not_found(self, mock_db_connection, mock_db_cursor):
        """Barkod bulunamadı testi"""
        # Mock setup
        mock_db_connection.execute.return_value = mock_db_cursor
        mock_db_cursor.fetchone.return_value = None
        
        # Test
        result = lookup_barcode("999999")
        
        # Assertions
        assert result is None


class TestConstants:
    """Constants testleri"""
    
    def test_max_retry_is_positive(self):
        """MAX_RETRY pozitif sayı olmalı"""
        assert MAX_RETRY > 0
        assert isinstance(MAX_RETRY, int)
    
    def test_retry_wait_is_positive(self):
        """RETRY_WAIT pozitif sayı olmalı"""
        assert RETRY_WAIT > 0
        assert isinstance(RETRY_WAIT, (int, float))