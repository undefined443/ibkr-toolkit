"""
IBKR Flex Query API Client
Used to fetch trading data from Interactive Brokers
"""

import json
import time
from typing import Any, Dict, Union

import requests
import xmltodict

from ..constants import (
    MAX_RETRIES,
    RETRY_BACKOFF,
    RETRY_DELAY,
)
from ..exceptions import APIError
from ..utils.logging import get_logger

logger = get_logger(__name__)


class FlexQueryClient:
    """IBKR Flex Query API client for fetching trading records"""

    def __init__(self, token: str, query_id: str):
        """
        Initialize the Flex Query API client

        Args:
            token: Flex Query token from IBKR Client Portal
            query_id: Query ID from IBKR Client Portal

        Raises:
            ValueError: If token or query_id is empty
        """
        if not token or not query_id:
            raise ValueError("Token and query_id cannot be empty")

        self.token = token
        self.query_id = query_id
        self.base_url = "https://gdcdyn.interactivebrokers.com/Universal/servlet"
        logger.debug(f"Initialized FlexQueryClient with query_id: {query_id}")

    def request_report(self, from_date: str = None, to_date: str = None) -> str:
        """
        Request report generation

        Args:
            from_date: Start date in YYYYMMDD format (optional, overrides query default)
            to_date: End date in YYYYMMDD format (optional, overrides query default)

        Returns:
            Reference code for retrieving the report

        Raises:
            APIError: If request fails
        """
        url = f"{self.base_url}/FlexStatementService.SendRequest"
        params = {
            "t": self.token,
            "q": self.query_id,
            "v": "3",  # API version
        }

        # Add date override parameters if provided
        if from_date:
            params["fd"] = from_date
        if to_date:
            params["td"] = to_date

        date_info = ""
        if from_date and to_date:
            date_info = f" (from {from_date} to {to_date})"
        logger.info(f"Requesting report from IBKR{date_info}...")

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Failed to request report: {e}")
            raise APIError(f"Failed to request report: {e}") from e

        try:
            # Parse XML response
            result = xmltodict.parse(response.content)
        except Exception as e:
            logger.error(f"Failed to parse XML response: {e}")
            raise APIError(f"Failed to parse XML response: {e}") from e

        if result["FlexStatementResponse"]["Status"] == "Success":
            reference_code = result["FlexStatementResponse"]["ReferenceCode"]
            logger.info(f"Report request successful, Reference Code: {reference_code}")
            return reference_code
        else:
            error_msg = result["FlexStatementResponse"].get("ErrorMessage", "Unknown error")
            logger.error(f"Request failed: {error_msg}")
            raise APIError(f"Request failed: {error_msg}")

    def get_report(
        self, reference_code: str, max_retries: int = MAX_RETRIES
    ) -> Union[Dict[str, Any], list]:
        """
        Retrieve report data using reference code

        Args:
            reference_code: Reference code from request_report()
            max_retries: Maximum number of retry attempts

        Returns:
            Report data as dictionary or list (for multiple accounts)

        Raises:
            APIError: If retrieval fails or times out
        """
        url = f"{self.base_url}/FlexStatementService.GetStatement"
        params = {"t": self.token, "q": reference_code, "v": "3"}

        logger.info("Retrieving report data...")

        # Report generation may take time, use retry mechanism
        for attempt in range(max_retries):
            try:
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
            except requests.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    delay = RETRY_DELAY * (RETRY_BACKOFF**attempt)
                    time.sleep(delay)
                    continue
                else:
                    raise APIError(f"Failed to retrieve report after {max_retries} attempts") from e

            try:
                result = xmltodict.parse(response.content)
            except Exception as e:
                logger.error(f"Failed to parse XML response: {e}")
                raise APIError(f"Failed to parse XML response: {e}") from e

            if "FlexStatementResponse" in result:
                status = result["FlexStatementResponse"]["Status"]
                if status == "Success":
                    logger.info("Report retrieved successfully")
                    flex_statement = result["FlexStatementResponse"]["FlexStatements"][
                        "FlexStatement"
                    ]
                    if isinstance(flex_statement, list):
                        logger.info(f"Found {len(flex_statement)} account(s)")
                    return flex_statement
                elif status == "Fail":
                    error = result["FlexStatementResponse"].get("ErrorMessage", "")
                    if "Statement is not yet ready" in error:
                        logger.info(f"Report generating... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(RETRY_DELAY)
                        continue
                    else:
                        logger.error(f"Retrieval failed: {error}")
                        raise APIError(f"Retrieval failed: {error}")
            elif "FlexQueryResponse" in result:
                logger.info("Report retrieved successfully")
                flex_statement = result["FlexQueryResponse"]["FlexStatements"]["FlexStatement"]
                if isinstance(flex_statement, list):
                    logger.info(f"Found {len(flex_statement)} account(s)")
                return flex_statement

        raise APIError(f"Report retrieval timeout after {max_retries} attempts")

    def fetch_data(self, from_date: str = None, to_date: str = None) -> Union[Dict[str, Any], list]:
        """
        Complete workflow: request and retrieve data

        Args:
            from_date: Start date in YYYYMMDD format (optional, overrides query default)
            to_date: End date in YYYYMMDD format (optional, overrides query default)

        Returns:
            Report data as dictionary or list (for multiple accounts)

        Raises:
            APIError: If any step fails
        """
        reference_code = self.request_report(from_date=from_date, to_date=to_date)
        time.sleep(2)  # Wait for report generation
        data = self.get_report(reference_code)
        return data

    def save_raw_data(self, data: Union[Dict[str, Any], list], filepath: str) -> None:
        """
        Save raw data to JSON file

        Args:
            data: Report data
            filepath: Output file path

        Raises:
            IOError: If file write fails
        """
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Raw data saved to: {filepath}")
        except IOError as e:
            logger.error(f"Failed to save raw data: {e}")
            raise IOError(f"Failed to save raw data: {e}") from e
