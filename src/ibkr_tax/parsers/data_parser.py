"""
Data parser for IBKR Flex Query reports
Parses trades, dividends, and withholding tax data
"""

from typing import Any, Dict

import pandas as pd

from ..services.exchange_rate import get_exchange_rate_service


def safe_float(value: Any, default: float = 0.0) -> float:
    """
    Safely convert a value to float, handling empty strings and None

    Args:
        value: Value to convert
        default: Default value if conversion fails

    Returns:
        Float value or default
    """
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def parse_trades(flex_data: Dict[str, Any]) -> pd.DataFrame:
    """
    Parse trade data from Flex Query response
    Uses 'Lot' data which contains closed positions with realized P&L

    Args:
        flex_data: Flex Query response data

    Returns:
        DataFrame with trade details
    """
    # Use Lot data which has closed positions with realized P&L
    trades_section = flex_data.get("Trades")
    if not trades_section or trades_section is None:
        print("  No trade data in this period")
        return pd.DataFrame()

    lots = trades_section.get("Lot", [])

    # Ensure it's a list (single item returns dict)
    if isinstance(lots, dict):
        lots = [lots]

    if not lots:
        print("  No closed lot data found")
        return pd.DataFrame()

    trade_list = []
    for lot in lots:
        trade_list.append(
            {
                "Date": lot.get("@tradeDate", lot.get("@dateTime", "")).split(";")[0]
                if lot.get("@tradeDate") or lot.get("@dateTime")
                else "",
                "Time": lot.get("@dateTime", "").split(";")[1]
                if ";" in lot.get("@dateTime", "")
                else "",
                "Symbol": lot.get("@symbol", ""),
                "Description": lot.get("@description", ""),
                "Quantity": abs(safe_float(lot.get("@quantity"))),
                "Price": safe_float(lot.get("@tradePrice")),
                "Amount": safe_float(lot.get("@proceeds")),
                "Cost": safe_float(lot.get("@cost")),
                "Commission": 0,  # Commission is in the trade records, not lots
                "Realized P&L": safe_float(lot.get("@fifoPnlRealized")),
                "Buy_Sell": lot.get("@buySell", ""),
                "Currency": lot.get("@currency", ""),
                "Asset_Category": lot.get("@assetCategory", ""),
                "Open_DateTime": lot.get("@openDateTime", ""),
            }
        )

    df = pd.DataFrame(trade_list)
    print(f"  Parsed {len(df)} closed lots (realized trades)")
    return df


def parse_dividends(flex_data: Dict[str, Any]) -> pd.DataFrame:
    """
    Parse dividend data from Flex Query response

    Args:
        flex_data: Flex Query response data

    Returns:
        DataFrame with dividend details
    """
    # Try different possible locations for dividend data
    cash_section = flex_data.get("CashTransactions")
    if not cash_section or cash_section is None:
        print("  No cash transaction data in this period")
        return pd.DataFrame()

    cash_txns = cash_section.get("CashTransaction", [])

    if isinstance(cash_txns, dict):
        cash_txns = [cash_txns]

    if not cash_txns:
        print("  No dividend data found")
        return pd.DataFrame()

    div_list = []
    for txn in cash_txns:
        txn_type = txn.get("@type", "")
        description = txn.get("@description", "")

        # Filter for dividend transactions
        if "Dividend" in txn_type or "Dividend" in description:
            date_time = txn.get("@dateTime", txn.get("@reportDate", ""))
            div_list.append(
                {
                    "Date": date_time.split(";")[0] if ";" in date_time else date_time,
                    "Symbol": txn.get("@symbol", ""),
                    "Description": description,
                    "Amount": safe_float(txn.get("@amount")),
                    "Currency": txn.get("@currency", ""),
                    "Type": txn_type,
                }
            )

    df = pd.DataFrame(div_list)
    print(f"  Parsed {len(df)} dividend transactions")
    return df


def parse_withholding_tax(flex_data: Dict[str, Any]) -> pd.DataFrame:
    """
    Parse withholding tax data from Flex Query response

    Args:
        flex_data: Flex Query response data

    Returns:
        DataFrame with withholding tax details
    """
    # Check multiple possible locations
    taxes = flex_data.get("WithholdingTax", {}).get("Tax", [])

    if not taxes:
        # Try alternative location in cash transactions
        cash_section = flex_data.get("CashTransactions")
        if not cash_section or cash_section is None:
            print("  No withholding tax data in this period")
            return pd.DataFrame()

        cash_txns = cash_section.get("CashTransaction", [])
        if isinstance(cash_txns, dict):
            cash_txns = [cash_txns]

        tax_list = []
        for txn in cash_txns:
            txn_type = txn.get("@type", "")
            if "Withholding" in txn_type or "TAX" in txn_type.upper():
                date_time = txn.get("@dateTime", txn.get("@reportDate", ""))
                tax_list.append(
                    {
                        "Date": date_time.split(";")[0] if ";" in date_time else date_time,
                        "Symbol": txn.get("@symbol", ""),
                        "Description": txn.get("@description", ""),
                        "Amount": abs(safe_float(txn.get("@amount"))),
                        "Currency": txn.get("@currency", ""),
                        "Type": txn_type,
                    }
                )

        if tax_list:
            df = pd.DataFrame(tax_list)
            print(f"  Parsed {len(df)} withholding tax transactions from cash transactions")
            return df
        else:
            print("  No withholding tax data found")
            return pd.DataFrame()

    if isinstance(taxes, dict):
        taxes = [taxes]

    tax_list = []
    for tax in taxes:
        tax_list.append(
            {
                "Date": tax.get("@date", ""),
                "Symbol": tax.get("@symbol", ""),
                "Description": tax.get("@description", ""),
                "Amount": abs(safe_float(tax.get("@amount"))),
                "Currency": tax.get("@currency", ""),
                "Type": tax.get("@code", ""),
            }
        )

    df = pd.DataFrame(tax_list)
    print(f"  Parsed {len(df)} withholding tax transactions")
    return df


