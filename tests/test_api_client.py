"""
Tests for API client module
"""

from unittest.mock import Mock, patch

import pytest
import requests

from ibkr_tax.api.flex_query import FlexQueryClient
from ibkr_tax.exceptions import APIError


def test_client_initialization():
    """Test client initialization"""
    client = FlexQueryClient("test_token", "test_query")
    assert client.token == "test_token"
    assert client.query_id == "test_query"


def test_client_initialization_empty_token():
    """Test client initialization fails with empty token"""
    with pytest.raises(ValueError, match="Token and query_id cannot be empty"):
        FlexQueryClient("", "test_query")


def test_client_initialization_empty_query_id():
    """Test client initialization fails with empty query_id"""
    with pytest.raises(ValueError, match="Token and query_id cannot be empty"):
        FlexQueryClient("test_token", "")


@patch("ibkr_tax.api.flex_query.requests.get")
@patch("ibkr_tax.api.flex_query.xmltodict.parse")
def test_request_report_success(mock_parse, mock_get):
    """Test successful report request"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b"<xml>test</xml>"
    mock_get.return_value = mock_response

    mock_parse.return_value = {
        "FlexStatementResponse": {"Status": "Success", "ReferenceCode": "REF123"}
    }

    client = FlexQueryClient("test_token", "test_query")
    ref_code = client.request_report()

    assert ref_code == "REF123"
    mock_get.assert_called_once()


@patch("ibkr_tax.api.flex_query.requests.get")
@patch("ibkr_tax.api.flex_query.xmltodict.parse")
def test_request_report_failure(mock_parse, mock_get):
    """Test failed report request"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b"<xml>test</xml>"
    mock_get.return_value = mock_response

    mock_parse.return_value = {
        "FlexStatementResponse": {"Status": "Fail", "ErrorMessage": "Invalid token"}
    }

    client = FlexQueryClient("test_token", "test_query")

    with pytest.raises(APIError, match="Request failed: Invalid token"):
        client.request_report()


@patch("ibkr_tax.api.flex_query.requests.get")
def test_request_report_network_error(mock_get):
    """Test report request with network error"""
    mock_get.side_effect = requests.RequestException("Network error")

    client = FlexQueryClient("test_token", "test_query")

    with pytest.raises(APIError, match="Failed to request report"):
        client.request_report()


@patch("ibkr_tax.api.flex_query.requests.get")
@patch("ibkr_tax.api.flex_query.xmltodict.parse")
def test_request_report_with_date_params(mock_parse, mock_get):
    """Test report request with date parameters"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b"<xml>test</xml>"
    mock_get.return_value = mock_response

    mock_parse.return_value = {
        "FlexStatementResponse": {"Status": "Success", "ReferenceCode": "REF123"}
    }

    client = FlexQueryClient("test_token", "test_query")
    ref_code = client.request_report(from_date="20250101", to_date="20250131")

    assert ref_code == "REF123"
    call_params = mock_get.call_args[1]["params"]
    assert call_params["fd"] == "20250101"
    assert call_params["td"] == "20250131"


@patch("ibkr_tax.api.flex_query.requests.get")
@patch("ibkr_tax.api.flex_query.xmltodict.parse")
@patch("ibkr_tax.api.flex_query.time.sleep")
def test_get_report_retry_on_not_ready(mock_sleep, mock_parse, mock_get):
    """Test get_report retries when report is not ready"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b"<xml>test</xml>"
    mock_get.return_value = mock_response

    # First two calls return "not ready", third returns success
    mock_parse.side_effect = [
        {
            "FlexStatementResponse": {
                "Status": "Fail",
                "ErrorMessage": "Statement is not yet ready",
            }
        },
        {
            "FlexStatementResponse": {
                "Status": "Fail",
                "ErrorMessage": "Statement is not yet ready",
            }
        },
        {
            "FlexStatementResponse": {
                "Status": "Success",
                "FlexStatements": {"FlexStatement": {"@accountId": "U123"}},
            }
        },
    ]

    client = FlexQueryClient("test_token", "test_query")
    result = client.get_report("REF123", max_retries=3)

    assert result == {"@accountId": "U123"}
    assert mock_get.call_count == 3
    assert mock_sleep.call_count == 2


