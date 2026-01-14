#!/usr/bin/env python3
"""
Command-line interface for IBKR Stop Loss Manager
"""

import argparse
import sys
from typing import List, Optional

from .api.trading_client import TradingClient
from .config import Config
from .exceptions import APIError, ConfigurationError, IBKRTaxError
from .utils.logging import setup_logger


def print_banner() -> None:
    """Print application banner"""
    print("=" * 60)
    print("IBKR Stop Loss Manager")
    print("=" * 60)
    print()


def place_trailing_stop_orders(
    config: Config,
    account: str,
    trailing_percent: float,
    symbols: Optional[List[str]] = None,
    logger: Optional[any] = None,
) -> None:
    """
    Place trailing stop orders in IB system for specific account

    Args:
        config: Configuration object
        account: Account ID to place orders for
        trailing_percent: Trailing stop percentage
        symbols: Optional list of symbols (if None, all positions)
        logger: Logger instance
    """
    if logger is None:
        logger = setup_logger("stop_loss", level="INFO", console=True)

    logger.info("Connecting to IBKR Web API...")

    # Connect to IBKR Web API
    client = TradingClient(
        base_url=config.web_api_url,
        verify_ssl=config.web_api_verify_ssl,
        timeout=config.web_api_timeout,
    )

    try:
        client.connect()

        print(f"\n{'=' * 80}")
        print(f"Placing trailing stop orders for account {account}")
        print(f"Trailing stop percentage: {trailing_percent}%")
        if symbols:
            print(f"Symbols: {', '.join(symbols)}")
        print(f"{'=' * 80}\n")

        # Place orders
        results = client.place_trailing_stop_for_positions(
            account=account,
            trailing_percent=trailing_percent,
            symbols=symbols,
        )

        if not results:
            print("No positions found for order placement")
            return

        # Display results
        print(f"\n{'=' * 80}")
        print("Order Placement Results:")
        print(f"{'=' * 80}\n")

        success_count = 0
        failed_count = 0

        for result in results:
            symbol = result.get("symbol")
            if "orderId" in result:
                print(
                    f"  {symbol:6s}: Order ID {result['orderId']:4d}, "
                    f"{result['quantity']:2.0f} shares, "
                    f"{result['trailing_percent']:.1f}% trail, "
                    f"Status: {result['status']}"
                )
                success_count += 1
            else:
                print(f"  {symbol:6s}: {result.get('error', 'Unknown error')}")
                failed_count += 1

        print(f"\n{'=' * 80}")
        print(f"Success: {success_count} | Failed: {failed_count}")
        print(f"{'=' * 80}\n")

        print("Note: Orders submitted to IB system will be monitored and executed automatically.")
        print("You can view and manage these orders in TWS/IB Gateway.")

    finally:
        client.disconnect()


