#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Comprehensive Logging System for Delhi Power Consumption Forecast Application.

This module provides a centralized logging infrastructure with support for:
- Multiple log destinations (file, console, cloud)
- Different log levels based on environment
- Structured logging with contextual information
- Log rotation and archiving
- Performance metrics tracking
- Error aggregation and reporting
"""

import os
import sys
import time
import json
import logging
import logging.handlers
import datetime
import traceback
import threading
import socket
import platform
import uuid
from typing import Dict, List, Optional, Union, Any
from functools import wraps
from pathlib import Path

# Create logs directory if it doesn't exist
log_dir = Path('logs')
log_dir.mkdir(exist_ok=True)

# Default configuration
DEFAULT_CONFIG = {
    'app_name': 'delhi-power-forecast',
    'log_level': 'INFO',
    'console_logging': True,
    'file_logging': True,
    'log_format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'date_format': '%Y-%m-%d %H:%M:%S',
    'max_log_size_mb': 10,
    'backup_count': 5,
    'include_hostname': True,
    'include_process_id': True,
    'structured_logging': True,
    'log_request_body': False,  # For security, don't log request bodies by default
    'sensitive_fields': ['password', 'token', 'api_key', 'secret'],
    'performance_tracking': True,
    'log_to_cloud': False,
    'cloud_logging_service': None,  # 'aws', 'gcp', or 'azure'
}

# Global context for all loggers
GLOBAL_CONTEXT = {}

# Thread local storage for request context
thread_local = threading.local()

class LogFormatter(logging.Formatter):
    """Custom log formatter that supports both text and JSON formats"""
    
    def __init__(self, fmt=None, datefmt=None, style='%', structured=False, 
                 include_hostname=False, include_process_id=False,
                 sensitive_fields=None):
        super().__init__(fmt, datefmt, style)
        self.structured = structured
        self.include_hostname = include_hostname
        self.include_process_id = include_process_id
        self.hostname = socket.gethostname() if include_hostname else None
        self.pid = os.getpid() if include_process_id else None
        self.sensitive_fields = sensitive_fields or []
    
    def format(self, record):
        if self.structured:
            return self._format_json(record)
        return super().format(record)
    
    def _format_json(self, record):
        """Format log record as JSON"""
        # Start with the basic record attributes
        log_data = {
            'timestamp': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        
        # Add source location
        log_data.update({
            'location': {
                'file': record.pathname,
                'line': record.lineno,
                'function': record.funcName,
            }
        })
        
        # Add contextual information
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
            
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
            
        if hasattr(record, 'session_id'):
            log_data['session_id'] = record.session_id
            
        # Add all extra attributes
        for key, value in record.__dict__.items():
            if key not in ('args', 'asctime', 'created', 'exc_info', 'exc_text', 'filename',
                          'funcName', 'id', 'levelname', 'levelno', 'lineno', 'module',
                          'msecs', 'message', 'msg', 'name', 'pathname', 'process',
                          'processName', 'relativeCreated', 'stack_info', 'thread', 'threadName'):
                # Sanitize sensitive fields
                if key in self.sensitive_fields:
                    log_data[key] = '******'
                else:
                    log_data[key] = value
                    
        # Include exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
            
        # Add system information
        if self.include_hostname:
            log_data['hostname'] = self.hostname
            
        if self.include_process_id:
            log_data['pid'] = self.pid
            
        # Add global context
        if GLOBAL_CONTEXT:
            log_data['context'] = GLOBAL_CONTEXT.copy()
            
        # Add thread-local context
        if hasattr(thread_local, 'context') and thread_local.context:
            if 'context' not in log_data:
                log_data['context'] = {}
            log_data['context'].update(thread_local.context)
            
        return json.dumps(log_data)

class LoggerManager:
    """
    Central manager for all application loggers.
    Configures and provides access to different loggers for various components.
    """
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(LoggerManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config_path: Optional[str] = None):
        if self._initialized:
            return
            
        # Load configuration
        self.config = DEFAULT_CONFIG.copy()
        
        if config_path:
            self._load_config(config_path)
            
        # Override with environment variables
        self._load_env_config()
        
        # Initialize root logger
        self.root_logger = logging.getLogger()
        self.root_logger.setLevel(self._get_log_level(self.config['log_level']))
        
        # Clear existing handlers
        for handler in self.root_logger.handlers[:]:
            self.root_logger.removeHandler(handler)
        
        # Add handlers based on configuration
        self._configure_handlers()
        
        # Track performance metrics if enabled
        self.performance_metrics = {}
        if self.config['performance_tracking']:
            self.perf_logger = self.get_logger('performance')
        
        # Set global context
        app_version = os.environ.get('APP_VERSION', '1.0.0')
        environment = os.environ.get('ENVIRONMENT', 'development')
        
        self.set_global_context({
            'app_name': self.config['app_name'],
            'app_version': app_version,
            'environment': environment,
            'python_version': platform.python_version(),
            'platform': platform.platform(),
        })
        
        self._initialized = True
        
        # Log startup
        startup_logger = self.get_logger('system')
        startup_logger.info(f"Logging system initialized for {self.config['app_name']}")
    
    def _load_config(self, config_path: str) -> None:
        """Load configuration from a file"""
        try:
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                self.config.update(user_config)
        except Exception as e:
            sys.stderr.write(f"Error loading logging configuration: {str(e)}\n")
    
    def _load_env_config(self) -> None:
        """Override configuration with environment variables"""
        # LOG_LEVEL environment variable
        env_log_level = os.environ.get('LOG_LEVEL')
        if env_log_level:
            self.config['log_level'] = env_log_level
            
        # APP_NAME environment variable
        env_app_name = os.environ.get('APP_NAME')
        if env_app_name:
            self.config['app_name'] = env_app_name
    
    def _get_log_level(self, level_name: str) -> int:
        """Convert log level name to logging module constant"""
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        return level_map.get(level_name.upper(), logging.INFO)

    def _configure_handlers(self) -> None:
        """Configure log handlers based on configuration"""
        # Console handler
        if self.config['console_logging']:
            console_handler = logging.StreamHandler(sys.stdout)
            formatter = LogFormatter(
                fmt=self.config['log_format'],
                datefmt=self.config['date_format'],
                structured=self.config['structured_logging'],
                include_hostname=self.config['include_hostname'],
                include_process_id=self.config['include_process_id'],
                sensitive_fields=self.config['sensitive_fields']
            )
            console_handler.setFormatter(formatter)
            self.root_logger.addHandler(console_handler)
        
        # File handlers
        if self.config['file_logging']:
            # Main log file
            main_log_path = log_dir / 'app.log'
            main_handler = logging.handlers.RotatingFileHandler(
                main_log_path,
                maxBytes=self.config['max_log_size_mb'] * 1024 * 1024,
                backupCount=self.config['backup_count']
            )
            main_handler.setFormatter(LogFormatter(
                fmt=self.config['log_format'],
                datefmt=self.config['date_format'],
                structured=self.config['structured_logging'],
                include_hostname=self.config['include_hostname'],
                include_process_id=self.config['include_process_id'],
                sensitive_fields=self.config['sensitive_fields']
            ))
            self.root_logger.addHandler(main_handler)
            
            # Error log file
            error_log_path = log_dir / 'error.log'
            error_handler = logging.handlers.RotatingFileHandler(
                error_log_path,
                maxBytes=self.config['max_log_size_mb'] * 1024 * 1024,
                backupCount=self.config['backup_count']
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(LogFormatter(
                fmt=self.config['log_format'],
                datefmt=self.config['date_format'],
                structured=self.config['structured_logging'],
                include_hostname=self.config['include_hostname'],
                include_process_id=self.config['include_process_id'],
                sensitive_fields=self.config['sensitive_fields']
            ))
            self.root_logger.addHandler(error_handler)
            
            # Access log file
            access_log_path = log_dir / 'access.log'
            self.access_handler = logging.handlers.RotatingFileHandler(
                access_log_path,
                maxBytes=self.config['max_log_size_mb'] * 1024 * 1024,
                backupCount=self.config['backup_count']
            )
            self.access_handler.setFormatter(LogFormatter(
                fmt=self.config['log_format'],
                datefmt=self.config['date_format'],
                structured=self.config['structured_logging'],
                include_hostname=self.config['include_hostname'],
                include_process_id=self.config['include_process_id'],
                sensitive_fields=self.config['sensitive_fields']
            ))
            # Don't add to root logger, it's for the access logger only
        
        # Cloud logging if enabled
        if self.config['log_to_cloud'] and self.config['cloud_logging_service']:
            self._setup_cloud_logging()
    
    def _setup_cloud_logging(self) -> None:
        """Setup cloud logging handler based on the configured service"""
        service = self.config['cloud_logging_service'].lower()
        
        if service == 'aws':
            try:
                # AWS CloudWatch Logs integration
                # This is a placeholder - in a real implementation, 
                # you would import and configure a watchtower handler
                pass
            except ImportError:
                sys.stderr.write("AWS CloudWatch integration requires the watchtower package\n")
        
        elif service == 'gcp':
            try:
                # Google Cloud Logging integration
                # This is a placeholder - in a real implementation,
                # you would import and configure a google-cloud-logging handler
                pass
            except ImportError:
                sys.stderr.write("GCP logging integration requires the google-cloud-logging package\n")
        
        elif service == 'azure':
            try:
                # Azure Monitor integration
                # This is a placeholder - in a real implementation,
                # you would import and configure an opencensus-ext-azure handler
                pass
            except ImportError:
                sys.stderr.write("Azure logging integration requires the opencensus-ext-azure package\n")
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a logger with the specified name
        
        Args:
            name: Logger name, will be prefixed with app name
        
        Returns:
            Configured logger instance
        """
        prefix = self.config['app_name']
        logger_name = f"{prefix}.{name}" if name else prefix
        return logging.getLogger(logger_name)
    
    def get_access_logger(self) -> logging.Logger:
        """
        Get a specialized logger for access logs
        
        Returns:
            Access logger instance
        """
        access_logger = logging.getLogger(f"{self.config['app_name']}.access")
        # Ensure it has the access handler
        if hasattr(self, 'access_handler'):
            for handler in access_logger.handlers:
                if handler == self.access_handler:
                    break
            else:
                access_logger.addHandler(self.access_handler)
        return access_logger
    
    def set_global_context(self, context_dict: Dict[str, Any]) -> None:
        """
        Set global context values that will be included in all logs
        
        Args:
            context_dict: Dictionary of context values
        """
        GLOBAL_CONTEXT.update(context_dict)
    
    def clear_global_context(self) -> None:
        """Clear all global context values"""
        GLOBAL_CONTEXT.clear()
    
    def start_request_context(self, request_id: Optional[str] = None, 
                             user_id: Optional[str] = None,
                             session_id: Optional[str] = None,
                             **kwargs) -> str:
        """
        Start a new request context with a unique ID and optional user/session IDs
        
        Args:
            request_id: Optional request ID, will be generated if not provided
            user_id: Optional user ID
            session_id: Optional session ID
            **kwargs: Additional context values
        
        Returns:
            Request ID (either provided or generated)
        """
        if not hasattr(thread_local, 'context'):
            thread_local.context = {}
            
        if request_id is None:
            request_id = str(uuid.uuid4())
            
        thread_local.context['request_id'] = request_id
        
        if user_id:
            thread_local.context['user_id'] = user_id
            
        if session_id:
            thread_local.context['session_id'] = session_id
            
        # Add any additional context
        thread_local.context.update(kwargs)
        
        return request_id
    
    def end_request_context(self) -> None:
        """Clean up the request context at the end of a request"""
        if hasattr(thread_local, 'context'):
            thread_local.context.clear()
    
    def log_request(self, method: str, path: str, status_code: int, 
                   response_time_ms: float, user_id: Optional[str] = None,
                   user_agent: Optional[str] = None, ip: Optional[str] = None,
                   request_size: Optional[int] = None, 
                   response_size: Optional[int] = None) -> None:
        """
        Log an HTTP request
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: Request path
            status_code: HTTP status code
            response_time_ms: Response time in milliseconds
            user_id: Optional user ID
            user_agent: Optional user agent string
            ip: Optional IP address
            request_size: Optional request size in bytes
            response_size: Optional response size in bytes
        """
        access_logger = self.get_access_logger()
        
        extra = {
            'http_method': method,
            'path': path,
            'status_code': status_code,
            'response_time_ms': response_time_ms,
        }
        
        if user_id:
            extra['user_id'] = user_id
            
        if user_agent:
            extra['user_agent'] = user_agent
            
        if ip:
            extra['ip_address'] = ip
            
        if request_size is not None:
            extra['request_size'] = request_size
            
        if response_size is not None:
            extra['response_size'] = response_size
        
        # Include request context if available
        if hasattr(thread_local, 'context'):
            extra.update(thread_local.context)
        
        # Log at appropriate level based on status code
        if status_code >= 500:
            access_logger.error(f"{method} {path} {status_code} {response_time_ms}ms", extra=extra)
        elif status_code >= 400:
            access_logger.warning(f"{method} {path} {status_code} {response_time_ms}ms", extra=extra)
        else:
            access_logger.info(f"{method} {path} {status_code} {response_time_ms}ms", extra=extra)
    
    def track_performance(self, operation: str, start_time: float, 
                         end_time: Optional[float] = None, 
                         success: bool = True) -> float:
        """
        Track performance metrics for an operation
        
        Args:
            operation: Name of the operation
            start_time: Start time (from time.time())
            end_time: Optional end time, current time if not provided
            success: Whether the operation completed successfully
            
        Returns:
            Duration in milliseconds
        """
        if not self.config['performance_tracking']:
            return 0.0
            
        if end_time is None:
            end_time = time.time()
            
        duration_ms = (end_time - start_time) * 1000
        
        # Update metrics
        if operation not in self.performance_metrics:
            self.performance_metrics[operation] = {
                'count': 0,
                'success_count': 0,
                'total_time_ms': 0,
                'min_time_ms': float('inf'),
                'max_time_ms': 0,
            }
            
        metrics = self.performance_metrics[operation]
        metrics['count'] += 1
        if success:
            metrics['success_count'] += 1
        metrics['total_time_ms'] += duration_ms
        metrics['min_time_ms'] = min(metrics['min_time_ms'], duration_ms)
        metrics['max_time_ms'] = max(metrics['max_time_ms'], duration_ms)
        
        # Log the performance data
        self.perf_logger.info(
            f"Performance: {operation} completed in {duration_ms:.2f}ms",
            extra={
                'operation': operation,
                'duration_ms': duration_ms,
                'success': success,
            }
        )
        
        return duration_ms
    
    def get_performance_metrics(self) -> Dict[str, Dict[str, Any]]:
        """
        Get current performance metrics
        
        Returns:
            Dictionary of performance metrics by operation
        """
        result = {}
        
        for operation, metrics in self.performance_metrics.items():
            if metrics['count'] > 0:
                avg_time = metrics['total_time_ms'] / metrics['count']
                success_rate = metrics['success_count'] / metrics['count'] * 100
                
                result[operation] = {
                    'count': metrics['count'],
                    'success_rate': success_rate,
                    'avg_time_ms': avg_time,
                    'min_time_ms': metrics['min_time_ms'],
                    'max_time_ms': metrics['max_time_ms'],
                }
                
        return result