@patch("ibkr_tax.api.flex_query.requests.get")
@patch("ibkr_tax.api.flex_query.xmltodict.parse")
@patch("ibkr_tax.api.flex_query.time.sleep")
def test_get_report_timeout_after_max_retries(mock_sleep, mock_parse, mock_get):
    """Test get_report raises error after max retries"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b"<xml>test</xml>"
    mock_get.return_value = mock_response

    # Always return "not ready"
    mock_parse.return_value = {
        "FlexStatementResponse": {
            "Status": "Fail",
            "ErrorMessage": "Statement is not yet ready",
        }
    }

    client = FlexQueryClient("test_token", "test_query")

    with pytest.raises(APIError, match="Report retrieval timeout after 3 attempts"):
        client.get_report("REF123", max_retries=3)

    assert mock_get.call_count == 3


@patch("ibkr_tax.api.flex_query.requests.get")
@patch("ibkr_tax.api.flex_query.xmltodict.parse")
def test_get_report_multiple_accounts(mock_parse, mock_get):
    """Test get_report with multiple accounts"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b"<xml>test</xml>"
    mock_get.return_value = mock_response

    mock_parse.return_value = {
        "FlexStatementResponse": {
            "Status": "Success",
            "FlexStatements": {"FlexStatement": [{"@accountId": "U123"}, {"@accountId": "U456"}]},
        }
    }

    client = FlexQueryClient("test_token", "test_query")
    result = client.get_report("REF123")

    assert isinstance(result, list)
    assert len(result) == 2


@patch("ibkr_tax.api.flex_query.requests.get")
def test_get_report_network_retry(mock_get):
    """Test get_report retries on network error"""
    # First call fails, second succeeds
    mock_response_fail = Mock()
    mock_response_fail.side_effect = requests.RequestException("Timeout")

    mock_response_success = Mock()
    mock_response_success.status_code = 200
    mock_response_success.content = (
        b'<?xml version="1.0"?>'
        b"<FlexStatementResponse>"
        b"<Status>Success</Status>"
        b"<FlexStatements>"
        b'<FlexStatement accountId="U123"></FlexStatement>'
        b"</FlexStatements>"
        b"</FlexStatementResponse>"
    )

    mock_get.side_effect = [requests.RequestException("Timeout"), mock_response_success]

    client = FlexQueryClient("test_token", "test_query")

    with patch("ibkr_tax.api.flex_query.time.sleep"):
        result = client.get_report("REF123", max_retries=3)

    assert result is not None
    assert mock_get.call_count == 2


@patch("ibkr_tax.api.flex_query.FlexQueryClient.request_report")
@patch("ibkr_tax.api.flex_query.FlexQueryClient.get_report")
@patch("ibkr_tax.api.flex_query.time.sleep")
def test_fetch_data_complete_workflow(mock_sleep, mock_get_report, mock_request_report):
    """Test fetch_data complete workflow"""
    mock_request_report.return_value = "REF123"
    mock_get_report.return_value = {"@accountId": "U123"}

    client = FlexQueryClient("test_token", "test_query")
    result = client.fetch_data(from_date="20250101", to_date="20250131")

    assert result == {"@accountId": "U123"}
    mock_request_report.assert_called_once_with(from_date="20250101", to_date="20250131")
    mock_get_report.assert_called_once_with("REF123")
    mock_sleep.assert_called_once_with(2)


def test_save_raw_data_success(tmp_path):
    """Test save_raw_data writes file successfully"""
    client = FlexQueryClient("test_token", "test_query")
    data = {"@accountId": "U123", "Trades": []}

    filepath = tmp_path / "raw_data.json"
    client.save_raw_data(data, str(filepath))

    assert filepath.exists()

    import json

    with open(filepath, "r") as f:
        loaded_data = json.load(f)

    assert loaded_data == data


def test_save_raw_data_io_error(tmp_path):
    """Test save_raw_data handles IO error"""
    client = FlexQueryClient("test_token", "test_query")
    data = {"@accountId": "U123"}

    invalid_path = tmp_path / "nonexistent" / "raw_data.json"

    with pytest.raises(IOError, match="Failed to save raw data"):
        client.save_raw_data(data, str(invalid_path))
