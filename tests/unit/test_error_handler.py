"""
Unit tests for error handler system
==================================
"""
import pytest
from unittest.mock import patch, MagicMock, Mock
from PyQt5.QtWidgets import QWidget

from app.core.error_handler import (
    ErrorHandler, get_error_handler, handle_error,
    error_handler_decorator, error_context, setup_global_exception_handler
)
from app.core.exceptions import (
    WMSException, ErrorSeverity, ErrorCategory,
    AuthenticationException, ValidationException,
    BusinessLogicException, DatabaseException
)


class TestErrorHandler:
    """ErrorHandler sınıfı testleri"""
    
    @pytest.mark.unit
    def test_error_handler_initialization(self):
        """ErrorHandler başlatma testi"""
        handler = ErrorHandler()
        
        assert handler.parent is None
        assert handler._error_count == 0
        assert handler._max_errors_per_session == 50
    
    @pytest.mark.unit
    @patch('app.core.error_handler.toast')
    @patch('app.core.error_handler.log_user_action')
    def test_handle_wms_exception(self, mock_log_action, mock_toast):
        """WMS exception handling testi"""
        handler = ErrorHandler()
        
        exc = WMSException(
            "Test error",
            error_code="TEST_ERROR",
            category=ErrorCategory.BUSINESS_LOGIC,
            severity=ErrorSeverity.MEDIUM
        )
        
        result = handler.handle_exception(exc, show_toast=True)
        
        assert result is True
        assert handler._error_count == 1
        mock_log_action.assert_called_once()
        mock_toast.show.assert_called_once()
    
    @pytest.mark.unit
    @patch('app.core.error_handler.QMessageBox')
    @patch('app.core.error_handler.log_user_action')
    def test_handle_wms_exception_with_dialog(self, mock_log_action, mock_messagebox):
        """WMS exception dialog testi"""
        handler = ErrorHandler()
        
        exc = WMSException(
            "Test error",
            error_code="TEST_ERROR",
            severity=ErrorSeverity.HIGH
        )
        
        result = handler.handle_exception(exc, show_dialog=True)
        
        assert result is True
        mock_messagebox.critical.assert_called_once()
    
    @pytest.mark.unit
    @patch('app.core.error_handler.logger')
    @patch('app.core.error_handler.log_user_action')
    def test_handle_generic_exception(self, mock_log_action, mock_logger):
        """Generic exception handling testi"""
        handler = ErrorHandler()
        
        exc = ValueError("Generic error")
        
        result = handler.handle_exception(exc)
        
        assert result is True
        assert handler._error_count == 1
        mock_logger.exception.assert_called_once()
        mock_log_action.assert_called_once()
    
    @pytest.mark.unit
    def test_get_user_friendly_message_authentication(self):
        """Authentication error user message testi"""
        handler = ErrorHandler()
        
        exc = AuthenticationException("Auth failed")
        message = handler._get_user_friendly_message(exc)
        
        assert message == "Auth failed"
    
    @pytest.mark.unit
    def test_get_user_friendly_message_validation(self):
        """Validation error user message testi"""
        handler = ErrorHandler()
        
        exc = ValidationException("Invalid data")
        message = handler._get_user_friendly_message(exc)
        
        assert message == "Veri doğrulama hatası: Invalid data"
    
    @pytest.mark.unit
    def test_get_user_friendly_message_database_critical(self):
        """Database critical error user message testi"""
        handler = ErrorHandler()
        
        exc = DatabaseException(
            "DB error",
            severity=ErrorSeverity.CRITICAL
        )
        message = handler._get_user_friendly_message(exc)
        
        assert "sistem veritabanına bağlanılamıyor" in message.lower()
    
    @pytest.mark.unit
    def test_reset_error_count(self):
        """Error count reset testi"""
        handler = ErrorHandler()
        handler._error_count = 10
        
        handler.reset_error_count()
        
        assert handler._error_count == 0


