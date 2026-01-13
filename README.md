# IBKR Toolkit

自动获取 Interactive Brokers (IBKR) 交易数据并生成中国税务申报报表的工具。

## 目录

- [功能特点](#功能特点)
- [快速开始](#快速开始)
- [IBKR Flex Query 配置](#ibkr-flex-query-配置)
- [汇率计算机制](#汇率计算机制)
- [税率计算逻辑](#税率计算逻辑)
- [输出文件说明](#输出文件说明)
- [开发指南](#开发指南)
- [常见问题](#常见问题)
- [许可证](#许可证)

## 功能特点

### 税务报表功能

- ✅ 自动从 IBKR 获取交易记录
- ✅ 解析交易、股息、预扣税数据
- ✅ 自动获取实时汇率或使用固定汇率
- ✅ 生成 Excel 报表和 JSON 数据
- ✅ 自动计算应纳税额和可抵免税额
- ✅ 支持多账户合并
- ✅ **投资表现分析**：计算总收益率、年化收益率、最大回撤、已实现 ROI

### 🆕 止损管理功能

- ✅ **移动止损策略**：止损价随股价上涨自动上移，保护已实现利润
- ✅ **手动触发检查**：按需检查持仓，无需常驻后台
- ✅ **邮件通知**：触发止损时自动发送邮件提醒
- ✅ **灵活配置**：每个股票可设置不同的止损百分比
- ✅ **持久化存储**：止损配置自动保存，重启后仍然有效

📖 **详细使用指南**: [止损管理功能使用文档](docs/STOP_LOSS_GUIDE.md)

## 快速开始

### 1. 安装

```bash
# 克隆或下载项目
cd ibkr-toolkit

# 使用 uv 安装（推荐）
uv pip install -e .

# 或使用传统 pip
pip install -e .
```

### 2. 配置

复制配置文件模板：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的 IBKR 凭证：

```bash
IBKR_FLEX_TOKEN=你的token
IBKR_QUERY_ID=你的query_id
USD_CNY_RATE=7.2
USE_DYNAMIC_EXCHANGE_RATES=true
OUTPUT_DIR=./data/output
```

配置参数说明：

- `IBKR_FLEX_TOKEN`: IBKR Flex Query Token（必填）
- `IBKR_QUERY_ID`: IBKR Flex Query ID（必填）
- `USD_CNY_RATE`: 固定汇率，作为 API 失败时的备用汇率（默认 7.2）
- `USE_DYNAMIC_EXCHANGE_RATES`: 是否使用动态汇率（默认 true）
- `OUTPUT_DIR`: 输出目录（默认 ./data/output）
- `FIRST_TRADE_YEAR`: 首次交易年份（可选，用于 `--all` 参数）

### 3. 运行

```bash
# 使用默认日期范围（Flex Query 中配置的日期）
uv run ibkr-toolkit

# 指定单个税务年度（推荐，适用于中国税务申报）
uv run ibkr-toolkit --year 2025

# 获取当前年度数据
uv run ibkr-toolkit --year $(date +%Y)

# 查询从指定年份到当前的所有数据（自动分年查询）
uv run ibkr-toolkit --from-year 2020

# 查询从开始交易到现在的所有数据（需配置 FIRST_TRADE_YEAR）
uv run ibkr-toolkit --all

# 查看所有可用选项
uv run ibkr-toolkit --help
```

**日期参数说明**：

- `--year` / `-y`：指定单个税务年度，查询该年 1月1日 至 12月31日 的数据
- `--from-year`：指定起始年份，自动分年查询从该年到当前年份的所有数据
- `--all`：查询从 `FIRST_TRADE_YEAR`（.env 配置）到当前年份的所有数据
- 不指定任何参数：使用 Flex Query 中预设的日期范围
- 这些参数互斥，只能使用其中一个

**多年查询特性**：

- 使用 `--from-year` 或 `--all` 时，工具会自动按年分段查询
- 每年查询一次（1/1 - 12/31），自动合并所有数据
- 某一年查询失败不会中断，会继续查询其他年份
- 避免 IBKR API 365 天的单次查询限制

## IBKR Flex Query 配置

要使用此工具，你需要在 IBKR 客户端门户创建一个 Flex Query。

### 步骤 1：登录 IBKR 客户端门户

访问 [IBKR Client Portal](https://www.interactivebrokers.com/portal) 并登录。

### 步骤 2：创建 Flex Query

1. 进入 **Reports** → **Flex Queries**
2. 点击 **Create** 创建新查询
3. 选择 **Activity Flex Query**

### 步骤 3：配置查询参数

#### 必需的数据类型

确保包含以下数据类型：

1. **Trades** (交易记录)
   - 包含字段：Symbol, Date/Time, Quantity, Price, Proceeds, Commission, Realized P/L, Currency

2. **Cash Transactions** (现金交易)
   - 包含字段：Symbol, Date/Time, Amount, Type, Currency
   - 用于获取股息数据

3. **Withholding Tax** (预扣税)
   - 包含字段：Date, Amount, Currency
   - 用于计算外国税额抵免

#### 投资表现分析所需数据类型（可选）

如需使用投资表现分析功能，需要额外添加以下数据类型：

4. **Open Positions** (持仓数据)
   - 包含字段：Symbol, Quantity, Mark Price, Position Value, Cost Basis, FX P&L, Currency, Asset Category
   - 用于计算期末净值、未实现盈亏等

5. **Cash Report** (现金报告)
   - 选择 Base Currency Summary
   - 包含字段：Starting Cash, Ending Cash, Deposits, Withdrawals, Deposit/Withdrawals
   - 用于计算期初期末净值、净存入额等

#### 日期范围设置

根据你需要分析的时间段设置：

- **From**: 开始日期（如 2025-01-01）
- **To**: 结束日期（如 2025-12-31）

**注意**：工具支持通过命令行参数 `--year` 覆盖这里设置的日期范围。建议在 Flex Query 中设置一个较长的默认日期范围（如最近一年），然后在命令行中根据需要指定具体年份。

#### 其他设置

- **Format**: XML
- **Include Header/Trailer**: Yes
- **Include Audit Trail**: No（可选）

### 步骤 4：保存并获取凭证

1. 保存查询后，系统会分配一个 **Query ID**
2. 在 Flex Query 页面点击 **Generate Token** 生成 **Token**
3. 将 `Query ID` 和 `Token` 填入 `.env` 文件

### 步骤 5：测试配置

运行工具验证配置是否正确：

```bash
uv run ibkr-toolkit
```

如果配置正确，工具将自动获取数据并生成报表。

## 汇率计算机制

本工具支持两种汇率计算模式：动态汇率和固定汇率。

### 动态汇率（推荐）

**配置方式**：

```bash
USE_DYNAMIC_EXCHANGE_RATES=true
```

**工作原理**：

1. 为每笔交易获取**当日的实际汇率**（不是月平均汇率）
2. 优先从本地缓存读取（`data/cache/exchange_rates_cache.json`）
3. 缓存未命中时，按以下顺序调用 API：
   - **exchangerate-api.com**（1500次/月免费额度）
   - **Frankfurter API**（无限制，但数据仅到前一天）
4. API 失败时使用 `USD_CNY_RATE` 作为备用汇率
5. 成功获取的汇率会自动缓存供后续使用

**优势**：

- 精确的税务计算，每笔交易使用当日汇率
- 符合税务申报要求
- 缓存机制提高性能，减少 API 调用

**示例**：

```
2025-01-05: 买入股票 $1000 → 使用 1月5日汇率 7.2456 = ¥7,245.60
2025-01-15: 卖出股票 $1200 → 使用 1月15日汇率 7.2512 = ¥8,701.44
2025-01-20: 收到股息 $50   → 使用 1月20日汇率 7.2489 = ¥362.45
```

### 固定汇率

**配置方式**：

```bash
USE_DYNAMIC_EXCHANGE_RATES=false
USD_CNY_RATE=7.2
```

**工作原理**：

- 所有美元金额统一使用 `USD_CNY_RATE` 转换为人民币
- 简化计算，不调用任何外部 API
- 适合网络不稳定或小额交易场景

**示例**：

```
所有交易使用固定汇率 7.2
$1000 → ¥7,200.00
$1200 → ¥8,640.00
$50   → ¥360.00
```

### 汇率应用场景

工具在以下三个场景应用汇率转换：

1. **交易盈亏转换**
   - 已实现盈亏（Realized P/L）USD → CNY
   - 佣金（Commission）USD → CNY

2. **股息转换**
   - 股息金额（Dividend Amount）USD → CNY

3. **预扣税转换**
   - 预扣税金额（Withholding Tax）USD → CNY

所有转换后的人民币金额将用于税务计算。

### 缓存管理

**缓存位置**：`data/cache/exchange_rates_cache.json`

**缓存结构**：

```json
{
  "2025-01-15": 7.2456,
  "2025-01-16": 7.2512,
  "2025-01-AVG": 7.2484
}
```

**建议**：

- 每个税务年度初清理缓存，避免使用过期数据
- 可以手动编辑缓存文件添加已知的汇率

## 税率计算逻辑

本工具按照中国个人所得税法，自动计算境外所得应纳税额。

### 固定税率：20%

根据中国税法，境外投资收益（包括交易盈亏和股息）适用 **20% 的固定税率**。

代码定义位置：`src/ibkr_tax/constants.py:20`

```python
CHINA_DIVIDEND_TAX_RATE = 0.20  # 20% tax rate
```

### 三个关键计算公式

#### 公式 1：应纳税额

```
应纳税额 = 应税所得 × 20%
```

**应税所得构成**：

```
应税所得 = 交易净利润（人民币）+ 股息收入（人民币）
```

其中：

- **交易净利润** = 已实现损益 - 手续费（均按人民币计算）
- **股息收入** = 所有美元股息按汇率转换后的人民币金额

#### 公式 2：外国税额抵免

```
可抵免税额 = min(境外实际预扣税, 股息收入 × 20%)
```

这个公式确保：

- 不超额抵免（取较小值）
- 最多抵免到中国税率对应的税额
- 符合中国税法关于境外所得税收抵免的规定

#### 公式 3：实际应补税额

```
应补税额 = 应纳税额 - 外国税额抵免
```

这是最终需要向中国税务机关缴纳的税额。

### 计算示例

假设 2025 年有以下数据（已转换为人民币）：

**输入数据**：

- 交易盈亏：¥10,000
- 佣金：¥200
- 股息收入：¥3,000
- 境外预扣税：¥450

**计算过程**：

```
1. 交易净利润 = 10,000 - 200 = ¥9,800
2. 应税所得 = 9,800 + 3,000 = ¥12,800
3. 应纳税额 = 12,800 × 0.2 = ¥2,560
4. 可抵免税额 = min(450, 3,000 × 0.2) = min(450, 600) = ¥450
5. 应补税额 = 2,560 - 450 = ¥2,110
```

**最终结果**：需要补缴税款 ¥2,110

### 特殊情况处理

**亏损情况**：

- 如果交易产生亏损（负的盈亏），会直接体现在应税所得中
- 交易亏损可以抵减股息收入
- 示例：交易亏损 ¥5,000 + 股息 ¥3,000 = 应税所得 -¥2,000（可能无需缴税）

**无股息情况**：

- 如果没有股息收入，外国税额抵免为 0
- 仅对交易净利润征税

**无交易盈亏情况**：

- 如果只有股息收入，应税所得 = 股息收入
- 可以抵免境外预扣的股息税

### 代码实现位置

核心税务计算函数：`src/ibkr_tax/parsers/data_parser.py:321-342`

## 输出文件说明

工具会在 `data/output/` 目录生成以下文件（文件名包含时间戳）：

### 1. Excel 报表

**文件名格式**：`ibkr_report_YYYYMMDD_HHMMSS.xlsx`

包含 7 个工作表：

#### Sheet 1: Trades（交易明细）

- DateTime: 交易日期时间
- Symbol: 股票代码
- Description: 证券名称
- Quantity: 数量
- Price: 价格
- Amount: 交易金额
- Cost: 成本
- Commission: 佣金
- Realized P&L: 已实现盈亏
- Buy Sell: 买入/卖出
- Currency: 货币
- Asset Category: 资产类别
- Open DateTime: 开仓时间
- Account: 账户

#### Sheet 2: Dividends（股息明细）

- Date: 发放日期
- Symbol: 股票代码
- Description: 证券名称
- Amount: 股息金额
- Currency: 货币
- Type: 类型
- Account: 账户

#### Sheet 3: Withholding Tax（预扣税明细）

- Date: 日期
- Symbol: 股票代码
- Description: 证券名称
- Amount: 预扣税金额
- Currency: 货币
- Type: 类型
- Account: 账户

#### Sheet 4: Deposits & Withdrawals（存取款明细）

- Date: 日期
- Time: 时间
- Description: 描述
- Amount: 金额
- Currency: 货币
- FX Rate To Base: 汇率
- Amount Base Currency: 基础货币金额
- Transaction Type: 交易类型
- Account: 账户

#### Sheet 5: Summary（汇总数据）

- Trade_Summary: 交易汇总
  - Total_Trades: 总交易笔数
  - Realized_P&L_USD: 美元盈亏
  - Realized_P&L_CNY: 人民币盈亏
  - Total_Commission_USD: 美元佣金
  - Total_Commission_CNY: 人民币佣金
  - Net_P&L_CNY: 净盈亏（人民币）
  - Average_Exchange_Rate: 平均汇率

- Dividend_Summary: 股息汇总
  - Total_Dividends: 股息笔数
  - Total_Amount_USD: 美元总额
  - Total_Amount_CNY: 人民币总额
  - Average_Exchange_Rate: 平均汇率

- Tax_Summary: 预扣税汇总
  - Total_Withholding_Tax_USD: 美元预扣税
  - Total_Withholding_Tax_CNY: 人民币预扣税
  - Average_Exchange_Rate: 平均汇率

- China_Tax_Calculation: 中国税务计算
  - Taxable_Income_CNY: 应税所得（人民币）
  - Tax_Due_20pct_CNY: 应纳税额（20%）
  - Foreign_Tax_Credit_CNY: 可抵免税额
  - Tax_Payable_CNY: 应补税额

- Account_Summary: 账户汇总（如有存取款）
  - Total_Deposits_Count: 存款笔数
  - Total_Withdrawals_Count: 取款笔数
  - Total_Deposits_Base_Currency: 存款总额
  - Total_Withdrawals_Base_Currency: 取款总额
  - Net_Deposits_Base_Currency: 净存入额

#### Sheet 6: Open Positions（持仓明细）

- Symbol: 股票代码
- Description: 证券名称
- Quantity: 持仓数量
- Mark Price: 市场价格
- Position Value: 持仓市值
- Cost Basis: 成本基础
- Unrealized P&L: 未实现盈亏
- Currency: 货币
- Asset Category: 资产类别
- Account: 账户

#### Sheet 7: Performance（投资表现）

包含以下指标：

**Performance_Summary（投资表现汇总）**：

- Beginning_Net_Worth_USD/CNY: 期初净值（美元/人民币）
- Ending_Net_Worth_USD/CNY: 期末净值（美元/人民币）
- Net_Deposits_USD/CNY: 净存入额（美元/人民币）
- Total_Return_Percent: 总收益率（%）
- Annualized_Return_Percent: 年化收益率（%）
- Max_Drawdown_Percent: 最大回撤（%）
- Realized_ROI_Percent: 已实现投资回报率（%）
- Investment_Period_Days: 投资天数
- Avg_Exchange_Rate: 平均汇率

**Position_Details（持仓详情）**（如有持仓）：

- Total_Positions: 持仓数量
- Total_Position_Value_USD/CNY: 持仓总市值（美元/人民币）
- Total_Cost_Basis_USD: 总成本基础
- Total_Unrealized_P&L_USD/CNY: 总未实现盈亏（美元/人民币）

**投资表现指标说明**：

- **总收益率**：`(期末净值 - 期初净值 - 净存入) / 期初净值 × 100%`
  - 衡量投资的整体增长情况，已剔除存取款影响

- **年化收益率**：`(1 + 总收益率)^(365/投资天数) - 1`
  - 将总收益率转换为年度百分比，便于比较不同投资期的表现

- **最大回撤**：`(峰值 - 谷底) / 峰值 × 100%`
  - 衡量投资期间从最高点到最低点的最大损失幅度

- **已实现 ROI**：`已实现盈亏 / 投资成本 × 100%`
  - 仅基于已平仓交易计算的回报率，不包括未实现盈亏

### 2. 原始数据

**文件名格式**：`raw_data_YYYYMMDD_HHMMSS.json`

从 IBKR Flex Query API 获取的原始 JSON 数据，用于调试和审计。

### 3. 汇总数据

**文件名格式**：`summary_YYYYMMDD_HHMMSS.json`

包含所有汇总统计数据的 JSON 格式文件，便于其他工具或脚本读取。

## 开发指南

### 项目结构

```
ibkr-toolkit/
├── src/ibkr_tax/
│   ├── api/              # IBKR API 客户端
│   ├── parsers/          # 数据解析器
│   ├── services/         # 汇率服务等
│   ├── utils/            # 工具函数
│   ├── cli.py            # 命令行入口
│   ├── config.py         # 配置管理
│   └── constants.py      # 常量定义
├── tests/                # 测试文件
├── data/
│   ├── cache/            # 汇率缓存
│   └── output/           # 输出文件
├── pyproject.toml        # 项目配置
└── README.md
```

### 运行测试

```bash
# 运行所有测试
uv run pytest

# 运行特定测试
uv run pytest tests/test_data_parser.py

# 查看测试覆盖率
uv run pytest --cov=ibkr_tax
```

### 代码格式化

```bash
# 格式化代码
ruff format src tests

# 检查格式
ruff format --check src tests
```

### 代码检查

```bash
# 运行 linter
ruff check src tests

# 自动修复可修复的问题
ruff check --fix src tests
```

### Pre-commit Hooks

项目配置了 pre-commit hooks 来自动检查代码质量和敏感信息：

```bash
# 安装 pre-commit hooks
uv run pre-commit install

# 手动运行所有 hooks
uv run pre-commit run --all-files

# 跳过 hooks 提交（不推荐）
git commit --no-verify
```

**配置的检查项**：

- ✅ 代码格式化（ruff）
- ✅ Markdown/YAML/JSON 格式化（prettier）
- ✅ 检测私钥泄露
- ✅ 防止提交 .env 文件
- ✅ 防止提交输出文件（包含财务数据）
- ✅ 防止提交大文件（>500KB）
- ✅ 检查合并冲突标记
- ✅ 修复行尾空格和文件末尾换行

### 添加依赖

```bash
# 使用 uv 添加依赖
uv add package-name

# 添加开发依赖
uv add --dev package-name
```

## 常见问题

### Q1: 为什么推荐使用动态汇率？

**A**: 动态汇率为每笔交易使用当日实际汇率，更符合税务申报要求，计算结果更准确。特别是在汇率波动较大的情况下，差异会更明显。

### Q2: API 调用次数有限制吗？

**A**: exchangerate-api.com 有 1500 次/月的免费额度。如果超过，工具会自动切换到 Frankfurter API（无限制）。本地缓存机制可以大幅减少 API 调用次数。

### Q3: 如何处理多个账户？

**A**: 在 IBKR Flex Query 中配置多个账户，工具会自动合并所有账户的数据并在输出中标注账户信息。

### Q4: 汇率缓存文件可以手动编辑吗？

**A**: 可以。缓存文件是标准 JSON 格式，你可以手动添加或修改汇率数据。格式为 `{"YYYY-MM-DD": 汇率值}`。

### Q5: 计算结果中的"平均汇率"是什么？

**A**: 这是所有交易使用的汇率的算术平均值，仅用于统计展示，不是用来计算金额的月平均汇率。每笔交易仍然使用其当日汇率。

### Q6: 支持哪些货币？

**A**: 目前主要支持 USD 交易，自动转换为 CNY。其他货币的支持计划中。

### Q7: 如何验证计算结果的准确性？

**A**:

1. 检查 Excel 中每笔交易的汇率和人民币金额
2. 对比原始数据文件（raw*data*\*.json）
3. 使用 Summary sheet 中的数据与自己的记录核对

### Q8: 遇到 API 错误怎么办？

**A**:

1. 检查 `.env` 中的 `IBKR_FLEX_TOKEN` 和 `IBKR_QUERY_ID` 是否正确
2. 确认 IBKR Flex Query 已正确配置并包含必需的数据类型
3. 检查网络连接
4. 查看 IBKR Client Portal 中 Flex Query 的状态

### Q9: 如何查询特定年份的数据？

**A**: 使用 `--year` 参数指定税务年度：

```bash
# 查询 2025 年数据
uv run ibkr-toolkit --year 2025

# 查询 2024 年数据
uv run ibkr-toolkit --year 2024
```

工具会自动查询该年度 1月1日 至 12月31日 的所有交易记录，无需修改 Flex Query 配置。

### Q10: Flex Query 中配置的日期会被覆盖吗？

**A**: 是的。当使用 `--year`、`--from-year` 或 `--all` 参数时，命令行指定的日期范围会覆盖 Flex Query 中预设的日期。建议：

- 在 Flex Query 中设置一个默认日期范围（如最近一年）
- 在实际使用时通过命令行参数指定具体年份
- 这样可以灵活查询不同年份的数据而无需修改 Flex Query 配置

### Q11: 如何查询从开始到现在的所有交易数据？

**A**: 有两种方法：

方法 1：使用 `--from-year` 参数

```bash
# 从 2020 年查询到现在
uv run ibkr-toolkit --from-year 2020
```

方法 2：使用 `--all` 参数（推荐）

```bash
# 1. 在 .env 文件中设置首次交易年份
echo "FIRST_TRADE_YEAR=2020" >> .env

# 2. 运行工具
uv run ibkr-toolkit --all
```

工具会自动按年查询（2020, 2021, 2022...直到当前年份），然后合并所有数据。

### Q12: 多年查询会不会很慢？

**A**: 会比单年查询慢，但工具已做优化：

- 按年分段查询，每年独立请求（避免 IBKR 365 天限制）
- 某一年失败不影响其他年份
- 显示实时进度，可以看到当前查询状态
- 示例：查询 5 年数据大约需要 1-2 分钟

### Q13: 多年数据的汇率如何计算？

**A**: 与单年查询完全相同：

- 动态汇率模式：每笔交易使用其交易日的实际汇率
- 固定汇率模式：所有交易使用配置的固定汇率
- 汇率缓存跨年共享，减少 API 调用

## 中国税务申报参考

### 官方资源

**国家税务总局**

- [官方网站](https://www.chinatax.gov.cn/)
- [个人所得税专题](https://www.chinatax.gov.cn/chinatax/n810341/n810760/index.html)

**个人所得税 APP**

- [APP 下载页面](https://etax.chinatax.gov.cn/download.html)
- 用途：境外所得年度自行申报

**相关政策文件**

- [《中华人民共和国个人所得税法》](https://jdjc.mof.gov.cn/fgzd/202201/t20220118_3783067.htm)
- [《关于境外所得有关个人所得税政策的公告》（财政部 税务总局公告 2020年第3号）](https://www.gov.cn/zhengce/zhengceku/2020-01/22/content_5471604.htm)

### 申报要点

1. **申报时间**：次年 3月1日 至 6月30日
2. **申报方式**：
   - 个人所得税 APP（推荐）
   - 自然人电子税务局网页版
   - 办税服务厅现场办理

3. **所需资料**：
   - 境外所得证明（本工具生成的 Excel 报表）
   - 境外纳税凭证（IBKR 税务文件，获取方法见下文）
   - 身份证件

4. **税收抵免**：
   - 境外已缴税款可抵免
   - 抵免限额 = 境外所得 × 中国税率（20%）

### 注意事项

- 本工具计算结果仅供参考，不构成税务建议
- 实际申报时请以税务机关要求为准
- 建议咨询专业税务顾问确认申报细节
- 保存好所有交易凭证和纳税证明以备核查

### 如何获取 IBKR 税务文件

IBKR 每年会为账户持有人生成税务文件，用于证明境外已缴纳的税款。

**获取步骤**：

1. 登录 [IBKR 客户端门户](https://www.interactivebrokers.com/portal)
2. 点击 **Performance & Reports** → **Tax Documents**
   - 或通过 **Menu** → **Reporting** → **Tax Documents**
3. 选择所需年份，下载税务文件

**常见税务文件类型**：

- **Form 1042-S**：非美国居民的美国来源收入预扣税证明（含股息税）
- **年度报表**：完整的交易和收入记录
- **股息报告**：股息收入明细

**文件可用时间**：

- 年度报表：次年 2月1日 起
- 股息报告：次年 2月15日 起
- Form 1042-S：次年 3月15日 起

**参考链接**：

- [IBKR 税务文件指南（英文）](https://www.ibkrguides.com/clientportal/performanceandstatements/taxreporting.htm)
- [IBKR 税务信息概览（中文）](https://www.interactivebrokers.com/cn/support/tax-overview.php)

## 许可证

MIT License

## 免责声明

本工具仅供个人学习和税务申报参考使用。不保证数据的绝对准确性，税务申报请咨询专业税务顾问。

## 贡献

欢迎提交 Issue 和 Pull Request！

## 联系方式

如有问题或建议，请在 GitHub 上提交 Issue。
