"""
Pytest configuration and fixtures
"""

from typing import Dict

import pytest


@pytest.fixture
def sample_config() -> Dict[str, str]:
    """Sample configuration for testing"""
    return {
        "IBKR_FLEX_TOKEN": "test_token_123",
        "IBKR_QUERY_ID": "test_query_456",
        "USD_CNY_RATE": "7.2",
        "USE_DYNAMIC_EXCHANGE_RATES": "false",
    }


@pytest.fixture
def mock_env(sample_config, monkeypatch):
    """Mock environment variables"""
    for key, value in sample_config.items():
        monkeypatch.setenv(key, value)


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create temporary output directory"""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def sample_flex_data() -> Dict:
    """Sample Flex Query response data"""
    return {
        "@accountId": "U1234567",
        "Trades": {
            "Lot": [
                {
                    "@tradeDate": "2025-01-01",
                    "@symbol": "AAPL",
                    "@description": "APPLE INC",
                    "@quantity": "10",
                    "@tradePrice": "150.00",
                    "@proceeds": "1500.00",
                    "@cost": "1400.00",
                    "@fifoPnlRealized": "100.00",
                    "@buySell": "SELL",
                    "@currency": "USD",
                    "@assetCategory": "STK",
                }
            ]
        },
        "CashTransactions": {
            "CashTransaction": [
                {
                    "@dateTime": "2025-01-02",
                    "@symbol": "AAPL",
                    "@description": "AAPL Dividend",
                    "@amount": "10.50",
                    "@currency": "USD",
                    "@type": "Dividends",
                },
                {
                    "@dateTime": "2025-01-02",
                    "@symbol": "AAPL",
                    "@description": "AAPL Withholding Tax",
                    "@amount": "-1.50",
                    "@currency": "USD",
                    "@type": "Withholding Tax",
                },
            ]
        },
    }
