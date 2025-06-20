"""
Auto-Update System
=================

Git repository'den otomatik güncelleme sistemi.
"""

import os
import sys
import json
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime

import requests
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from PyQt5.QtWidgets import QMessageBox, QProgressDialog, QApplication

from app.core.logger import get_logger, log_user_action
from app.core.exceptions import NetworkException, ValidationException
from app.core.error_handler import handle_error

logger = get_logger(__name__)

# GitHub repository bilgileri
GITHUB_OWNER = "lushaj14"  # GitHub kullanıcı adınız
GITHUB_REPO = "wms-warehouse-management"  # Repository adı
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}"
GITHUB_DOWNLOAD_URL = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/archive/refs/heads/main.zip"

# Version dosyası
VERSION_FILE = Path(__file__).parent.parent.parent / "version.json"


class UpdateInfo:
    """Güncelleme bilgileri"""
    
    def __init__(self, data: Dict):
        self.version = data.get('version', '1.0.0')
        self.commit_sha = data.get('commit_sha', '')
        self.commit_message = data.get('commit_message', '')
        self.commit_date = data.get('commit_date', '')
        self.download_url = data.get('download_url', '')
        self.changelog = data.get('changelog', [])


class UpdateWorker(QThread):
    """Güncelleme işlemi için worker thread"""
    
    progress_updated = pyqtSignal(int, str)
    update_completed = pyqtSignal(bool, str)
    
    def __init__(self, download_url: str, target_dir: str):
        super().__init__()
        self.download_url = download_url
        self.target_dir = Path(target_dir)
        
    def run(self):
        """Güncelleme işlemini gerçekleştir"""
        try:
            self.progress_updated.emit(10, "Güncelleme indiriliyor...")
            
            # Geçici klasör oluştur
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                zip_file = temp_path / "update.zip"
                
                # Dosyayı indir
                self._download_file(self.download_url, zip_file)
                self.progress_updated.emit(50, "Dosyalar çıkarılıyor...")
                
                # ZIP'i çıkar
                import zipfile
                extract_dir = temp_path / "extracted"
                with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                
                self.progress_updated.emit(70, "Dosyalar güncelleniyor...")
                
                # Ana klasörü bul (genelde reponame-main)
                extracted_folders = list(extract_dir.iterdir())
                if extracted_folders:
                    source_dir = extracted_folders[0]
                    
                    # Kritik dosyaları yedekle
                    self._backup_critical_files()
                    
                    self.progress_updated.emit(80, "Yeni dosyalar kopyalanıyor...")
                    
                    # Dosyaları kopyala (bazı dosyaları atla)
                    self._copy_update_files(source_dir, self.target_dir)
                    
                    self.progress_updated.emit(95, "Güncelleme tamamlanıyor...")
                    
                    # Version bilgisini güncelle
                    self._update_version_info()
                    
                    self.progress_updated.emit(100, "Güncelleme tamamlandı!")
                    self.update_completed.emit(True, "Güncelleme başarıyla tamamlandı!")
                    
                else:
                    self.update_completed.emit(False, "Güncelleme dosyaları bulunamadı")
                    
        except Exception as e:
            logger.exception(f"Update failed: {e}")
            self.update_completed.emit(False, f"Güncelleme hatası: {str(e)}")
    
    def _download_file(self, url: str, file_path: Path):
        """Dosyayı indir"""
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # Progress güncelle
                    if total_size > 0:
                        progress = int((downloaded / total_size) * 40) + 10  # 10-50 arası
                        self.progress_updated.emit(progress, f"İndiriliyor... {downloaded // 1024}KB")
    
    def _backup_critical_files(self):
        """Kritik dosyaları yedekle"""
        critical_files = [
            "config.json",
            "settings.json", 
            "users.json",
            ".env"
        ]
        
        backup_dir = self.target_dir / "backup"
        backup_dir.mkdir(exist_ok=True)
        
        for file_name in critical_files:
            file_path = self.target_dir / file_name
            if file_path.exists():
                shutil.copy2(file_path, backup_dir / file_name)
                logger.info(f"Backed up: {file_name}")
    
    def _copy_update_files(self, source_dir: Path, target_dir: Path):
        """Güncelleme dosyalarını kopyala"""
        # Atlanacak dosya/klasörler
        skip_items = {
            '.git', '__pycache__', '*.pyc', 'venv', 'env',
            'config.json', 'settings.json', 'users.json', '.env',
            'logs', 'backup'
        }
        
        for item in source_dir.rglob('*'):
            if any(skip in str(item) for skip in skip_items):
                continue
                
            # Hedef yolu hesapla
            relative_path = item.relative_to(source_dir)
            target_path = target_dir / relative_path
            
            if item.is_file():
                # Klasör oluştur
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Dosyayı kopyala
                shutil.copy2(item, target_path)
                logger.debug(f"Copied: {relative_path}")
    
    def _update_version_info(self):
        """Version bilgisini güncelle"""
        version_info = {
            "version": "latest",
            "updated_at": datetime.now().isoformat(),
            "update_method": "auto_update"
        }
        
        with open(VERSION_FILE, 'w', encoding='utf-8') as f:
            json.dump(version_info, f, indent=2, ensure_ascii=False)


