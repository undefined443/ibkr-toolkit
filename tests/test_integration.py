"""
Integration tests for the complete data processing pipeline
"""

from unittest.mock import Mock, patch

import pytest

from ibkr_tax.api.flex_query import FlexQueryClient
from ibkr_tax.parsers.data_parser import (
    calculate_summary,
    parse_dividends,
    parse_trades,
    parse_withholding_tax,
)


@pytest.fixture
def mock_flex_data_complete():
    """Complete mock Flex Query data with all transaction types"""
    return {
        "@accountId": "U1234567",
        "Trades": {
            "Lot": [
                {
                    "@tradeDate": "20250101",
                    "@dateTime": "20250101;09:30:00",
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
                },
                {
                    "@tradeDate": "20250102",
                    "@dateTime": "20250102;14:15:00",
                    "@symbol": "TSLA",
                    "@description": "TESLA INC",
                    "@quantity": "-5",
                    "@tradePrice": "200.00",
                    "@proceeds": "-1000.00",
                    "@cost": "-950.00",
                    "@fifoPnlRealized": "-50.00",
                    "@buySell": "BUY",
                    "@currency": "USD",
                    "@assetCategory": "STK",
                },
            ]
        },
        "CashTransactions": {
            "CashTransaction": [
                {
                    "@dateTime": "20250103;00:00:00",
                    "@symbol": "AAPL",
                    "@description": "AAPL Dividend",
                    "@amount": "25.50",
                    "@currency": "USD",
                    "@type": "Dividends",
                },
                {
                    "@dateTime": "20250103;00:00:00",
                    "@symbol": "AAPL",
                    "@description": "AAPL Withholding Tax",
                    "@amount": "-3.75",
                    "@currency": "USD",
                    "@type": "Withholding Tax",
                },
            ]
        },
    }


def test_parse_trades_integration(mock_flex_data_complete):
    """Test trades parsing with complete data"""
    trades = parse_trades(mock_flex_data_complete)

    assert not trades.empty
    assert len(trades) == 2
    assert "Symbol" in trades.columns
    assert "Date" in trades.columns
    assert "Time" in trades.columns


def test_parse_dividends_integration(mock_flex_data_complete):
    """Test dividends parsing with complete data"""
    dividends = parse_dividends(mock_flex_data_complete)

    assert not dividends.empty
    assert len(dividends) == 1
    assert dividends["Symbol"].iloc[0] == "AAPL"


def test_parse_withholding_tax_integration(mock_flex_data_complete):
    """Test withholding tax parsing with complete data"""
    taxes = parse_withholding_tax(mock_flex_data_complete)

    assert not taxes.empty
    assert len(taxes) == 1
    assert abs(taxes["Amount"].iloc[0]) == 3.75


def test_calculate_summary_integration(mock_flex_data_complete):
    """Test summary calculation with complete data"""
    trades = parse_trades(mock_flex_data_complete)
    dividends = parse_dividends(mock_flex_data_complete)
    taxes = parse_withholding_tax(mock_flex_data_complete)

    summary = calculate_summary(trades, dividends, taxes, default_rate=7.2)

    assert "Trade_Summary" in summary
    assert "Dividend_Summary" in summary
    assert "Tax_Summary" in summary
    assert "China_Tax_Calculation" in summary


@patch("ibkr_tax.api.flex_query.requests.get")
@patch("ibkr_tax.api.flex_query.xmltodict.parse")
@patch("ibkr_tax.api.flex_query.time.sleep")
def test_api_to_parser_integration(mock_sleep, mock_parse, mock_get, mock_flex_data_complete):
    """Test integration from API fetch to data parsing"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b"<xml>test</xml>"
    mock_get.return_value = mock_response

    mock_parse.side_effect = [
        {"FlexStatementResponse": {"Status": "Success", "ReferenceCode": "REF123"}},
        {
            "FlexStatementResponse": {
                "Status": "Success",
                "FlexStatements": {"FlexStatement": mock_flex_data_complete},
            }
        },
    ]

    client = FlexQueryClient("test_token", "test_query")
    data = client.fetch_data()

    trades = parse_trades(data)
    dividends = parse_dividends(data)

    assert not trades.empty
    assert not dividends.empty
