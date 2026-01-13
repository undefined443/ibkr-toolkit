"""
Configuration management for IBKR Tax Tool
"""

import os
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

from .constants import DEFAULT_OUTPUT_DIR, DEFAULT_USD_CNY_RATE
from .exceptions import ConfigurationError


class Config:
    """Configuration manager for IBKR Tax Tool"""

    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize configuration

        Args:
            env_file: Optional path to .env file
        """
        # Load .env file
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()

        # Cache configuration values
        self._token = os.getenv("IBKR_FLEX_TOKEN", "")
        self._query_id = os.getenv("IBKR_QUERY_ID", "")

        self._validate()

    def _validate(self) -> None:
        """
        Validate required configuration

        Raises:
            ConfigurationError: If required config is missing
        """
        if not self._token:
            raise ConfigurationError("IBKR_FLEX_TOKEN is required")
        if not self._query_id:
            raise ConfigurationError("IBKR_QUERY_ID is required")

    @property
    def token(self) -> str:
        """Get IBKR Flex Token"""
        return self._token

    @property
    def query_id(self) -> str:
        """Get IBKR Query ID"""
        return self._query_id

    @property
    def exchange_rate(self) -> float:
        """Get default USD to CNY exchange rate"""
        try:
            return float(os.getenv("USD_CNY_RATE", str(DEFAULT_USD_CNY_RATE)))
        except ValueError:
            return DEFAULT_USD_CNY_RATE

    @property
    def use_dynamic_rates(self) -> bool:
        """Check if dynamic exchange rates should be used"""
        return os.getenv("USE_DYNAMIC_EXCHANGE_RATES", "true").lower() == "true"

    @property
    def output_dir(self) -> Path:
        """Get output directory path"""
        return Path(os.getenv("OUTPUT_DIR", DEFAULT_OUTPUT_DIR))

    @property
    def log_level(self) -> str:
        """Get log level"""
        return os.getenv("LOG_LEVEL", "INFO").upper()

    @property
    def log_file(self) -> Optional[str]:
        """Get log file path"""
        return os.getenv("LOG_FILE")

    @property
    def first_trade_year(self) -> Optional[int]:
        """Get first year of trading"""
        year_str = os.getenv("FIRST_TRADE_YEAR")
        if year_str:
            try:
                return int(year_str)
            except ValueError:
                return None
        return None

    # Trading API Configuration
    @property
    def ibkr_gateway_host(self) -> str:
        """Get IBKR Gateway host"""
        return os.getenv("IBKR_GATEWAY_HOST", "127.0.0.1")

    @property
    def ibkr_gateway_port(self) -> int:
        """Get IBKR Gateway port"""
        return int(os.getenv("IBKR_GATEWAY_PORT", "7497"))

    @property
    def ibkr_client_id(self) -> int:
        """Get IBKR client ID"""
        return int(os.getenv("IBKR_CLIENT_ID", "1"))

    @property
    def default_trailing_stop_percent(self) -> float:
        """Get default trailing stop percentage"""
        return float(os.getenv("DEFAULT_TRAILING_STOP_PERCENT", "5.0"))

    # Email Notification Configuration
    @property
    def smtp_host(self) -> Optional[str]:
        """Get SMTP server host"""
        return os.getenv("SMTP_HOST")

    @property
    def smtp_port(self) -> Optional[int]:
        """Get SMTP server port"""
        port = os.getenv("SMTP_PORT")
        return int(port) if port else None

    @property
    def smtp_user(self) -> Optional[str]:
        """Get SMTP username"""
        return os.getenv("SMTP_USER")

    @property
    def smtp_password(self) -> Optional[str]:
        """Get SMTP password"""
        return os.getenv("SMTP_PASSWORD")

    @property
    def email_from(self) -> Optional[str]:
        """Get sender email address"""
        return os.getenv("EMAIL_FROM")

    @property
    def email_to(self) -> Optional[List[str]]:
        """Get recipient email addresses"""
        emails = os.getenv("EMAIL_TO")
        if emails:
            return [e.strip() for e in emails.split(",")]
        return None

    @property
    def smtp_use_tls(self) -> bool:
        """Check if SMTP should use TLS"""
        return os.getenv("SMTP_USE_TLS", "true").lower() == "true"