def parse_deposits_withdrawals(flex_data: Dict[str, Any]) -> pd.DataFrame:
    """
    Parse deposits and withdrawals from Flex Query response

    Args:
        flex_data: Flex Query response data

    Returns:
        DataFrame with deposits and withdrawals details
    """
    cash_section = flex_data.get("CashTransactions")
    if not cash_section or cash_section is None:
        print("  No cash transaction data in this period")
        return pd.DataFrame()

    cash_txns = cash_section.get("CashTransaction", [])
    if isinstance(cash_txns, dict):
        cash_txns = [cash_txns]

    if not cash_txns:
        print("  No deposits/withdrawals data found")
        return pd.DataFrame()

    dw_list = []
    for txn in cash_txns:
        txn_type = txn.get("@type", "")
        if txn_type == "Deposits/Withdrawals":
            date_time = txn.get("@dateTime", txn.get("@reportDate", ""))
            amount = safe_float(txn.get("@amount"))
            currency = txn.get("@currency", "")
            fx_rate = safe_float(txn.get("@fxRateToBase"), 1.0)

            amount_base = amount * fx_rate

            # Parse date and time (format: YYYYMMDD;HHMMSS or just YYYYMMDD)
            if ";" in date_time:
                date_part, time_part = date_time.split(";")
                # Convert HHMMSS to HH:MM:SS
                if len(time_part) == 6:
                    time_formatted = f"{time_part[0:2]}:{time_part[2:4]}:{time_part[4:6]}"
                else:
                    time_formatted = time_part
            else:
                date_part = date_time
                time_formatted = ""

            dw_list.append(
                {
                    "Date": date_part,
                    "Time": time_formatted,
                    "Description": txn.get("@description", ""),
                    "Amount": amount,
                    "Currency": currency,
                    "FX_Rate_To_Base": fx_rate,
                    "Amount_Base_Currency": amount_base,
                    "Transaction_Type": "Deposit" if amount_base > 0 else "Withdrawal",
                }
            )

    df = pd.DataFrame(dw_list)
    print(f"  Parsed {len(df)} deposits/withdrawals transactions")
    return df


