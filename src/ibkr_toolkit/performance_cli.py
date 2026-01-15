"""
Performance query command-line interface for IBKR Web API

This module provides CLI commands for querying account performance data.
"""

import json
import sys
from typing import List

from .api.trading_client import TradingClient
from .api.web_client import WebAPIError
from .config import Config
from .utils.logging import setup_logger

logger = setup_logger("ibkr_toolkit.performance_cli", level="INFO", console=True)


def view_performance(
    config: Config,
    accounts: List[str],
    period: str = "1M",
    output_format: str = "table",
):
    """
    View account performance data

    Args:
        config: Configuration object
        accounts: List of account IDs
        period: Time period (1D, 7D, MTD, 1M, YTD, 1Y)
        output_format: Output format (table, json)
    """
    client = TradingClient(
        base_url=config.web_api_url,
        verify_ssl=config.web_api_verify_ssl,
        timeout=config.web_api_timeout,
    )

    try:
        # Connect to Web API
        logger.info("Connecting to IBKR Web API...")
        if not client.connect():
            logger.error("Failed to connect to IBKR Web API")
            logger.error("Please ensure Client Portal Gateway is running and you are logged in")
            sys.exit(1)

        # Get performance data
        logger.info(f"Fetching performance data for {len(accounts)} account(s)...")
        logger.info(f"Period: {period}")
        logger.info("")

        performance_data = client.get_performance(accounts, period)

        # Display results
        if output_format == "json":
            print(json.dumps(performance_data, indent=2))
        else:
            _display_performance_table(performance_data, accounts, period)

        logger.info("")
        logger.info("Performance data retrieved successfully")
        logger.info("")
        logger.info("Note: Rate limit is 1 request per 15 minutes for this endpoint")

    except WebAPIError as e:
        logger.error(f"Failed to get performance data: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        client.disconnect()


def _display_performance_table(data: dict, accounts: List[str], period: str):
    """
    Display performance data in table format

    Args:
        data: Performance data from API
        accounts: List of account IDs
        period: Time period
    """
    print("=" * 80)
    print(f"Account Performance - {period}")
    print("=" * 80)
    print("")

    # Handle IBKR performance API response format
    if isinstance(data, dict):
        # Display NAV data if available
        if "nav" in data and "data" in data["nav"]:
            for account_data in data["nav"]["data"]:
                account_id = account_data.get("id")
                if account_id in accounts or not accounts:
                    _display_nav_summary(account_data, period)

        # Display cumulative returns if available
        if "cps" in data and "data" in data["cps"]:
            for account_data in data["cps"]["data"]:
                account_id = account_data.get("id")
                if account_id in accounts or not accounts:
                    _display_returns_summary(account_data, data["cps"].get("dates", []))

        # Display time period returns if available
        if "tpps" in data and "data" in data["tpps"]:
            for account_data in data["tpps"]["data"]:
                account_id = account_data.get("id")
                if account_id in accounts or not accounts:
                    _display_period_returns(account_data, data["tpps"].get("dates", []))

        # If old format, try old display methods
        if "nav" not in data and "cps" not in data and "tpps" not in data:
            _display_raw_data(data)

    print("")
    print("=" * 80)


def _display_nav_summary(account_data: dict, period: str):
    """Display NAV summary for an account"""
    account_id = account_data.get("id", "Unknown")
    print(f"\nAccount: {account_id}")
    print("-" * 80)
    print("Net Asset Value (NAV)")
    print("")

    # Get start NAV
    start_nav_info = account_data.get("startNAV", {})
    start_nav = start_nav_info.get("val")
    start_date = start_nav_info.get("date", "")

    # Get end NAV (last value in navs array)
    navs = account_data.get("navs", [])
    end_nav = navs[-1] if navs else None

    # Get date range
    end_period = account_data.get("end", "")

    currency = account_data.get("baseCurrency", "USD")

    if start_nav:
        print(f"  Start NAV ({start_date}):  {currency} {start_nav:,.2f}")
    if end_nav:
        print(f"  End NAV   ({end_period}):  {currency} {end_nav:,.2f}")

    if start_nav and end_nav:
        change = end_nav - start_nav
        change_pct = (change / start_nav * 100) if start_nav != 0 else 0
        print(f"  Change:              {currency} {change:+,.2f} ({change_pct:+.2f}%)")

    print("")


def _display_returns_summary(account_data: dict, dates: List[str]):
    """Display cumulative returns summary"""
    account_id = account_data.get("id", "Unknown")
    returns = account_data.get("returns", [])

    if not returns:
        return

    print(f"\nCumulative Returns - {account_id}")
    print("-" * 80)

    # Show latest return
    latest_return = returns[-1] * 100 if returns else 0
    latest_date = dates[-1] if dates and len(dates) >= len(returns) else ""

    print(f"  Latest Return ({latest_date}):  {latest_return:+.2f}%")

    # Show best and worst returns
    if len(returns) > 1:
        best_return = max(returns) * 100
        worst_return = min(returns) * 100
        best_idx = returns.index(max(returns))
        worst_idx = returns.index(min(returns))
        best_date = dates[best_idx] if dates and len(dates) > best_idx else ""
        worst_date = dates[worst_idx] if dates and len(dates) > worst_idx else ""

        print(f"  Best Return  ({best_date}):  {best_return:+.2f}%")
        print(f"  Worst Return ({worst_date}):  {worst_return:+.2f}%")

    print("")


def _display_period_returns(account_data: dict, dates: List[str]):
    """Display period returns (monthly, etc.)"""
    account_id = account_data.get("id", "Unknown")
    returns = account_data.get("returns", [])

    if not returns:
        return

    print(f"\nPeriod Returns - {account_id}")
    print("-" * 80)

    # Display each period
    for i, (date, ret) in enumerate(zip(dates, returns)):
        ret_pct = ret * 100
        # Format date (YYYYMM -> YYYY-MM)
        if len(date) == 6:
            formatted_date = f"{date[:4]}-{date[4:]}"
        else:
            formatted_date = date
        print(f"  {formatted_date}:  {ret_pct:+.2f}%")

    print("")


def _display_nav_data(nav_data: dict):
    """Display NAV (Net Asset Value) data - legacy format"""
    print("Net Asset Value (NAV)")
    print("-" * 80)

    if "total" in nav_data:
        total = nav_data["total"]
        print(
            f"Total NAV:        ${total:,.2f}"
            if isinstance(total, (int, float))
            else f"Total NAV:        {total}"
        )

    if "start" in nav_data:
        start = nav_data["start"]
        print(
            f"Start NAV:        ${start:,.2f}"
            if isinstance(start, (int, float))
            else f"Start NAV:        {start}"
        )

    if "end" in nav_data:
        end = nav_data["end"]
        print(
            f"End NAV:          ${end:,.2f}"
            if isinstance(end, (int, float))
            else f"End NAV:          {end}"
        )


def _display_account_metrics(metrics: dict):
    """Display account performance metrics"""

    # Common metric fields
    metric_fields = {
        "returns": "Returns",
        "totalReturn": "Total Return",
        "totalReturnPct": "Total Return %",
        "unrealizedPnl": "Unrealized P&L",
        "realizedPnl": "Realized P&L",
        "netPnl": "Net P&L",
        "timeWeightedReturn": "Time Weighted Return",
        "moneyWeightedReturn": "Money Weighted Return",
        "startingValue": "Starting Value",
        "endingValue": "Ending Value",
        "deposits": "Deposits",
        "withdrawals": "Withdrawals",
    }

    for key, label in metric_fields.items():
        if key in metrics:
            value = metrics[key]
            if isinstance(value, (int, float)):
                if "Pct" in key or "Return" in label:
                    print(f"{label:25} {value:>10.2f}%")
                else:
                    print(f"{label:25} ${value:>10,.2f}")
            else:
                print(f"{label:25} {value}")


def _display_raw_data(data: dict):
    """Display raw data when structure is unknown"""
    print("Performance Data:")
    print("-" * 80)

    for key, value in data.items():
        if isinstance(value, (int, float)):
            print(f"{key:25} {value:>15,.2f}")
        elif isinstance(value, dict):
            print(f"\n{key}:")
            for sub_key, sub_value in value.items():
                if isinstance(sub_value, (int, float)):
                    print(f"  {sub_key:23} {sub_value:>15,.2f}")
                else:
                    print(f"  {sub_key:23} {sub_value}")
        else:
            print(f"{key:25} {value}")
