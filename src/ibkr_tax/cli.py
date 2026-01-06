#!/usr/bin/env python3
"""
Command-line interface for IBKR Tax Tool
"""

import argparse
import json
import sys
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd

from .api.flex_query import FlexQueryClient
from .config import Config
from .constants import TIMESTAMP_FORMAT
from .exceptions import APIError, ConfigurationError, IBKRTaxError
from .parsers.data_parser import (
    calculate_summary,
    parse_dividends,
    parse_trades,
    parse_withholding_tax,
)
from .utils.logging import setup_logger


def print_banner() -> None:
    """Print application banner"""
    print("=" * 60)
    print("IBKR Tax Tool - Trading Data Fetcher")
    print("=" * 60)
    print()


def export_to_excel(
    trades_df: pd.DataFrame,
    dividends_df: pd.DataFrame,
    tax_df: pd.DataFrame,
    summary: Dict[str, Any],
    filepath: str,
) -> None:
    """
    Export data to Excel file with multiple sheets

    Args:
        trades_df: DataFrame with trade data
        dividends_df: DataFrame with dividend data
        tax_df: DataFrame with tax data
        summary: Summary dictionary
        filepath: Output file path

    Raises:
        IOError: If file write fails
    """
    try:
        with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
            # Write data sheets
            if not trades_df.empty:
                trades_df.to_excel(writer, sheet_name="Trades", index=False)

            if not dividends_df.empty:
                dividends_df.to_excel(writer, sheet_name="Dividends", index=False)

            if not tax_df.empty:
                tax_df.to_excel(writer, sheet_name="Withholding_Tax", index=False)

            # Write summary sheet
            summary_data = []
            for category, values in summary.items():
                summary_data.append({"Category": category, "Metric": "", "Value": ""})
                for metric, value in values.items():
                    summary_data.append(
                        {"Category": "", "Metric": metric.replace("_", " "), "Value": value}
                    )

            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name="Summary", index=False)
    except Exception as e:
        raise IOError(f"Failed to export Excel file: {e}") from e


def print_summary(summary: Dict[str, Any]) -> None:
    """
    Print summary to console

    Args:
        summary: Summary dictionary
    """
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for category, values in summary.items():
        print(f"\n{category}:")
        print("-" * 40)
        for metric, value in values.items():
            metric_name = metric.replace("_", " ")
            if isinstance(value, (int, float)):
                print(f"  {metric_name:<35} {value:>15,.2f}")
            else:
                print(f"  {metric_name:<35} {value:>15}")


def convert_to_native(obj: Any) -> Any:
    """
    Convert numpy types to Python native types for JSON serialization

    Args:
        obj: Object to convert

    Returns:
        Converted object
    """
    if isinstance(obj, dict):
        return {k: convert_to_native(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_native(item) for item in obj]
    elif hasattr(obj, "item"):  # numpy types
        return obj.item()
    else:
        return obj


def process_accounts(data: Any, logger: Any) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Process single or multiple accounts data

    Args:
        data: Flex query response data (dict or list)
        logger: Logger instance

    Returns:
        Tuple of (trades_df, dividends_df, tax_df)
    """
    if isinstance(data, list):
        logger.info(f"Processing {len(data)} account(s)...")
        all_trades: List[pd.DataFrame] = []
        all_dividends: List[pd.DataFrame] = []
        all_taxes: List[pd.DataFrame] = []

        for idx, account_data in enumerate(data):
            account_id = account_data.get("@accountId", f"Account_{idx + 1}")
            logger.info(f"Processing account: {account_id}")

            trades = parse_trades(account_data)
            dividends = parse_dividends(account_data)
            taxes = parse_withholding_tax(account_data)

            if not trades.empty:
                trades["Account"] = account_id
                all_trades.append(trades)
            if not dividends.empty:
                dividends["Account"] = account_id
                all_dividends.append(dividends)
            if not taxes.empty:
                taxes["Account"] = account_id
                all_taxes.append(taxes)

        # Merge all accounts
        trades_df = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()
        dividends_df = (
            pd.concat(all_dividends, ignore_index=True) if all_dividends else pd.DataFrame()
        )
        tax_df = pd.concat(all_taxes, ignore_index=True) if all_taxes else pd.DataFrame()

        logger.info(
            f"Total across all accounts: {len(trades_df)} trades, "
            f"{len(dividends_df)} dividends, {len(tax_df)} taxes"
        )
    else:
        # Single account
        logger.info("Processing single account...")
        trades_df = parse_trades(data)
        dividends_df = parse_dividends(data)
        tax_df = parse_withholding_tax(data)

    return trades_df, dividends_df, tax_df


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="IBKR Tax Tool - Fetch and analyze trading data for Chinese tax reporting",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default date range from Flex Query
  ibkr-tax

  # Get data for specific year (China tax year: Jan 1 - Dec 31)
  ibkr-tax --year 2025

  # Get data for current year
  ibkr-tax --year $(date +%%Y)

  # Get all data from start year to current year
  ibkr-tax --from-year 2020

  # Get all data from FIRST_TRADE_YEAR (in .env) to current year
  ibkr-tax --all
        """,
    )

    parser.add_argument(
        "-y",
        "--year",
        type=int,
        help="Tax year (e.g., 2025). Fetches data from Jan 1 to Dec 31 of specified year.",
    )

    parser.add_argument(
        "--from-year",
        type=int,
        help="Starting year. Fetches all data from this year to current year (year by year).",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Fetch all data from FIRST_TRADE_YEAR (in .env) to current year.",
    )

    return parser.parse_args()


