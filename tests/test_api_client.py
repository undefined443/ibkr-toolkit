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
