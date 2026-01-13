"""
IBKR Trading API Client

This module provides a client for interacting with Interactive Brokers
using the ib_async library for trading operations like getting positions
and placing stop-loss orders.
"""

from typing import List, Optional

from ib_async import IB, PortfolioItem, Stock

from ..exceptions import APIError
from ..utils.logging import setup_logger

logger = setup_logger(__name__)


class TradingClient:
    """Client for IBKR Trading API operations"""

    def __init__(self, host: str = "127.0.0.1", port: int = 7497, client_id: int = 1):
        """
        Initialize Trading API client

        Args:
            host: TWS/IB Gateway host address
            port: TWS/IB Gateway port (7497 for TWS paper, 7496 for TWS live,
                  4002 for IB Gateway paper, 4001 for IB Gateway live)
            client_id: Client ID for connection (must be unique)
        """
        self.host = host
        self.port = port
        self.client_id = client_id
        self.ib = IB()
        self._connected = False

    def connect(self) -> None:
        """
        Connect to TWS or IB Gateway

        Raises:
            APIError: If connection fails
        """
        try:
            logger.info(f"正在连接到 IBKR Gateway {self.host}:{self.port}...")
            self.ib.connect(self.host, self.port, clientId=self.client_id)
            self._connected = True

            # Request delayed market data (free, 15-20 min delay)
            # This avoids "Error 10089: Requested market data requires additional subscription"
            self.ib.reqMarketDataType(3)  # 1=Live, 2=Frozen, 3=Delayed, 4=Delayed-Frozen

            logger.info("连接成功（使用延迟市场数据）")
        except Exception as e:
            raise APIError(f"连接失败: {e}")

    def disconnect(self) -> None:
        """Disconnect from TWS or IB Gateway"""
        if self._connected:
            self.ib.disconnect()
            self._connected = False
            logger.info("已断开连接")

    def is_connected(self) -> bool:
        """Check if currently connected"""
        return self._connected and self.ib.isConnected()

    def get_positions(self) -> List[PortfolioItem]:
        """
        Get current portfolio positions

        Returns:
            List of PortfolioItem objects containing position information

        Raises:
            APIError: If not connected or request fails
        """
        if not self.is_connected():
            raise APIError("未连接到 IBKR Gateway")

        try:
            # Use reqPositions() instead of portfolio() for better compatibility
            positions = self.ib.reqPositions()
            # Wait for data to arrive
            self.ib.sleep(2)

            # Convert Position objects to PortfolioItem format for compatibility
            portfolio_items = []
            for pos in positions:
                # Get market data for each position
                contract = pos.contract
                self.ib.qualifyContracts(contract)

                # Request market data
                ticker = self.ib.reqMktData(contract, "", False, False)
                self.ib.sleep(1)

                # Get market price
                market_price = ticker.marketPrice()
                if market_price != market_price:  # Check for NaN
                    market_price = ticker.last if ticker.last == ticker.last else ticker.close

                # Cancel market data
                self.ib.cancelMktData(contract)

                # Create PortfolioItem-like object
                from ib_async import PortfolioItem

                item = PortfolioItem(
                    contract=contract,
                    position=pos.position,
                    marketPrice=market_price if market_price == market_price else 0.0,
                    marketValue=pos.position
                    * (market_price if market_price == market_price else 0.0),
                    averageCost=pos.avgCost,
                    unrealizedPNL=0.0,  # Will be calculated if needed
                    realizedPNL=0.0,
                    account=pos.account,
                )
                portfolio_items.append(item)

            logger.info(f"获取到 {len(portfolio_items)} 个持仓")
            return portfolio_items
        except Exception as e:
            raise APIError(f"获取持仓失败: {e}")

    def get_market_price(self, symbol: str, exchange: str = "SMART") -> Optional[float]:
        """
        Get current market price for a symbol

        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            exchange: Exchange code (default: 'SMART' for best execution)

        Returns:
            Current market price or None if unavailable

        Raises:
            APIError: If not connected or request fails
        """
        if not self.is_connected():
            raise APIError("未连接到 IBKR Gateway")

        try:
            contract = Stock(symbol, exchange, "USD")
            self.ib.qualifyContracts(contract)

            # Request market data
            ticker = self.ib.reqMktData(contract, "", False, False)
            self.ib.sleep(2)  # Wait for data to arrive

            # Get last price or close price
            price = ticker.last if ticker.last == ticker.last else ticker.close

            # Cancel market data subscription
            self.ib.cancelMktData(contract)

            if price and price == price:  # Check for NaN
                logger.info(f"{symbol} 当前价格: ${price:.2f}")
                return float(price)
            else:
                logger.warning(f"无法获取 {symbol} 的价格")
                return None

        except Exception as e:
            raise APIError(f"获取价格失败: {e}")

    def place_stop_loss_order(
        self, symbol: str, quantity: int, stop_price: float, exchange: str = "SMART"
    ) -> str:
        """
        Place a stop-loss order

        Args:
            symbol: Stock symbol
            quantity: Number of shares to sell (positive number)
            stop_price: Stop price trigger
            exchange: Exchange code

        Returns:
            Order ID

        Raises:
            APIError: If order placement fails
        """
        if not self.is_connected():
            raise APIError("未连接到 IBKR Gateway")

        try:
            from ib_async import Order

            contract = Stock(symbol, exchange, "USD")
            self.ib.qualifyContracts(contract)

            # Create stop-loss order
            order = Order()
            order.action = "SELL"
            order.orderType = "STP"
            order.totalQuantity = quantity
            order.auxPrice = stop_price  # Stop price
            order.tif = "GTC"  # Good Till Cancelled

            # Place order
            trade = self.ib.placeOrder(contract, order)
            order_id = str(trade.order.orderId)

            logger.info(
                f"已下达止损单: {symbol} {quantity}股 @ ${stop_price:.2f} (订单ID: {order_id})"
            )
            return order_id

        except Exception as e:
            raise APIError(f"下达止损单失败: {e}")

    def cancel_order(self, order_id: int) -> None:
        """
        Cancel an order

        Args:
            order_id: Order ID to cancel

        Raises:
            APIError: If cancellation fails
        """
        if not self.is_connected():
            raise APIError("未连接到 IBKR Gateway")

        try:
            # Find the order
            trades = self.ib.trades()
            for trade in trades:
                if trade.order.orderId == order_id:
                    self.ib.cancelOrder(trade.order)
                    logger.info(f"已取消订单 {order_id}")
                    return

            logger.warning(f"未找到订单 {order_id}")

        except Exception as e:
            raise APIError(f"取消订单失败: {e}")

    def place_trailing_stop_order(
        self,
        symbol: str,
        quantity: int,
        trailing_percent: float,
        account: Optional[str] = None,
        exchange: str = "SMART",
    ) -> dict:
        """
        Place a trailing stop order

        Args:
            symbol: Stock symbol
            quantity: Number of shares to sell (positive number)
            trailing_percent: Trailing stop percentage (e.g., 5.0 for 5%)
            account: Account to place order for (optional)
            exchange: Exchange code (default: SMART)

        Returns:
            Dictionary with order information:
            {
                'orderId': int,
                'symbol': str,
                'quantity': int,
                'trailing_percent': float,
                'status': str
            }

        Raises:
            APIError: If order placement fails
        """
        if not self.is_connected():
            raise APIError("未连接到 IBKR Gateway")

        try:
            from ib_async import Order

            contract = Stock(symbol, exchange, "USD")
            self.ib.qualifyContracts(contract)

            # Create trailing stop order
            order = Order()
            order.action = "SELL"
            order.orderType = "TRAIL"
            order.totalQuantity = quantity
            order.trailingPercent = trailing_percent
            order.tif = "GTC"  # Good Till Cancelled
            order.outsideRth = True  # Allow execution outside regular trading hours

            if account:
                order.account = account

            # Place order
            trade = self.ib.placeOrder(contract, order)
            self.ib.sleep(1)  # Wait for order to be submitted

            order_id = trade.order.orderId
            status = trade.orderStatus.status

            logger.info(
                f"已下达追踪止损单: {symbol} {quantity}股 @ {trailing_percent}% "
                f"(订单ID: {order_id}, 状态: {status})"
            )

            return {
                "orderId": order_id,
                "symbol": symbol,
                "quantity": quantity,
                "trailing_percent": trailing_percent,
                "status": status,
            }

        except Exception as e:
            raise APIError(f"下达追踪止损单失败: {e}")

    def get_open_orders(self, account: Optional[str] = None) -> List[dict]:
        """
        Get all open orders

        Args:
            account: Filter by account (optional)

        Returns:
            List of order dictionaries with keys:
            - orderId, symbol, quantity, orderType, status, etc.

        Raises:
            APIError: If request fails
        """
        if not self.is_connected():
            raise APIError("未连接到 IBKR Gateway")

        try:
            trades = self.ib.openTrades()
            self.ib.sleep(1)

            orders = []
            for trade in trades:
                # Filter by account if specified
                if account and trade.order.account != account:
                    continue

                order_info = {
                    "orderId": trade.order.orderId,
                    "symbol": trade.contract.symbol,
                    "action": trade.order.action,
                    "quantity": trade.order.totalQuantity,
                    "orderType": trade.order.orderType,
                    "status": trade.orderStatus.status,
                    "account": trade.order.account,
                }

                # Add type-specific fields
                if trade.order.orderType == "TRAIL":
                    order_info["trailing_percent"] = trade.order.trailingPercent
                elif trade.order.orderType == "STP":
                    order_info["stop_price"] = trade.order.auxPrice

                orders.append(order_info)

            logger.info(f"找到 {len(orders)} 个活跃订单")
            return orders

        except Exception as e:
            raise APIError(f"获取订单失败: {e}")

    def place_trailing_stop_for_positions(
        self, account: str, trailing_percent: float, symbols: Optional[List[str]] = None
    ) -> List[dict]:
        """
        Place trailing stop orders for all positions in an account

        Args:
            account: Account ID to place orders for
            trailing_percent: Trailing stop percentage
            symbols: Optional list of symbols to filter (if None, all positions)

        Returns:
            List of order result dictionaries

        Raises:
            APIError: If request fails
        """
        if not self.is_connected():
            raise APIError("未连接到 IBKR Gateway")

        try:
            # Get positions for the account
            all_positions = self.get_positions()
            account_positions = [p for p in all_positions if p.account == account]

            # Filter by symbols if specified
            if symbols:
                account_positions = [p for p in account_positions if p.contract.symbol in symbols]

            if not account_positions:
                logger.warning(f"账户 {account} 没有找到持仓")
                return []

            results = []
            for pos in account_positions:
                symbol = pos.contract.symbol
                quantity = int(abs(pos.position))  # Use absolute value

                if quantity <= 0:
                    logger.warning(f"跳过 {symbol}：数量为 {quantity}")
                    continue

                try:
                    result = self.place_trailing_stop_order(
                        symbol=symbol,
                        quantity=quantity,
                        trailing_percent=trailing_percent,
                        account=account,
                    )
                    results.append(result)
                except Exception as e:
                    logger.error(f"为 {symbol} 下单失败: {e}")
                    results.append({"symbol": symbol, "error": str(e), "status": "failed"})

            logger.info(f"成功为 {len([r for r in results if 'orderId' in r])} 个持仓下单")
            return results

        except Exception as e:
            raise APIError(f"批量下单失败: {e}")

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
