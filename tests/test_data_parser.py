"""
Tests for data parser module
"""

import pandas as pd

from ibkr_toolkit.parsers.data_parser import (
    calculate_summary,
    parse_dividends,
    parse_trades,
    parse_withholding_tax,
    safe_float,
)


def test_safe_float():
    """Test safe_float function"""
    assert safe_float("10.5") == 10.5
    assert safe_float(None) == 0.0
    assert safe_float("") == 0.0
    assert safe_float("invalid", 5.0) == 5.0
    assert safe_float(42) == 42.0


def test_parse_trades(sample_flex_data):
    """Test parsing trade data"""
    df = parse_trades(sample_flex_data)

    assert not df.empty
    assert len(df) == 1
    assert df.iloc[0]["Symbol"] == "AAPL"
    assert df.iloc[0]["Quantity"] == 10.0
    assert df.iloc[0]["Realized P&L"] == 100.0


def test_parse_trades_empty():
    """Test parsing with no trade data"""
    df = parse_trades({})
    assert df.empty


def test_parse_dividends(sample_flex_data):
    """Test parsing dividend data"""
    df = parse_dividends(sample_flex_data)

    assert not df.empty
    assert len(df) == 1
    assert df.iloc[0]["Symbol"] == "AAPL"
    assert df.iloc[0]["Amount"] == 10.5


def test_parse_dividends_empty():
    """Test parsing with no dividend data"""
    df = parse_dividends({})
    assert df.empty


def test_parse_withholding_tax(sample_flex_data):
    """Test parsing withholding tax data"""
    df = parse_withholding_tax(sample_flex_data)

    assert not df.empty
    assert len(df) == 1
    assert df.iloc[0]["Symbol"] == "AAPL"
    assert df.iloc[0]["Amount"] == 1.5  # Absolute value


def test_parse_withholding_tax_empty():
    """Test parsing with no tax data"""
    df = parse_withholding_tax({})
    assert df.empty


def test_calculate_summary(sample_flex_data):
    """Test calculating summary"""
    trades_df = parse_trades(sample_flex_data)
    dividends_df = parse_dividends(sample_flex_data)
    tax_df = parse_withholding_tax(sample_flex_data)

    summary = calculate_summary(
        trades_df, dividends_df, tax_df, use_dynamic_rates=False, default_rate=7.0
    )

    assert "Trade_Summary" in summary
    assert "Dividend_Summary" in summary
    assert "Tax_Summary" in summary
    assert "China_Tax_Calculation" in summary

    # Check trade summary
    assert summary["Trade_Summary"]["Total_Trades"] == 1
    assert summary["Trade_Summary"]["Realized_P&L_USD"] == 100.0

    # Check dividend summary
    assert summary["Dividend_Summary"]["Total_Amount_USD"] == 10.5

    # Check tax summary
    assert summary["Tax_Summary"]["Total_Withholding_Tax_USD"] == 1.5


def test_calculate_summary_empty():
    """Test calculating summary with empty data"""
    empty_df = pd.DataFrame()
    summary = calculate_summary(empty_df, empty_df, empty_df)

    assert summary == {}
