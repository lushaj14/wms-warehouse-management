"""
Gelişmiş Logging System
=======================
"""
import logging
import logging.handlers
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from app.constants import DEFAULT_LOG_DIR


class ColoredFormatter(logging.Formatter):
    """Renkli console output için formatter"""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{log_color}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)


class ContextFilter(logging.Filter):
    """Kullanıcı context bilgilerini log'a ekler"""
    
    def filter(self, record):
        # User context'i varsa ekle (circular import'ı önlemek için global var kullan)
        record.username = getattr(self, '_current_username', 'system')
        record.user_id = getattr(self, '_current_user_id', 'N/A')
        return True
    
    def set_user_context(self, username: str, user_id: str):
        """User context'i manuel olarak set et (circular import olmadan)"""
        self._current_username = username
        self._current_user_id = user_id


class WMSLogger:
    """WMS özel logger sistemi"""
    
    _loggers: Dict[str, logging.Logger] = {}
    _initialized = False
    
    @classmethod
    def initialize(cls, log_dir: str = None):
        """Logging sistemini başlatır"""
        if cls._initialized:
            return
        
        log_dir = Path(log_dir or DEFAULT_LOG_DIR)
        log_dir.mkdir(exist_ok=True, parents=True)
        
        # Root logger ayarları
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        
        # Mevcut handler'ları temizle
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = ColoredFormatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s [%(username)s]'
        )
        console_handler.setFormatter(console_formatter)
        console_handler.addFilter(ContextFilter())
        
        # File handler - Main log
        main_file_handler = logging.handlers.RotatingFileHandler(
            log_dir / 'wms.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        main_file_handler.setLevel(logging.DEBUG)
        main_file_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s '
            '[User: %(username)s, ID: %(user_id)s] [%(pathname)s:%(lineno)d]'
        )
        main_file_handler.setFormatter(main_file_formatter)
        main_file_handler.addFilter(ContextFilter())
        
        # Error file handler
        error_file_handler = logging.handlers.RotatingFileHandler(
            log_dir / 'errors.log',
            maxBytes=5*1024*1024,  # 5MB
            backupCount=10,
            encoding='utf-8'
        )
        error_file_handler.setLevel(logging.ERROR)
        error_file_handler.setFormatter(main_file_formatter)
        error_file_handler.addFilter(ContextFilter())
        
        # Root logger'a handler'ları ekle
        root_logger.addHandler(console_handler)
        root_logger.addHandler(main_file_handler)
        root_logger.addHandler(error_file_handler)
        
        cls._initialized = True
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Named logger döndürür"""
        if not cls._initialized:
            cls.initialize()
        
        if name not in cls._loggers:
            logger = logging.getLogger(name)
            cls._loggers[name] = logger
        
        return cls._loggers[name]
    
    @classmethod
    def log_user_activity(cls, action: str, details: str = "", **context):
        """Kullanıcı aktivitesi loglar"""
        logger = cls.get_logger('user_activity')
        
        # Context bilgilerini formatla
        context_str = " | ".join(f"{k}={v}" for k, v in context.items() if v is not None)
        log_message = f"ACTION: {action} | DETAILS: {details}"
        if context_str:
            log_message += f" | CONTEXT: {context_str}"
        
        logger.info(log_message)
    
    @classmethod
    def log_database_operation(cls, operation: str, table: str, affected_rows: int = None, **context):
        """Veritabanı operasyonu loglar"""
        logger = cls.get_logger('database')
        
        context_str = " | ".join(f"{k}={v}" for k, v in context.items() if v is not None)
        log_message = f"DB_OP: {operation} | TABLE: {table}"
        if affected_rows is not None:
            log_message += f" | ROWS: {affected_rows}"
        if context_str:
            log_message += f" | {context_str}"
        
        logger.info(log_message)
    
    @classmethod
    def log_barcode_scan(cls, barcode: str, item_code: str, order_no: str, result: str):
        """Barkod tarama loglar"""
        logger = cls.get_logger('barcode_scanner')
        logger.info(
            f"BARCODE_SCAN: {barcode} | ITEM: {item_code} | ORDER: {order_no} | RESULT: {result}"
        )
    
    @classmethod
    def log_error_with_context(cls, error: Exception, context: Dict[str, Any] = None):
        """Hata ile birlikte context bilgilerini loglar"""
        logger = cls.get_logger('error_handler')
        
        error_details = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc()
        }
        
        if context:
            error_details.update(context)
        
        logger.error(f"ERROR_OCCURRED: {error_details}")


# Kolay erişim için kısayollar
def get_logger(name: str) -> logging.Logger:
    """Logger al"""
    return WMSLogger.get_logger(name)


def log_user_action(action: str, details: str = "", **context):
    """Kullanıcı aksiyonu logla"""
    WMSLogger.log_user_activity(action, details, **context)


def log_db_operation(operation: str, table: str, affected_rows: int = None, **context):
    """DB operasyonu logla"""
    WMSLogger.log_database_operation(operation, table, affected_rows, **context)


def log_barcode_scan(barcode: str, item_code: str, order_no: str, result: str):
    """Barkod tarama logla"""
    WMSLogger.log_barcode_scan(barcode, item_code, order_no, result)


def log_error(error: Exception, context: Dict[str, Any] = None):
    """Hata logla"""
    WMSLogger.log_error_with_context(error, context)


# Sistem başlatılırken logger'ı initialize et
WMSLogger.initialize()