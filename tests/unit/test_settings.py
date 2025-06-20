"""
Unit tests for settings module
==============================
"""
import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

import app.settings as settings


class TestSettingsModule:
    """Settings modülü testleri"""
    
    @pytest.mark.unit
    def test_default_settings_structure(self):
        """Varsayılan ayarlar yapısı testi"""
        defaults = settings.DEFAULTS
        
        # Ana bölümler mevcut olmalı
        assert "ui" in defaults
        assert "scanner" in defaults
        assert "loader" in defaults
        assert "db" in defaults
        assert "paths" in defaults
        assert "print" in defaults
        
        # UI ayarları
        ui_settings = defaults["ui"]
        assert "theme" in ui_settings
        assert "font_pt" in ui_settings
        assert "sounds" in ui_settings
        assert ui_settings["theme"] in ["light", "dark", "system"]
        assert isinstance(ui_settings["font_pt"], int)
    
    @pytest.mark.unit
    def test_get_function_with_dot_notation(self):
        """Dot notation ile get fonksiyonu testi"""
        # Mock _cfg
        with patch.object(settings, '_cfg', {
            "ui": {"theme": "dark", "font_pt": 12},
            "db": {"retry": 5}
        }):
            # Test mevcut değerler
            assert settings.get("ui.theme") == "dark"
            assert settings.get("ui.font_pt") == 12
            assert settings.get("db.retry") == 5
            
            # Test olmayan değer
            assert settings.get("nonexistent.key", "default") == "default"
            assert settings.get("ui.nonexistent") is None
    
    @pytest.mark.unit
    def test_set_function(self):
        """Set fonksiyonu testi"""
        with patch.object(settings, '_cfg', {}), \
             patch.object(settings, 'save') as mock_save:
            
            # Test set operation
            settings.set("ui.theme", "dark")
            
            # Değer set edilmeli
            assert settings._cfg["ui"]["theme"] == "dark"
            
            # Save çağrılmalı
            mock_save.assert_called_once()
    
    @pytest.mark.unit
    def test_deep_update_function(self):
        """Deep update fonksiyonu testi"""
        dst = {
            "ui": {"theme": "light", "font_pt": 10},
            "db": {"retry": 3}
        }
        
        src = {
            "ui": {"theme": "dark", "new_setting": True},
            "scanner": {"enabled": True}
        }
        
        settings._deep_update(dst, src)
        
        # Mevcut değerler güncellenmeli
        assert dst["ui"]["theme"] == "dark"
        assert dst["ui"]["font_pt"] == 10  # Değişmemeli
        assert dst["ui"]["new_setting"] is True  # Eklenmeli
        
        # Yeni bölüm eklenmeli
        assert dst["scanner"]["enabled"] is True
        
        # Mevcut değer korunmalı
        assert dst["db"]["retry"] == 3
    
    @pytest.mark.unit
    def test_load_disk_with_valid_json(self, temp_config_file):
        """Geçerli JSON dosyası yükleme testi"""
        with patch.object(settings, 'CFG_PATH', Path(temp_config_file)):
            result = settings._load_disk()
            
            assert isinstance(result, dict)
            assert "ui" in result
            assert result["ui"]["theme"] == "light"
    
    @pytest.mark.unit
    def test_load_disk_with_invalid_json(self):
        """Bozuk JSON dosyası yükleme testi"""
        invalid_json = "{ invalid json content"
        
        with patch("builtins.open", mock_open(read_data=invalid_json)), \
             patch.object(settings.CFG_PATH, 'exists', return_value=True), \
             patch.object(settings.CFG_PATH, 'rename') as mock_rename:
            
            result = settings._load_disk()
            
            # Boş dict dönmeli
            assert result == {}
            
            # Bozuk dosya yedeklenmeli
            mock_rename.assert_called_once()
    
    @pytest.mark.unit
    def test_load_disk_nonexistent_file(self):
        """Olmayan dosya yükleme testi"""
        with patch.object(settings.CFG_PATH, 'exists', return_value=False):
            result = settings._load_disk()
            assert result == {}
    
    @pytest.mark.unit
    def test_save_function(self):
        """Save fonksiyonu testi"""
        test_config = {"ui": {"theme": "dark"}}
        
        with patch.object(settings, '_cfg', test_config), \
             patch("builtins.open", mock_open()) as mock_file, \
             patch("json.dump") as mock_json_dump:
            
            settings.save()
            
            # Dosya açılmalı
            mock_file.assert_called_once()
            
            # JSON dump çağrılmalı
            mock_json_dump.assert_called_once_with(
                test_config, 
                mock_file.return_value.__enter__.return_value,
                ensure_ascii=False,
                indent=2
            )


class TestSettingsReload:
    """Settings reload testi"""
    
    @pytest.mark.unit
    def test_reload_merges_defaults_and_disk(self):
        """Reload varsayılanlar ve disk dosyasını birleştirmeli"""
        disk_data = {
            "ui": {"theme": "dark"},  # Override default
            "custom": {"setting": "value"}  # New setting
        }
        
        with patch.object(settings, '_load_disk', return_value=disk_data):
            result = settings.reload()
            
            # Varsayılan değerler mevcut olmalı
            assert "scanner" in result
            assert "loader" in result
            assert "db" in result
            
            # Disk değerleri override etmeli
            assert result["ui"]["theme"] == "dark"
            
            # Yeni ayarlar eklenmeli
            assert result["custom"]["setting"] == "value"
            
            # Diğer varsayılan UI ayarları korunmalı
            assert "font_pt" in result["ui"]