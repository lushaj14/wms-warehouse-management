"""
Error Handler Utilities
======================

UI katmanında hata yönetimi için yardımcı fonksiyonlar ve sınıflar.
"""

from __future__ import annotations
import sys
import traceback
from typing import Optional, Callable, Any
from functools import wraps
from contextlib import contextmanager

from PyQt5.QtWidgets import QMessageBox, QWidget
from PyQt5.QtCore import QObject, pyqtSignal

from app.core.exceptions import (
    WMSException, ErrorSeverity, ErrorCategory,
    AuthenticationException, AuthorizationException,
    ValidationException, BusinessLogicException,
    DatabaseException, NetworkException
)
from app.core.logger import get_logger, log_user_action
from app.core.auth import get_current_user
from app import toast

logger = get_logger(__name__)


class ErrorHandler(QObject):
    """Merkezi hata yönetici sınıfı"""
    
    error_occurred = pyqtSignal(str, str)  # title, message
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__()
        self.parent = parent
        self._error_count = 0
        self._max_errors_per_session = 50
    
    def handle_exception(
        self,
        exception: Exception,
        user_message: Optional[str] = None,
        show_dialog: bool = True,
        show_toast: bool = False,
        context: Optional[str] = None
    ) -> bool:
        """
        Exception'ı handle et
        
        Args:
            exception: Yakalanan exception
            user_message: Kullanıcıya gösterilecek özel mesaj
            show_dialog: Dialog göster
            show_toast: Toast göster
            context: Hata context'i
            
        Returns:
            bool: Hata başarıyla handle edildi mi
        """
        self._error_count += 1
        
        # Çok fazla hata varsa durdur
        if self._error_count > self._max_errors_per_session:
            self._show_critical_error("Çok fazla hata oluştu. Uygulama kapatılacak.")
            sys.exit(1)
        
        # WMS Exception ise
        if isinstance(exception, WMSException):
            return self._handle_wms_exception(
                exception, user_message, show_dialog, show_toast, context
            )
        
        # Diğer exception'lar için
        return self._handle_generic_exception(
            exception, user_message, show_dialog, show_toast, context
        )
    
    def _handle_wms_exception(
        self,
        exception: WMSException,
        user_message: Optional[str],
        show_dialog: bool,
        show_toast: bool,
        context: Optional[str]
    ) -> bool:
        """WMS Exception'ı handle et"""
        
        # User action log
        current_user = get_current_user()
        log_user_action(
            "ERROR",
            f"Hata oluştu: {exception.error_code}",
            error_code=exception.error_code,
            error_category=exception.category.value,
            error_severity=exception.severity.value,
            context=context or "unknown"
        )
        
        # Kullanıcıya gösterilecek mesaj
        display_message = user_message or self._get_user_friendly_message(exception)
        
        # UI feedback
        if show_dialog:
            self._show_error_dialog(exception, display_message)
        elif show_toast:
            self._show_error_toast(exception, display_message)
        
        # Signal emit
        self.error_occurred.emit(exception.error_code, display_message)
        
        return True
    
    def _handle_generic_exception(
        self,
        exception: Exception,
        user_message: Optional[str],
        show_dialog: bool,
        show_toast: bool,
        context: Optional[str]
    ) -> bool:
        """Generic exception'ı handle et"""
        
        # Log the exception
        logger.exception(f"Beklenmeyen hata: {str(exception)}")
        
        # User action log
        log_user_action(
            "ERROR",
            f"Beklenmeyen hata: {type(exception).__name__}",
            error_type=type(exception).__name__,
            context=context or "unknown"
        )
        
        # Kullanıcıya gösterilecek mesaj
        display_message = user_message or "Beklenmeyen bir hata oluştu. Lütfen tekrar deneyin."
        
        # UI feedback
        if show_dialog:
            self._show_generic_error_dialog(exception, display_message)
        elif show_toast:
            toast.show("Hata", display_message)
        
        return True
    
    def _get_user_friendly_message(self, exception: WMSException) -> str:
        """Kullanıcı dostu hata mesajı üret"""
        
        # Authentication errors
        if isinstance(exception, (AuthenticationException, AuthorizationException)):
            return exception.message
        
        # Validation errors
        if isinstance(exception, ValidationException):
            return f"Veri doğrulama hatası: {exception.message}"
        
        # Business logic errors
        if isinstance(exception, BusinessLogicException):
            return exception.message
        
        # Database errors
        if isinstance(exception, DatabaseException):
            if exception.severity == ErrorSeverity.CRITICAL:
                return "Sistem veritabanına bağlanılamıyor. Lütfen sistem yöneticisi ile iletişime geçin."
            return "Veri işleme sırasında bir hata oluştu. Lütfen tekrar deneyin."
        
        # Network errors
        if isinstance(exception, NetworkException):
            return "Ağ bağlantısı sorunu. Lütfen internet bağlantınızı kontrol edin."
        
        # Default
        return exception.message
    
    def _show_error_dialog(self, exception: WMSException, message: str):
        """Hata dialog'u göster"""
        
        # Severity'e göre dialog tipi
        if exception.severity == ErrorSeverity.CRITICAL:
            QMessageBox.critical(self.parent, "Kritik Hata", message)
        elif exception.severity == ErrorSeverity.HIGH:
            QMessageBox.critical(self.parent, "Hata", message)
        elif exception.severity == ErrorSeverity.MEDIUM:
            QMessageBox.warning(self.parent, "Uyarı", message)
        else:
            QMessageBox.information(self.parent, "Bilgi", message)
    
    def _show_generic_error_dialog(self, exception: Exception, message: str):
        """Generic hata dialog'u göster"""
        QMessageBox.critical(self.parent, "Beklenmeyen Hata", message)
    
    def _show_error_toast(self, exception: WMSException, message: str):
        """Hata toast'u göster"""
        
        if exception.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.HIGH]:
            toast.show("Hata", message)
        elif exception.severity == ErrorSeverity.MEDIUM:
            toast.show("Uyarı", message)
        else:
            toast.show("Bilgi", message)
    
    def _show_critical_error(self, message: str):
        """Kritik hata göster"""
        QMessageBox.critical(self.parent, "Kritik Hata", message)
    
    def reset_error_count(self):
        """Hata sayacını sıfırla"""
        self._error_count = 0


