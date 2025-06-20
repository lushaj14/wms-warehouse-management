"""
Unit tests for exception system
==============================
"""
import pytest
from unittest.mock import patch, MagicMock

from app.core.exceptions import (
    WMSException, ErrorSeverity, ErrorCategory,
    DatabaseException, ConnectionException, QueryException,
    AuthenticationException, AuthorizationException,
    InvalidUserException, InactiveUserException,
    ValidationException, BusinessLogicException,
    OrderNotFoundException, InsufficientStockException,
    BarcodeNotFoundException, InvalidBarcodeException,
    handle_exceptions
)


class TestWMSException:
    """WMSException base class testleri"""
    
    @pytest.mark.unit
    def test_wms_exception_creation(self):
        """WMSException oluşturma testi"""
        exc = WMSException(
            "Test error",
            error_code="TEST_ERROR",
            category=ErrorCategory.BUSINESS_LOGIC,
            severity=ErrorSeverity.HIGH,
            context={"key": "value"}
        )
        
        assert exc.message == "Test error"
        assert exc.error_code == "TEST_ERROR"
        assert exc.category == ErrorCategory.BUSINESS_LOGIC
        assert exc.severity == ErrorSeverity.HIGH
        assert exc.context["key"] == "value"
    
    @pytest.mark.unit
    def test_wms_exception_defaults(self):
        """WMSException varsayılan değerler testi"""
        exc = WMSException("Test error")
        
        assert exc.error_code == "WMSException"
        assert exc.category == ErrorCategory.BUSINESS_LOGIC
        assert exc.severity == ErrorSeverity.MEDIUM
        assert exc.context == {}
    
    @pytest.mark.unit
    def test_wms_exception_to_dict(self):
        """WMSException to_dict testi"""
        exc = WMSException(
            "Test error",
            error_code="TEST_ERROR",
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.CRITICAL
        )
        
        result = exc.to_dict()
        
        assert isinstance(result, dict)
        assert result["message"] == "Test error"
        assert result["error_code"] == "TEST_ERROR"
        assert result["category"] == "database"
        assert result["severity"] == "critical"


class TestDatabaseExceptions:
    """Database exception testleri"""
    
    @pytest.mark.unit
    def test_database_exception(self):
        """DatabaseException testi"""
        exc = DatabaseException("DB error")
        
        assert exc.category == ErrorCategory.DATABASE
        assert exc.severity == ErrorSeverity.HIGH
    
    @pytest.mark.unit
    def test_connection_exception(self):
        """ConnectionException testi"""
        exc = ConnectionException()
        
        assert exc.message == "Veritabanı bağlantısı kurulamadı"
        assert exc.error_code == "DB_CONNECTION_FAILED"
        assert exc.severity == ErrorSeverity.CRITICAL
    
    @pytest.mark.unit
    def test_query_exception(self):
        """QueryException testi"""
        exc = QueryException("Query failed", query="SELECT * FROM table")
        
        assert exc.error_code == "DB_QUERY_FAILED"
        assert exc.context["query"] == "SELECT * FROM table"


class TestAuthenticationExceptions:
    """Authentication exception testleri"""
    
    @pytest.mark.unit
    def test_authentication_exception(self):
        """AuthenticationException testi"""
        exc = AuthenticationException()
        
        assert exc.message == "Kimlik doğrulaması başarısız"
        assert exc.error_code == "AUTH_FAILED"
        assert exc.category == ErrorCategory.AUTHENTICATION
        assert exc.severity == ErrorSeverity.HIGH
    
    @pytest.mark.unit
    def test_authorization_exception(self):
        """AuthorizationException testi"""
        exc = AuthorizationException()
        
        assert exc.message == "Bu işlem için yetkiniz yok"
        assert exc.error_code == "AUTHORIZATION_DENIED"
        assert exc.category == ErrorCategory.AUTHORIZATION
    
    @pytest.mark.unit
    def test_invalid_user_exception(self):
        """InvalidUserException testi"""
        exc = InvalidUserException("testuser")
        
        assert exc.message == "Geçersiz kullanıcı: testuser"
        assert exc.error_code == "INVALID_USER"
        assert exc.context["username"] == "testuser"
    
    @pytest.mark.unit
    def test_inactive_user_exception(self):
        """InactiveUserException testi"""
        exc = InactiveUserException("testuser")
        
        assert exc.message == "Kullanıcı aktif değil: testuser"
        assert exc.error_code == "USER_INACTIVE"
        assert exc.context["username"] == "testuser"


