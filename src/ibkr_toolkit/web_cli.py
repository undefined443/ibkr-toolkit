"""
Command-line interface for IBKR Web API operations

Provides commands for:
- Account information and management
- Position viewing
- Order management
- Contract search
- Market data snapshots
"""

import argparse
import json
import sys
import time

from .api.web_client import WebAPIClient, WebAPIError
from .config import Config
from .utils.logging import setup_logger

logger = setup_logger("ibkr_toolkit.web_cli", level="INFO", console=True)


def display_json(data, indent=2):
    """Pretty print JSON data"""
    print(json.dumps(data, indent=indent, ensure_ascii=False))


def account_info_command(config: Config, output_format: str = "table"):
    """
    Display account information

    Args:
        config: Configuration object
        output_format: Output format (table or json)
    """
    client = WebAPIClient(
        base_url=config.web_api_url,
        verify_ssl=config.web_api_verify_ssl,
        timeout=config.web_api_timeout,
    )

    try:
        # Get authentication status
        auth_status = client.get_auth_status()
        if not auth_status.get("authenticated"):
            logger.error("Not authenticated. Please login at https://localhost:5001")
            return 1

        # Get accounts
        accounts = client.get_accounts()

        if output_format == "json":
            display_json(accounts)
        else:
            print("\nAccounts:")
            print("-" * 80)
            for account in accounts:
                account_id = account.get("id") or account.get("accountId")
                alias = account.get("accountAlias", "N/A")
                acc_type = account.get("type", "N/A")
                trading_type = account.get("tradingType", "N/A")
                currency = account.get("currency", "N/A")

                print(f"Account ID: {account_id}")
                print(f"  Alias: {alias}")
                print(f"  Type: {acc_type}")
                print(f"  Trading Type: {trading_type}")
                print(f"  Currency: {currency}")
                print()

        return 0

    except WebAPIError as e:
        logger.error(f"Web API Error: {e}")
        return 1


def positions_command(config: Config, account_id: str, output_format: str = "table"):
    """
    Display account positions

    Args:
        config: Configuration object
        account_id: Account identifier
        output_format: Output format (table or json)
    """
    client = WebAPIClient(
        base_url=config.web_api_url,
        verify_ssl=config.web_api_verify_ssl,
        timeout=config.web_api_timeout,
    )

    try:
        positions = client.get_positions(account_id)

        if output_format == "json":
            display_json(positions)
        else:
            print(f"\nPositions for account {account_id}:")
            print("-" * 100)
            header = (
                f"{'Symbol':<10} {'Quantity':>12} {'Avg Cost':>12} "
                f"{'Market Price':>14} {'Market Value':>14} {'P&L':>12}"
            )
            print(header)
            print("-" * 100)

            total_value = 0
            total_pnl = 0

            for pos in positions:
                symbol = pos.get("contractDesc", "N/A")
                quantity = pos.get("position", 0)
                avg_cost = pos.get("avgCost", 0)
                mkt_price = pos.get("mktPrice", 0)
                mkt_value = pos.get("mktValue", 0)
                unrealized_pnl = pos.get("unrealizedPnl", 0)

                total_value += mkt_value
                total_pnl += unrealized_pnl

                pnl_str = (
                    f"+${unrealized_pnl:.2f}"
                    if unrealized_pnl >= 0
                    else f"-${abs(unrealized_pnl):.2f}"
                )

                row = (
                    f"{symbol:<10} {quantity:>12.4f} ${avg_cost:>11.2f} "
                    f"${mkt_price:>13.2f} ${mkt_value:>13.2f} {pnl_str:>11}"
                )
                print(row)

            print("-" * 100)
            total_pnl_str = f"+${total_pnl:.2f}" if total_pnl >= 0 else f"-${abs(total_pnl):.2f}"
            total_row = (
                f"{'TOTAL':<10} {'':>12} {'':>12} {'':>14} "
                f"${total_value:>13.2f} {total_pnl_str:>11}"
            )
            print(total_row)
            print()

        return 0

    except WebAPIError as e:
        logger.error(f"Web API Error: {e}")
        return 1


