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
                    "@tradeDate": "20250101",
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
                    "@dateTime": "20250102",
                    "@symbol": "AAPL",
                    "@description": "AAPL Dividend",
                    "@amount": "10.50",
                    "@currency": "USD",
                    "@type": "Dividends",
                },
                {
                    "@dateTime": "20250102",
                    "@symbol": "AAPL",
                    "@description": "AAPL Withholding Tax",
                    "@amount": "-1.50",
                    "@currency": "USD",
                    "@type": "Withholding Tax",
                },
            ]
        },
    }


@pytest.fixture
def sample_open_positions_data() -> Dict:
    """Sample open positions data for testing"""
    return {
        "OpenPositions": {
            "OpenPosition": [
                {
                    "@positionCode": "AAPL",
                    "@symbol": "AAPL",
                    "@description": "APPLE INC",
                    "@quantity": "100",
                    "@markPrice": "150.0",
                    "@positionValue": "15000.0",
                    "@fxPnl": "1000.0",
                    "@costBasisMoney": "14000.0",
                    "@currency": "USD",
                    "@assetCategory": "STK",
                },
                {
                    "@positionCode": "TSLA",
                    "@symbol": "TSLA",
                    "@description": "TESLA INC",
                    "@quantity": "50",
                    "@markPrice": "200.0",
                    "@positionValue": "10000.0",
                    "@fxPnl": "-500.0",
                    "@costBasisMoney": "10500.0",
                    "@currency": "USD",
                    "@assetCategory": "STK",
                },
            ]
        }
    }


@pytest.fixture
def sample_cash_report_data() -> Dict:
    """Sample cash report data"""
    return {
        "CashReport": {
            "CashReportCurrency": {
                "@currency": "BASE_SUMMARY",
                "@startingCash": "10000.0",
                "@endingCash": "12000.0",
                "@depositWithdrawals": "2000.0",
                "@deposits": "3000.0",
                "@withdrawals": "-1000.0",
                "@dividends": "50.0",
                "@commissions": "-1.5",
                "@netTradesSales": "500.0",
                "@netTradesPurchases": "-300.0",
            }
        }
    }
