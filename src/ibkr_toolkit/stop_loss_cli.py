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
from .services.notification import EmailNotifier
from .services.stop_loss import StopLossChecker, StopLossManager
from .utils.logging import setup_logger


def print_banner() -> None:
    """Print application banner"""
    print("=" * 60)
    print("IBKR Stop Loss Manager")
    print("=" * 60)
    print()


def print_results(results: list) -> None:
    """
    Print stop-loss check results

    Args:
        results: List of check results from StopLossChecker
    """
    if not results:
        print("\nNo positions to check")
        return

    print("\n" + "=" * 80)
    print("Stop Loss Check Results")
    print("=" * 80)

    # Print summary
    triggered_count = sum(1 for r in results if r["triggered"])
    total_positions = len(results)
    total_unrealized_pnl = sum(r["unrealized_pnl"] for r in results)

    print(f"\nTotal positions: {total_positions}")
    print(f"Stop loss triggered: {triggered_count}")
    print(f"Total unrealized P&L: ${total_unrealized_pnl:+,.2f}")

    # Print triggered positions
    if triggered_count > 0:
        print("\n" + "=" * 80)
        print("TRIGGERED Positions:")
        print("=" * 80)
        print(
            f"{'Symbol':<10} {'Qty':>8} {'Avg Cost':>10} {'Current':>10} "
            f"{'Stop':>10} {'Unreal P&L':>12} {'Action'}"
        )
        print("-" * 80)

        for r in results:
            if r["triggered"]:
                print(
                    f"{r['symbol']:<10} {r['quantity']:>8} "
                    f"${r['avg_cost']:>9.2f} ${r['current_price']:>9.2f} "
                    f"${r['stop_price']:>9.2f} ${r['unrealized_pnl']:>+11.2f} "
                    f"{r.get('action_taken', 'Manual order suggested')}"
                )

    # Print all positions
    print("\n" + "=" * 80)
    print("All Positions:")
    print("=" * 80)
    print(
        f"{'Symbol':<10} {'Current':>10} {'Stop':>10} {'Unreal P&L':>12} {'P&L %':>10} {'Status'}"
    )
    print("-" * 80)

    for r in results:
        status = "TRIGGERED" if r["triggered"] else "OK"
        print(
            f"{r['symbol']:<10} ${r['current_price']:>9.2f} "
            f"${r['stop_price']:>9.2f} ${r['unrealized_pnl']:>+11.2f} "
            f"{r['pnl_percent']:>+9.2f}% {status}"
        )


def check_stop_loss(
    config: Config,
    auto_execute: bool = False,
    send_email: bool = False,
    logger: Optional[any] = None,
) -> None:
    """
    Check stop-loss conditions for all positions

    Args:
        config: Configuration object
        auto_execute: Whether to automatically execute stop-loss orders
        send_email: Whether to send email notification
        logger: Logger instance
    """
    if logger is None:
        logger = setup_logger("stop_loss", level="INFO", console=True)

    # Initialize trading client
    logger.info("Connecting to IBKR Gateway...")
    trading_client = TradingClient(
        host=config.ibkr_gateway_host,
        port=config.ibkr_gateway_port,
        client_id=config.ibkr_client_id,
    )

    # Initialize stop-loss manager
    stop_loss_manager = StopLossManager()

    try:
        # Connect to IBKR
        trading_client.connect()

        # Create checker
        checker = StopLossChecker(
            trading_client=trading_client,
            stop_loss_manager=stop_loss_manager,
            default_trailing_percent=config.default_trailing_stop_percent,
        )

        # Check positions
        logger.info("Checking stop-loss conditions for positions...")
        results = checker.check_positions(auto_execute=auto_execute)

        # Print results
        print_results(results)

        # Send email notification if configured
        if send_email and any(r["triggered"] for r in results):
            logger.info("Sending email notification...")
            try:
                # Check if email is configured
                if not all(
                    [
                        config.smtp_host,
                        config.smtp_port,
                        config.smtp_user,
                        config.smtp_password,
                        config.email_from,
                        config.email_to,
                    ]
                ):
                    logger.warning("Email configuration incomplete, skipping notification")
                else:
                    notifier = EmailNotifier(
                        smtp_host=config.smtp_host,
                        smtp_port=config.smtp_port,
                        smtp_user=config.smtp_user,
                        smtp_password=config.smtp_password,
                        from_email=config.email_from,
                        to_emails=config.email_to,
                        use_tls=config.smtp_use_tls,
                    )
                    notifier.send_stop_loss_alert(results)
            except ConfigurationError as e:
                logger.warning(f"Email notification failed: {e}")

    finally:
        trading_client.disconnect()


def set_trailing_stop(
    config: Config, symbol: str, trailing_percent: float, logger: Optional[any] = None
) -> None:
    """
    Set trailing stop-loss for a specific symbol

    Args:
        config: Configuration object
        symbol: Stock symbol
        trailing_percent: Trailing percentage (e.g., 5.0 for 5%)
        logger: Logger instance
    """
    if logger is None:
        logger = setup_logger("stop_loss", level="INFO", console=True)

    # Initialize trading client
    logger.info("Connecting to IBKR Gateway...")
    trading_client = TradingClient(
        host=config.ibkr_gateway_host,
        port=config.ibkr_gateway_port,
        client_id=config.ibkr_client_id,
    )

    # Initialize stop-loss manager
    stop_loss_manager = StopLossManager()

    try:
        # Connect to IBKR
        trading_client.connect()

        # Get current price
        logger.info(f"Getting current price for {symbol}...")
        current_price = trading_client.get_market_price(symbol)

        if current_price is None:
            logger.error(f"Unable to get price for {symbol}")
            return

        # Set trailing stop
        config_obj = stop_loss_manager.set_trailing_stop(symbol, current_price, trailing_percent)

        print(f"\nTrailing stop set for {symbol}:")
        print(f"  Current price: ${current_price:.2f}")
        print(f"  Stop percentage: {trailing_percent}%")
        print(f"  Stop price: ${config_obj.stop_price:.2f}")
        print()

    finally:
        trading_client.disconnect()


