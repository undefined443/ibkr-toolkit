"""
IBKR Tax Tool
A tool for fetching and processing IBKR trading data for Chinese tax filing
"""

__version__ = "0.1.0"
__author__ = "IBKR Tax Tool Contributors"

from .api.flex_query import FlexQueryClient
from .services.exchange_rate import ExchangeRateService

__all__ = [
    "FlexQueryClient",
    "ExchangeRateService",
]
