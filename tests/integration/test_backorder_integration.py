"""
Integration tests for backorder functionality
=============================================
"""
import pytest
from unittest.mock import patch, Mock
from datetime import date

import app.backorder as bo


class TestBackorderIntegration:
    """Backorder entegrasyon testleri"""
    
    @pytest.mark.integration
    @pytest.mark.database
    def test_insert_and_list_backorder_flow(self, mock_db_connection):
        """Backorder ekleme ve listeleme akışı testi"""
        # Mock setup
        mock_db_connection.execute.return_value.fetchone.return_value = None  # İlk sorgu boş
        
        # Test data
        order_no = "TEST001"
        item_code = "ITEM001"
        qty_missing = 5.0
        
        # Test backorder ekleme
        bo.insert_backorder(
            order_no=order_no,
            line_id=1,
            warehouse_id=0,
            item_code=item_code,
            qty_missing=qty_missing
        )
        
        # Database operasyonu çağrılmalı
        assert mock_db_connection.execute.call_count >= 1
    
    @pytest.mark.integration
    @pytest.mark.database
    def test_shipment_creation_flow(self, mock_db_connection):
        """Sevkiyat oluşturma akışı testi"""
        # Test data
        order_no = "TEST001"
        trip_date = str(date.today())
        item_code = "ITEM001"
        warehouse_id = 0
        invoiced_qty = 10.0
        qty_delta = 8.0
        
        # Test shipment ekleme
        bo.add_shipment(
            order_no=order_no,
            trip_date=trip_date,
            item_code=item_code,
            warehouse_id=warehouse_id,
            invoiced_qty=invoiced_qty,
            qty_delta=qty_delta
        )
        
        # MERGE sorgusu çalışmalı
        assert mock_db_connection.execute.called
        
        # Çağrılan SQL'de MERGE keyword olmalı
        call_args = mock_db_connection.execute.call_args
        sql_query = call_args[0][0]
        assert "MERGE" in sql_query.upper()
    
    @pytest.mark.integration
    def test_complete_backorder_workflow(self, mock_db_connection, sample_order_data):
        """Tam backorder iş akışı testi"""
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            (1, "TEST001", 1, 0, "ITEM001", 5.0, None, 0, "2025-01-01", None)
        ]
        mock_cursor.description = [
            ["id"], ["order_no"], ["line_id"], ["warehouse_id"], 
            ["item_code"], ["qty_missing"], ["eta_date"], 
            ["fulfilled"], ["created_at"], ["fulfilled_at"]
        ]
        mock_db_connection.execute.return_value = mock_cursor
        
        # 1. Pending backorders listele
        pending = bo.list_pending()
        assert isinstance(pending, list)
        
        # 2. Backorder'ı fulfilled yap
        if pending:
            bo.mark_fulfilled(pending[0]["id"])
        
        # 3. Fulfilled backorders listele
        fulfilled = bo.list_fulfilled()
        assert isinstance(fulfilled, list)


class TestBackorderErrorHandling:
    """Backorder hata yönetimi testleri"""
    
    @pytest.mark.integration
    def test_database_error_handling(self):
        """Veritabanı hata yönetimi testi"""
        with patch('app.backorder.get_conn') as mock_get_conn:
            # Database hatası simüle et
            mock_get_conn.side_effect = Exception("Database connection failed")
            
            # Hata fırlatılmalı
            with pytest.raises(Exception):
                bo.list_pending()
    
    @pytest.mark.integration
    def test_invalid_data_handling(self, mock_db_connection):
        """Geçersiz veri yönetimi testi"""
        # Negatif miktar ile test
        with pytest.raises((ValueError, TypeError)):
            bo.insert_backorder(
                order_no="TEST001",
                line_id=1,
                warehouse_id=0,
                item_code="ITEM001",
                qty_missing=-5.0  # Negatif miktar
            )