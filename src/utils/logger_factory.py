import json
import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
import logging
from typing import Dict, Any, List, Optional
from enum import Enum

class LogLevel(str, Enum):
    """Log levels enum matching standard syslog severity levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    NOTICE = "NOTICE"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    ALERT = "ALERT"
    EMERGENCY = "EMERGENCY"

class LoggerInterface(ABC):
    """Abstract base class for all logger implementations"""
    
    @abstractmethod
    def debug(self, message: str, context: Dict[str, Any] = None):
        """Log a debug message"""
        pass
    
    @abstractmethod
    def info(self, message: str, context: Dict[str, Any] = None):
        """Log an info message"""
        pass
    
    @abstractmethod
    def notice(self, message: str, context: Dict[str, Any] = None):
        """Log a notice message"""
        pass
    
    @abstractmethod
    def warning(self, message: str, context: Dict[str, Any] = None):
        """Log a warning message"""
        pass
    
    @abstractmethod
    def error(self, message: str, context: Dict[str, Any] = None, exception: Exception = None):
        """Log an error message"""
        pass
    
    @abstractmethod
    def critical(self, message: str, context: Dict[str, Any] = None, exception: Exception = None):
        """Log a critical message"""
        pass
    
    @abstractmethod
    def alert(self, message: str, context: Dict[str, Any] = None, exception: Exception = None):
        """Log an alert message"""
        pass
    
    @abstractmethod
    def emergency(self, message: str, context: Dict[str, Any] = None, exception: Exception = None):
        """Log an emergency message"""
        pass


class AxiomLogger(LoggerInterface):
    """Axiom implementation of the Logger Interface"""
    
    def __init__(self, service_name: str, dataset: str = None, token: str = None, additional_fields: Dict[str, Any] = None):
        self.service_name = service_name
        self.dataset = dataset or os.getenv("AXIOM_DATASET", "imcrm-logs")
        self.token = token or os.getenv("AXIOM_TOKEN")
        self.additional_fields = {}  # Keep empty for now as per requirement
        
        if not self.token:
            raise ValueError("Axiom token not provided or found in environment variables")
        
        try:
            from axiom_py import Client
            self.client = Client(token=self.token)
            logging.info(f"Axiom logger initialized for service '{service_name}' and dataset '{self.dataset}'")
        except ImportError:
            raise ImportError("Could not import axiom_py. Ensure 'axiom-py' is installed.")
        except Exception as e:
            raise Exception(f"Error initializing Axiom client: {str(e)}")
    
    def _format_log_data(self, message: str, level: str, context: Dict[str, Any] = None, exception: Exception = None) -> Dict[str, Any]:
        """Format log data according to Axiom schema"""
        trace_id = str(uuid.uuid4())
        
        # Default context data - just use trace_id without additional_fields for now
        context_data = {
            "trace_id": trace_id
        }
        
        # Add any provided context
        if context:
            context_data.update(context)
        
        # Add exception info if available
        if exception:
            import traceback
            context_data["exception"] = {
                "trace": ''.join(traceback.format_exception(type(exception), exception, exception.__traceback__)),
                "message": str(exception),
                "code": getattr(exception, 'code', 500)
            }
        
        # Create the log entry
        log_data = {
            "message": message,
            "context": json.dumps(context_data),
            "level": level,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            "service": self.service_name
        }
        
        return log_data
    
    def _send_log(self, log_data: Dict[str, Any]):
        """Send log data to Axiom"""
        try:
            self.client.ingest_events(dataset=self.dataset, events=[log_data])
        except Exception as e:
            # Fallback to console logging if Axiom fails
            fallback_msg = f"Failed to send log to Axiom: {str(e)}\nLog data: {json.dumps(log_data, indent=2)}"
            print(fallback_msg)
    
    def debug(self, message: str, context: Dict[str, Any] = None):
        log_data = self._format_log_data(message, LogLevel.DEBUG, context)
        self._send_log(log_data)
    
    def info(self, message: str, context: Dict[str, Any] = None):
        log_data = self._format_log_data(message, LogLevel.INFO, context)
        self._send_log(log_data)
    
    def notice(self, message: str, context: Dict[str, Any] = None):
        log_data = self._format_log_data(message, LogLevel.NOTICE, context)
        self._send_log(log_data)
    
    def warning(self, message: str, context: Dict[str, Any] = None):
        log_data = self._format_log_data(message, LogLevel.WARNING, context)
        self._send_log(log_data)
    
    def error(self, message: str, context: Dict[str, Any] = None, exception: Exception = None):
        log_data = self._format_log_data(message, LogLevel.ERROR, context, exception)
        self._send_log(log_data)
    
    def critical(self, message: str, context: Dict[str, Any] = None, exception: Exception = None):
        log_data = self._format_log_data(message, LogLevel.CRITICAL, context, exception)
        self._send_log(log_data)
    
    def alert(self, message: str, context: Dict[str, Any] = None, exception: Exception = None):
        log_data = self._format_log_data(message, LogLevel.ALERT, context, exception)
        self._send_log(log_data)
    
    def emergency(self, message: str, context: Dict[str, Any] = None, exception: Exception = None):
        log_data = self._format_log_data(message, LogLevel.EMERGENCY, context, exception)
        self._send_log(log_data)


class ConsoleLogger(LoggerInterface):
    """Simple console logger as fallback"""
    
    # Map our log levels to Python's standard logging levels
    _LEVEL_MAP = {
        LogLevel.DEBUG: logging.DEBUG,
        LogLevel.INFO: logging.INFO,
        LogLevel.NOTICE: logging.INFO + 1,  # Custom level between INFO and WARNING
        LogLevel.WARNING: logging.WARNING,
        LogLevel.ERROR: logging.ERROR,
        LogLevel.CRITICAL: logging.CRITICAL,
        LogLevel.ALERT: logging.CRITICAL + 1,  # Custom level above CRITICAL
        LogLevel.EMERGENCY: logging.CRITICAL + 2  # Custom level above ALERT
    }
    
    def __init__(self, service_name: str, additional_fields: Dict[str, Any] = None):
        self.service_name = service_name
        self.additional_fields = {}  # Keep empty for now as per requirement
        
        # Setup Python's built-in logger with custom levels
        logging.addLevelName(self._LEVEL_MAP[LogLevel.NOTICE], "NOTICE")
        logging.addLevelName(self._LEVEL_MAP[LogLevel.ALERT], "ALERT")
        logging.addLevelName(self._LEVEL_MAP[LogLevel.EMERGENCY], "EMERGENCY")
        
        self.logger = logging.getLogger(service_name)
        self.logger.setLevel(logging.DEBUG)
        
        # Check if handler already exists to avoid duplicating handlers
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def _format_message(self, message: str, context: Dict[str, Any] = None, exception: Exception = None) -> str:
        """Format message with context and exception details for console"""
        log_parts = [message]
        
        # Add context as JSON if available, but skip additional_fields
        if context:
            log_parts.append(f"Context: {json.dumps(context)}")
        
        # Add exception info if available
        if exception:
            log_parts.append(f"Exception: {str(exception)}")
        
        return " | ".join(log_parts)
    
    def _log(self, level: LogLevel, message: str, context: Dict[str, Any] = None, exception: Exception = None):
        """Generic logging method for all levels"""
        formatted_message = self._format_message(message, context, exception)
        self.logger.log(self._LEVEL_MAP[level], formatted_message)
    
    def debug(self, message: str, context: Dict[str, Any] = None):
        self._log(LogLevel.DEBUG, message, context)
    
    def info(self, message: str, context: Dict[str, Any] = None):
        self._log(LogLevel.INFO, message, context)
    
    def notice(self, message: str, context: Dict[str, Any] = None):
        self._log(LogLevel.NOTICE, message, context)
    
    def warning(self, message: str, context: Dict[str, Any] = None):
        self._log(LogLevel.WARNING, message, context)
    
    def error(self, message: str, context: Dict[str, Any] = None, exception: Exception = None):
        self._log(LogLevel.ERROR, message, context, exception)
    
    def critical(self, message: str, context: Dict[str, Any] = None, exception: Exception = None):
        self._log(LogLevel.CRITICAL, message, context, exception)
    
    def alert(self, message: str, context: Dict[str, Any] = None, exception: Exception = None):
        self._log(LogLevel.ALERT, message, context, exception)
    
    def emergency(self, message: str, context: Dict[str, Any] = None, exception: Exception = None):
        self._log(LogLevel.EMERGENCY, message, context, exception)


class LoggerFactory:
    """Factory for creating logger instances"""
    
    @staticmethod
    def create_logger(
        logger_type: str = "auto", 
        service_name: str = "Invest-GPT", 
        dataset: str = None, 
        additional_fields: Dict[str, Any] = None
    ) -> LoggerInterface:
        """
        Create and return a logger instance based on the specified type
        
        Args:
            logger_type: Type of logger to create ('axiom', 'console', or 'auto')
            service_name: Name of the service for logging
            dataset: Dataset name for Axiom logger
            additional_fields: Additional fields to include in all logs (currently not used in logging)
            
        Returns:
            LoggerInterface: A concrete logger implementation
        """
        # Keep additional_fields parameter for future use, but don't pass values to loggers now
        
        # Auto-detect logger type based on environment
        if logger_type == "auto":
            if os.getenv("AXIOM_TOKEN"):
                logger_type = "axiom"
            else:
                logger_type = "console"
        
        # Create logger based on type
        try:
            if logger_type == "axiom":
                return AxiomLogger(
                    service_name=service_name,
                    dataset=dataset,
                    additional_fields={}  # Empty dict for now
                )
            else:
                return ConsoleLogger(
                    service_name=service_name,
                    additional_fields={}  # Empty dict for now
                )
        except Exception as e:
            print(f"Error creating {logger_type} logger: {str(e)}")
            print("Falling back to console logger")
            return ConsoleLogger(
                service_name=service_name,
                additional_fields={}  # Empty dict for now
            )

# Create a default logger instance for direct import
default_logger = LoggerFactory.create_logger() 