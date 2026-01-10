"""
Tests for exchange rate service
"""

import json
from unittest.mock import Mock, patch

import requests

from ibkr_tax.services.exchange_rate import ExchangeRateService, get_exchange_rate_service


def test_load_cache_from_file(tmp_path):
    """Test loading cache from existing file"""
    cache_file = tmp_path / "cache.json"
    cache_data = {"2025-01-01": 7.2, "2025-01-02": 7.3}

    with open(cache_file, "w") as f:
        json.dump(cache_data, f)

    service = ExchangeRateService(str(cache_file))

    assert service.cache == cache_data


def test_load_cache_nonexistent_file(tmp_path):
    """Test loading cache when file does not exist"""
    cache_file = tmp_path / "nonexistent.json"

    service = ExchangeRateService(str(cache_file))

    assert service.cache == {}


def test_load_cache_corrupted_file(tmp_path):
    """Test loading cache from corrupted file"""
    cache_file = tmp_path / "corrupted.json"

    with open(cache_file, "w") as f:
        f.write("invalid json {")

    service = ExchangeRateService(str(cache_file))

    assert service.cache == {}


def test_save_cache(tmp_path):
    """Test saving cache to file"""
    cache_file = tmp_path / "cache.json"
    service = ExchangeRateService(str(cache_file))

    service.cache["2025-01-01"] = 7.2
    service._save_cache()

    assert cache_file.exists()

    with open(cache_file, "r") as f:
        loaded = json.load(f)

    assert loaded == {"2025-01-01": 7.2}


def test_get_rate_from_cache(tmp_path):
    """Test getting rate from cache"""
    cache_file = tmp_path / "cache.json"
    cache_data = {"2025-01-01": 7.5}

    with open(cache_file, "w") as f:
        json.dump(cache_data, f)

    service = ExchangeRateService(str(cache_file))
    rate = service.get_rate("2025-01-01", default_rate=7.2)

    assert rate == 7.5


def test_get_rate_normalizes_date_format(tmp_path):
    """Test date format normalization (YYYYMMDD to YYYY-MM-DD)"""
    cache_file = tmp_path / "cache.json"
    cache_data = {"2025-01-01": 7.5}

    with open(cache_file, "w") as f:
        json.dump(cache_data, f)

    service = ExchangeRateService(str(cache_file))

    # Test with YYYYMMDD format
    rate = service.get_rate("20250101", default_rate=7.2)

    assert rate == 7.5


@patch("ibkr_tax.services.exchange_rate.requests.get")
def test_get_rate_fetches_from_api(mock_get, tmp_path):
    """Test fetching rate from API when not in cache"""
    cache_file = tmp_path / "cache.json"
    service = ExchangeRateService(str(cache_file))

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"rates": {"CNY": 7.25}}
    mock_get.return_value = mock_response

    rate = service.get_rate("2025-01-01", default_rate=7.2)

    assert rate == 7.25
    assert service.cache["2025-01-01"] == 7.25


@patch("ibkr_tax.services.exchange_rate.requests.get")
def test_get_rate_uses_default_when_api_fails(mock_get, tmp_path):
    """Test using default rate when API fails"""
    cache_file = tmp_path / "cache.json"
    service = ExchangeRateService(str(cache_file))

    mock_get.side_effect = requests.RequestException("Network error")

    rate = service.get_rate("2025-01-01", default_rate=7.2)

    assert rate == 7.2
    assert service.cache["2025-01-01"] == 7.2


@patch("ibkr_tax.services.exchange_rate.requests.get")
def test_fetch_from_exchangerate_api_success(mock_get, tmp_path):
    """Test successful fetch from exchangerate-api.com"""
    cache_file = tmp_path / "cache.json"
    service = ExchangeRateService(str(cache_file))

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"rates": {"CNY": 7.28}}
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    with patch("ibkr_tax.services.exchange_rate.time.sleep"):
        rate = service._fetch_from_exchangerate_api("2025-01-01")

    assert rate == 7.28


@patch("ibkr_tax.services.exchange_rate.requests.get")
def test_fetch_from_exchangerate_api_failure(mock_get, tmp_path):
    """Test failed fetch from exchangerate-api.com"""
    cache_file = tmp_path / "cache.json"
    service = ExchangeRateService(str(cache_file))

    mock_get.side_effect = requests.RequestException("Timeout")

    with patch("ibkr_tax.services.exchange_rate.time.sleep"):
        rate = service._fetch_from_exchangerate_api("2025-01-01")

    assert rate is None