def place_trailing_stop_buy_orders(
    config: Config,
    account: str,
    trailing_percent: float,
    symbols: List[str],
    logger: Optional[any] = None,
) -> None:
    """
    Place trailing stop BUY orders in IB system for specific symbols

    Args:
        config: Configuration object
        account: Account ID to place orders for
        trailing_percent: Trailing stop percentage
        symbols: List of symbols to place buy orders for (required)
        logger: Logger instance
    """
    if logger is None:
        logger = setup_logger("stop_loss", level="INFO", console=True)

    logger.info("Connecting to IBKR Web API...")

    # Connect to IBKR Web API
    client = TradingClient(
        base_url=config.web_api_url,
        verify_ssl=config.web_api_verify_ssl,
        timeout=config.web_api_timeout,
    )

    try:
        client.connect()

        print(f"\n{'=' * 80}")
        print(f"Placing trailing stop BUY orders for account {account}")
        print(f"Trailing stop percentage: {trailing_percent}%")
        print(f"Symbols: {', '.join(symbols)}")
        print(f"{'=' * 80}\n")

        # Place buy orders for each symbol with fixed quantity
        results = []
        for symbol in symbols:
            try:
                # Use a default quantity of 1 for buy orders
                # User can modify the order in TWS/IB Gateway if needed
                result = client.place_trailing_stop_order(
                    symbol=symbol,
                    quantity=1,
                    trailing_percent=trailing_percent,
                    action="BUY",
                    account=account,
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to place order for {symbol}: {e}")
                results.append({"symbol": symbol, "error": str(e), "status": "failed"})

        if not results:
            print("No orders placed")
            return

        # Display results
        print(f"\n{'=' * 80}")
        print("Order Placement Results:")
        print(f"{'=' * 80}\n")

        success_count = 0
        failed_count = 0

        for result in results:
            symbol = result.get("symbol")
            if "orderId" in result:
                print(
                    f"  {symbol:6s}: Order ID {result['orderId']:4d}, "
                    f"{result['quantity']:2.0f} shares, "
                    f"{result['trailing_percent']:.1f}% trail BUY, "
                    f"Status: {result['status']}"
                )
                success_count += 1
            else:
                print(f"  {symbol:6s}: {result.get('error', 'Unknown error')}")
                failed_count += 1

        print(f"\n{'=' * 80}")
        print(f"Success: {success_count} | Failed: {failed_count}")
        print(f"{'=' * 80}\n")

        print("Note: These are BUY orders with quantity=1 (default).")
        print("You can modify quantity in TWS/IB Gateway after placement.")
        print("Orders will execute when price rises by the trailing percentage.")

    finally:
        client.disconnect()


def view_open_orders(
    config: Config,
    account: Optional[str] = None,
    logger: Optional[any] = None,
) -> None:
    """
    View open orders in IB system

    Args:
        config: Configuration object
        account: Optional account filter
        logger: Logger instance
    """
    if logger is None:
        logger = setup_logger("stop_loss", level="INFO", console=True)

    logger.info("Connecting to IBKR Web API...")

    # Connect to IBKR Web API
    client = TradingClient(
        base_url=config.web_api_url,
        verify_ssl=config.web_api_verify_ssl,
        timeout=config.web_api_timeout,
    )

    try:
        client.connect()

        print(f"\n{'=' * 80}")
        if account:
            print(f"Active Orders for Account {account}:")
        else:
            print("Active Orders for All Accounts:")
        print(f"{'=' * 80}\n")

        # Get open orders
        orders = client.get_open_orders(account=account)

        if not orders:
            print("No active orders found")
            return

        # Group by account
        accounts = {}
        for order in orders:
            acc = order.get("account", "Unknown")
            if acc not in accounts:
                accounts[acc] = []
            accounts[acc].append(order)

        # Display orders
        for acc, order_list in sorted(accounts.items()):
            print(f"\nAccount: {acc}")
            print("-" * 80)
            print(
                f"{'OrderID':<8} {'Symbol':<8} {'Action':<6} {'Qty':<6} "
                f"{'Type':<8} {'Trail%/Price':<12} {'Status':<15}"
            )
            print("-" * 80)

            for order in order_list:
                order_id = order.get("orderId", "N/A")
                # Web API uses "ticker" instead of "symbol"
                symbol = order.get("ticker") or order.get("symbol", "N/A")
                # Web API uses "side" instead of "action"
                action = order.get("side") or order.get("action", "N/A")
                # Web API uses "totalSize" instead of "quantity"
                quantity = order.get("totalSize") or order.get("quantity", 0)
                order_type = order.get("orderType", "N/A")
                status = order.get("status", "N/A")

                # Get type-specific field
                if order_type == "TRAIL":
                    # Web API may use different field names for trailing percent
                    type_info = (
                        f"{order.get('trailingPercent', order.get('trailing_percent', 0)):.1f}%"
                    )
                elif order_type == "STP":
                    # Web API uses "auxPrice" for stop price
                    type_info = f"${order.get('auxPrice', order.get('stop_price', 0)):.2f}"
                else:
                    type_info = "-"

                print(
                    f"{order_id:<8} {symbol:<8} {action:<6} {quantity:<6.0f} "
                    f"{order_type:<8} {type_info:<12} {status:<15}"
                )

        print(f"\nTotal: {len(orders)} active orders")

    finally:
        client.disconnect()


def cancel_trailing_stop_orders(
    config: Config,
    order_ids: Optional[List[int]] = None,
    account: Optional[str] = None,
    symbols: Optional[List[str]] = None,
    logger: Optional[any] = None,
) -> None:
    """
    Cancel trailing stop orders

    Args:
        config: Configuration object
        order_ids: Optional list of order IDs to cancel
        account: Optional account filter
        symbols: Optional symbols filter (requires account)
        logger: Logger instance
    """
    if logger is None:
        logger = setup_logger("stop_loss", level="INFO", console=True)

    # Validate arguments
    if not order_ids and not account:
        print("\nError: Must specify order IDs or use --account parameter")
        print("\nExamples:")
        print("  # Cancel specific orders")
        print("  ibkr-toolkit stop-loss cancel 15 12")
        print("\n  # Cancel all orders for account")
        print("  ibkr-toolkit stop-loss cancel --account U12345678")
        print("\n  # Cancel orders for specific symbols in account")
        print("  ibkr-toolkit stop-loss cancel --account U12345678 --symbols AAPL TSLA")
        sys.exit(1)

    if symbols and not account:
        print("\nError: --symbols parameter requires --account")
        sys.exit(1)

    logger.info("Connecting to IBKR Web API...")

    # Connect to IBKR Web API
    client = TradingClient(
        base_url=config.web_api_url,
        verify_ssl=config.web_api_verify_ssl,
        timeout=config.web_api_timeout,
    )

    try:
        client.connect()

        print(f"\n{'=' * 80}")
        print("Cancel Trailing Stop Orders")
        print(f"{'=' * 80}\n")

        if order_ids:
            # Cancel specific order IDs
            print(f"Cancelling order IDs: {', '.join(map(str, order_ids))}\n")

            cancelled_count = 0
            failed_count = 0

            # First, get all orders to find which account each order belongs to
            all_orders = client.get_open_orders()
            order_account_map = {
                order.get("orderId"): order.get("account", "") for order in all_orders
            }

            for order_id in order_ids:
                # Find the account for this order
                order_account = order_account_map.get(order_id)
                if not order_account:
                    print(f"  Order {order_id} not found or no account info")
                    failed_count += 1
                    continue

                try:
                    client.cancel_order(order_account, order_id)
                    print(f"  Order {order_id} (Account: {order_account}) cancelled")
                    cancelled_count += 1
                except Exception as e:
                    print(f"  Order {order_id} cancellation failed: {e}")
                    failed_count += 1

            print(f"\n{'=' * 80}")
            print(f"Success: {cancelled_count} | Failed: {failed_count}")
            print(f"{'=' * 80}")

        else:
            # Cancel by account and symbols
            print(f"Account: {account}")
            if symbols:
                print(f"Symbols: {', '.join(symbols)}")
            print()

            results = client.cancel_orders_by_account(
                account=account,
                symbols=symbols,
            )

            if not results:
                print("No orders found to cancel")
                return

            # Display results
            print("Cancellation Results:\n")

            cancelled_count = 0
            failed_count = 0

            for result in results:
                order_id = result.get("orderId")
                symbol = result.get("symbol")
                status = result.get("status")

                if status == "cancelled":
                    print(f"  Order {order_id:4d} ({symbol:6s}) cancelled")
                    cancelled_count += 1
                else:
                    error = result.get("error", "Unknown error")
                    print(f"  Order {order_id:4d} ({symbol:6s}) cancellation failed: {error}")
                    failed_count += 1

            print(f"\n{'=' * 80}")
            print(f"Success: {cancelled_count} | Failed: {failed_count}")
            print(f"{'=' * 80}")

    finally:
        client.disconnect()


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="IBKR Stop Loss Manager - Place and manage trailing stop orders",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:

  # Place trailing stop SELL orders for account (all positions)
  ibkr-toolkit stop-loss place U12345678 --percent 5.0

  # Place trailing stop SELL orders for specific symbols
  ibkr-toolkit stop-loss place U12345678 --percent 5.0 --symbols AAPL TSLA

  # Place trailing stop BUY orders (buy-on-dip strategy)
  ibkr-toolkit stop-loss place-buy U12345678 --percent 5.0 --symbols AAPL TSLA

  # View active orders
  ibkr-toolkit stop-loss orders

  # View orders for specific account
  ibkr-toolkit stop-loss orders --account U12345678

  # Cancel specific orders by ID
  ibkr-toolkit stop-loss cancel 15 12

  # Cancel all orders for account
  ibkr-toolkit stop-loss cancel --account U12345678

  # Cancel orders for specific symbols
  ibkr-toolkit stop-loss cancel --account U12345678 --symbols AAPL TSLA

Note:
  - TWS or IB Gateway must be running before use
  - Default ports: 7497 (TWS Paper), 4002 (IB Gateway Paper)
  - Connection parameters can be configured in .env file
  - All orders are placed directly in IB system (24/7 monitoring)
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Subcommands")

    # Place command - place trailing stop SELL orders in IB system
    place_parser = subparsers.add_parser(
        "place", help="Place trailing stop SELL orders in IB system for account"
    )
    place_parser.add_argument("account", help="Account ID (e.g., U12345678)")
    place_parser.add_argument(
        "--percent",
        type=float,
        required=True,
        help="Trailing stop percentage (e.g., 5.0 triggers on 5%% price drop)",
    )
    place_parser.add_argument(
        "--symbols",
        nargs="+",
        help="Specific symbols (if not specified, all positions in account)",
    )

    # Place-buy command - place trailing stop BUY orders
    place_buy_parser = subparsers.add_parser(
        "place-buy", help="Place trailing stop BUY orders for specific symbols"
    )
    place_buy_parser.add_argument("account", help="Account ID (e.g., U12345678)")
    place_buy_parser.add_argument(
        "--percent",
        type=float,
        required=True,
        help="Trailing stop percentage (e.g., 5.0 triggers on 5%% price rise)",
    )
    place_buy_parser.add_argument(
        "--symbols",
        nargs="+",
        required=True,
        help="Symbols to place buy orders for (required)",
    )

    # Orders command - view open orders
    orders_parser = subparsers.add_parser("orders", help="View active orders")
    orders_parser.add_argument("--account", help="Filter by account (optional)")

    # Cancel command - cancel orders
    cancel_parser = subparsers.add_parser("cancel", help="Cancel trailing stop orders")
    cancel_parser.add_argument(
        "order_ids",
        nargs="*",
        type=int,
        help="Order IDs (if not specified, use --account filter)",
    )
    cancel_parser.add_argument("--account", help="Cancel all trailing stop orders for this account")
    cancel_parser.add_argument(
        "--symbols",
        nargs="+",
        help="Cancel only orders for these symbols (requires --account)",
    )

    return parser.parse_args()


def main() -> None:
    """Main execution function"""
    args = parse_args()

    if not args.command:
        print("Error: Please specify a subcommand (place, place-buy, orders, cancel)")
        print("Use --help for help")
        sys.exit(1)

    print_banner()

    # Initialize logger
    logger = setup_logger("stop_loss", level="INFO", console=True)

    try:
        # Load configuration
        logger.info("Loading configuration...")
        try:
            config = Config()
            logger.info("Configuration loaded successfully")
        except ConfigurationError as e:
            logger.error(f"Configuration error: {e}")
            print("\nPlease check .env file or environment variables")
            print("Required variables:")
            print("  - IBKR_FLEX_TOKEN")
            print("  - IBKR_QUERY_ID")
            sys.exit(1)

        # Execute command
        if args.command == "place":
            place_trailing_stop_orders(
                config=config,
                account=args.account,
                trailing_percent=args.percent,
                symbols=[s.upper() for s in args.symbols] if args.symbols else None,
                logger=logger,
            )
        elif args.command == "place-buy":
            place_trailing_stop_buy_orders(
                config=config,
                account=args.account,
                trailing_percent=args.percent,
                symbols=[s.upper() for s in args.symbols],
                logger=logger,
            )
        elif args.command == "orders":
            view_open_orders(
                config=config,
                account=args.account if hasattr(args, "account") else None,
                logger=logger,
            )
        elif args.command == "cancel":
            cancel_trailing_stop_orders(
                config=config,
                order_ids=args.order_ids if args.order_ids else None,
                account=args.account if hasattr(args, "account") else None,
                symbols=[s.upper() for s in args.symbols]
                if hasattr(args, "symbols") and args.symbols
                else None,
                logger=logger,
            )

        print("\n" + "=" * 60)
        print("Operation completed")
        print("=" * 60)

    except KeyboardInterrupt:
        logger.warning("Operation cancelled by user")
        print("\n\nOperation cancelled by user")
        sys.exit(0)
    except APIError as e:
        logger.error(f"API error: {e}")
        print(f"\nAPI error: {e}")
        print("\nPlease check:")
        print("  1. TWS or IB Gateway is running")
        print("  2. API settings are enabled")
        print("  3. Port number is correct")
        sys.exit(1)
    except IBKRTaxError as e:
        logger.error(f"Application error: {e}", exc_info=True)
        print(f"\nError: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\nUnexpected error: {e}")
        print("\nSee logs for detailed error information")
        sys.exit(1)


if __name__ == "__main__":
    main()
