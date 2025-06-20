"""
WMS Application Exception Classes
==============================

Merkezi hata yönetimi sistemi - tüm uygulama katmanları için
standardize edilmiş exception sınıfları ve hata işleme mekanizmaları.
"""

from __future__ import annotations
import traceback
from typing import Optional, Dict, Any
from enum import Enum

from app.core.logger import get_logger

logger = get_logger(__name__)


class ErrorSeverity(Enum):
    """Hata ciddiyeti seviyeleri"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Hata kategorileri"""
    DATABASE = "database"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    BUSINESS_LOGIC = "business_logic"
    NETWORK = "network"
    FILE_SYSTEM = "file_system"
    EXTERNAL_SERVICE = "external_service"
    CONFIGURATION = "configuration"
    USER_INPUT = "user_input"


class WMSException(Exception):
    """Base exception class for WMS application"""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        category: ErrorCategory = ErrorCategory.BUSINESS_LOGIC,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.category = category
        self.severity = severity
        self.context = context or {}
        self.original_exception = original_exception
        
        # Log the exception
        self._log_exception()
    
    def _log_exception(self):
        """Exception'ı uygun seviyede logla"""
        log_context = {
            "error_code": self.error_code,
            "category": self.category.value,
            "severity": self.severity.value,
            "context": self.context
        }
        
        if self.severity == ErrorSeverity.CRITICAL:
            logger.critical(f"{self.message}", extra=log_context)
        elif self.severity == ErrorSeverity.HIGH:
            logger.error(f"{self.message}", extra=log_context)
        elif self.severity == ErrorSeverity.MEDIUM:
            logger.warning(f"{self.message}", extra=log_context)
        else:
            logger.info(f"{self.message}", extra=log_context)
    
    def to_dict(self) -> Dict[str, Any]:
        """Exception'ı dictionary'ye çevir"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "context": self.context,
            "traceback": traceback.format_exc() if self.original_exception else None
        }


# Database Exceptions
class DatabaseException(WMSException):
    """Database operations exception"""
    
    def __init__(self, message: str, **kwargs):
        kwargs.setdefault("category", ErrorCategory.DATABASE)
        kwargs.setdefault("severity", ErrorSeverity.HIGH)
        super().__init__(message, **kwargs)


class ConnectionException(DatabaseException):
    """Database connection exception"""
    
    def __init__(self, message: str = "Veritabanı bağlantısı kurulamadı", **kwargs):
        kwargs.setdefault("error_code", "DB_CONNECTION_FAILED")
        kwargs.setdefault("severity", ErrorSeverity.CRITICAL)
        super().__init__(message, **kwargs)


class QueryException(DatabaseException):
    """SQL query execution exception"""
    
    def __init__(self, message: str, query: Optional[str] = None, **kwargs):
        if query:
            kwargs.setdefault("context", {})["query"] = query
        kwargs.setdefault("error_code", "DB_QUERY_FAILED")
        super().__init__(message, **kwargs)


# Authentication & Authorization Exceptions
class AuthenticationException(WMSException):
    """Authentication related exception"""
    
    def __init__(self, message: str = "Kimlik doğrulaması başarısız", **kwargs):
        kwargs.setdefault("category", ErrorCategory.AUTHENTICATION)
        kwargs.setdefault("severity", ErrorSeverity.HIGH)
        kwargs.setdefault("error_code", "AUTH_FAILED")
        super().__init__(message, **kwargs)


class AuthorizationException(WMSException):
    """Authorization related exception"""
    
    def __init__(self, message: str = "Bu işlem için yetkiniz yok", **kwargs):
        kwargs.setdefault("category", ErrorCategory.AUTHORIZATION)
        kwargs.setdefault("severity", ErrorSeverity.MEDIUM)
        kwargs.setdefault("error_code", "AUTHORIZATION_DENIED")
        super().__init__(message, **kwargs)


class InvalidUserException(AuthenticationException):
    """Invalid user exception"""
    
    def __init__(self, username: str, **kwargs):
        message = f"Geçersiz kullanıcı: {username}"
        kwargs.setdefault("context", {})["username"] = username
        kwargs.setdefault("error_code", "INVALID_USER")
        super().__init__(message, **kwargs)


class InactiveUserException(AuthenticationException):
    """Inactive user exception"""
    
    def __init__(self, username: str, **kwargs):
        message = f"Kullanıcı aktif değil: {username}"
        kwargs.setdefault("context", {})["username"] = username
        kwargs.setdefault("error_code", "USER_INACTIVE")
        super().__init__(message, **kwargs)


# Business Logic Exceptions
class ValidationException(WMSException):
    """Data validation exception"""
    
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        if field:
            kwargs.setdefault("context", {})["field"] = field
        kwargs.setdefault("category", ErrorCategory.VALIDATION)
        kwargs.setdefault("severity", ErrorSeverity.LOW)
        kwargs.setdefault("error_code", "VALIDATION_FAILED")
        super().__init__(message, **kwargs)


class BusinessLogicException(WMSException):
    """Business logic violation exception"""
    
    def __init__(self, message: str, **kwargs):
        kwargs.setdefault("category", ErrorCategory.BUSINESS_LOGIC)
        kwargs.setdefault("severity", ErrorSeverity.MEDIUM)
        super().__init__(message, **kwargs)


class OrderNotFoundException(BusinessLogicException):
    """Order not found exception"""
    
    def __init__(self, order_no: str, **kwargs):
        message = f"Sipariş bulunamadı: {order_no}"
        kwargs.setdefault("context", {})["order_no"] = order_no
        kwargs.setdefault("error_code", "ORDER_NOT_FOUND")
        super().__init__(message, **kwargs)


class InsufficientStockException(BusinessLogicException):
    """Insufficient stock exception"""
    
    def __init__(self, item_code: str, requested: int, available: int, **kwargs):
        message = f"Yetersiz stok - Ürün: {item_code}, İstenen: {requested}, Mevcut: {available}"
        kwargs.setdefault("context", {}).update({
            "item_code": item_code,
            "requested_qty": requested,
            "available_qty": available
        })
        kwargs.setdefault("error_code", "INSUFFICIENT_STOCK")
        super().__init__(message, **kwargs)


class BarcodeNotFoundException(BusinessLogicException):
    """Barcode not found exception"""
    
    def __init__(self, barcode: str, **kwargs):
        message = f"Barkod bulunamadı: {barcode}"
        kwargs.setdefault("context", {})["barcode"] = barcode
        kwargs.setdefault("error_code", "BARCODE_NOT_FOUND")
        super().__init__(message, **kwargs)


class InvalidBarcodeException(ValidationException):
    """Invalid barcode format exception"""
    
    def __init__(self, barcode: str, **kwargs):
        message = f"Geçersiz barkod formatı: {barcode}"
        kwargs.setdefault("context", {})["barcode"] = barcode
        kwargs.setdefault("error_code", "INVALID_BARCODE")
        super().__init__(message, **kwargs)


# File System Exceptions
class FileSystemException(WMSException):
    """File system related exception"""
    
    def __init__(self, message: str, file_path: Optional[str] = None, **kwargs):
        if file_path:
            kwargs.setdefault("context", {})["file_path"] = file_path
        kwargs.setdefault("category", ErrorCategory.FILE_SYSTEM)
        kwargs.setdefault("severity", ErrorSeverity.MEDIUM)
        super().__init__(message, **kwargs)


class ConfigurationException(WMSException):
    """Configuration related exception"""
    
    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        if config_key:
            kwargs.setdefault("context", {})["config_key"] = config_key
        kwargs.setdefault("category", ErrorCategory.CONFIGURATION)
        kwargs.setdefault("severity", ErrorSeverity.HIGH)
        kwargs.setdefault("error_code", "CONFIG_ERROR")
        super().__init__(message, **kwargs)


# Network & External Service Exceptions
class NetworkException(WMSException):
    """Network related exception"""
    
    def __init__(self, message: str, **kwargs):
        kwargs.setdefault("category", ErrorCategory.NETWORK)
        kwargs.setdefault("severity", ErrorSeverity.HIGH)
        super().__init__(message, **kwargs)


class ExternalServiceException(WMSException):
    """External service exception"""
    
    def __init__(self, message: str, service_name: Optional[str] = None, **kwargs):
        if service_name:
            kwargs.setdefault("context", {})["service_name"] = service_name
        kwargs.setdefault("category", ErrorCategory.EXTERNAL_SERVICE)
        kwargs.setdefault("severity", ErrorSeverity.HIGH)
        super().__init__(message, **kwargs)


# User Input Exceptions
class UserInputException(WMSException):
    """User input related exception"""
    
    def __init__(self, message: str, **kwargs):
        kwargs.setdefault("category", ErrorCategory.USER_INPUT)
        kwargs.setdefault("severity", ErrorSeverity.LOW)
        super().__init__(message, **kwargs)


# Exception Handler Decorator
def handle_exceptions(
    default_message: str = "Bir hata oluştu",
    log_traceback: bool = True,
    reraise: bool = False
):
    """
    Exception handling decorator
    
    Args:
        default_message: Varsayılan hata mesajı
        log_traceback: Traceback'i logla
        reraise: Exception'ı yeniden fırlat
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except WMSException:
                # WMS exception'ları zaten loglandı, sadece yeniden fırlat
                if reraise:
                    raise
                return None
            except Exception as e:
                # Beklenmeyen exception'ları WMSException'a çevir
                if log_traceback:
                    logger.exception(f"Beklenmeyen hata in {func.__name__}: {str(e)}")
                
                wms_exc = WMSException(
                    message=f"{default_message}: {str(e)}",
                    error_code="UNEXPECTED_ERROR",
                    severity=ErrorSeverity.HIGH,
                    original_exception=e,
                    context={"function": func.__name__}
                )
                
                if reraise:
                    raise wms_exc
                return None
        return wrapper
    return decorator