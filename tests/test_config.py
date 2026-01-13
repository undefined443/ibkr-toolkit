"""
Tests for configuration module
"""

from unittest.mock import patch

import pytest

from ibkr_toolkit.config import Config
from ibkr_toolkit.exceptions import ConfigurationError


def test_config_with_valid_env(mock_env):
    """Test configuration with valid environment variables"""
    config = Config()
    assert config.token == "test_token_123"
    assert config.query_id == "test_query_456"
    assert config.exchange_rate == 7.2
    assert config.use_dynamic_rates is False


@patch("ibkr_toolkit.config.load_dotenv")
def test_config_missing_token(mock_load_dotenv, monkeypatch):
    """Test configuration fails without token"""
    # Prevent loading from .env file
    mock_load_dotenv.return_value = None

    monkeypatch.delenv("IBKR_FLEX_TOKEN", raising=False)
    monkeypatch.setenv("IBKR_QUERY_ID", "test_query")

    with pytest.raises(ConfigurationError, match="IBKR_FLEX_TOKEN is required"):
        Config()


@patch("ibkr_toolkit.config.load_dotenv")
def test_config_missing_query_id(mock_load_dotenv, monkeypatch):
    """Test configuration fails without query ID"""
    # Prevent loading from .env file
    mock_load_dotenv.return_value = None

    monkeypatch.setenv("IBKR_FLEX_TOKEN", "test_token")
    monkeypatch.delenv("IBKR_QUERY_ID", raising=False)

    with pytest.raises(ConfigurationError, match="IBKR_QUERY_ID is required"):
        Config()


def test_config_default_values(mock_env, monkeypatch):
    """Test configuration default values"""
    monkeypatch.delenv("USD_CNY_RATE", raising=False)
    monkeypatch.delenv("USE_DYNAMIC_EXCHANGE_RATES", raising=False)

    config = Config()
    assert config.exchange_rate == 7.2  # Default
    assert config.use_dynamic_rates is True  # Default


def test_config_invalid_exchange_rate(mock_env, monkeypatch):
    """Test configuration handles invalid exchange rate"""
    monkeypatch.setenv("USD_CNY_RATE", "invalid")

    config = Config()
    assert config.exchange_rate == 7.2  # Falls back to default
