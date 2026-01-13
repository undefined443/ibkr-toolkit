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
        print("\n没有持仓需要检查")
        return

    print("\n" + "=" * 80)
    print("止损检查结果")
    print("=" * 80)

    # Print summary
    triggered_count = sum(1 for r in results if r["triggered"])
    total_positions = len(results)
    total_unrealized_pnl = sum(r["unrealized_pnl"] for r in results)

    print(f"\n总持仓数: {total_positions}")
    print(f"触发止损: {triggered_count} 个")
    print(f"总未实现盈亏: ${total_unrealized_pnl:+,.2f}")

    # Print triggered positions
    if triggered_count > 0:
        print("\n" + "=" * 80)
        print("🚨 触发止损的持仓:")
        print("=" * 80)
        print(
            f"{'代码':<10} {'数量':>8} {'成本价':>10} {'当前价':>10} "
            f"{'止损价':>10} {'未实现盈亏':>12} {'操作'}"
        )
        print("-" * 80)

        for r in results:
            if r["triggered"]:
                print(
                    f"{r['symbol']:<10} {r['quantity']:>8} "
                    f"${r['avg_cost']:>9.2f} ${r['current_price']:>9.2f} "
                    f"${r['stop_price']:>9.2f} ${r['unrealized_pnl']:>+11.2f} "
                    f"{r.get('action_taken', '建议手动下单')}"
                )

    # Print all positions
    print("\n" + "=" * 80)
    print("📊 所有持仓:")
    print("=" * 80)
    print(
        f"{'代码':<10} {'当前价':>10} {'止损价':>10} {'未实现盈亏':>12} {'盈亏比例':>10} {'状态'}"
    )
    print("-" * 80)

    for r in results:
        status = "🚨 触发" if r["triggered"] else "✅ 正常"
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
    logger.info("正在连接到 IBKR Gateway...")
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
        logger.info("开始检查持仓止损条件...")
        results = checker.check_positions(auto_execute=auto_execute)

        # Print results
        print_results(results)

        # Send email notification if configured
        if send_email and any(r["triggered"] for r in results):
            logger.info("正在发送邮件通知...")
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
                    logger.warning("邮件配置不完整，跳过发送通知")
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
                logger.warning(f"邮件通知失败: {e}")

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
    logger.info("正在连接到 IBKR Gateway...")
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
        logger.info(f"获取 {symbol} 当前价格...")
        current_price = trading_client.get_market_price(symbol)

        if current_price is None:
            logger.error(f"无法获取 {symbol} 的价格")
            return

        # Set trailing stop
        config_obj = stop_loss_manager.set_trailing_stop(symbol, current_price, trailing_percent)

        print(f"\n✓ 已为 {symbol} 设置移动止损:")
        print(f"  当前价格: ${current_price:.2f}")
        print(f"  止损百分比: {trailing_percent}%")
        print(f"  止损价格: ${config_obj.stop_price:.2f}")
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
        print("\n未设置任何止损配置")
        return

    print("\n" + "=" * 80)
    print("当前止损配置:")
    print("=" * 80)
    print(f"{'代码':<10} {'峰值价格':>12} {'止损价格':>12} {'止损百分比':>12} {'最后更新'}")
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
        print(f"为账户 {account} 下追踪止损单")
        print(f"止损百分比: {trailing_percent}%")
        if symbols:
            print(f"指定股票: {', '.join(symbols)}")
        print(f"{'=' * 80}\n")

        # Place orders
        results = client.place_trailing_stop_for_positions(
            account=account,
            trailing_percent=trailing_percent,
            symbols=symbols,
        )

        if not results:
            print("未找到需要下单的持仓")
            return

        # Display results
        print(f"\n{'=' * 80}")
        print("下单结果:")
        print(f"{'=' * 80}\n")

        success_count = 0
        failed_count = 0

        for result in results:
            symbol = result.get("symbol")
            if "orderId" in result:
                print(
                    f"✓ {symbol:6s}: 订单ID {result['orderId']:4d}, "
                    f"{result['quantity']:2.0f}股, "
                    f"止损{result['trailing_percent']:.1f}%, "
                    f"状态: {result['status']}"
                )
                success_count += 1
            else:
                print(f"✗ {symbol:6s}: {result.get('error', '未知错误')}")
                failed_count += 1

        print(f"\n{'=' * 80}")
        print(f"成功: {success_count} 个 | 失败: {failed_count} 个")
        print(f"{'=' * 80}\n")

        print("提示: 这些订单已提交到IB系统，会自动监控和执行。")
        print("你可以在TWS/IB Gateway中查看和管理这些订单。")

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
            print(f"账户 {account} 的活跃订单:")
        else:
            print("所有账户的活跃订单:")
        print(f"{'=' * 80}\n")

        # Get open orders
        orders = client.get_open_orders(account=account)

        if not orders:
            print("未找到活跃订单")
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
            print(f"\n账户: {acc}")
            print("-" * 80)
            print(
                f"{'订单ID':<8} {'股票':<8} {'动作':<6} {'数量':<6} "
                f"{'类型':<8} {'止损%/价格':<12} {'状态':<15}"
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

        print(f"\n共 {len(orders)} 个活跃订单")

    finally:
        client.disconnect()


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="IBKR Stop Loss Manager - 管理移动止损策略",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:

  # 检查所有持仓的止损条件
  ibkr-stop-loss check

  # 检查并自动执行止损订单
  ibkr-stop-loss check --auto-execute

  # 检查并发送邮件通知
  ibkr-stop-loss check --email

  # 为特定股票设置 5% 移动止损
  ibkr-stop-loss set AAPL --percent 5.0

  # 查看所有止损配置
  ibkr-stop-loss list

注意:
  - 使用前需要先启动 TWS 或 IB Gateway
  - 默认端口: 7497 (TWS Paper), 4002 (IB Gateway Paper)
  - 可以在 .env 文件中配置连接参数
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # Check command
    check_parser = subparsers.add_parser("check", help="检查持仓止损条件")
    check_parser.add_argument(
        "--auto-execute", action="store_true", help="自动执行止损订单（谨慎使用）"
    )
    check_parser.add_argument("--email", action="store_true", help="发送邮件通知")

    # Set command
    set_parser = subparsers.add_parser("set", help="设置移动止损")
    set_parser.add_argument("symbol", help="股票代码 (如 AAPL)")
    set_parser.add_argument(
        "--percent",
        type=float,
        default=5.0,
        help="止损百分比 (默认: 5.0，表示价格下跌5%%时触发)",
    )

    # List command
    subparsers.add_parser("list", help="查看所有止损配置")

    # Place command - place trailing stop orders in IB system
    place_parser = subparsers.add_parser("place", help="在IB系统中为指定账户下追踪止损单")
    place_parser.add_argument("account", help="账户ID (如 U13900978)")
    place_parser.add_argument(
        "--percent",
        type=float,
        required=True,
        help="止损百分比 (如 5.0 表示价格下跌5%%时触发)",
    )
    place_parser.add_argument(
        "--symbols",
        nargs="+",
        help="指定股票代码（如不指定则为该账户所有持仓下单）",
    )

    # Orders command - view open orders
    orders_parser = subparsers.add_parser("orders", help="查看当前活跃订单")
    orders_parser.add_argument("--account", help="按账户过滤 (可选)")

    return parser.parse_args()


def main() -> None:
    """Main execution function"""
    args = parse_args()

    if not args.command:
        print("错误: 请指定子命令 (check, set, list, place, orders)")
        print("使用 --help 查看帮助")
        sys.exit(1)

    print_banner()

    # Initialize logger
    logger = setup_logger("stop_loss", level="INFO", console=True)

    try:
        # Load configuration
        logger.info("加载配置...")
        try:
            config = Config()
            logger.info("配置加载成功")
        except ConfigurationError as e:
            logger.error(f"配置错误: {e}")
            print("\n请检查 .env 文件或环境变量")
            print("必需的变量:")
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
        elif args.command == "orders":
            view_open_orders(
                config=config,
                account=args.account if hasattr(args, "account") else None,
                logger=logger,
            )

        print("\n" + "=" * 60)
        print("✓ 操作完成")
        print("=" * 60)

    except KeyboardInterrupt:
        logger.warning("操作被用户取消")
        print("\n\n操作被用户取消")
        sys.exit(0)
    except APIError as e:
        logger.error(f"API 错误: {e}")
        print(f"\n✗ API 错误: {e}")
        print("\n请检查:")
        print("  1. TWS 或 IB Gateway 是否已启动")
        print("  2. API 设置是否已启用")
        print("  3. 端口号是否正确")
        sys.exit(1)
    except IBKRTaxError as e:
        logger.error(f"应用错误: {e}", exc_info=True)
        print(f"\n✗ 错误: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"未预期的错误: {e}", exc_info=True)
        print(f"\n✗ 未预期的错误: {e}")
        print("\n详细错误信息请查看日志")
        sys.exit(1)


if __name__ == "__main__":
    main()
