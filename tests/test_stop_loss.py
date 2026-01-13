"""
Tests for Stop Loss Manager
"""

import json

import pytest

from ibkr_tax.services.stop_loss import StopLossConfig, StopLossManager


@pytest.fixture
def temp_config_file(tmp_path):
    """Create temporary config file"""
    return tmp_path / "stop_loss_config.json"


@pytest.fixture
def manager(temp_config_file):
    """Create StopLossManager with temporary config file"""
    return StopLossManager(config_file=temp_config_file)


class TestStopLossConfig:
    """Test StopLossConfig dataclass"""

    def test_config_creation(self):
        """Test creating a stop-loss configuration"""
        config = StopLossConfig(
            symbol="AAPL",
            trailing_percent=5.0,
            peak_price=150.0,
            stop_price=142.5,
            last_updated="2025-01-13T10:00:00",
        )

        assert config.symbol == "AAPL"
        assert config.trailing_percent == 5.0
        assert config.peak_price == 150.0
        assert config.stop_price == 142.5
        assert config.last_updated == "2025-01-13T10:00:00"


class TestStopLossManager:
    """Test StopLossManager"""

    def test_initial_state(self, manager):
        """Test manager initial state"""
        assert len(manager.configs) == 0

    def test_set_trailing_stop_new(self, manager):
        """Test setting trailing stop for new position"""
        config = manager.set_trailing_stop("AAPL", 150.0, 5.0)

        assert config.symbol == "AAPL"
        assert config.trailing_percent == 5.0
        assert config.peak_price == 150.0
        assert config.stop_price == 142.5  # 150 * 0.95

    def test_set_trailing_stop_update_higher_price(self, manager):
        """Test updating trailing stop with higher price"""
        # Initial setup
        manager.set_trailing_stop("AAPL", 150.0, 5.0)

        # Update with higher price
        config = manager.set_trailing_stop("AAPL", 160.0, 5.0)

        assert config.peak_price == 160.0
        assert config.stop_price == 152.0  # 160 * 0.95

    def test_set_trailing_stop_update_lower_price(self, manager):
        """Test updating trailing stop with lower price (should not change peak)"""
        # Initial setup
        manager.set_trailing_stop("AAPL", 160.0, 5.0)

        # Update with lower price - peak should not change
        config = manager.set_trailing_stop("AAPL", 155.0, 5.0)

        assert config.peak_price == 160.0  # Unchanged
        assert config.stop_price == 152.0  # Unchanged

    def test_check_stop_loss_not_triggered(self, manager):
        """Test checking stop-loss when not triggered"""
        manager.set_trailing_stop("AAPL", 150.0, 5.0)

        triggered, stop_price = manager.check_stop_loss_triggered("AAPL", 145.0)

        assert triggered is False
        assert stop_price == 142.5

    def test_check_stop_loss_triggered(self, manager):
        """Test checking stop-loss when triggered"""
        manager.set_trailing_stop("AAPL", 150.0, 5.0)

        triggered, stop_price = manager.check_stop_loss_triggered("AAPL", 140.0)

        assert triggered is True
        assert stop_price == 142.5

    def test_check_stop_loss_triggered_exact(self, manager):
        """Test checking stop-loss when price equals stop price"""
        manager.set_trailing_stop("AAPL", 150.0, 5.0)

        triggered, stop_price = manager.check_stop_loss_triggered("AAPL", 142.5)

        assert triggered is True
        assert stop_price == 142.5

    def test_check_stop_loss_update_peak(self, manager):
        """Test that checking stop-loss updates peak if price is higher"""
        manager.set_trailing_stop("AAPL", 150.0, 5.0)

        # Check with higher price
        triggered, stop_price = manager.check_stop_loss_triggered("AAPL", 160.0)

        assert triggered is False
        assert manager.configs["AAPL"].peak_price == 160.0
        assert manager.configs["AAPL"].stop_price == 152.0

    def test_check_stop_loss_no_config(self, manager):
        """Test checking stop-loss for symbol without config"""
        triggered, stop_price = manager.check_stop_loss_triggered("TSLA", 250.0)

        assert triggered is False
        assert stop_price is None

    def test_remove_stop_loss(self, manager):
        """Test removing stop-loss configuration"""
        manager.set_trailing_stop("AAPL", 150.0, 5.0)
        assert "AAPL" in manager.configs

        manager.remove_stop_loss("AAPL")
        assert "AAPL" not in manager.configs

    def test_get_all_configs(self, manager):
        """Test getting all configurations"""
        manager.set_trailing_stop("AAPL", 150.0, 5.0)
        manager.set_trailing_stop("TSLA", 250.0, 8.0)

        configs = manager.get_all_configs()

        assert len(configs) == 2
        assert "AAPL" in configs
        assert "TSLA" in configs

    def test_save_and_load_configs(self, temp_config_file):
        """Test saving and loading configurations"""
        # Create manager and set configs
        manager1 = StopLossManager(config_file=temp_config_file)
        manager1.set_trailing_stop("AAPL", 150.0, 5.0)
        manager1.set_trailing_stop("TSLA", 250.0, 8.0)

        # Create new manager with same file - should load configs
        manager2 = StopLossManager(config_file=temp_config_file)

        assert len(manager2.configs) == 2
        assert manager2.configs["AAPL"].peak_price == 150.0
        assert manager2.configs["TSLA"].peak_price == 250.0

    def test_config_file_format(self, temp_config_file, manager):
        """Test that config file is saved in correct JSON format"""
        manager.set_trailing_stop("AAPL", 150.0, 5.0)

        # Read the file
        with open(temp_config_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "AAPL" in data
        assert data["AAPL"]["symbol"] == "AAPL"
        assert data["AAPL"]["trailing_percent"] == 5.0
        assert data["AAPL"]["peak_price"] == 150.0
        assert data["AAPL"]["stop_price"] == 142.5

    def test_multiple_symbols(self, manager):
        """Test managing multiple symbols"""
        symbols = ["AAPL", "TSLA", "GOOGL", "MSFT"]
        prices = [150.0, 250.0, 140.0, 380.0]
        percents = [5.0, 8.0, 4.0, 6.0]

        for symbol, price, percent in zip(symbols, prices, percents):
            manager.set_trailing_stop(symbol, price, percent)

        assert len(manager.configs) == 4

        # Test each configuration
        for symbol, price, percent in zip(symbols, prices, percents):
            config = manager.configs[symbol]
            assert config.peak_price == price
            assert config.trailing_percent == percent
            expected_stop = price * (1 - percent / 100)
            assert abs(config.stop_price - expected_stop) < 0.01

    def test_trailing_percent_edge_cases(self, manager):
        """Test edge cases for trailing percentage"""
        # Very small percentage
        config1 = manager.set_trailing_stop("AAPL", 100.0, 0.1)
        assert abs(config1.stop_price - 99.9) < 0.01

        # Large percentage
        config2 = manager.set_trailing_stop("TSLA", 100.0, 20.0)
        assert abs(config2.stop_price - 80.0) < 0.01

    def test_price_precision(self, manager):
        """Test that prices are calculated with correct precision"""
        manager.set_trailing_stop("AAPL", 123.456, 5.5)

        expected_stop = 123.456 * (1 - 5.5 / 100)
        assert abs(manager.configs["AAPL"].stop_price - expected_stop) < 0.0001
