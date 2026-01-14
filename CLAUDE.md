# IBKR Toolkit - 项目开发指南

本文档为项目开发者和 AI 助手提供项目特定的约定和指南。

## 项目概述

IBKR Toolkit 是一个综合性的 Interactive Brokers 工具集，提供两大核心功能：

1. **税务报表功能**：从 IBKR 获取交易数据并生成中国税务申报报表
2. **交易管理功能**：通过 IBKR Web API (Client Portal Gateway) 实时管理交易订单和持仓

## 技术栈

- Python 3.13+
- pandas: 数据处理
- requests: HTTP 请求
- xmltodict: XML 解析
- openpyxl: Excel 文件生成
- uv: 包管理和环境管理

## 代码规范

### 语言约定

- **代码：所有代码文件中的所有内容必须使用英文**
  - 函数名、变量名、类名：英文
  - 注释、docstring：英文
  - **字符串字面量（print、logger、错误消息等）：英文**
  - ❌ 禁止在代码中使用任何非英文字符（包括中文、emoji）
  - ✅ 用户面向的输出消息可以使用英文

- 文档：用户文档（README.md、STOP_LOSS_GUIDE.md）使用中文
- Emoji：禁止在代码和文档中使用 emoji

**示例：**

```python
# ❌ 错误 - 代码中不能有中文
logger.info("正在连接到 IBKR Gateway...")
print("✅ 订单已取消")  # emoji 也不允许

# ✅ 正确 - 全部使用英文
logger.info("Connecting to IBKR Gateway...")
print("Order cancelled successfully")
```

### 代码风格

- 使用 `ruff` 进行代码格式化和检查
- Docstring 使用 Google 风格
- 类型注解：尽可能使用类型提示

```python
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
```

## 项目结构

```
ibkr-toolkit/
├── src/ibkr_toolkit/
│   ├── api/
│   │   ├── flex_query.py       # IBKR Flex Query API 客户端（税务报表）
│   │   ├── trading_client.py   # IBKR Web API 客户端（交易管理）
│   │   └── web_client.py       # IBKR Web API 底层客户端
│   ├── parsers/
│   │   └── data_parser.py      # 数据解析和税务计算
│   ├── services/
│   │   └── exchange_rate.py    # 汇率服务
│   ├── utils/
│   │   └── logging.py          # 日志工具
│   ├── cli.py                  # 税务报表命令行入口
│   ├── stop_loss_cli.py        # 交易管理命令行入口
│   ├── main.py                 # 主入口（路由到各子命令）
│   ├── config.py               # 配置管理
│   ├── constants.py            # 常量定义
│   └── exceptions.py           # 自定义异常
├── tests/                      # 测试文件
├── data/
│   ├── cache/                  # 汇率缓存
│   └── output/                 # 输出文件
└── pyproject.toml              # 项目配置
```

## 核心功能模块

### 1. API 客户端 (`api/flex_query.py`)

负责与 IBKR Flex Query API 交互：

- `request_report()`: 请求报告生成，支持 `from_date` 和 `to_date` 参数
- `get_report()`: 获取报告数据，支持重试机制
- `fetch_data()`: 完整工作流，结合请求和获取

**重要特性**：

- 支持动态日期参数覆盖 Flex Query 配置
- 使用 `fd` (from date) 和 `td` (to date) 参数
- 最多支持 365 天的数据查询（IBKR 限制）

### 2. 数据解析器 (`parsers/data_parser.py`)

负责解析 IBKR 数据并计算税务：

- `parse_trades()`: 解析交易记录
- `parse_dividends()`: 解析股息数据
- `parse_withholding_tax()`: 解析预扣税
- `calculate_summary()`: 计算税务汇总

**税务计算逻辑**：

- 固定税率：20%（`constants.py:CHINA_DIVIDEND_TAX_RATE`）
- 应纳税额 = (交易净利润 + 股息收入) × 20%
- 可抵免税额 = min(境外预扣税, 股息收入 × 20%)
- 应补税额 = 应纳税额 - 可抵免税额

### 3. 汇率服务 (`services/exchange_rate.py`)

提供汇率查询和缓存：

- 支持动态汇率（从 API 获取当日汇率）
- 支持固定汇率（使用配置的固定值）
- 本地缓存机制（`data/cache/exchange_rates_cache.json`）
- 双 API 备份：exchangerate-api.com → Frankfurter API

**注意**：使用的是**当日汇率**，不是月平均汇率。

### 4. 命令行接口 (`cli.py` 和 `stop_loss_cli.py`)

**税务报表接口 (`cli.py`)**：

- 支持 `--year` / `-y` 参数指定单个税务年度
- 支持 `--from-year` 参数指定起始年份（多年查询）
- 支持 `--all` 参数查询从 `FIRST_TRADE_YEAR` 到当前的所有数据
- 自动分年查询并合并多年数据
- 自动处理单账户和多账户数据
- 生成 Excel、JSON 格式的输出文件

**交易管理接口 (`stop_loss_cli.py`)**：

