"""
Stop-loss management service

Implements trailing stop-loss strategy for IBKR positions
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ..api.trading_client import TradingClient
from ..exceptions import APIError
from ..utils.logging import setup_logger

logger = setup_logger(__name__)


@dataclass
class StopLossConfig:
    """Configuration for a single position's stop-loss"""

    symbol: str
    trailing_percent: float  # Percentage below peak price (e.g., 5.0 for 5%)
    peak_price: float  # Highest price seen since position opened
    stop_price: float  # Current stop-loss trigger price
    last_updated: str  # ISO format timestamp


class StopLossManager:
    """Manager for trailing stop-loss strategy"""

    def __init__(self, config_file: Optional[Path] = None):
        """
        Initialize stop-loss manager

        Args:
            config_file: Path to stop-loss configuration file (JSON)
        """
        self.config_file = config_file or Path("data/cache/stop_loss_config.json")
        self.configs: Dict[str, StopLossConfig] = {}
        self._load_configs()

    def _load_configs(self) -> None:
        """Load stop-loss configurations from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.configs = {symbol: StopLossConfig(**cfg) for symbol, cfg in data.items()}
                logger.info(f"从 {self.config_file} 加载了 {len(self.configs)} 个止损配置")
            except Exception as e:
                logger.error(f"加载止损配置失败: {e}")
                self.configs = {}
        else:
            logger.info("未找到止损配置文件，将创建新配置")

    def _save_configs(self) -> None:
        """Save stop-loss configurations to file"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                data = {symbol: asdict(cfg) for symbol, cfg in self.configs.items()}
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"已保存 {len(self.configs)} 个止损配置到 {self.config_file}")
        except Exception as e:
            logger.error(f"保存止损配置失败: {e}")

    def set_trailing_stop(
        self, symbol: str, current_price: float, trailing_percent: float
    ) -> StopLossConfig:
        """
        Set or update trailing stop-loss for a position

        Args:
            symbol: Stock symbol
            current_price: Current market price
            trailing_percent: Trailing percentage (e.g., 5.0 for 5% below peak)

        Returns:
            Updated StopLossConfig
        """
        now = datetime.now().isoformat()

        if symbol in self.configs:
            # Update existing config
            config = self.configs[symbol]
            config.trailing_percent = trailing_percent

            # Update peak price if current price is higher
            if current_price > config.peak_price:
                config.peak_price = current_price
                config.stop_price = current_price * (1 - trailing_percent / 100)
                config.last_updated = now
                logger.info(
                    f"{symbol}: 更新峰值价格 ${config.peak_price:.2f}, "
                    f"止损价 ${config.stop_price:.2f}"
                )
        else:
            # Create new config
            stop_price = current_price * (1 - trailing_percent / 100)
            config = StopLossConfig(
                symbol=symbol,
                trailing_percent=trailing_percent,
                peak_price=current_price,
                stop_price=stop_price,
                last_updated=now,
            )
            self.configs[symbol] = config
            logger.info(
                f"{symbol}: 设置移动止损 {trailing_percent}%, "
                f"初始价格 ${current_price:.2f}, 止损价 ${stop_price:.2f}"
            )

        self._save_configs()
        return config

    def check_stop_loss_triggered(
        self, symbol: str, current_price: float
    ) -> tuple[bool, Optional[float]]:
        """
        Check if stop-loss is triggered for a position

        Args:
            symbol: Stock symbol
            current_price: Current market price

        Returns:
            (triggered: bool, stop_price: Optional[float])
        """
        if symbol not in self.configs:
            logger.warning(f"{symbol}: 未设置止损配置")
            return False, None

        config = self.configs[symbol]

        # Update peak and stop prices if current price is higher
        if current_price > config.peak_price:
            config.peak_price = current_price
            config.stop_price = current_price * (1 - config.trailing_percent / 100)
            config.last_updated = datetime.now().isoformat()
            self._save_configs()
            logger.info(
                f"{symbol}: 价格创新高 ${current_price:.2f}, 止损价上移至 ${config.stop_price:.2f}"
            )

        # Check if stop-loss is triggered
        triggered = current_price <= config.stop_price
        return triggered, config.stop_price

    def remove_stop_loss(self, symbol: str) -> None:
        """
        Remove stop-loss configuration for a symbol

        Args:
            symbol: Stock symbol
        """
        if symbol in self.configs:
            del self.configs[symbol]
            self._save_configs()
            logger.info(f"{symbol}: 已移除止损配置")

    def get_all_configs(self) -> Dict[str, StopLossConfig]:
        """Get all stop-loss configurations"""
        return self.configs.copy()


