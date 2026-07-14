"""Exceptions for the parsers package."""


class ParserError(Exception):
    """Base exception for all parser-related failures."""
    pass


class ExtractionError(ParserError):
    """Raised when structured content cannot be extracted from text."""
    pass


class JSONParseError(ParserError):
    """Raised when extracted content cannot be parsed into valid JSON."""
    pass


class ValidationError(ParserError):
    """Raised when parsed data fails validation."""
    pass


class SchemaError(ParserError):
    """Raised when the developer provides an invalid schema definition."""
    pass