def summary_command(config: Config, account_id: str, output_format: str = "table"):
    """
    Display account summary

    Args:
        config: Configuration object
        account_id: Account identifier
        output_format: Output format (table or json)
    """
    client = WebAPIClient(
        base_url=config.web_api_url,
        verify_ssl=config.web_api_verify_ssl,
        timeout=config.web_api_timeout,
    )

    try:
        summary = client.get_account_summary(account_id)

        if output_format == "json":
            display_json(summary)
        else:
            # Extract key metrics
            net_liq = summary.get("netliquidation", {}).get("amount", 0)
            cash = summary.get("totalcashvalue", {}).get("amount", 0)
            buying_power = summary.get("buyingpower", {}).get("amount", 0)
            available_funds = summary.get("availablefunds", {}).get("amount", 0)
            excess_liquidity = summary.get("excessliquidity", {}).get("amount", 0)
            init_margin = summary.get("initmarginreq", {}).get("amount", 0)
            maint_margin = summary.get("maintmarginreq", {}).get("amount", 0)

            print(f"\nAccount Summary for {account_id}:")
            print("-" * 60)
            print(f"Net Liquidation Value:    ${net_liq:>16,.2f}")
            print(f"Cash Balance:             ${cash:>16,.2f}")
            print(f"Buying Power:             ${buying_power:>16,.2f}")
            print(f"Available Funds:          ${available_funds:>16,.2f}")
            print(f"Excess Liquidity:         ${excess_liquidity:>16,.2f}")
            print("-" * 60)
            print(f"Initial Margin Required:  ${init_margin:>16,.2f}")
            print(f"Maintenance Margin Req:   ${maint_margin:>16,.2f}")
            print()

        return 0

    except WebAPIError as e:
        logger.error(f"Web API Error: {e}")
        return 1


def orders_command(config: Config, account_id: str, output_format: str = "table"):
    """
    Display live orders

    Args:
        config: Configuration object
        account_id: Account identifier
        output_format: Output format (table or json)
    """
    client = WebAPIClient(
        base_url=config.web_api_url,
        verify_ssl=config.web_api_verify_ssl,
        timeout=config.web_api_timeout,
    )

    try:
        orders = client.get_live_orders(account_id)

        # Handle different response formats
        if isinstance(orders, dict):
            order_list = orders.get("orders", [])
        elif isinstance(orders, list):
            order_list = orders
        else:
            order_list = []

        if output_format == "json":
            display_json(order_list)
        else:
            print(f"\nLive Orders for account {account_id}:")
            print("-" * 100)
            header = (
                f"{'Order ID':<15} {'Symbol':<10} {'Side':<6} "
                f"{'Quantity':>10} {'Type':<8} {'Price':>12} {'Status':<15}"
            )
            print(header)
            print("-" * 100)

            for order in order_list:
                order_id = str(order.get("orderId", "N/A"))
                symbol = order.get("ticker", "N/A")
                side = order.get("side", "N/A")
                quantity = order.get("totalSize", 0)
                order_type = order.get("orderType", "N/A")
                price = order.get("price", 0)
                status = order.get("status", "N/A")

                price_str = f"${price:.2f}" if price > 0 else "MARKET"

                row = (
                    f"{order_id:<15} {symbol:<10} {side:<6} "
                    f"{quantity:>10.2f} {order_type:<8} {price_str:>12} {status:<15}"
                )
                print(row)

            print("-" * 100)
            print(f"Total: {len(order_list)} order(s)")
            print()

        return 0

    except WebAPIError as e:
        logger.error(f"Web API Error: {e}")
        return 1


def search_command(config: Config, symbol: str, output_format: str = "table"):
    """
    Search for contracts

    Args:
        config: Configuration object
        symbol: Symbol to search
        output_format: Output format (table or json)
    """
    client = WebAPIClient(
        base_url=config.web_api_url,
        verify_ssl=config.web_api_verify_ssl,
        timeout=config.web_api_timeout,
    )

    try:
        results = client.search_contract(symbol)

        if output_format == "json":
            display_json(results)
        else:
            print(f"\nSearch results for '{symbol}':")
            print("-" * 80)
            print(f"{'Contract ID':<15} {'Description':<30} {'Exchange':<20}")
            print("-" * 80)

            for result in results:
                conid = result.get("conid", "N/A")
                description = result.get("description", "N/A")
                exchange = result.get("exchange", "N/A")

                print(f"{conid:<15} {description:<30} {exchange:<20}")

            print("-" * 80)
            print(f"Total: {len(results)} result(s)")
            print()

        return 0

    except WebAPIError as e:
        logger.error(f"Web API Error: {e}")
        return 1


