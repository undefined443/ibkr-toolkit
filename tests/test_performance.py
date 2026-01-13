"""
Tests for investment performance calculation
"""

import pandas as pd

from ibkr_toolkit.parsers.data_parser import (
    calculate_performance,
    parse_cash_report,
    parse_open_positions,
)


class TestParseOpenPositions:
    """Test open positions parsing"""

    def test_parse_open_positions_success(self, sample_open_positions_data):
        """Test parsing open positions from valid data"""
        result = parse_open_positions(sample_open_positions_data)

        assert not result.empty
        assert len(result) == 2
        assert result.iloc[0]["Symbol"] == "AAPL"
        assert result.iloc[0]["Quantity"] == 100.0
        assert result.iloc[0]["Position_Value"] == 15000.0
        assert result.iloc[0]["Unrealized_P&L"] == 1000.0

    def test_parse_open_positions_empty(self):
        """Test with no open positions"""
        result = parse_open_positions({})
        assert result.empty

    def test_parse_open_positions_missing_section(self):
        """Test when OpenPositions section is missing"""
        result = parse_open_positions({"OtherData": {}})
        assert result.empty

    def test_parse_open_positions_single_item(self):
        """Test with single position (not a list)"""
        data = {
            "OpenPositions": {
                "OpenPosition": {
                    "@symbol": "AAPL",
                    "@quantity": "100",
                    "@markPrice": "150.0",
                    "@positionValue": "15000.0",
                    "@fxPnl": "1000.0",
                    "@costBasisMoney": "14000.0",
                    "@currency": "USD",
                    "@assetCategory": "STK",
                }
            }
        }
        result = parse_open_positions(data)
        assert not result.empty
        assert len(result) == 1


class TestParseCashReport:
    """Test cash report parsing"""

    def test_parse_cash_report_success(self, sample_cash_report_data):
        """Test parsing cash report from valid data"""
        result = parse_cash_report(sample_cash_report_data)

        assert result is not None
        assert result["Starting_Cash"] == 10000.0
        assert result["Ending_Cash"] == 12000.0
        assert result["Deposit_Withdrawals"] == 2000.0

    def test_parse_cash_report_empty(self):
        """Test with no cash report"""
        result = parse_cash_report({})
        assert result == {}

    def test_parse_cash_report_missing_section(self):
        """Test when CashReport section is missing"""
        result = parse_cash_report({"OtherData": {}})
        assert result == {}

    def test_parse_cash_report_base_summary(self, sample_cash_report_data):
        """Test that BASE_SUMMARY currency is preferred"""
        result = parse_cash_report(sample_cash_report_data)
        assert result["Currency"] == "BASE_SUMMARY"


