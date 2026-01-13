"""
Custom exceptions for IBKR Tax Tool
"""


class IBKRTaxError(Exception):
    """Base exception for IBKR Tax Tool"""

    pass


class ConfigurationError(IBKRTaxError):
    """Raised when configuration is invalid or missing"""

    pass


class APIError(IBKRTaxError):
    """Raised when API request fails"""

    pass


class DataParsingError(IBKRTaxError):
    """Raised when data parsing fails"""

    pass


class ExchangeRateError(IBKRTaxError):
    """Raised when exchange rate fetching fails"""

    pass


class ValidationError(IBKRTaxError):
    """Raised when data validation fails"""

    pass
