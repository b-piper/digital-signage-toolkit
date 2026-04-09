"""Tests for error handling decorators."""
from digital_signage_toolkit.utils.error_handling import log_operation_errors, log_operation_errors_with_message


class TestLogOperationErrors:
    """Test log_operation_errors decorator."""

    def test_decorator_success(self):
        """Test decorator when function succeeds."""
        @log_operation_errors("TEST_OPERATION")
        def test_func():
            return True

        result = test_func()
        assert result is True

    def test_decorator_exception(self):
        """Test decorator when function raises exception."""
        @log_operation_errors("TEST_OPERATION")
        def test_func():
            raise ValueError("Test error")

        result = test_func()
        assert result is False  # Default return value

    def test_decorator_custom_return(self):
        """Test decorator with custom return value."""
        @log_operation_errors("TEST_OPERATION", return_on_error=None)
        def test_func():
            raise ValueError("Test error")

        result = test_func()
        assert result is None

    def test_decorator_preserves_function_metadata(self):
        """Test that decorator preserves function metadata."""
        @log_operation_errors("TEST_OPERATION")
        def test_func():
            """Test function docstring."""
            return True

        assert test_func.__name__ == 'test_func'
        assert 'Test function docstring' in test_func.__doc__


class TestLogOperationErrorsWithMessage:
    """Test log_operation_errors_with_message decorator."""

    def test_decorator_success(self):
        """Test decorator when function succeeds."""
        @log_operation_errors_with_message("TEST_OPERATION", (False, ""))
        def test_func():
            return (True, "Success")

        result = test_func()
        assert result == (True, "Success")

    def test_decorator_exception_with_tuple_return(self):
        """Test decorator when function raises exception and returns tuple."""
        @log_operation_errors_with_message("TEST_OPERATION", (False, ""), "Custom error")
        def test_func():
            raise ValueError("Test error")

        result = test_func()
        assert result == (False, "Custom error")

    def test_decorator_exception_with_default_message(self):
        """Test decorator with default error message."""
        @log_operation_errors_with_message("TEST_OPERATION", (False, ""))
        def test_func():
            raise ValueError("Test error message")

        result = test_func()
        assert result[0] is False
        assert "Test error message" in result[1]

    def test_decorator_non_tuple_return(self):
        """Test decorator with non-tuple return value."""
        @log_operation_errors_with_message("TEST_OPERATION", False)
        def test_func():
            raise ValueError("Test error")

        result = test_func()
        assert result is False