- `place` 命令：为账户持仓下追踪止损卖单
- `place-buy` 命令：下追踪止损买单（逢低买入）
- `orders` 命令：查看所有活跃订单
- `cancel` 命令：取消订单
- 支持按账户、按股票过滤
- 使用 IBKR Web API (Client Portal Gateway)

**主入口 (`main.py`)**：

- 路由到 `report` 或 `stop-loss` 子命令
- 统一的命令行接口

**多年查询机制**：

- 当使用 `--from-year` 或 `--all` 时，自动按年分段查询
- 每年独立请求 IBKR API（1/1 - 12/31）
- 某一年查询失败不影响其他年份
- 自动合并所有年份的交易、股息、预扣税数据
- 避免 IBKR API 365 天的单次查询限制

### 5. 交易客户端 (`api/trading_client.py`)

负责与 IBKR Web API 交互：

**连接管理**：

- `connect()`: 检查 Web API 连接状态
- `disconnect()`: 断开连接
- `is_connected()`: 检查连接状态

**仓位和行情**：

- `get_positions()`: 获取账户所有持仓（股票代码、数量、市值、成本）
- `get_market_price()`: 获取股票当前市场价格

**订单管理**：

- `place_trailing_stop_order()`: 下追踪止损单（支持 SELL/BUY）
- `place_trailing_stop_for_positions()`: 为所有持仓批量下单
- `get_open_orders()`: 查看所有活跃订单
- `cancel_order()`: 取消指定订单
- `cancel_orders_by_account()`: 批量取消订单

**重要特性**：

- 使用 IBKR Web API (RESTful API)
- 订单直接提交到 IBKR 系统，24/7 自动监控
- 支持 GTC（Good Till Cancelled）订单
- 支持盘前盘后交易（outsideRth=True）

## 配置管理

### 环境变量（`.env`）

**税务报表功能（必需）**：

- `IBKR_FLEX_TOKEN`: IBKR API Token
- `IBKR_QUERY_ID`: Flex Query ID

**税务报表功能（可选）**：

- `USD_CNY_RATE`: 固定汇率（默认 7.2）
- `USE_DYNAMIC_EXCHANGE_RATES`: 是否使用动态汇率（默认 true）
- `OUTPUT_DIR`: 输出目录（默认 ./data/output）
- `FIRST_TRADE_YEAR`: 首次交易年份（用于 `--all` 参数）

**Web API 功能（可选）**：

- `IBKR_WEB_API_URL`: Client Portal Gateway URL（默认 https://localhost:5001/v1/api）
- `IBKR_WEB_API_VERIFY_SSL`: 是否验证 SSL 证书（默认 false）
- `IBKR_WEB_API_TIMEOUT`: 请求超时时间（默认 30 秒）
- `IBKR_WEB_API_MAX_REQUESTS_PER_SECOND`: 速率限制（默认 50 次/秒）

### 配置类 (`config.py`)

从环境变量和 `.env` 文件加载配置，提供默认值和验证。

## 开发工作流

### 环境设置

```bash
# 克隆项目
git clone <repository>
cd ibkr-toolkit

# 安装依赖（开发模式）
uv pip install -e .
```

### 运行测试

```bash
# 运行所有测试
uv run pytest

# 查看覆盖率
uv run pytest --cov=ibkr_tax

# 运行特定测试
uv run pytest tests/test_data_parser.py -v
```

### 代码质量检查

```bash
# 格式化代码
ruff format src tests

# 检查代码质量
ruff check src tests

# 自动修复
ruff check --fix src tests
```

### Pre-commit Hooks

项目使用 pre-commit 自动化代码质量检查和安全检查：

```bash
# 首次设置：安装 hooks 到 .git/hooks
uv run pre-commit install

# 手动运行所有文件检查
uv run pre-commit run --all-files

# 只检查暂存的文件
uv run pre-commit run

# 更新 hooks 到最新版本
uv run pre-commit autoupdate
```

**安全检查**：

- 检测私钥（detect-private-key）
- 防止提交 .env 文件
- 防止提交 data/output/ 下的财务数据文件
- 防止提交缓存文件
- 检测大文件（>500KB）

**代码质量检查**：

- Python 代码格式化和 linting（ruff）
- Markdown/YAML/JSON 格式化（prettier）
- 移除行尾空格
- 确保文件末尾有换行
- 检查合并冲突标记
- 验证 YAML/JSON/TOML 语法

**工作流程**：

1. 配置好后，每次 `git commit` 都会自动运行检查
2. 如果检查失败，提交会被阻止
3. 修复问题后重新提交
4. 紧急情况可以用 `git commit --no-verify` 跳过（不推荐）

### 运行工具

**税务报表**：

```bash
# 使用默认配置（Flex Query 日期范围）
uv run ibkr-toolkit report

# 指定单个年份
uv run ibkr-toolkit report --year 2025

# 从指定年份查询到现在
uv run ibkr-toolkit report --from-year 2020

# 查询所有数据（从 FIRST_TRADE_YEAR 到现在）
uv run ibkr-toolkit report --all

# 查看帮助
uv run ibkr-toolkit --help
```

