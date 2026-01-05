"""Error handling utilities and decorators."""
import functools
from typing import Callable, Any, Optional
from digital_signage_toolkit.utils.logger import get_logger


def log_operation_errors(operation_name: str, return_on_error: Any = False):
    """Decorator to log errors for operations that silently fail.
    
    Args:
        operation_name: Name of the operation for logging
        return_on_error: Value to return on error (default: False)
    
    Usage:
        @log_operation_errors("APT_UPDATE")
        def apt_update(self) -> bool:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger()
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.log_error(e, operation_name)
                return return_on_error
        return wrapper
    return decorator


def log_operation_errors_with_message(operation_name: str, 
                                     return_on_error: Any = False,
                                     error_message: Optional[str] = None):
    """Decorator to log errors and optionally return a tuple (success, message).
    
    Args:
        operation_name: Name of the operation for logging
        return_on_error: Value to return on error (default: False)
        error_message: Custom error message to include in return tuple
    
    Usage:
        @log_operation_errors_with_message("APT_UPDATE", (False, ""), "Update failed")
        def apt_update(self) -> Tuple[bool, str]:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger()
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_msg = error_message or str(e)
                logger.log_error(e, operation_name)
                
                # If function returns tuple, return tuple with error message
                if isinstance(return_on_error, tuple):
                    return (return_on_error[0], error_msg)
                return return_on_error
        return wrapper
    return decorator