class AutoUpdater(QObject):
    """Otomatik güncelleme sistemi"""
    
    update_available = pyqtSignal(UpdateInfo)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self._current_version = self._get_current_version()
        
    def _get_current_version(self) -> Dict:
        """Mevcut version bilgisini al"""
        if VERSION_FILE.exists():
            try:
                with open(VERSION_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Version file read error: {e}")
        
        # Default version
        return {
            "version": "1.0.0",
            "commit_sha": "",
            "updated_at": "2025-01-01T00:00:00"
        }
    
    def check_for_updates(self, silent: bool = False) -> Optional[UpdateInfo]:
        """Güncellemeleri kontrol et"""
        try:
            # GitHub API'den son commit bilgilerini al
            response = requests.get(f"{GITHUB_API_URL}/commits/main", timeout=10)
            response.raise_for_status()
            
            commit_data = response.json()
            latest_sha = commit_data['sha']
            current_sha = self._current_version.get('commit_sha', '')
            
            # Güncelleme var mı kontrol et
            if latest_sha != current_sha:
                update_info = UpdateInfo({
                    'version': 'latest',
                    'commit_sha': latest_sha,
                    'commit_message': commit_data['commit']['message'],
                    'commit_date': commit_data['commit']['committer']['date'],
                    'download_url': GITHUB_DOWNLOAD_URL,
                    'changelog': self._get_changelog(current_sha, latest_sha)
                })
                
                if not silent:
                    self.update_available.emit(update_info)
                
                return update_info
            else:
                if not silent:
                    QMessageBox.information(
                        self.parent,
                        "Güncel Sürüm",
                        "Uygulama zaten en güncel sürümde!"
                    )
                return None
                
        except requests.RequestException as e:
            if not silent:
                handle_error(
                    NetworkException(f"Güncelleme kontrolü başarısız: {str(e)}"),
                    "İnternet bağlantısını kontrol edin",
                    show_dialog=True,
                    parent=self.parent
                )
            return None
        except Exception as e:
            if not silent:
                handle_error(e, "Güncelleme kontrolünde hata", show_dialog=True, parent=self.parent)
            return None
    
    def _get_changelog(self, from_sha: str, to_sha: str) -> list:
        """Değişiklik listesini al"""
        try:
            if not from_sha:
                return ["İlk kurulum"]
                
            # Commit'ler arasındaki farkı al
            response = requests.get(
                f"{GITHUB_API_URL}/compare/{from_sha}...{to_sha}",
                timeout=10
            )
            response.raise_for_status()
            
            compare_data = response.json()
            changelog = []
            
            for commit in compare_data.get('commits', []):
                message = commit['commit']['message'].split('\n')[0]  # İlk satır
                if not message.startswith('Merge') and not message.startswith('Update'):
                    changelog.append(message)
            
            return changelog[:10]  # Son 10 değişiklik
            
        except Exception as e:
            logger.warning(f"Changelog fetch error: {e}")
            return ["Changelog alınamadı"]
    
    def perform_update(self, update_info: UpdateInfo) -> bool:
        """Güncellemeyi gerçekleştir"""
        try:
            # Onay al
            reply = QMessageBox.question(
                self.parent,
                "Güncelleme Onayı",
                f"Yeni güncelleme mevcut!\n\n"
                f"Son değişiklik: {update_info.commit_message}\n"
                f"Tarih: {update_info.commit_date}\n\n"
                f"Güncellemeleri:\n" + "\n".join(f"• {change}" for change in update_info.changelog[:5]) + "\n\n"
                f"Güncelleme yapılsın mı?\n\n"
                f"⚠️ Uygulama güncelleme sonrası yeniden başlatılacak.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply != QMessageBox.Yes:
                return False
            
            # Progress dialog
            progress = QProgressDialog(
                "Güncelleme yapılıyor...",
                "İptal",
                0, 100,
                self.parent
            )
            progress.setWindowModality(Qt.WindowModal)
            progress.setAutoClose(True)
            progress.setAutoReset(False)
            progress.show()
            
            # Worker thread başlat
            app_dir = Path(__file__).parent.parent.parent
            self.worker = UpdateWorker(update_info.download_url, str(app_dir))
            
            self.worker.progress_updated.connect(
                lambda value, text: (
                    progress.setValue(value),
                    progress.setLabelText(text)
                )
            )
            
            self.worker.update_completed.connect(
                lambda success, message: self._on_update_completed(success, message, progress)
            )
            
            # İptal butonunu deaktive et (güncelleme sırasında)
            progress.setCancelButton(None)
            
            self.worker.start()
            return True
            
        except Exception as e:
            handle_error(e, "Güncelleme başlatılamadı", show_dialog=True, parent=self.parent)
            return False
    
    def _on_update_completed(self, success: bool, message: str, progress: QProgressDialog):
        """Güncelleme tamamlandığında çağrılır"""
        progress.close()
        
        if success:
            # Başarılı güncelleme
            log_user_action(
                "APP_UPDATE",
                "Application updated successfully",
                update_method="auto_update"
            )
            
            reply = QMessageBox.question(
                self.parent,
                "Güncelleme Tamamlandı",
                f"{message}\n\n"
                f"Değişikliklerin geçerli olması için uygulamanın yeniden başlatılması gerekiyor.\n\n"
                f"Şimdi yeniden başlatılsın mı?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                self._restart_application()
        else:
            # Güncelleme hatası
            QMessageBox.critical(
                self.parent,
                "Güncelleme Hatası",
                f"Güncelleme sırasında hata oluştu:\n\n{message}\n\n"
                f"Lütfen manuel olarak GitHub'dan son sürümü indirin."
            )
    
    def _restart_application(self):
        """Uygulamayı yeniden başlat"""
        try:
            # Mevcut script path'i al
            script_path = sys.argv[0]
            
            # Yeni process başlat
            if sys.platform.startswith('win'):
                # Windows
                subprocess.Popen([sys.executable, script_path])
            else:
                # Linux/Mac
                subprocess.Popen([sys.executable, script_path])
            
            # Mevcut uygulamayı kapat
            QApplication.instance().quit()
            
        except Exception as e:
            logger.error(f"Restart failed: {e}")
            QMessageBox.warning(
                self.parent,
                "Yeniden Başlatma Hatası",
                "Uygulama otomatik yeniden başlatılamadı.\n"
                "Lütfen manuel olarak kapatıp açın."
            )
    
    def check_updates_on_startup(self):
        """Uygulama başlangıcında güncelleme kontrol et (sessiz)"""
        update_info = self.check_for_updates(silent=True)
        if update_info:
            # Toast notification
            from app import toast
            toast(
                "Güncelleme Mevcut", 
                "Yeni güncelleme var! Menüden kontrol edin."
            )