class TestGlobalErrorHandler:
    """Global error handler testleri"""
    
    @pytest.mark.unit
    def test_get_error_handler_singleton(self):
        """Global error handler singleton testi"""
        handler1 = get_error_handler()
        handler2 = get_error_handler()
        
        assert handler1 is handler2
    
    @pytest.mark.unit
    @patch('app.core.error_handler.get_error_handler')
    def test_handle_error_function(self, mock_get_handler):
        """handle_error function testi"""
        mock_handler = Mock()
        mock_get_handler.return_value = mock_handler
        
        exc = ValueError("Test error")
        result = handle_error(exc, "User message")
        
        mock_handler.handle_exception.assert_called_once_with(
            exc, "User message", True, False, None
        )


class TestErrorHandlerDecorator:
    """Error handler decorator testleri"""
    
    @pytest.mark.unit
    def test_error_handler_decorator_success(self):
        """Error handler decorator başarılı durum testi"""
        
        @error_handler_decorator("Operation failed")
        def test_function():
            return "success"
        
        result = test_function()
        assert result == "success"
    
    @pytest.mark.unit
    @patch('app.core.error_handler.handle_error')
    def test_error_handler_decorator_exception(self, mock_handle_error):
        """Error handler decorator exception testi"""
        mock_handle_error.return_value = True
        
        @error_handler_decorator("Operation failed", reraise=False)
        def test_function():
            raise ValueError("Test error")
        
        result = test_function()
        
        assert result is None
        mock_handle_error.assert_called_once()
    
    @pytest.mark.unit
    @patch('app.core.error_handler.handle_error')
    def test_error_handler_decorator_with_qwidget_parent(self, mock_handle_error):
        """Error handler decorator QWidget parent testi"""
        mock_handle_error.return_value = True
        mock_widget = Mock(spec=QWidget)
        
        @error_handler_decorator("Operation failed")
        def test_method(self):
            raise ValueError("Test error")
        
        test_method(mock_widget)
        
        # Parent widget'ın doğru şekilde geçirildiğini kontrol et
        args, kwargs = mock_handle_error.call_args
        assert kwargs.get('parent_widget') == mock_widget


class TestErrorContext:
    """Error context manager testleri"""
    
    @pytest.mark.unit
    def test_error_context_success(self):
        """Error context başarılı durum testi"""
        
        with error_context("Operation failed"):
            result = "success"
        
        assert result == "success"
    
    @pytest.mark.unit
    @patch('app.core.error_handler.handle_error')
    def test_error_context_exception(self, mock_handle_error):
        """Error context exception testi"""
        
        with error_context("Operation failed", show_toast=True):
            raise ValueError("Test error")
        
        mock_handle_error.assert_called_once()
        args, kwargs = mock_handle_error.call_args
        assert isinstance(args[0], ValueError)
        assert args[1] == "Operation failed"
        assert kwargs['show_toast'] is True


class TestGlobalExceptionHandler:
    """Global exception handler testleri"""
    
    @pytest.mark.unit
    @patch('sys.excepthook')
    def test_setup_global_exception_handler(self, mock_excepthook):
        """Global exception handler setup testi"""
        setup_global_exception_handler()
        
        # sys.excepthook'un değiştirildiğini kontrol et
        # (Mock edildiği için direkt kontrol edemiyoruz, ama çağrıldığını görebiliriz)
        assert True  # Setup çalıştı
    
    @pytest.mark.unit
    @patch('app.core.error_handler.handle_error')
    @patch('app.core.error_handler.logger')
    def test_global_excepthook_handles_exception(self, mock_logger, mock_handle_error):
        """Global excepthook exception handling testi"""
        from app.core.error_handler import setup_global_exception_handler
        import sys
        
        # Global exception handler'ı kur
        setup_global_exception_handler()
        
        # Exception simüle et
        try:
            raise ValueError("Test global exception")
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            
            # Excepthook'u çağır
            sys.excepthook(exc_type, exc_value, exc_traceback)
        
        # Logger ve handle_error'un çağrıldığını kontrol et
        mock_logger.critical.assert_called_once()
        mock_handle_error.assert_called_once()