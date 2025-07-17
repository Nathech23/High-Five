import logging
import sys
import json
from datetime import datetime
from typing import Dict, Any

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        return json.dumps(log_entry, ensure_ascii=False)

def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Setup logger with JSON formatting"""
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    logger.setLevel(getattr(logging, level.upper()))
    
    # Console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.upper()))
    
    # Set formatter
    formatter = JSONFormatter()
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    logger.propagate = False
    
    return logger

def log_with_context(logger: logging.Logger, level: str, message: str, **context: Any):
    """Log message with additional context"""
    # Create log record with extra fields
    if context:
        extra = {"extra_fields": context}
        getattr(logger, level.lower())(message, extra=extra)
    else:
        getattr(logger, level.lower())(message)

# Common context loggers
def log_api_request(logger: logging.Logger, method: str, path: str, status_code: int, 
                   duration_ms: float, user_id: str = None):
    """Log API request with context"""
    context = {
        "request_method": method,
        "request_path": path,
        "response_status": status_code,
        "duration_ms": duration_ms,
        "user_id": user_id
    }
    log_with_context(logger, "info", f"{method} {path} - {status_code}", **context)

def log_database_operation(logger: logging.Logger, operation: str, table: str, 
                         record_id: str = None, duration_ms: float = None):
    """Log database operation with context"""
    context = {
        "db_operation": operation,
        "db_table": table,
        "record_id": record_id,
        "duration_ms": duration_ms
    }
    log_with_context(logger, "info", f"DB {operation} on {table}", **context)

def log_error_with_context(logger: logging.Logger, error: Exception, 
                         operation: str = None, **context: Any):
    """Log error with full context"""
    error_context = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "operation": operation
    }
    error_context.update(context)
    
    log_with_context(logger, "error", f"Error in {operation}: {str(error)}", **error_context)