class StopLossChecker:
    """Checker for monitoring positions and executing stop-loss orders"""

    def __init__(
        self,
        trading_client: TradingClient,
        stop_loss_manager: StopLossManager,
        default_trailing_percent: float = 5.0,
    ):
        """
        Initialize stop-loss checker

        Args:
            trading_client: Trading API client
            stop_loss_manager: Stop-loss configuration manager
            default_trailing_percent: Default trailing percentage for new positions
        """
        self.client = trading_client
        self.manager = stop_loss_manager
        self.default_trailing_percent = default_trailing_percent

    def check_positions(self, auto_execute: bool = False) -> List[Dict]:
        """
        Check all positions for stop-loss conditions

        Args:
            auto_execute: If True, automatically execute stop-loss orders

        Returns:
            List of check results with position details and recommendations
        """
        if not self.client.is_connected():
            raise APIError("未连接到 IBKR Gateway")

        results = []
        positions = self.client.get_positions()

        logger.info(f"开始检查 {len(positions)} 个持仓的止损条件")

        for position in positions:
            symbol = position.contract.symbol
            quantity = int(position.position)
            avg_cost = float(position.averageCost)

            # Skip if no position
            if quantity <= 0:
                continue

            # Get current market price
            current_price = self.client.get_market_price(symbol)
            if current_price is None:
                logger.warning(f"{symbol}: 无法获取当前价格，跳过检查")
                continue

            # Initialize stop-loss config if not exists
            if symbol not in self.manager.configs:
                self.manager.set_trailing_stop(symbol, current_price, self.default_trailing_percent)

            # Check if stop-loss is triggered
            triggered, stop_price = self.manager.check_stop_loss_triggered(symbol, current_price)

            # Calculate P&L
            unrealized_pnl = (current_price - avg_cost) * quantity
            pnl_percent = ((current_price - avg_cost) / avg_cost) * 100

            result = {
                "symbol": symbol,
                "quantity": quantity,
                "avg_cost": avg_cost,
                "current_price": current_price,
                "stop_price": stop_price,
                "unrealized_pnl": unrealized_pnl,
                "pnl_percent": pnl_percent,
                "triggered": triggered,
                "action_taken": None,
            }

            if triggered:
                logger.warning(
                    f"{symbol}: 触发止损! 当前价 ${current_price:.2f} <= 止损价 ${stop_price:.2f}"
                )

                if auto_execute:
                    try:
                        order_id = self.client.place_stop_loss_order(symbol, quantity, stop_price)
                        result["action_taken"] = f"已下达止损单 (订单ID: {order_id})"
                        logger.info(f"{symbol}: {result['action_taken']}")
                    except Exception as e:
                        result["action_taken"] = f"下单失败: {e}"
                        logger.error(f"{symbol}: {result['action_taken']}")
                else:
                    result["action_taken"] = "建议手动下达止损单"
            else:
                logger.info(
                    f"{symbol}: 当前价 ${current_price:.2f}, "
                    f"止损价 ${stop_price:.2f}, "
                    f"未实现盈亏 ${unrealized_pnl:+.2f} ({pnl_percent:+.2f}%)"
                )

            results.append(result)

        return results