def calculate_summary(
    trades_df: pd.DataFrame,
    dividends_df: pd.DataFrame,
    tax_df: pd.DataFrame,
    deposits_withdrawals_df: pd.DataFrame = None,
    use_dynamic_rates: bool = True,
    default_rate: float = 7.2,
) -> Dict[str, Any]:
    """
    Calculate tax summary from parsed data

    Args:
        trades_df: DataFrame of trades
        dividends_df: DataFrame of dividends
        tax_df: DataFrame of withholding taxes
        deposits_withdrawals_df: DataFrame of deposits and withdrawals
        use_dynamic_rates: If True, use actual exchange rates for each date
        default_rate: Fallback exchange rate if dynamic rates not available

    Returns:
        Dictionary with tax summary
    """
    summary = {}

    # Get exchange rate service
    rate_service = get_exchange_rate_service() if use_dynamic_rates else None

    # Trade summary
    if not trades_df.empty:
        usd_trades = trades_df[trades_df["Currency"] == "USD"].copy()

        # Calculate CNY amounts using date-specific rates
        if use_dynamic_rates and rate_service:
            print("  Using dynamic exchange rates for trades...")
            usd_trades["Exchange_Rate"] = usd_trades["Date"].apply(
                lambda d: rate_service.get_rate(d, default_rate)
            )
            usd_trades["Realized P&L CNY"] = (
                usd_trades["Realized P&L"] * usd_trades["Exchange_Rate"]
            )
            usd_trades["Commission_CNY"] = usd_trades["Commission"] * usd_trades["Exchange_Rate"]

            total_pnl_cny = usd_trades["Realized P&L CNY"].sum()
            total_commission_cny = usd_trades["Commission_CNY"].sum()
            avg_rate = usd_trades["Exchange_Rate"].mean()
        else:
            total_pnl_cny = usd_trades["Realized P&L"].sum() * default_rate
            total_commission_cny = usd_trades["Commission"].sum() * default_rate
            avg_rate = default_rate

        total_pnl = usd_trades["Realized P&L"].sum()
        total_commission = usd_trades["Commission"].sum()

        summary["Trade_Summary"] = {
            "Total_Trades": len(trades_df),
            "USD_Trades": len(usd_trades),
            "Realized_P&L_USD": round(total_pnl, 2),
            "Realized_P&L_CNY": round(total_pnl_cny, 2),
            "Total_Commission_USD": round(total_commission, 2),
            "Total_Commission_CNY": round(total_commission_cny, 2),
            "Net_P&L_USD": round(total_pnl - total_commission, 2),
            "Net_P&L_CNY": round(total_pnl_cny - total_commission_cny, 2),
            "Average_Exchange_Rate": round(avg_rate, 4),
        }

    # Dividend summary
    if not dividends_df.empty:
        usd_divs = dividends_df[dividends_df["Currency"] == "USD"].copy()

        # Calculate CNY amounts using date-specific rates
        if use_dynamic_rates and rate_service:
            print("  Using dynamic exchange rates for dividends...")
            usd_divs["Exchange_Rate"] = usd_divs["Date"].apply(
                lambda d: rate_service.get_rate(d, default_rate)
            )
            usd_divs["Amount_CNY"] = usd_divs["Amount"] * usd_divs["Exchange_Rate"]
            total_dividends_cny = usd_divs["Amount_CNY"].sum()
            avg_rate = usd_divs["Exchange_Rate"].mean()
        else:
            total_dividends_cny = usd_divs["Amount"].sum() * default_rate
            avg_rate = default_rate

        total_dividends = usd_divs["Amount"].sum()

        summary["Dividend_Summary"] = {
            "Total_Dividends": len(dividends_df),
            "Total_Amount_USD": round(total_dividends, 2),
            "Total_Amount_CNY": round(total_dividends_cny, 2),
            "Average_Exchange_Rate": round(avg_rate, 4),
        }

    # Tax summary
    if not tax_df.empty:
        usd_tax = tax_df[tax_df["Currency"] == "USD"].copy()

        # Calculate CNY amounts using date-specific rates
        if use_dynamic_rates and rate_service:
            print("  Using dynamic exchange rates for taxes...")
            usd_tax["Exchange_Rate"] = usd_tax["Date"].apply(
                lambda d: rate_service.get_rate(d, default_rate)
            )
            usd_tax["Amount_CNY"] = usd_tax["Amount"] * usd_tax["Exchange_Rate"]
            total_tax_cny = usd_tax["Amount_CNY"].sum()
            avg_rate = usd_tax["Exchange_Rate"].mean()
        else:
            total_tax_cny = usd_tax["Amount"].sum() * default_rate
            avg_rate = default_rate

        total_tax = usd_tax["Amount"].sum()

        summary["Tax_Summary"] = {
            "Total_Withholding_Tax_USD": round(total_tax, 2),
            "Total_Withholding_Tax_CNY": round(total_tax_cny, 2),
            "Average_Exchange_Rate": round(avg_rate, 4),
        }

    # Calculate tax liability for China
    if "Trade_Summary" in summary and "Dividend_Summary" in summary:
        taxable_income_cny = (
            summary["Trade_Summary"]["Net_P&L_CNY"]
            + summary["Dividend_Summary"]["Total_Amount_CNY"]
        )
        tax_due_20_pct = taxable_income_cny * 0.2

        foreign_tax_credit = 0
        if "Tax_Summary" in summary:
            # Credit is limited to China tax rate on foreign income
            foreign_tax_credit = min(
                summary["Tax_Summary"]["Total_Withholding_Tax_CNY"],
                summary["Dividend_Summary"]["Total_Amount_CNY"] * 0.2,
            )

        summary["China_Tax_Calculation"] = {
            "Taxable_Income_CNY": round(taxable_income_cny, 2),
            "Tax_Due_20pct_CNY": round(tax_due_20_pct, 2),
            "Foreign_Tax_Credit_CNY": round(foreign_tax_credit, 2),
            "Tax_Payable_CNY": round(tax_due_20_pct - foreign_tax_credit, 2),
        }

    # Account summary (deposits/withdrawals)
    if deposits_withdrawals_df is not None and not deposits_withdrawals_df.empty:
        deposits = deposits_withdrawals_df[deposits_withdrawals_df["Transaction_Type"] == "Deposit"]
        withdrawals = deposits_withdrawals_df[
            deposits_withdrawals_df["Transaction_Type"] == "Withdrawal"
        ]

        total_deposits_base = deposits["Amount_Base_Currency"].sum()
        total_withdrawals_base = abs(withdrawals["Amount_Base_Currency"].sum())
        net_deposits_base = total_deposits_base - total_withdrawals_base

        summary["Account_Summary"] = {
            "Total_Deposits_Count": len(deposits),
            "Total_Withdrawals_Count": len(withdrawals),
            "Total_Deposits_Base_Currency": round(total_deposits_base, 2),
            "Total_Withdrawals_Base_Currency": round(total_withdrawals_base, 2),
            "Net_Deposits_Base_Currency": round(net_deposits_base, 2),
        }

    return summary
