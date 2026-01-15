"""
IBKR Trading Client using Web API

This module provides a client for interacting with IBKR's Web API for trading operations.
Replaces the previous ib_async implementation.
"""

from typing import Any, Dict, List, Optional

from ..utils.logging import setup_logger
from .web_client import WebAPIClient, WebAPIError

logger = setup_logger("ibkr_toolkit.trading_client", level="INFO", console=True)


class TradingClient:
    """
    Trading client using IBKR Web API

    Provides functionality for:
    - Position management
    - Market data queries
    - Order placement and management
    - Account queries
    """

    def __init__(
        self,
        base_url: str = "https://localhost:5001/v1/api",
        verify_ssl: bool = False,
        timeout: int = 30,
    ):
        """
        Initialize trading client

        Args:
            base_url: IBKR Web API base URL
            verify_ssl: Whether to verify SSL certificates
            timeout: Request timeout in seconds
        """
        self.client = WebAPIClient(base_url=base_url, verify_ssl=verify_ssl, timeout=timeout)
        self._connected = False
        logger.info("Trading client initialized")

    def connect(self) -> bool:
        """
        Check connection to IBKR Web API

        Returns:
            True if connected and authenticated

        Raises:
            WebAPIError: If connection fails
        """
        try:
            auth_status = self.client.get_auth_status()
            self._connected = auth_status.get("authenticated", False)

            if self._connected:
                logger.info("Connected to IBKR Web API")
            else:
                logger.error("Not authenticated with IBKR Web API")

            return self._connected

        except WebAPIError as e:
            logger.error(f"Failed to connect: {e}")
            raise

    def disconnect(self):
        """
        Disconnect from IBKR Web API

        Note: Web API doesn't require explicit disconnect
        """
        self._connected = False
        logger.info("Disconnected from IBKR Web API")

    def is_connected(self) -> bool:
        """
        Check if connected

        Returns:
            True if connected
        """
        return self._connected

    def get_positions(self, account: str) -> List[Dict[str, Any]]:
        """
        Get account positions

        Args:
            account: Account ID

        Returns:
            List of position dictionaries with keys:
            - symbol: Stock symbol
            - position: Number of shares
            - avgCost: Average cost per share
            - mktPrice: Current market price
            - mktValue: Market value
            - unrealizedPnl: Unrealized P&L
            - conid: Contract ID

        Raises:
            WebAPIError: If request fails
        """
        try:
            positions = self.client.get_positions(account)

            # Format positions to match expected interface
            formatted_positions = []
            for pos in positions:
                formatted_positions.append(
                    {
                        "symbol": pos.get("contractDesc", ""),
                        "position": pos.get("position", 0),
                        "avgCost": pos.get("avgCost", 0),
                        "mktPrice": pos.get("mktPrice", 0),
                        "mktValue": pos.get("mktValue", 0),
                        "unrealizedPnl": pos.get("unrealizedPnl", 0),
                        "conid": pos.get("conid", 0),
                    }
                )

            logger.info(f"Retrieved {len(formatted_positions)} positions for account {account}")
            return formatted_positions

        except WebAPIError as e:
            logger.error(f"Failed to get positions: {e}")
            raise

    def get_market_price(self, symbol: str) -> Optional[float]:
        """
        Get current market price for a symbol

        Args:
            symbol: Stock symbol

        Returns:
            Current market price, or None if not available

        Raises:
            WebAPIError: If request fails
        """
        try:
            # First search for the contract
            results = self.client.search_contract(symbol)
            if not results:
                logger.warning(f"No contract found for symbol {symbol}")
                return None

            # Use the first result (usually the primary exchange)
            conid = results[0].get("conid")

            # Get market snapshot
            snapshot = self.client.get_market_snapshot([conid])
            if not snapshot:
                logger.warning(f"No market data available for {symbol}")
                return None

            # Extract last price (field 31)
            price = snapshot[0].get("31")
            if price:
                logger.info(f"Market price for {symbol}: ${price:.2f}")
                return float(price)

            return None

        except WebAPIError as e:
            logger.error(f"Failed to get market price for {symbol}: {e}")
            raise

    def place_trailing_stop_order(
        self,
        symbol: str,
        quantity: float,
        trailing_percent: float,
        action: str = "SELL",
        account: Optional[str] = None,
    ) -> dict:
        """
        Place a trailing stop order

        Args:
            symbol: Stock symbol
            quantity: Number of shares
            trailing_percent: Trailing stop percentage (e.g., 5.0 for 5%)
            action: Order action (SELL or BUY)
            account: Account ID (required)

        Returns:
            Dictionary with order information:
            {
                'orderId': int,
                'symbol': str,
                'quantity': float,
                'trailing_percent': float,
                'action': str,
                'status': str
            }

        Raises:
            WebAPIError: If order placement fails
        """
        if not account:
            raise WebAPIError("Account ID is required for placing orders")

        try:
            # Search for contract
            results = self.client.search_contract(symbol)
            if not results:
                logger.error(f"No contract found for symbol {symbol}")
                return {"symbol": symbol, "error": "Contract not found", "status": "failed"}

            conid = results[0].get("conid")

            # Create order payload
            order_payload = {
                "conid": conid,
                "orderType": "TRAIL",
                "side": action,
                "quantity": abs(quantity),
                "tif": "GTC",  # Good till cancelled
                "outsideRTH": True,  # Allow outside regular trading hours
                "auxPrice": trailing_percent,  # Trailing amount (percentage)
            }

            # Place order
            response = self.client.place_order(account, [order_payload])

            # Handle response
            if isinstance(response, list) and len(response) > 0:
                order_id = response[0].get("order_id")
                logger.info(
                    f"Placed {action} trailing stop order for {quantity} {symbol} "
                    f"with {trailing_percent}% trail, Order ID: {order_id}"
                )
                return {
                    "orderId": order_id,
                    "symbol": symbol,
                    "quantity": quantity,
                    "trailing_percent": trailing_percent,
                    "action": action,
                    "status": "Submitted",
                }

            logger.error(f"Failed to place order: {response}")
            return {"symbol": symbol, "error": str(response), "status": "failed"}

        except WebAPIError as e:
            logger.error(f"Failed to place trailing stop order: {e}")
            return {"symbol": symbol, "error": str(e), "status": "failed"}

    def place_trailing_stop_for_positions(
        self,
        account: str,
        trailing_percent: float,
        symbols: Optional[List[str]] = None,
        action: str = "SELL",
    ) -> List[dict]:
        """
        Place trailing stop orders for all positions in account

        Args:
            account: Account ID
            trailing_percent: Trailing stop percentage
            symbols: Optional list of symbols to filter (if None, all positions)
            action: Order action (SELL or BUY)

        Returns:
            List of order result dictionaries

        Raises:
            WebAPIError: If request fails
        """
        results = []

        try:
            positions = self.get_positions(account)

            for pos in positions:
                symbol = pos["symbol"]
                quantity = pos["position"]

                # Skip if quantity is 0
                if quantity == 0:
                    continue

                # Skip if symbols filter is provided and symbol not in list
                if symbols and symbol not in symbols:
                    continue

                # Place trailing stop order
                result = self.place_trailing_stop_order(
                    symbol=symbol,
                    quantity=quantity,
                    trailing_percent=trailing_percent,
                    action=action,
                    account=account,
                )

                results.append(result)

            logger.info(f"Placed {len(results)} trailing stop orders")
            return results

        except WebAPIError as e:
            logger.error(f"Failed to place trailing stop orders: {e}")
            raise

    def get_open_orders(self, account: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get open orders

        Args:
            account: Optional account ID filter

        Returns:
            List of order dictionaries

        Raises:
            WebAPIError: If request fails
        """
        try:
            if account:
                orders = self.client.get_live_orders(account)
            else:
                # Get all accounts and their orders
                accounts = self.client.get_accounts()
                orders = []
                for acc in accounts:
                    acc_id = acc.get("id") or acc.get("accountId")
                    acc_orders = self.client.get_live_orders(acc_id)
                    orders.extend(acc_orders)

            # Handle different response formats
            if isinstance(orders, dict):
                order_list = orders.get("orders", [])
            elif isinstance(orders, list):
                order_list = orders
            else:
                order_list = []

            logger.info(f"Retrieved {len(order_list)} open orders")
            return order_list

        except WebAPIError as e:
            logger.error(f"Failed to get open orders: {e}")
            raise

    def cancel_order(self, account: str, order_id: int) -> bool:
        """
        Cancel an order

        Args:
            account: Account ID
            order_id: Order ID to cancel

        Returns:
            True if successful

        Raises:
            WebAPIError: If cancellation fails
        """
        try:
            self.client.cancel_order(account, order_id)
            logger.info(f"Cancelled order {order_id}")
            return True

        except WebAPIError as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            raise

    def cancel_orders_by_account(
        self,
        account: str,
        symbols: Optional[List[str]] = None,
        order_type: Optional[str] = None,
    ) -> List[dict]:
        """
        Cancel all orders for an account

        Args:
            account: Account ID
            symbols: Optional list of symbols to filter
            order_type: Optional order type filter (e.g., "TRAIL")

        Returns:
            List of cancelled order info dictionaries

        Raises:
            WebAPIError: If request fails
        """
        results = []

        try:
            orders = self.get_open_orders(account)

            for order in orders:
                # Check if order matches filters
                if symbols and order.get("ticker") not in symbols:
                    continue

                if order_type and order.get("orderType") != order_type:
                    continue

                # Cancel the order
                order_id = order.get("orderId")
                symbol = order.get("ticker", "N/A")
                if order_id:
                    try:
                        self.cancel_order(account, order_id)
                        results.append(
                            {
                                "orderId": order_id,
                                "symbol": symbol,
                                "status": "cancelled",
                            }
                        )
                    except WebAPIError as e:
                        results.append(
                            {
                                "orderId": order_id,
                                "symbol": symbol,
                                "status": "failed",
                                "error": str(e),
                            }
                        )

            cancelled_count = len([r for r in results if r["status"] == "cancelled"])
            logger.info(f"Cancelled {cancelled_count} orders for account {account}")
            return results

        except WebAPIError as e:
            logger.error(f"Failed to cancel orders: {e}")
            raise

    def get_performance(self, account_ids: List[str], period: str = "1M") -> Dict[str, Any]:
        """
        Get account performance data

        Args:
            account_ids: List of account IDs to query
            period: Time period. Options: 1D, 7D, MTD, 1M, YTD, 1Y

        Returns:
            Performance data dictionary with returns, P&L, and metrics

        Raises:
            WebAPIError: If request fails

        Note:
            Rate limit: 1 request per 15 minutes
        """
        try:
            performance = self.client.get_performance(account_ids, period)
            logger.info(f"Retrieved performance data for {len(account_ids)} accounts")
            return performance

        except WebAPIError as e:
            logger.error(f"Failed to get performance data: {e}")
            raise

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
