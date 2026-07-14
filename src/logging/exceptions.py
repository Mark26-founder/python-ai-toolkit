"""Exceptions for the logging package."""


class LoggingError(Exception):
    """Base exception for all logging-related errors."""
    pass


class LoggerConfigurationError(LoggingError):
    """Raised when logger configuration is invalid or missing."""
    pass


class FormatterError(LoggingError):
    """Raised when log formatting fails."""
    pass


class HandlerError(LoggingError):
    """Raised when handler creation or configuration fails."""
    pass


class ContextError(LoggingError):
    """Raised when context propagation or access fails."""
    pass
