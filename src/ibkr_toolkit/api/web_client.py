"""
IBKR Client Portal Web API Client

Provides a Python interface to the IBKR Client Portal Web API (RESTful API).
Handles authentication, session management, rate limiting, and common API operations.
"""

import logging
import time
from typing import Any, Dict, List, Optional

import requests
from urllib3.exceptions import InsecureRequestWarning

# Disable SSL warnings for self-signed certificate
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

logger = logging.getLogger(__name__)


class WebAPIError(Exception):
    """Exception raised for Web API errors"""

    def __init__(
        self, message: str, status_code: Optional[int] = None, response: Optional[Dict] = None
    ):
        self.status_code = status_code
        self.response = response
        super().__init__(message)


class RateLimiter:
    """Simple rate limiter for API calls"""

    def __init__(self, max_requests: int = 50, time_window: float = 1.0):
        """
        Initialize rate limiter

        Args:
            max_requests: Maximum number of requests per time window
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []

    def wait_if_needed(self):
        """Wait if rate limit would be exceeded"""
        now = time.time()

        # Remove old requests outside the time window
        self.requests = [
            req_time for req_time in self.requests if now - req_time < self.time_window
        ]

        # If at limit, wait
        if len(self.requests) >= self.max_requests:
            sleep_time = self.time_window - (now - self.requests[0])
            if sleep_time > 0:
                logger.debug(f"Rate limit reached, sleeping for {sleep_time:.2f}s")
                time.sleep(sleep_time)
                # Clean up again after sleeping
                now = time.time()
                self.requests = [
                    req_time for req_time in self.requests if now - req_time < self.time_window
                ]

        # Record this request
        self.requests.append(now)


class WebAPIClient:
    """
    Client for IBKR Client Portal Web API

    Provides methods for:
    - Account information and management
    - Market data retrieval
    - Order placement and management
    - Contract search
    - Portfolio analytics
    """

    def __init__(
        self,
        base_url: str = "https://localhost:5001/v1/api",
        verify_ssl: bool = False,
        max_requests_per_second: int = 50,
        timeout: int = 30,
    ):
        """
        Initialize Web API client

        Args:
            base_url: Base URL for the Client Portal Gateway
            verify_ssl: Whether to verify SSL certificates (False for self-signed certs)
            max_requests_per_second: Maximum API requests per second (global limit is 50)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.session = requests.Session()
        self.rate_limiter = RateLimiter(max_requests=max_requests_per_second, time_window=1.0)
        self._last_tickle = 0
        self._tickle_interval = 60  # Tickle every 60 seconds

    def _request(
        self, method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None
    ) -> Any:
        """
        Make HTTP request with rate limiting and error handling

        Args:
            method: HTTP method (GET, POST, DELETE)
            endpoint: API endpoint (without base URL)
            data: Request body data (for POST)
            params: Query parameters

        Returns:
            Response data (dict, list, or string)

        Raises:
            WebAPIError: If request fails
        """
        # Rate limiting
        self.rate_limiter.wait_if_needed()

        # Auto-tickle to keep session alive
        self._auto_tickle()

        # Prepare request
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {"Content-Type": "application/json"}

        try:
            # Make request
            if method == "GET":
                response = self.session.get(
                    url, params=params, verify=self.verify_ssl, timeout=self.timeout
                )
            elif method == "POST":
                response = self.session.post(
                    url,
                    json=data,
                    params=params,
                    headers=headers,
                    verify=self.verify_ssl,
                    timeout=self.timeout,
                )
            elif method == "DELETE":
                response = self.session.delete(
                    url, params=params, verify=self.verify_ssl, timeout=self.timeout
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            # Check status code
            if response.status_code == 404:
                raise WebAPIError(f"Endpoint not found: {endpoint}", status_code=404)

            if response.status_code >= 400:
                error_msg = f"API request failed with status {response.status_code}"
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_msg += f": {error_data['error']}"
                except Exception:
                    error_msg += f": {response.text[:200]}"
                raise WebAPIError(
                    error_msg,
                    status_code=response.status_code,
                    response=response.json() if response.text else None,
                )

            # Parse response
            if response.text:
                try:
                    return response.json()
                except ValueError:
                    return response.text
            return None

        except requests.exceptions.Timeout:
            raise WebAPIError(f"Request timeout after {self.timeout}s")
        except requests.exceptions.ConnectionError as e:
            raise WebAPIError(f"Connection error: {e}")
        except WebAPIError:
            raise
        except Exception as e:
            raise WebAPIError(f"Unexpected error: {e}")

    def _auto_tickle(self):
        """Automatically tickle session if needed"""
        now = time.time()
        if now - self._last_tickle > self._tickle_interval:
            try:
                # Directly call tickle endpoint without going through _request to avoid recursion
                url = f"{self.base_url}/tickle"
                self.session.post(url, verify=self.verify_ssl, timeout=self.timeout)
                self._last_tickle = now
            except Exception as e:
                logger.warning(f"Auto-tickle failed: {e}")

    # ==================== Session Management ====================

    def tickle(self) -> Dict[str, Any]:
        """
        Keep session alive

        Returns:
            Session information including authentication status
        """
        return self._request("POST", "/tickle")

    def get_auth_status(self) -> Dict[str, Any]:
        """
        Get authentication status

        Returns:
            Auth status including authenticated, competing, connected flags
        """
        return self._request("GET", "/iserver/auth/status")

    def reauthenticate(self) -> Dict[str, Any]:
        """
        Reauthenticate to establish brokerage session

        Returns:
            Authentication response
        """
        return self._request("POST", "/iserver/reauthenticate")

    # ==================== Account Information ====================

    def get_accounts(self) -> List[Dict[str, Any]]:
        """
        Get list of accounts

        Returns:
            List of account objects with id, alias, type, etc.
        """
        return self._request("GET", "/portfolio/accounts")

    def get_server_accounts(self) -> Dict[str, Any]:
        """
        Get server accounts with properties and features

        Returns:
            Server accounts response including account list and properties
        """
        return self._request("GET", "/iserver/accounts")

    def get_account_summary(self, account_id: str) -> Dict[str, Any]:
        """
        Get account summary (balances, margins, etc.)

        Args:
            account_id: Account identifier

        Returns:
            Account summary with all balance and margin fields
        """
        return self._request("GET", f"/portfolio/{account_id}/summary")

    def get_account_ledger(self, account_id: str) -> Dict[str, Any]:
        """
        Get account ledger (currency balances)

        Args:
            account_id: Account identifier

        Returns:
            Currency-specific balance information
        """
        return self._request("GET", f"/portfolio/{account_id}/ledger")

    # ==================== Positions ====================

    def get_positions(self, account_id: str, page_id: int = 0) -> List[Dict[str, Any]]:
        """
        Get account positions

        Args:
            account_id: Account identifier
            page_id: Page ID for pagination (default 0)

        Returns:
            List of position objects
        """
        return self._request("GET", f"/portfolio/{account_id}/positions/{page_id}")

    # ==================== Contract Search ====================

    def search_contract(self, symbol: str, name: bool = False) -> List[Dict[str, Any]]:
        """
        Search for contracts by symbol

        Args:
            symbol: Stock symbol to search
            name: Search by name instead of symbol

        Returns:
            List of matching contracts
        """
        data = {"symbol": symbol}
        if name:
            data["name"] = True
        return self._request("POST", "/iserver/secdef/search", data=data)

    def get_contract_info(self, conid: int) -> Dict[str, Any]:
        """
        Get detailed contract information

        Args:
            conid: Contract ID

        Returns:
            Contract details
        """
        return self._request("GET", f"/iserver/contract/{conid}/info")

    # ==================== Market Data ====================

    def get_market_snapshot(
        self, conids: List[int], fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get market data snapshot for contracts

        Args:
            conids: List of contract IDs
            fields: List of field IDs to retrieve (default: last, bid, ask, volume, change)

        Returns:
            List of market data snapshots

        Note:
            First call initializes data stream, may return empty. Call again for data.
        """
        if fields is None:
            fields = ["31", "84", "85", "86", "88"]  # Last, Bid, Ask, Volume, Change

        conids_str = ",".join(str(c) for c in conids)
        fields_str = ",".join(fields)

        params = {"conids": conids_str, "fields": fields_str}
        return self._request("GET", "/iserver/marketdata/snapshot", params=params)

    # ==================== Orders ====================

    def get_live_orders(
        self, account_id: Optional[str] = None, filters: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get live orders

        Args:
            account_id: Filter by account ID
            filters: Additional filters

        Returns:
            Live orders response
        """
        params = {}
        if account_id:
            params["accountId"] = account_id
        if filters:
            params["filters"] = filters
        return self._request("GET", "/iserver/account/orders", params=params)

    def preview_order(self, account_id: str, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Preview order (what-if analysis)

        Args:
            account_id: Account identifier
            order_data: Order parameters (conid, orderType, side, tif, quantity, etc.)

        Returns:
            Order preview with margin and risk info
        """
        return self._request(
            "POST", f"/iserver/account/{account_id}/orders/whatif", data=order_data
        )

    def place_order(self, account_id: str, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Place an order

        Args:
            account_id: Account identifier
            order_data: Order parameters

        Returns:
            Order placement response

        Warning:
            This places a REAL order. Use preview_order first.
        """
        logger.warning(f"Placing REAL order for account {account_id}")
        return self._request("POST", f"/iserver/account/{account_id}/orders", data=order_data)

    def modify_order(
        self, account_id: str, order_id: str, order_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Modify an existing order

        Args:
            account_id: Account identifier
            order_id: Order ID to modify
            order_data: Updated order parameters

        Returns:
            Modification response
        """
        return self._request(
            "POST", f"/iserver/account/{account_id}/order/{order_id}", data=order_data
        )

    def cancel_order(self, account_id: str, order_id: str) -> Dict[str, Any]:
        """
        Cancel an order

        Args:
            account_id: Account identifier
            order_id: Order ID to cancel

        Returns:
            Cancellation response
        """
        return self._request("DELETE", f"/iserver/account/{account_id}/order/{order_id}")

    # ==================== Trades and P&L ====================

    def get_trades(self, days: int = 1) -> List[Dict[str, Any]]:
        """
        Get recent trades

        Args:
            days: Number of days of trade history

        Returns:
            List of trade executions
        """
        return self._request("GET", "/iserver/account/trades")

    def get_pnl(self) -> Dict[str, Any]:
        """
        Get profit and loss data

        Returns:
            P&L data partitioned by account
        """
        return self._request("GET", "/iserver/account/pnl/partitioned")

    # ==================== Scanner ====================

    def get_scanner_params(self) -> Dict[str, Any]:
        """
        Get available scanner parameters

        Returns:
            Scanner configuration including instruments, locations, scan types
        """
        return self._request("GET", "/iserver/scanner/params")

    def run_scanner(self, scanner_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Run market scanner

        Args:
            scanner_data: Scanner parameters

        Returns:
            List of matching contracts
        """
        return self._request("POST", "/iserver/scanner/run", data=scanner_data)
