"""
Unit tests for constants module
===============================
"""
import pytest
from app.constants import (
    MAX_RETRY, RETRY_WAIT, DEFAULT_COMPANY_NR, DEFAULT_PERIOD_NR,
    WAREHOUSE_PREFIXES, SOUND_FILES, PDF_COLUMN_WIDTHS_MM,
    DARK_THEME_CSS, QUEUE_TABLE, DEFAULT_SIDEBAR_WIDTH
)


class TestDatabaseConstants:
    """Veritabanı sabitleri testleri"""
    
    @pytest.mark.unit
    def test_max_retry_valid(self):
        """MAX_RETRY geçerli değer olmalı"""
        assert isinstance(MAX_RETRY, int)
        assert MAX_RETRY > 0
        assert MAX_RETRY <= 10  # Makul bir üst limit
    
    @pytest.mark.unit
    def test_retry_wait_valid(self):
        """RETRY_WAIT geçerli değer olmalı"""
        assert isinstance(RETRY_WAIT, (int, float))
        assert RETRY_WAIT > 0
        assert RETRY_WAIT <= 60  # Makul bir üst limit
    
    @pytest.mark.unit
    def test_company_nr_format(self):
        """COMPANY_NR formatı doğru olmalı"""
        assert isinstance(DEFAULT_COMPANY_NR, str)
        assert len(DEFAULT_COMPANY_NR) == 3
        assert DEFAULT_COMPANY_NR.isdigit()
    
    @pytest.mark.unit
    def test_period_nr_format(self):
        """PERIOD_NR formatı doğru olmalı"""
        assert isinstance(DEFAULT_PERIOD_NR, str)
        assert len(DEFAULT_PERIOD_NR) == 2
        assert DEFAULT_PERIOD_NR.isdigit()
        assert 1 <= int(DEFAULT_PERIOD_NR) <= 12


class TestWarehouseConstants:
    """Depo sabitleri testleri"""
    
    @pytest.mark.unit
    def test_warehouse_prefixes_structure(self):
        """WAREHOUSE_PREFIXES yapısı doğru olmalı"""
        assert isinstance(WAREHOUSE_PREFIXES, dict)
        assert len(WAREHOUSE_PREFIXES) > 0
        
        for warehouse_id, prefix in WAREHOUSE_PREFIXES.items():
            assert isinstance(warehouse_id, int)
            assert isinstance(prefix, str)
            assert prefix.endswith("-")
            assert len(prefix) >= 2
    
    @pytest.mark.unit
    def test_warehouse_prefixes_unique(self):
        """Depo prefix'leri benzersiz olmalı"""
        prefixes = list(WAREHOUSE_PREFIXES.values())
        assert len(prefixes) == len(set(prefixes))


class TestSoundConstants:
    """Ses sabitleri testleri"""
    
    @pytest.mark.unit
    def test_sound_files_structure(self):
        """SOUND_FILES yapısı doğru olmalı"""
        assert isinstance(SOUND_FILES, dict)
        
        required_sounds = ["success", "duplicate", "error"]
        for sound_type in required_sounds:
            assert sound_type in SOUND_FILES
            assert isinstance(SOUND_FILES[sound_type], str)
            assert SOUND_FILES[sound_type].endswith(".wav")


class TestUIConstants:
    """UI sabitleri testleri"""
    
    @pytest.mark.unit
    def test_sidebar_width_valid(self):
        """Sidebar genişliği geçerli olmalı"""
        assert isinstance(DEFAULT_SIDEBAR_WIDTH, int)
        assert DEFAULT_SIDEBAR_WIDTH > 100  # Minimum kullanılabilir genişlik
        assert DEFAULT_SIDEBAR_WIDTH < 500  # Maximum makul genişlik
    
    @pytest.mark.unit
    def test_dark_theme_css_valid(self):
        """Koyu tema CSS'i geçerli olmalı"""
        assert isinstance(DARK_THEME_CSS, str)
        assert len(DARK_THEME_CSS.strip()) > 0
        assert "QWidget" in DARK_THEME_CSS
        assert "background" in DARK_THEME_CSS


class TestPDFConstants:
    """PDF sabitleri testleri"""
    
    @pytest.mark.unit
    def test_pdf_column_widths(self):
        """PDF kolon genişlikleri doğru olmalı"""
        assert isinstance(PDF_COLUMN_WIDTHS_MM, list)
        assert len(PDF_COLUMN_WIDTHS_MM) > 0
        
        for width in PDF_COLUMN_WIDTHS_MM:
            assert isinstance(width, (int, float))
            assert width > 0
        
        # Toplam genişlik makul olmalı (A4 için)
        total_width = sum(PDF_COLUMN_WIDTHS_MM)
        assert total_width <= 200  # A4 genişliği yaklaşık 210mm


class TestTableConstants:
    """Tablo sabitleri testleri"""
    
    @pytest.mark.unit
    def test_queue_table_name(self):
        """Kuyruk tablo adı geçerli olmalı"""
        assert isinstance(QUEUE_TABLE, str)
        assert len(QUEUE_TABLE) > 0
        assert QUEUE_TABLE.replace("_", "").isalnum()  # Alfanumerik + underscore


class TestConstantsIntegrity:
    """Sabitler bütünlük testleri"""
    
    @pytest.mark.unit
    def test_no_none_values(self):
        """Hiçbir sabit None olmamalı"""
        constants_to_check = [
            MAX_RETRY, RETRY_WAIT, DEFAULT_COMPANY_NR, DEFAULT_PERIOD_NR,
            WAREHOUSE_PREFIXES, SOUND_FILES, PDF_COLUMN_WIDTHS_MM,
            DARK_THEME_CSS, QUEUE_TABLE, DEFAULT_SIDEBAR_WIDTH
        ]
        
        for constant in constants_to_check:
            assert constant is not None
    
    @pytest.mark.unit
    def test_string_constants_not_empty(self):
        """String sabitler boş olmamalı"""
        string_constants = [
            DEFAULT_COMPANY_NR, DEFAULT_PERIOD_NR, DARK_THEME_CSS, QUEUE_TABLE
        ]
        
        for constant in string_constants:
            assert isinstance(constant, str)
            assert len(constant.strip()) > 0