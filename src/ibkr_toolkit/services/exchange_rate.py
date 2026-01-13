"""
Exchange Rate Service
Automatically fetches USD to CNY exchange rates from various sources
"""

import json
import os
import time
from typing import Dict, Optional

import requests


class ExchangeRateService:
    """Service to fetch and cache USD to CNY exchange rates"""

    def __init__(self, cache_file: str = "./exchange_rates_cache.json"):
        """
        Initialize exchange rate service

        Args:
            cache_file: Path to cache file for storing rates
        """
        self.cache_file = cache_file
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict[str, float]:
        """Load cached exchange rates from file"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Failed to load exchange rate cache: {e}")
                return {}
        return {}

    def _save_cache(self):
        """Save exchange rates to cache file"""
        try:
            with open(self.cache_file, "w") as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save exchange rate cache: {e}")

    def get_rate(self, date_str: str, default_rate: float = 7.2) -> float:
        """
        Get USD to CNY exchange rate for a specific date

        Args:
            date_str: Date in YYYYMMDD or YYYY-MM-DD format
            default_rate: Fallback rate if API fails

        Returns:
            Exchange rate (CNY per USD)
        """
        # Normalize date format to YYYY-MM-DD
        if len(date_str) == 8:  # YYYYMMDD
            normalized_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        else:
            normalized_date = date_str

        # Check cache first
        if normalized_date in self.cache:
            return self.cache[normalized_date]

        # Try to fetch from API
        rate = self._fetch_rate_from_api(normalized_date)

        if rate:
            self.cache[normalized_date] = rate
            self._save_cache()
            return rate
        else:
            # Use default rate and cache it
            print(f"  Warning: Using default rate {default_rate} for {normalized_date}")
            self.cache[normalized_date] = default_rate
            self._save_cache()
            return default_rate

    def _fetch_rate_from_api(self, date: str) -> Optional[float]:
        """
        Fetch exchange rate from API

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            Exchange rate or None if failed
        """
        # Try multiple APIs in order of preference
        apis = [
            self._fetch_from_exchangerate_api,
            self._fetch_from_frankfurter,
        ]

        for api_func in apis:
            try:
                rate = api_func(date)
                if rate:
                    return rate
            except Exception:
                continue

        return None

    def _fetch_from_exchangerate_api(self, date: str) -> Optional[float]:
        """
        Fetch from exchangerate-api.com (free tier: 1500 requests/month)

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            USD to CNY rate or None
        """
        try:
            # For historical data, use the date endpoint
            url = "https://api.exchangerate-api.com/v4/latest/USD"

            # Add a small delay to avoid rate limiting
            time.sleep(0.1)

            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            if "rates" in data and "CNY" in data["rates"]:
                return float(data["rates"]["CNY"])

        except Exception:
            pass

        return None

    def _fetch_from_frankfurter(self, date: str) -> Optional[float]:
        """
        Fetch from Frankfurter API (free, no limits, but data up to previous day)

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            USD to CNY rate or None
        """
        try:
            url = f"https://api.frankfurter.app/{date}"
            params = {"from": "USD", "to": "CNY"}

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if "rates" in data and "CNY" in data["rates"]:
                    return float(data["rates"]["CNY"])

        except Exception:
            pass

        return None

    def get_monthly_average_rate(self, year: int, month: int, default_rate: float = 7.2) -> float:
        """
        Get average exchange rate for a specific month

        Args:
            year: Year (e.g., 2025)
            month: Month (1-12)
            default_rate: Fallback rate if calculation fails

        Returns:
            Average exchange rate for the month
        """
        from calendar import monthrange

        # Get all days in the month
        num_days = monthrange(year, month)[1]
        rates = []

        for day in range(1, num_days + 1):
            date_str = f"{year:04d}-{month:02d}-{day:02d}"
            try:
                rate = self.get_rate(date_str, default_rate)
                rates.append(rate)
            except Exception:
                continue

        if rates:
            avg_rate = sum(rates) / len(rates)
            # Cache the monthly average
            month_key = f"{year:04d}-{month:02d}-AVG"
            self.cache[month_key] = avg_rate
            self._save_cache()
            return avg_rate
        else:
            return default_rate

    def get_rates_for_dataframe(self, dates, default_rate: float = 7.2) -> Dict[str, float]:
        """
        Get exchange rates for multiple dates efficiently

        Args:
            dates: List of dates in YYYYMMDD or YYYY-MM-DD format
            default_rate: Fallback rate

        Returns:
            Dictionary mapping date to exchange rate
        """
        rates = {}
        unique_dates = set(dates)

        print(f"  Fetching exchange rates for {len(unique_dates)} unique dates...")

        for i, date in enumerate(unique_dates):
            if i > 0 and i % 10 == 0:
                print(f"    Progress: {i}/{len(unique_dates)} dates processed")

            rates[date] = self.get_rate(date, default_rate)

        print("  ✓ Exchange rates fetched successfully")
        return rates


# Singleton instance
_exchange_rate_service = None


def get_exchange_rate_service(
    cache_file: str = "./exchange_rates_cache.json",
) -> ExchangeRateService:
    """
    Get or create exchange rate service instance

    Args:
        cache_file: Path to cache file

    Returns:
        ExchangeRateService instance
    """
    global _exchange_rate_service
    if _exchange_rate_service is None:
        _exchange_rate_service = ExchangeRateService(cache_file)
    return _exchange_rate_service
