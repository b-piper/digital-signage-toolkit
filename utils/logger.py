"""Centralized logging module with audit trail support."""
import logging
import logging.handlers
import os
from pathlib import Path
from datetime import datetime
from typing import Optional


from digital_signage_toolkit.utils.config import Config

class AuditLogger:
    """Audit logger for privileged operations."""
    
    def __init__(self, log_dir: Optional[Path] = None):
        # Determine strict log directory
        # 1. /var/log/dst-toolkit (Enterprise Standard) if we have permission
        # 2. ~/.dst-toolkit/logs (Fallback)
        
        system_log_dir = Path("/var/log/dst-toolkit")
        user_log_dir = Path.home() / ".dst-toolkit" / "logs"
        
        if os.access("/var/log", os.W_OK) or (system_log_dir.exists() and os.access(system_log_dir, os.W_OK)):
            # We are root or have rights to the system dir
            self.log_dir = system_log_dir
        else:
            self.log_dir = user_log_dir
            
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            # If creating user log dir, restrict it
            if self.log_dir == user_log_dir:
                 os.chmod(self.log_dir, 0o700)
        except PermissionError:
            # Absolute fallback
            self.log_dir = Path("/tmp/dst-toolkit-logs")
            self.log_dir.mkdir(parents=True, exist_ok=True)

        self.log_file = self.log_dir / "audit.log"      
        # Set secure permissions on log directory
        try:
            self.log_dir.chmod(0o750)
        except Exception:
            # If we can't set permissions (e.g., not root), continue anyway
            pass
        
        self.config = Config()
        
        # Main application log
        self.app_logger = self._setup_logger(
            'digital_signage_toolkit',
            self.log_dir / 'application.log',
            level=logging.INFO
        )
        
        # Audit log for privileged operations
        self.audit_logger = self._setup_logger(
            'digital_signage_toolkit.audit',
            self.log_dir / 'audit.log',
            level=logging.INFO,
            formatter='audit'
        )
        
        # Error log
        self.error_logger = self._setup_logger(
            'digital_signage_toolkit.error',
            self.log_dir / 'error.log',
            level=logging.ERROR
        )
    
    def _setup_logger(self, name: str, log_file: Path, 
                     level: int = logging.INFO,
                     formatter: str = 'standard') -> logging.Logger:
        """Setup a logger with rotation."""
        logger = logging.getLogger(name)
        logger.setLevel(level)
        
        # Avoid duplicate handlers
        if logger.handlers:
            return logger
        
        # Create formatters
        if formatter == 'audit':
            fmt = logging.Formatter(
                '%(asctime)s | %(levelname)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        else:
            fmt = logging.Formatter(
                '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        # File handler with rotation (Default 10MB, keep 5 backups)
        max_bytes = self.config.get('log_max_bytes', 10 * 1024 * 1024)
        backup_count = self.config.get('log_backup_count', 5)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)
        
        # Also log to console in debug mode
        if os.environ.get('DEBUG', '').lower() == 'true':
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            console_handler.setFormatter(fmt)
            logger.addHandler(console_handler)
        
        # Optional syslog handler for centralized logging (enterprise feature)
        if os.environ.get('DST_SYSLOG_ENABLED', '').lower() == 'true':
            try:
                syslog_address = os.environ.get('DST_SYSLOG_ADDRESS', '/dev/log')
                syslog_facility = logging.handlers.SysLogHandler.LOG_LOCAL0
                syslog_handler = logging.handlers.SysLogHandler(
                    address=syslog_address,
                    facility=syslog_facility
                )
                syslog_handler.setLevel(level)
                syslog_fmt = logging.Formatter(
                    f'dst-toolkit[%(process)d]: %(name)s | %(levelname)s | %(message)s'
                )
                syslog_handler.setFormatter(syslog_fmt)
                logger.addHandler(syslog_handler)
            except Exception:
                # Syslog not available, skip silently
                pass
        
        return logger
    
    def log_operation(self, operation: str, user: str, 
                     details: Optional[str] = None, 
                     success: bool = True) -> None:
        """Log a privileged operation to audit trail."""
        status = "SUCCESS" if success else "FAILED"
        message = f"{operation} | User: {user} | Status: {status}"
        if details:
            message += f" | Details: {details}"
        
        self.audit_logger.info(message)
        self.app_logger.info(f"Audit: {message}")
    
    def log_security_event(self, event_type: str, details: str) -> None:
        """Log security-related events."""
        message = f"SECURITY | {event_type} | {details}"
        self.audit_logger.warning(message)
        self.error_logger.warning(message)
    
    def log_error(self, error: Exception, context: Optional[str] = None) -> None:
        """Log an error with context."""
        message = f"Error: {str(error)}"
        if context:
            message = f"{context} | {message}"
        self.error_logger.error(message, exc_info=True)
        self.app_logger.error(message)


# Global logger instance
_logger_instance: Optional[AuditLogger] = None


def get_logger() -> AuditLogger:
    """Get or create the global logger instance."""
    global _logger_instance
    if _logger_instance is None:
        # Try system log dir first, fallback to user dir
        try:
            _logger_instance = AuditLogger()
        except PermissionError:
            # Fallback to user directory if we can't write to /var/log
            user_log_dir = Path.home() / '.local' / 'log' / 'digital-signage-toolkit'
            _logger_instance = AuditLogger(user_log_dir)
    
    return _logger_instance