def main() -> None:
    """Main execution function"""
    # Parse command-line arguments
    args = parse_args()

    print_banner()

    # Initialize logger (console only for now)
    logger = setup_logger("ibkr_tax", level="INFO", console=True)

    # Validate arguments
    if sum([bool(args.year), bool(args.from_year), args.all]) > 1:
        logger.error("Cannot specify multiple date options: --year, --from-year, and --all are mutually exclusive")
        print("\n✗ Error: Please specify only one of: --year, --from-year, or --all")
        sys.exit(1)

    # Calculate date range based on arguments
    from_date = None
    to_date = None
    years_to_fetch = []

    if args.year:
        # Single year mode
        from_date = f"{args.year}0101"
        to_date = f"{args.year}1231"
        years_to_fetch = [args.year]
        logger.info(f"Tax year: {args.year} (from {from_date} to {to_date})")
    elif args.from_year or args.all:
        # Multi-year mode
        current_year = datetime.now().year
        if args.all:
            # Need to load config to get FIRST_TRADE_YEAR
            try:
                temp_config = Config()
                start_year = temp_config.first_trade_year
                if not start_year:
                    logger.error("FIRST_TRADE_YEAR not set in .env file")
                    print("\n✗ Error: Please set FIRST_TRADE_YEAR in .env file to use --all option")
                    sys.exit(1)
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
                sys.exit(1)
        else:
            start_year = args.from_year

        years_to_fetch = list(range(start_year, current_year + 1))
        logger.info(f"Fetching data from {start_year} to {current_year} ({len(years_to_fetch)} years)")

    try:
        # Step 1: Load configuration
        logger.info("Step 1: Loading configuration...")
        try:
            config = Config()
            logger.info("Configuration loaded successfully")
            logger.info(f"Exchange rate: 1 USD = {config.exchange_rate} CNY")
            logger.info(f"Use dynamic rates: {config.use_dynamic_rates}")
        except ConfigurationError as e:
            logger.error(f"Configuration error: {e}")
            print("\nPlease check your .env file or environment variables.")
            print("Required variables:")
            print("  - IBKR_FLEX_TOKEN")
            print("  - IBKR_QUERY_ID")
            sys.exit(1)

        # Step 2: Prepare output directory
        logger.info("Step 2: Preparing output directory...")
        output_dir = config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Output directory: {output_dir}")

        # Step 3: Fetch data from IBKR
        logger.info("Step 3: Fetching data from IBKR...")
        client = FlexQueryClient(config.token, config.query_id)

        if years_to_fetch and len(years_to_fetch) > 1:
            # Multi-year mode: fetch year by year
            logger.info(f"Multi-year mode: fetching {len(years_to_fetch)} years of data...")
            all_data = []

            for year in years_to_fetch:
                year_from = f"{year}0101"
                year_to = f"{year}1231"
                logger.info(f"  Fetching year {year} ({year_from} to {year_to})...")

                try:
                    year_data = client.fetch_data(from_date=year_from, to_date=year_to)
                    all_data.append(year_data)
                    logger.info(f"  ✓ Year {year} fetched successfully")
                except APIError as e:
                    logger.warning(f"  ! Failed to fetch year {year}: {e}")
                    logger.warning(f"  Continuing with remaining years...")

            if not all_data:
                logger.error("Failed to fetch any data")
                sys.exit(1)

            logger.info(f"Successfully fetched {len(all_data)} year(s) of data")

            # Combine all years data
            logger.info("Combining data from all years...")
            if isinstance(all_data[0], list):
                # Multiple accounts: combine by account
                data = all_data[0]  # Start with first year's structure
                # This is complex, will be handled in process_accounts
            else:
                # Single account: will be handled in process_accounts
                data = all_data
        else:
            # Single year or default mode
            try:
                data = client.fetch_data(from_date=from_date, to_date=to_date)
                logger.info("Data fetched successfully")
            except APIError as e:
                logger.error(f"API error: {e}")
                sys.exit(1)

        # Save raw data
        timestamp = datetime.now().strftime(TIMESTAMP_FORMAT)
        raw_data_file = output_dir / f"raw_data_{timestamp}.json"
        try:
            client.save_raw_data(data, str(raw_data_file))
        except IOError as e:
            logger.error(f"Failed to save raw data: {e}")

        # Step 4: Parse data
        logger.info("Step 4: Parsing data...")
        if years_to_fetch and len(years_to_fetch) > 1 and isinstance(data, list) and not isinstance(data[0], dict):
            # Multi-year mode: process each year and combine
            all_trades = []
            all_dividends = []
            all_taxes = []

            for year_data in data:
                trades, dividends, taxes = process_accounts(year_data, logger)
                if not trades.empty:
                    all_trades.append(trades)
                if not dividends.empty:
                    all_dividends.append(dividends)
                if not taxes.empty:
                    all_taxes.append(taxes)

            trades_df = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()
            dividends_df = pd.concat(all_dividends, ignore_index=True) if all_dividends else pd.DataFrame()
            tax_df = pd.concat(all_taxes, ignore_index=True) if all_taxes else pd.DataFrame()

            logger.info(f"Combined data: {len(trades_df)} trades, {len(dividends_df)} dividends, {len(tax_df)} taxes")
        else:
            trades_df, dividends_df, tax_df = process_accounts(data, logger)

        # Step 5: Calculate summary
        logger.info("Step 5: Calculating summary...")
        if config.use_dynamic_rates:
            logger.info("Using dynamic exchange rates (fetched from API)")
        else:
            logger.info(f"Using fixed exchange rate: {config.exchange_rate}")

        summary = calculate_summary(
            trades_df,
            dividends_df,
            tax_df,
            use_dynamic_rates=config.use_dynamic_rates,
            default_rate=config.exchange_rate,
        )
        logger.info("Summary calculated successfully")

        # Step 6: Export to Excel
        logger.info("Step 6: Exporting to Excel...")
        excel_file = output_dir / f"ibkr_report_{timestamp}.xlsx"
        try:
            export_to_excel(trades_df, dividends_df, tax_df, summary, str(excel_file))
            logger.info(f"Excel file saved: {excel_file}")
        except IOError as e:
            logger.error(f"Failed to export Excel: {e}")

        # Export summary to JSON
        summary_file = output_dir / f"summary_{timestamp}.json"
        try:
            summary_native = convert_to_native(summary)
            with open(summary_file, "w", encoding="utf-8") as f:
                json.dump(summary_native, f, indent=2, ensure_ascii=False)
            logger.info(f"Summary JSON saved: {summary_file}")
        except IOError as e:
            logger.error(f"Failed to save summary JSON: {e}")

        # Print summary to console
        print_summary(summary)

        print("\n" + "=" * 60)
        print("✓ All tasks completed successfully!")
        print("=" * 60)

    except KeyboardInterrupt:
        logger.warning("Operation cancelled by user")
        print("\n\nOperation cancelled by user")
        sys.exit(0)
    except IBKRTaxError as e:
        logger.error(f"Application error: {e}", exc_info=True)
        print(f"\n✗ Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\n✗ Unexpected error: {e}")
        print("\nFor detailed error information, check the logs.")
        sys.exit(1)


if __name__ == "__main__":
    main()