# Performance tracking decorator
def track_performance(operation=None):
    """
    Decorator to track the performance of a function
    
    Args:
        operation: Name of the operation, defaults to function name if not provided
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get the logger manager
            logger_manager = LoggerManager()
            
            # Determine operation name
            op_name = operation or func.__name__
            
            # Record start time
            start_time = time.time()
            success = False
            
            try:
                # Call the function
                result = func(*args, **kwargs)
                success = True
                return result
            finally:
                # Track performance
                logger_manager.track_performance(op_name, start_time, success=success)
        
        return wrapper
    
    # Handle both @track_performance and @track_performance("operation_name")
    if callable(operation):
        func = operation
        operation = None
        return decorator(func)
    
    return decorator


# Streamlit integration
def setup_streamlit_logging():
    """Configure logging integration for Streamlit applications"""
    logger_manager = LoggerManager()
    
    # Get the app logger
    app_logger = logger_manager.get_logger('streamlit')
    
    # Create request ID for the Streamlit session
    session_id = str(uuid.uuid4())
    logger_manager.start_request_context(session_id=session_id)
    
    app_logger.info(f"Streamlit session started with ID: {session_id}")
    
    return app_logger


# Initialize the logger manager as a singleton
logger_manager = LoggerManager()

# Convenience function to get a logger
def get_logger(name=''):
    """Get a configured logger with the specified name"""
    return logger_manager.get_logger(name)


if __name__ == "__main__":
    # Example usage
    logger = get_logger("example")
    logger.info("This is an example log message")
    logger.error("This is an error message", exc_info=True)
    
    # Track performance
    @track_performance
    def example_operation():
        time.sleep(0.1)
        return "Operation completed"
    
    example_operation()
    
    # Log metrics
    metrics = logger_manager.get_performance_metrics()
    print("Performance metrics:", json.dumps(metrics, indent=2))