# Global error handler instance
_global_error_handler: Optional[ErrorHandler] = None


def get_error_handler(parent: Optional[QWidget] = None) -> ErrorHandler:
    """Global error handler'ı al"""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler(parent)
    return _global_error_handler


def handle_error(
    exception: Exception,
    user_message: Optional[str] = None,
    show_dialog: bool = True,
    show_toast: bool = False,
    context: Optional[str] = None,
    parent: Optional[QWidget] = None
) -> bool:
    """
    Hata handle etme utility fonksiyonu
    
    Usage:
        try:
            # some operation
        except Exception as e:
            handle_error(e, "İşlem başarısız", context="order_processing")
    """
    handler = get_error_handler(parent)
    return handler.handle_exception(exception, user_message, show_dialog, show_toast, context)


def error_handler_decorator(
    user_message: Optional[str] = None,
    show_dialog: bool = True,
    show_toast: bool = False,
    reraise: bool = False,
    context: Optional[str] = None
):
    """
    Error handling decorator
    
    Usage:
        @error_handler_decorator("Sipariş yüklenemedi", show_toast=True)
        def load_order(self, order_no):
            # implementation
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                func_context = context or f"{func.__module__}.{func.__name__}"
                
                # Parent widget'ı args'dan bulmaya çalış
                parent_widget = None
                for arg in args:
                    if isinstance(arg, QWidget):
                        parent_widget = arg
                        break
                
                handled = handle_error(
                    e, user_message, show_dialog, show_toast, func_context, parent_widget
                )
                
                if reraise and not handled:
                    raise
                
                return None
        return wrapper
    return decorator


@contextmanager
def error_context(
    user_message: Optional[str] = None,
    show_dialog: bool = True,
    show_toast: bool = False,
    parent: Optional[QWidget] = None,
    context: Optional[str] = None
):
    """
    Error handling context manager
    
    Usage:
        with error_context("İşlem başarısız", show_toast=True):
            # some operations
    """
    try:
        yield
    except Exception as e:
        handle_error(e, user_message, show_dialog, show_toast, context, parent)


def setup_global_exception_handler():
    """Global exception handler'ı kur"""
    def excepthook(exc_type, exc_value, exc_traceback):
        """Global exception hook"""
        
        # KeyboardInterrupt'ı normal şekilde handle et
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        # Exception'ı handle et
        logger.critical(
            "Beklenmeyen global hata",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
        
        # Global error handler ile handle et
        if exc_value:
            handle_error(
                exc_value,
                "Kritik bir hata oluştu. Uygulama yeniden başlatılmalı.",
                show_dialog=True,
                context="global_exception_handler"
            )
    
    sys.excepthook = excepthook