def list_stop_loss_configs(logger: Optional[any] = None) -> None:
    """
    List all stop-loss configurations

    Args:
        logger: Logger instance
    """
    if logger is None:
        logger = setup_logger("stop_loss", level="INFO", console=True)

    # Initialize stop-loss manager
    stop_loss_manager = StopLossManager()

    configs = stop_loss_manager.get_all_configs()

    if not configs:
        print("\nNo stop-loss configurations set")
        return

    print("\n" + "=" * 80)
    print("Current Stop-Loss Configurations:")
    print("=" * 80)
    print(f"{'Symbol':<10} {'Peak Price':>12} {'Stop Price':>12} {'Stop %':>12} {'Last Updated'}")
    print("-" * 80)

    for symbol, config in configs.items():
        print(
            f"{symbol:<10} ${config.peak_price:>11.2f} "
            f"${config.stop_price:>11.2f} {config.trailing_percent:>11.1f}% "
            f"{config.last_updated}"
        )


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

    from .api.trading_client import TradingClient

    logger.info("正在连接到 IBKR Gateway...")

    # Connect to IB Gateway
    client = TradingClient(
        host=config.ibkr_gateway_host,
        port=config.ibkr_gateway_port,
        client_id=config.ibkr_client_id,
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

    from .api.trading_client import TradingClient

    logger.info("Connecting to IBKR Gateway...")

    # Connect to IB Gateway
    client = TradingClient(
        host=config.ibkr_gateway_host,
        port=config.ibkr_gateway_port,
        client_id=config.ibkr_client_id,
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

    from .api.trading_client import TradingClient

    logger.info("正在连接到 IBKR Gateway...")

    # Connect to IB Gateway
    client = TradingClient(
        host=config.ibkr_gateway_host,
        port=config.ibkr_gateway_port,
        client_id=config.ibkr_client_id,
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
                symbol = order.get("symbol", "N/A")
                action = order.get("action", "N/A")
                quantity = order.get("quantity", 0)
                order_type = order.get("orderType", "N/A")
                status = order.get("status", "N/A")

                # Get type-specific field
                if order_type == "TRAIL":
                    type_info = f"{order.get('trailing_percent', 0):.1f}%"
                elif order_type == "STP":
                    type_info = f"${order.get('stop_price', 0):.2f}"
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
        print("  ibkr-toolkit stop-loss cancel --account U13900978")
        print("\n  # Cancel orders for specific symbols in account")
        print("  ibkr-toolkit stop-loss cancel --account U13900978 --symbols AAPL TSLA")
        sys.exit(1)

    if symbols and not account:
        print("\nError: --symbols parameter requires --account")
        sys.exit(1)

    from .api.trading_client import TradingClient

    logger.info("正在连接到 IBKR Gateway...")

    # Connect to IB Gateway
    client = TradingClient(
        host=config.ibkr_gateway_host,
        port=config.ibkr_gateway_port,
        client_id=config.ibkr_client_id,
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

            for order_id in order_ids:
                try:
                    client.cancel_order(order_id)
                    print(f"  Order {order_id} cancelled")
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
        description="IBKR Stop Loss Manager - Manage trailing stop strategies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:

  # Check stop-loss conditions for all positions
  ibkr-stop-loss check

  # Check and auto-execute stop-loss orders
  ibkr-stop-loss check --auto-execute

  # Check and send email notification
  ibkr-stop-loss check --email

  # Set 5% trailing stop for specific stock
  ibkr-stop-loss set AAPL --percent 5.0

  # View all stop-loss configurations
  ibkr-stop-loss list

Note:
  - TWS or IB Gateway must be running before use
  - Default ports: 7497 (TWS Paper), 4002 (IB Gateway Paper)
  - Connection parameters can be configured in .env file
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Subcommands")

    # Check command
    check_parser = subparsers.add_parser("check", help="Check stop-loss conditions for positions")
    check_parser.add_argument(
        "--auto-execute",
        action="store_true",
        help="Auto-execute stop-loss orders (use with caution)",
    )
    check_parser.add_argument("--email", action="store_true", help="Send email notification")

    # Set command
    set_parser = subparsers.add_parser("set", help="Set trailing stop")
    set_parser.add_argument("symbol", help="Stock symbol (e.g., AAPL)")
    set_parser.add_argument(
        "--percent",
        type=float,
        default=5.0,
        help="Stop percentage (default: 5.0, triggers on 5%% price drop)",
    )

    # List command
    subparsers.add_parser("list", help="View all stop-loss configurations")

    # Place command - place trailing stop orders in IB system
    place_parser = subparsers.add_parser(
        "place", help="Place trailing stop orders in IB system for account"
    )
    place_parser.add_argument("account", help="Account ID (e.g., U13900978)")
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
    place_buy_parser.add_argument("account", help="Account ID (e.g., U13900978)")
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
        print("Error: Please specify a subcommand (check, set, list, place, orders, cancel)")
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
        if args.command == "check":
            check_stop_loss(
                config=config,
                auto_execute=args.auto_execute,
                send_email=args.email,
                logger=logger,
            )
        elif args.command == "set":
            set_trailing_stop(
                config=config,
                symbol=args.symbol.upper(),
                trailing_percent=args.percent,
                logger=logger,
            )
        elif args.command == "list":
            list_stop_loss_configs(logger=logger)
        elif args.command == "place":
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