**交易管理**（需要先启动 Client Portal Gateway）：

```bash
# 查看所有活跃订单
uv run ibkr-toolkit stop-loss orders

# 为账户持仓下追踪止损单
uv run ibkr-toolkit stop-loss place U12345678 --percent 5.0

# 为特定股票下单
uv run ibkr-toolkit stop-loss place U12345678 --percent 5.0 --symbols AAPL TSLA

# 下追踪止损买单（逢低买入）
uv run ibkr-toolkit stop-loss place-buy U12345678 --percent 5.0 --symbols AAPL

# 取消订单
uv run ibkr-toolkit stop-loss cancel 15 12

# 取消账户所有追踪止损单
uv run ibkr-toolkit stop-loss cancel --account U12345678
```

## 常见开发任务

### 添加新的数据类型

1. 在 `parsers/data_parser.py` 添加解析函数
2. 更新 `process_accounts()` 函数处理新数据
3. 在 `cli.py` 的 `export_to_excel()` 添加新的 sheet
4. 添加相应的测试

### 修改税务计算逻辑

1. 更新 `parsers/data_parser.py` 中的 `calculate_summary()` 函数
2. 如果税率变更，修改 `constants.py` 中的 `CHINA_DIVIDEND_TAX_RATE`
3. 更新 README.md 中的税率计算说明
4. 添加或更新相关测试

### 添加新的交易功能

1. 在 `api/trading_client.py` 添加新的 API 方法
2. 在 `stop_loss_cli.py` 添加新的命令处理函数
3. 在 `main.py` 的参数解析器中添加新命令
4. 添加相应的测试
5. 更新 README.md 文档

**示例**：添加查询账户余额功能

```python
# 1. 在 trading_client.py 添加方法
def get_account_balance(self, account: str) -> dict:
    """Get account balance information"""
    summary = self.client.get_account_summary(account)
    # ... implementation

# 2. 在 stop_loss_cli.py 添加命令处理
def view_account_balance(config: Config, account: str):
    client = TradingClient(
        base_url=config.web_api_url,
        verify_ssl=config.web_api_verify_ssl,
        timeout=config.web_api_timeout,
    )
    balance = client.get_account_balance(account)
    # ... display logic

# 3. 在 main.py 添加子命令
balance_parser = stop_loss_subparsers.add_parser('balance', ...)
```

## 调试技巧

### 查看原始数据

工具会保存原始 JSON 数据到 `data/output/raw_data_*.json`，可用于：

- 调试数据解析问题
- 验证 IBKR API 响应
- 审计数据完整性

### 启用详细日志

修改 `cli.py` 中的日志级别：

```python
logger = setup_logger("ibkr_tax", level="DEBUG", console=True)
```

### 测试特定日期范围

```bash
# 测试特定年份
uv run ibkr-toolkit --year 2024

# 测试当前年份
uv run ibkr-toolkit --year $(date +%Y)

# 测试多年查询
uv run ibkr-toolkit --from-year 2023

# 测试所有数据查询
uv run ibkr-toolkit --all
```

### 验证多年查询

使用多年查询功能时需要注意：

- 检查每年的查询状态（日志中会显示 `✓ Year XXXX fetched successfully`）
- 查看合并后的数据量是否符合预期
- 验证汇率缓存是否正确跨年使用
- 确认某年失败时其他年份仍然成功

## 重要注意事项

### IBKR API 限制

- 最多查询 365 天的数据
- 报告生成可能需要几秒到几分钟
- 使用重试机制处理"报告未准备好"的情况

### 汇率 API 限制

- exchangerate-api.com: 1500 次/月免费额度
- Frankfurter API: 无限制，但只有前一天的数据
- 使用本地缓存减少 API 调用

### 税务计算注意事项

- 使用当日汇率，不是月平均汇率
- 交易亏损可以抵减股息收入
- 外国税额抵免不能超过应纳税额
- 只计算已实现盈亏（closed lots），不包括未实现盈亏

## 提交规范

使用 Conventional Commits 格式：

```
feat: add support for year parameter in CLI
fix: correct exchange rate calculation for dividends
docs: update README with year parameter usage
refactor: simplify date parsing logic
test: add tests for date range override
```

## 发布检查清单

1. ✅ 所有测试通过
2. ✅ 代码格式化和检查无错误
3. ✅ README.md 文档更新
4. ✅ CHANGELOG.md 记录变更
5. ✅ 版本号更新（pyproject.toml）
6. ✅ 测试实际 IBKR API 调用
7. ✅ 验证输出文件格式正确

## 参考资源

- [IBKR Flex Query API 文档](https://www.interactivebrokers.com/en/software/am/am/reports/flex_web_service_version_3.htm)
- [中国个人所得税法](http://www.chinatax.gov.cn/)
- [pandas 文档](https://pandas.pydata.org/)
- [uv 文档](https://github.com/astral-sh/uv)

## 联系方式

如有问题或建议，请在 GitHub 上提交 Issue。
