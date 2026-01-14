"""
Main CLI entry point for IBKR Toolkit
"""

import argparse
import sys

from ibkr_toolkit import __version__


def create_parser() -> argparse.ArgumentParser:
    """
    Create the main argument parser with subcommands

    Returns:
        ArgumentParser: Main parser with subcommands
    """
    parser = argparse.ArgumentParser(
        prog="ibkr-toolkit",
        description="A comprehensive toolkit for IBKR trading data processing and management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")

    # Create subcommands
    subparsers = parser.add_subparsers(
        title="commands",
        description="Available commands",
        dest="command",
        required=True,
        help="Command to execute",
    )

    # Report subcommand
    report_parser = subparsers.add_parser(
        "report",
        help="Generate tax reports from IBKR Flex Query data",
        description="Generate tax reports from IBKR Flex Query data",
    )
    report_parser.add_argument(
        "-y",
        "--year",
        type=int,
        help="Specify a single tax year (e.g., 2024)",
    )
    report_parser.add_argument(
        "--from-year",
        type=int,
        help="Specify the start year for multi-year query (e.g., 2020 will query 2020-current)",
    )
    report_parser.add_argument(
        "--all",
        action="store_true",
        help=(
            "Fetch all data from first trade year to current year (uses FIRST_TRADE_YEAR from .env)"
        ),
    )

    # Stop-loss subcommand
    stop_loss_parser = subparsers.add_parser(
        "stop-loss",
        help="Place and manage trailing stop orders in IB system",
        description="Place and manage trailing stop orders in IB system",
    )
    stop_loss_subparsers = stop_loss_parser.add_subparsers(
        title="stop-loss commands",
        description="Available stop-loss commands",
        dest="stop_loss_command",
        required=True,
        help="Stop-loss command to execute",
    )

    # Place command - place trailing stop orders in IB system
    place_parser = stop_loss_subparsers.add_parser(
        "place", help="Place trailing stop orders in IB system for specific account"
    )
    place_parser.add_argument("account", help="Account ID (e.g., U13900978)")
    place_parser.add_argument(
        "--percent",
        type=float,
        required=True,
        help="Trailing stop percentage (e.g., 5.0 for 5%%)",
    )
    place_parser.add_argument(
        "--symbols",
        nargs="+",
        help="Specific symbols to place orders for (if not specified, all positions)",
    )

    # Place-buy command - place trailing stop BUY orders
    place_buy_parser = stop_loss_subparsers.add_parser(
        "place-buy", help="Place trailing stop BUY orders for specific symbols"
    )
    place_buy_parser.add_argument("account", help="Account ID (e.g., U13900978)")
    place_buy_parser.add_argument(
        "--percent",
        type=float,
        required=True,
        help="Trailing stop percentage (e.g., 5.0 for 5%%)",
    )
    place_buy_parser.add_argument(
        "--symbols",
        nargs="+",
        required=True,
        help="Symbols to place buy orders for (required)",
    )

    # Orders command - view open orders
    orders_parser = stop_loss_subparsers.add_parser("orders", help="View open orders")
    orders_parser.add_argument("--account", help="Filter by account ID (optional)")

    # Cancel command - cancel orders
    cancel_parser = stop_loss_subparsers.add_parser("cancel", help="Cancel trailing stop orders")
    cancel_parser.add_argument(
        "order_ids",
        nargs="*",
        type=int,
        help="Order IDs to cancel (leave empty to use --account filter)",
    )
    cancel_parser.add_argument("--account", help="Cancel all trailing stop orders for this account")
    cancel_parser.add_argument(
        "--symbols",
        nargs="+",
        help="Only cancel orders for these symbols (requires --account)",
    )

    return parser


def main() -> None:
    """Main entry point for CLI"""
    parser = create_parser()
    args = parser.parse_args()

    # Route to appropriate command handler
    if args.command == "report":
        from ibkr_toolkit.cli import main as report_main

        # Pass arguments to report main
        sys.argv = ["ibkr-toolkit-report"]
        if args.year:
            sys.argv.extend(["--year", str(args.year)])
        if args.from_year:
            sys.argv.extend(["--from-year", str(args.from_year)])
        if args.all:
            sys.argv.append("--all")

        report_main()

    elif args.command == "stop-loss":
        from ibkr_toolkit.stop_loss_cli import main as stop_loss_main

        # Pass arguments to stop-loss main
        sys.argv = ["ibkr-toolkit-stop-loss", args.stop_loss_command]
        if args.stop_loss_command == "place":
            sys.argv.extend([args.account, "--percent", str(args.percent)])
            if args.symbols:
                sys.argv.extend(["--symbols"] + args.symbols)
        elif args.stop_loss_command == "place-buy":
            sys.argv.extend([args.account, "--percent", str(args.percent)])
            sys.argv.extend(["--symbols"] + args.symbols)
        elif args.stop_loss_command == "orders":
            if hasattr(args, "account") and args.account:
                sys.argv.extend(["--account", args.account])
        elif args.stop_loss_command == "cancel":
            if args.order_ids:
                sys.argv.extend([str(oid) for oid in args.order_ids])
            if hasattr(args, "account") and args.account:
                sys.argv.extend(["--account", args.account])
            if hasattr(args, "symbols") and args.symbols:
                sys.argv.extend(["--symbols"] + args.symbols)

        stop_loss_main()


if __name__ == "__main__":
    main()