class TestBusinessLogicExceptions:
    """Business logic exception testleri"""
    
    @pytest.mark.unit
    def test_validation_exception(self):
        """ValidationException testi"""
        exc = ValidationException("Invalid data", field="username")
        
        assert exc.category == ErrorCategory.VALIDATION
        assert exc.severity == ErrorSeverity.LOW
        assert exc.error_code == "VALIDATION_FAILED"
        assert exc.context["field"] == "username"
    
    @pytest.mark.unit
    def test_order_not_found_exception(self):
        """OrderNotFoundException testi"""
        exc = OrderNotFoundException("ORD-123")
        
        assert exc.message == "Sipariş bulunamadı: ORD-123"
        assert exc.error_code == "ORDER_NOT_FOUND"
        assert exc.context["order_no"] == "ORD-123"
    
    @pytest.mark.unit
    def test_insufficient_stock_exception(self):
        """InsufficientStockException testi"""
        exc = InsufficientStockException("ITEM-001", 10, 5)
        
        assert "Yetersiz stok" in exc.message
        assert exc.error_code == "INSUFFICIENT_STOCK"
        assert exc.context["item_code"] == "ITEM-001"
        assert exc.context["requested_qty"] == 10
        assert exc.context["available_qty"] == 5
    
    @pytest.mark.unit
    def test_barcode_not_found_exception(self):
        """BarcodeNotFoundException testi"""
        exc = BarcodeNotFoundException("1234567890")
        
        assert exc.message == "Barkod bulunamadı: 1234567890"
        assert exc.error_code == "BARCODE_NOT_FOUND"
        assert exc.context["barcode"] == "1234567890"
    
    @pytest.mark.unit
    def test_invalid_barcode_exception(self):
        """InvalidBarcodeException testi"""
        exc = InvalidBarcodeException("invalid")
        
        assert exc.message == "Geçersiz barkod formatı: invalid"
        assert exc.error_code == "INVALID_BARCODE"
        assert exc.context["barcode"] == "invalid"


class TestExceptionDecorator:
    """Exception decorator testleri"""
    
    @pytest.mark.unit
    def test_handle_exceptions_decorator_success(self):
        """handle_exceptions decorator başarılı durum testi"""
        
        @handle_exceptions("Test failed")
        def test_function():
            return "success"
        
        result = test_function()
        assert result == "success"
    
    @pytest.mark.unit
    def test_handle_exceptions_decorator_wms_exception(self):
        """handle_exceptions decorator WMS exception testi"""
        
        @handle_exceptions("Test failed", reraise=False)
        def test_function():
            raise WMSException("Test error")
        
        result = test_function()
        assert result is None
    
    @pytest.mark.unit
    @patch('app.core.exceptions.logger')
    def test_handle_exceptions_decorator_generic_exception(self, mock_logger):
        """handle_exceptions decorator generic exception testi"""
        
        @handle_exceptions("Test failed", reraise=False)
        def test_function():
            raise ValueError("Generic error")
        
        result = test_function()
        assert result is None
        mock_logger.exception.assert_called_once()
    
    @pytest.mark.unit
    def test_handle_exceptions_decorator_reraise(self):
        """handle_exceptions decorator reraise testi"""
        
        @handle_exceptions("Test failed", reraise=True)
        def test_function():
            raise ValueError("Generic error")
        
        with pytest.raises(WMSException) as exc_info:
            test_function()
        
        assert "Test failed: Generic error" in str(exc_info.value)
        assert exc_info.value.error_code == "UNEXPECTED_ERROR"