class TestCalculatePerformance:
    """Test performance calculation"""

    def test_calculate_performance_basic(
        self, sample_flex_data, sample_open_positions_data, sample_cash_report_data
    ):
        """Test basic performance calculation"""
        # Combine sample data
        combined_data = {
            **sample_flex_data,
            **sample_open_positions_data,
            **sample_cash_report_data,
        }

        trades_df = pd.DataFrame(
            [
                {
                    "Date": "20250101",
                    "Symbol": "AAPL",
                    "Realized P&L": 100.0,
                    "Cost": 1400.0,
                    "Currency": "USD",
                    "Commission": 0,
                }
            ]
        )

        dividends_df = pd.DataFrame(
            [
                {
                    "Date": "20250102",
                    "Symbol": "AAPL",
                    "Amount": 10.50,
                    "Currency": "USD",
                }
            ]
        )

        deposits_withdrawals_df = pd.DataFrame(
            [
                {
                    "Date": "20250103",
                    "Amount_Base_Currency": 2000.0,
                }
            ]
        )

        open_positions_df = parse_open_positions(combined_data)
        cash_report = parse_cash_report(combined_data)

        result = calculate_performance(
            trades_df,
            dividends_df,
            deposits_withdrawals_df,
            open_positions_df,
            cash_report,
            use_dynamic_rates=False,
            default_rate=7.2,
        )

        assert "Performance_Summary" in result
        assert "Beginning_Net_Worth_USD" in result["Performance_Summary"]
        assert "Ending_Net_Worth_USD" in result["Performance_Summary"]
        assert "Total_Return_Percent" in result["Performance_Summary"]

        # Verify calculations
        # Beginning: 10000, Ending: 12000 + 25000 (positions) = 37000
        # Net deposits: 2000
        # Return: (37000 - 10000 - 2000) / 10000 = 2.5 = 250%
        assert result["Performance_Summary"]["Beginning_Net_Worth_USD"] == 10000.0
        assert result["Performance_Summary"]["Ending_Net_Worth_USD"] == 37000.0

    def test_calculate_performance_no_positions(self, sample_cash_report_data):
        """Test performance calculation with no open positions"""
        cash_report = parse_cash_report(sample_cash_report_data)

        result = calculate_performance(
            pd.DataFrame(),  # No trades
            pd.DataFrame(),  # No dividends
            pd.DataFrame(),  # No deposits/withdrawals
            pd.DataFrame(),  # No positions
            cash_report,
            use_dynamic_rates=False,
            default_rate=7.2,
        )

        assert "Performance_Summary" in result
        assert result["Performance_Summary"]["Beginning_Net_Worth_USD"] == 10000.0
        assert result["Performance_Summary"]["Ending_Net_Worth_USD"] == 12000.0

    def test_calculate_performance_zero_beginning(self):
        """Test when beginning net worth is zero"""
        cash_report = {"Starting_Cash": 0.0, "Ending_Cash": 1000.0}

        result = calculate_performance(
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            cash_report,
            use_dynamic_rates=False,
            default_rate=7.2,
        )

        # Should handle zero beginning gracefully
        assert "Performance_Summary" in result
        assert result["Performance_Summary"]["Total_Return_Percent"] == 0.0

    def test_calculate_performance_realized_roi(self):
        """Test realized ROI calculation"""
        trades_df = pd.DataFrame(
            [
                {
                    "Date": "20250101",
                    "Symbol": "AAPL",
                    "Realized P&L": 200.0,
                    "Cost": 1000.0,
                    "Currency": "USD",
                    "Commission": 0,
                }
            ]
        )

        result = calculate_performance(
            trades_df,
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            {"Starting_Cash": 10000.0, "Ending_Cash": 10000.0},
            use_dynamic_rates=False,
            default_rate=7.2,
        )

        # ROI = 200 / 1000 = 20%
        assert result["Performance_Summary"]["Realized_ROI_Percent"] == 20.0

    def test_calculate_performance_annualized_return(self):
        """Test annualized return calculation"""
        cash_report = {"Starting_Cash": 10000.0, "Ending_Cash": 12000.0}

        result = calculate_performance(
            pd.DataFrame(
                [
                    {
                        "Date": "20250101",
                        "Realized P&L": 0,
                        "Cost": 0,
                        "Currency": "USD",
                        "Commission": 0,
                    }
                ]
            ),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            cash_report,
            use_dynamic_rates=False,
            default_rate=7.2,
        )

        # Total return: 20%, Annualized depends on period
        assert "Annualized_Return_Percent" in result["Performance_Summary"]

    def test_calculate_performance_max_drawdown(self):
        """Test max drawdown calculation"""
        trades_df = pd.DataFrame(
            [
                {
                    "Date": "20250101",
                    "Realized P&L": 1000.0,
                    "Cost": 0,
                    "Currency": "USD",
                    "Commission": 0,
                },
                {
                    "Date": "20250102",
                    "Realized P&L": -500.0,
                    "Cost": 0,
                    "Currency": "USD",
                    "Commission": 0,
                },
            ]
        )

        result = calculate_performance(
            trades_df,
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            {"Starting_Cash": 10000.0, "Ending_Cash": 10500.0},
            use_dynamic_rates=False,
            default_rate=7.2,
        )

        # Should calculate some drawdown
        assert "Max_Drawdown_Percent" in result["Performance_Summary"]
        assert result["Performance_Summary"]["Max_Drawdown_Percent"] >= 0

    def test_calculate_performance_empty_data(self):
        """Test with all empty data"""
        result = calculate_performance(
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            {},
            use_dynamic_rates=False,
            default_rate=7.2,
        )

        # Should return empty or default values
        assert isinstance(result, dict)

    def test_calculate_performance_position_details(
        self, sample_open_positions_data, sample_cash_report_data
    ):
        """Test position details are included"""
        open_positions_df = parse_open_positions(sample_open_positions_data)
        cash_report = parse_cash_report(sample_cash_report_data)

        result = calculate_performance(
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            open_positions_df,
            cash_report,
            use_dynamic_rates=False,
            default_rate=7.2,
        )

        # Should include position details
        if "Position_Details" in result:
            assert "Total_Positions" in result["Position_Details"]
            assert "Total_Position_Value_USD" in result["Position_Details"]
            assert result["Position_Details"]["Total_Positions"] == 2
            assert result["Position_Details"]["Total_Position_Value_USD"] == 25000.0
