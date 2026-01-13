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

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
