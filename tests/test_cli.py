"""
Tests for CLI module
"""

from unittest.mock import patch

import pandas as pd
import pytest

from ibkr_toolkit.cli import (
    _convert_date_columns,
    _format_column_names,
    _sort_by_date_time,
    export_to_excel,
)


def test_sort_by_date_time_with_time():
    """Test sorting by date and time"""
    df = pd.DataFrame(
        {
            "Date": ["20250102", "20250101", "20250101"],
            "Time": ["10:00:00", "15:00:00", "09:00:00"],
            "Symbol": ["AAPL", "TSLA", "GOOGL"],
        }
    )

    result = _sort_by_date_time(df)

    assert list(result["Symbol"]) == ["GOOGL", "TSLA", "AAPL"]
    assert list(result["Date"]) == ["20250101", "20250101", "20250102"]
    assert list(result["Time"]) == ["09:00:00", "15:00:00", "10:00:00"]


def test_sort_by_date_time_without_time():
    """Test sorting by date only when time column is missing"""
    df = pd.DataFrame(
        {
            "Date": ["20250103", "20250101", "20250102"],
            "Symbol": ["AAPL", "TSLA", "GOOGL"],
        }
    )

    result = _sort_by_date_time(df)

    assert list(result["Symbol"]) == ["TSLA", "GOOGL", "AAPL"]
    assert list(result["Date"]) == ["20250101", "20250102", "20250103"]


def test_sort_by_date_time_no_date_column():
    """Test sorting when date column is missing (should return original df)"""
    df = pd.DataFrame(
        {
            "Symbol": ["AAPL", "TSLA", "GOOGL"],
            "Quantity": [10, 20, 30],
        }
    )

    result = _sort_by_date_time(df)

    assert list(result["Symbol"]) == ["AAPL", "TSLA", "GOOGL"]


def test_convert_date_columns_valid_dates():
    """Test date conversion with valid YYYYMMDD dates"""
    df = pd.DataFrame(
        {
            "Date": ["20250101", "20250102", "20250103"],
            "Symbol": ["AAPL", "TSLA", "GOOGL"],
        }
    )

    result = _convert_date_columns(df)

    assert pd.api.types.is_datetime64_any_dtype(result["Date"])
    assert not result["Date"].isna().any()


def test_convert_date_columns_with_time():
    """Test time conversion to time object"""
    df = pd.DataFrame(
        {
            "Date": ["20250101", "20250102"],
            "Time": ["09:30:00", "15:45:30"],
            "Symbol": ["AAPL", "TSLA"],
        }
    )

    result = _convert_date_columns(df)

    assert result["Time"].iloc[0] == pd.to_datetime("09:30:00").time()


def test_convert_date_columns_empty_dataframe():
    """Test date conversion with empty dataframe"""
    df = pd.DataFrame()

    result = _convert_date_columns(df)

    assert result.empty


def test_format_column_names():
    """Test column name formatting"""
    df = pd.DataFrame(
        {
            "realized_pnl": [100.0],
            "total_tax": [20.0],
            "some_column": ["value"],
        }
    )

    result = _format_column_names(df)

    assert "realized pnl" in result.columns
    assert "total tax" in result.columns
    assert "some column" in result.columns


def test_format_column_names_preserves_data():
    """Test that formatting column names preserves data"""
    df = pd.DataFrame(
        {
            "realized_pnl": [100.0, 200.0],
            "symbol": ["AAPL", "TSLA"],
        }
    )

    result = _format_column_names(df)

    assert list(result["realized pnl"]) == [100.0, 200.0]
    assert list(result["symbol"]) == ["AAPL", "TSLA"]


@patch("ibkr_toolkit.cli._format_sheet")
@patch("ibkr_toolkit.cli._merge_summary_categories")
def test_export_to_excel_success(mock_merge, mock_format, tmp_path):
    """Test successful Excel export"""
    trades_df = pd.DataFrame(
        {
            "Date": ["20250101"],
            "Time": ["09:30:00"],
            "Symbol": ["AAPL"],
            "Realized_PnL": [100.0],
        }
    )

    dividends_df = pd.DataFrame(
        {
            "Date": ["20250102"],
            "Symbol": ["AAPL"],
            "Amount": [10.0],
        }
    )

    tax_df = pd.DataFrame(
        {
            "Date": ["20250102"],
            "Symbol": ["AAPL"],
            "Amount": [-1.5],
        }
    )

    deposits_withdrawals_df = pd.DataFrame()
    open_positions_df = pd.DataFrame()

    summary = {
        "Trading": {"Total_PnL": 100.0},
        "Dividends": {"Total_Dividends": 10.0},
    }

    performance = {}

    filepath = tmp_path / "test_output.xlsx"

    export_to_excel(
        trades_df,
        dividends_df,
        tax_df,
        deposits_withdrawals_df,
        open_positions_df,
        summary,
        performance,
        str(filepath),
    )

    assert filepath.exists()


@patch("ibkr_toolkit.cli._format_sheet")
@patch("ibkr_toolkit.cli._merge_summary_categories")
def test_export_to_excel_empty_dataframes(mock_merge, mock_format, tmp_path):
    """Test Excel export with empty dataframes"""
    trades_df = pd.DataFrame()
    dividends_df = pd.DataFrame()
    tax_df = pd.DataFrame()
    deposits_withdrawals_df = pd.DataFrame()
    open_positions_df = pd.DataFrame()

    summary = {}
    performance = {}

    filepath = tmp_path / "test_output.xlsx"

    export_to_excel(
        trades_df,
        dividends_df,
        tax_df,
        deposits_withdrawals_df,
        open_positions_df,
        summary,
        performance,
        str(filepath),
    )

    assert filepath.exists()


@patch("ibkr_toolkit.cli.pd.ExcelWriter")
def test_export_to_excel_io_error(mock_writer):
    """Test Excel export handles IO error"""
    mock_writer.side_effect = Exception("Permission denied")

    trades_df = pd.DataFrame({"Date": ["20250101"]})
    dividends_df = pd.DataFrame()
    tax_df = pd.DataFrame()
    deposits_withdrawals_df = pd.DataFrame()
    open_positions_df = pd.DataFrame()
    summary = {}
    performance = {}

    with pytest.raises(IOError, match="Failed to export Excel file"):
        export_to_excel(
            trades_df,
            dividends_df,
            tax_df,
            deposits_withdrawals_df,
            open_positions_df,
            summary,
            performance,
            "test_output.xlsx",
        )
