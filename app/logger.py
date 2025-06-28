"""
Logging Configuration and Utilities
Sets up structured logging for the application with different handlers and formatters
"""

import logging
import logging.handlers
import sys
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional
import traceback

from app.config import settings


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured JSON logs
    """
    
    def __init__(self, service_name: str = "ai-chatbot"):
        super().__init__()
        self.service_name = service_name
        self.hostname = self._get_hostname()
    
    def _get_hostname(self) -> str:
        """Get hostname for log entries"""
        import socket
        try:
            return socket.gethostname()
        except:
            return "unknown"
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        # Build base log entry
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service_name,
            "hostname": self.hostname,
            "environment": settings.ENVIRONMENT,
        }
        
        # Add extra fields from record
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id
        
        if hasattr(record, "chat_id"):
            log_entry["chat_id"] = record.chat_id
        
        # Add error information if present
        if record.exc_info:
            log_entry["error"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Add any extra fields passed via extra parameter
        for key, value in record.__dict__.items():
            if key not in [
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "message", "pathname", "process", "processName", "relativeCreated",
                "stack_info", "thread", "threadName", "exc_info", "exc_text"
            ]:
                log_entry[key] = value
        
        return json.dumps(log_entry, default=str)


class ColoredFormatter(logging.Formatter):
    """
    Colored formatter for console output
    """
    
    # Color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def __init__(self, fmt: str = None):
        super().__init__(fmt or self._get_default_format())
    
    def _get_default_format(self) -> str:
        """Get default format string"""
        return "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors"""
        # Apply color to level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        
        # Format the message
        formatted = super().format(record)
        
        # Reset levelname to original
        record.levelname = levelname
        
        return formatted


class RequestContextFilter(logging.Filter):
    """
    Filter that adds request context to log records
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add request context to log record"""
        # Try to get request context from contextvars
        try:
            from contextvars import copy_context
            context = copy_context()
            
            # Add request ID if available
            request_id = context.get("request_id", None)
            if request_id:
                record.request_id = request_id
            
            # Add user ID if available
            user_id = context.get("user_id", None)
            if user_id:
                record.user_id = user_id
        except:
            pass
        
        return True


def setup_logging(
    log_level: str = None,
    log_file: str = None,
    enable_json_logs: bool = None,
    enable_file_logging: bool = None
) -> logging.Logger:
    """
    Setup logging configuration for the application
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
        enable_json_logs: Whether to use JSON format for logs
        enable_file_logging: Whether to enable file logging
    
    Returns:
        Root logger instance
    """
    # Use settings if parameters not provided
    log_level = log_level or settings.LOG_LEVEL
    enable_json_logs = enable_json_logs if enable_json_logs is not None else settings.LOG_JSON_FORMAT
    enable_file_logging = enable_file_logging if enable_file_logging is not None else settings.LOG_FILE_ENABLED
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # Set formatter based on environment and configuration
    if enable_json_logs or settings.ENVIRONMENT == "production":
        console_formatter = StructuredFormatter()
    else:
        console_formatter = ColoredFormatter(
            fmt="%(asctime)s - %(name)-25s - %(levelname)-8s - %(message)s"
        )
    
    console_handler.setFormatter(console_formatter)
    console_handler.addFilter(RequestContextFilter())
    root_logger.addHandler(console_handler)
    
    # File handler (if enabled)
    if enable_file_logging:
        log_dir = Path(settings.LOG_FILE_PATH).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Use rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            filename=settings.LOG_FILE_PATH,
            maxBytes=settings.LOG_FILE_MAX_BYTES,
            backupCount=settings.LOG_FILE_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        
        # Always use structured format for file logs
        file_formatter = StructuredFormatter()
        file_handler.setFormatter(file_formatter)
        file_handler.addFilter(RequestContextFilter())
        root_logger.addHandler(file_handler)
    
    # Configure specific loggers
    configure_app_loggers()
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured",
        extra={
            "log_level": log_level,
            "json_logs": enable_json_logs,
            "file_logging": enable_file_logging,
            "log_file": settings.LOG_FILE_PATH if enable_file_logging else None
        }
    )
    
    return root_logger