def snapshot_command(config: Config, conids: str, output_format: str = "table"):
    """
    Get market data snapshot

    Args:
        config: Configuration object
        conids: Comma-separated list of contract IDs
        output_format: Output format (table or json)
    """
    client = WebAPIClient(
        base_url=config.web_api_url,
        verify_ssl=config.web_api_verify_ssl,
        timeout=config.web_api_timeout,
    )

    try:
        # Parse contract IDs
        conid_list = [int(c.strip()) for c in conids.split(",")]

        # First call to initialize
        client.get_market_snapshot(conid_list)

        # Wait and get actual data
        time.sleep(1)
        snapshot = client.get_market_snapshot(conid_list)

        if output_format == "json":
            display_json(snapshot)
        else:
            print("\nMarket Data Snapshot:")
            print("-" * 80)
            print(f"{'Contract ID':<15} {'Last Price':>12} {'Bid':>12} {'Ask':>12} {'Volume':>15}")
            print("-" * 80)

            for data in snapshot:
                conid = data.get("conid", "N/A")
                last_price = data.get("31", "N/A")  # Field 31 = Last Price
                bid = data.get("84", "N/A")  # Field 84 = Bid
                ask = data.get("85", "N/A")  # Field 85 = Ask
                volume = data.get("87", "N/A")  # Field 87 = Volume

                last_str = (
                    f"${last_price:.2f}"
                    if isinstance(last_price, (int, float))
                    else str(last_price)
                )
                bid_str = f"${bid:.2f}" if isinstance(bid, (int, float)) else str(bid)
                ask_str = f"${ask:.2f}" if isinstance(ask, (int, float)) else str(ask)
                volume_str = f"{volume:,}" if isinstance(volume, (int, float)) else str(volume)

                print(f"{conid:<15} {last_str:>12} {bid_str:>12} {ask_str:>12} {volume_str:>15}")

            print()

        return 0

    except WebAPIError as e:
        logger.error(f"Web API Error: {e}")
        return 1
    except ValueError as e:
        logger.error(f"Invalid contract IDs: {e}")
        return 1


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="IBKR Web API CLI")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Account info command
    account_info_parser = subparsers.add_parser("account-info", help="Display account information")
    account_info_parser.add_argument(
        "--format", choices=["table", "json"], default="table", help="Output format"
    )

    # Positions command
    positions_parser = subparsers.add_parser("positions", help="Display account positions")
    positions_parser.add_argument("account_id", help="Account ID")
    positions_parser.add_argument(
        "--format", choices=["table", "json"], default="table", help="Output format"
    )

    # Summary command
    summary_parser = subparsers.add_parser("summary", help="Display account summary")
    summary_parser.add_argument("account_id", help="Account ID")
    summary_parser.add_argument(
        "--format", choices=["table", "json"], default="table", help="Output format"
    )

    # Orders command
    orders_parser = subparsers.add_parser("orders", help="Display live orders")
    orders_parser.add_argument("account_id", help="Account ID")
    orders_parser.add_argument(
        "--format", choices=["table", "json"], default="table", help="Output format"
    )

    # Search command
    search_parser = subparsers.add_parser("search", help="Search for contracts")
    search_parser.add_argument("symbol", help="Symbol to search")
    search_parser.add_argument(
        "--format", choices=["table", "json"], default="table", help="Output format"
    )

    # Snapshot command
    snapshot_parser = subparsers.add_parser("snapshot", help="Get market data snapshot")
    snapshot_parser.add_argument("conids", help="Comma-separated list of contract IDs")
    snapshot_parser.add_argument(
        "--format", choices=["table", "json"], default="table", help="Output format"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Load configuration
    config = Config()

    # Execute command
    try:
        if args.command == "account-info":
            return account_info_command(config, args.format)
        elif args.command == "positions":
            return positions_command(config, args.account_id, args.format)
        elif args.command == "summary":
            return summary_command(config, args.account_id, args.format)
        elif args.command == "orders":
            return orders_command(config, args.account_id, args.format)
        elif args.command == "search":
            return search_command(config, args.symbol, args.format)
        elif args.command == "snapshot":
            return snapshot_command(config, args.conids, args.format)
        else:
            logger.error(f"Unknown command: {args.command}")
            return 1

    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
        return 130


if __name__ == "__main__":
    sys.exit(main())