@patch("ibkr_tax.services.exchange_rate.requests.get")
def test_fetch_from_frankfurter_success(mock_get, tmp_path):
    """Test successful fetch from Frankfurter API"""
    cache_file = tmp_path / "cache.json"
    service = ExchangeRateService(str(cache_file))

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"rates": {"CNY": 7.32}}
    mock_get.return_value = mock_response

    rate = service._fetch_from_frankfurter("2025-01-01")

    assert rate == 7.32


@patch("ibkr_tax.services.exchange_rate.requests.get")
def test_fetch_from_frankfurter_failure(mock_get, tmp_path):
    """Test failed fetch from Frankfurter API"""
    cache_file = tmp_path / "cache.json"
    service = ExchangeRateService(str(cache_file))

    mock_response = Mock()
    mock_response.status_code = 404
    mock_get.return_value = mock_response

    rate = service._fetch_from_frankfurter("2025-01-01")

    assert rate is None


@patch("ibkr_tax.services.exchange_rate.requests.get")
def test_fetch_rate_from_api_tries_multiple_sources(mock_get, tmp_path):
    """Test API fallback chain when first API fails"""
    cache_file = tmp_path / "cache.json"
    service = ExchangeRateService(str(cache_file))

    # First API fails, second succeeds
    mock_response_fail = Mock()
    mock_response_fail.side_effect = requests.RequestException("Timeout")

    mock_response_success = Mock()
    mock_response_success.status_code = 200
    mock_response_success.json.return_value = {"rates": {"CNY": 7.35}}

    mock_get.side_effect = [
        requests.RequestException("First API failed"),
        mock_response_success,
    ]

    rate = service._fetch_rate_from_api("2025-01-01")

    assert rate == 7.35
    assert mock_get.call_count == 2


@patch("ibkr_tax.services.exchange_rate.requests.get")
def test_get_monthly_average_rate(mock_get, tmp_path):
    """Test calculating monthly average rate"""
    cache_file = tmp_path / "cache.json"
    service = ExchangeRateService(str(cache_file))

    # Mock API to return increasing rates
    def mock_api_response(*args, **kwargs):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"rates": {"CNY": 7.2}}
        return mock_response

    mock_get.side_effect = mock_api_response

    with patch("ibkr_tax.services.exchange_rate.time.sleep"):
        avg_rate = service.get_monthly_average_rate(2025, 1, default_rate=7.0)

    assert avg_rate == 7.2
    assert "2025-01-AVG" in service.cache


def test_get_monthly_average_rate_uses_cache(tmp_path):
    """Test monthly average uses cached daily rates"""
    cache_file = tmp_path / "cache.json"

    # Pre-populate cache with all days of January 2025
    cache_data = {f"2025-01-{day:02d}": 7.2 + (day * 0.01) for day in range(1, 32)}

    with open(cache_file, "w") as f:
        json.dump(cache_data, f)

    service = ExchangeRateService(str(cache_file))
    avg_rate = service.get_monthly_average_rate(2025, 1, default_rate=7.0)

    # Calculate expected average
    expected_avg = sum(cache_data.values()) / len(cache_data)

    assert abs(avg_rate - expected_avg) < 0.01


@patch("ibkr_tax.services.exchange_rate.requests.get")
def test_get_rates_for_dataframe(mock_get, tmp_path):
    """Test batch fetching rates for multiple dates"""
    cache_file = tmp_path / "cache.json"
    service = ExchangeRateService(str(cache_file))

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"rates": {"CNY": 7.25}}
    mock_get.return_value = mock_response

    dates = ["20250101", "20250102", "20250103"]

    with patch("ibkr_tax.services.exchange_rate.time.sleep"):
        rates = service.get_rates_for_dataframe(dates, default_rate=7.2)

    assert len(rates) == 3
    assert "20250101" in rates or "2025-01-01" in rates


def test_get_rates_for_dataframe_deduplicates_dates(tmp_path):
    """Test batch fetching deduplicates dates"""
    cache_file = tmp_path / "cache.json"

    cache_data = {"2025-01-01": 7.2}
    with open(cache_file, "w") as f:
        json.dump(cache_data, f)

    service = ExchangeRateService(str(cache_file))

    dates = ["20250101", "20250101", "20250101"]

    rates = service.get_rates_for_dataframe(dates, default_rate=7.0)

    assert len(rates) == 1
    assert "20250101" in rates or "2025-01-01" in rates


def test_get_exchange_rate_service_singleton():
    """Test singleton pattern for exchange rate service"""
    service1 = get_exchange_rate_service()
    service2 = get_exchange_rate_service()

    assert service1 is service2