def configure_app_loggers():
    """Configure logging levels for specific application modules"""
    # Set specific log levels for different modules
    log_levels = {
        # Reduce noise from libraries
        "urllib3": logging.WARNING,
        "asyncio": logging.WARNING,
        "aiohttp": logging.WARNING,
        "httpx": logging.WARNING,
        
        # Application modules
        "app.routers": logging.INFO,
        "app.services": logging.INFO,
        "app.middleware": logging.INFO,
        "app.database": logging.INFO,
        
        # Detailed logging for specific services
        "app.services.openai_service": logging.DEBUG if settings.ENVIRONMENT == "development" else logging.INFO,
        "app.services.emotion_service": logging.DEBUG if settings.ENVIRONMENT == "development" else logging.INFO,
        "app.services.personalization_service": logging.DEBUG if settings.ENVIRONMENT == "development" else logging.INFO,
        
        # SQL logging (only in development)
        "sqlalchemy.engine": logging.INFO if settings.ENVIRONMENT == "development" else logging.WARNING,
        "sqlalchemy.pool": logging.INFO if settings.ENVIRONMENT == "development" else logging.WARNING,
    }
    
    for logger_name, level in log_levels.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class LogContext:
    """
    Context manager for adding context to logs
    """
    
    def __init__(self, **kwargs):
        self.context = kwargs
        self.token = None
    
    def __enter__(self):
        """Enter context and set context variables"""
        from contextvars import ContextVar
        
        # Store context in context variables
        self.tokens = {}
        for key, value in self.context.items():
            var = ContextVar(key)
            self.tokens[key] = var.set(value)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and reset context variables"""
        # Reset context variables
        for key, token in self.tokens.items():
            try:
                token.var.reset(token)
            except:
                pass


def log_function_call(func):
    """
    Decorator to log function calls with timing
    """
    import functools
    import time
    
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        start_time = time.time()
        
        logger.debug(
            f"Calling {func.__name__}",
            extra={
                "function": func.__name__,
                "module": func.__module__,
                "args_count": len(args),
                "kwargs_keys": list(kwargs.keys())
            }
        )
        
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            
            logger.debug(
                f"Completed {func.__name__}",
                extra={
                    "function": func.__name__,
                    "module": func.__module__,
                    "duration_seconds": round(duration, 3)
                }
            )
            
            return result
        
        except Exception as e:
            duration = time.time() - start_time
            
            logger.error(
                f"Failed {func.__name__}",
                extra={
                    "function": func.__name__,
                    "module": func.__module__,
                    "duration_seconds": round(duration, 3),
                    "error": str(e),
                    "error_type": type(e).__name__
                },
                exc_info=True
            )
            raise
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        start_time = time.time()
        
        logger.debug(
            f"Calling {func.__name__}",
            extra={
                "function": func.__name__,
                "module": func.__module__,
                "args_count": len(args),
                "kwargs_keys": list(kwargs.keys())
            }
        )
        
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            
            logger.debug(
                f"Completed {func.__name__}",
                extra={
                    "function": func.__name__,
                    "module": func.__module__,
                    "duration_seconds": round(duration, 3)
                }
            )
            
            return result
        
        except Exception as e:
            duration = time.time() - start_time
            
            logger.error(
                f"Failed {func.__name__}",
                extra={
                    "function": func.__name__,
                    "module": func.__module__,
                    "duration_seconds": round(duration, 3),
                    "error": str(e),
                    "error_type": type(e).__name__
                },
                exc_info=True
            )
            raise
    
    # Return appropriate wrapper based on function type
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


# Custom log levels
TRACE_LEVEL = 5
logging.addLevelName(TRACE_LEVEL, "TRACE")

def trace(self, message, *args, **kwargs):
    """Add trace level logging"""
    if self.isEnabledFor(TRACE_LEVEL):
        self._log(TRACE_LEVEL, message, args, **kwargs)

# Add trace method to Logger class
logging.Logger.trace = trace


# Export public interface
__all__ = [
    "setup_logging",
    "get_logger",
    "LogContext",
    "log_function_call",
    "StructuredFormatter",
    "ColoredFormatter",
    "RequestContextFilter"
]