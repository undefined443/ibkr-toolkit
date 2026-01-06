# IBKR Tax Tool

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

- ✅ 自动从 IBKR 获取交易记录
- ✅ 解析交易、股息、预扣税数据
- ✅ 自动获取实时汇率或使用固定汇率
- ✅ 生成 Excel 报表和 JSON 数据
- ✅ 自动计算应纳税额和可抵免税额
- ✅ 支持多账户合并

## 快速开始

### 1. 安装

```bash
# 克隆或下载项目
cd ibkr-tax

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
uv run ibkr-tax

# 指定单个税务年度（推荐，适用于中国税务申报）
uv run ibkr-tax --year 2025

# 获取当前年度数据
uv run ibkr-tax --year $(date +%Y)

# 查询从指定年份到当前的所有数据（自动分年查询）
uv run ibkr-tax --from-year 2020

# 查询从开始交易到现在的所有数据（需配置 FIRST_TRADE_YEAR）
uv run ibkr-tax --all

# 查看所有可用选项
uv run ibkr-tax --help
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
uv run ibkr-tax
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

包含 4 个工作表：

#### Sheet 1: Trades（交易明细）
- Symbol: 股票代码
- Date: 交易日期
- Quantity: 数量
- Price: 价格
- Proceeds: 交易金额
- Commission: 佣金
- Realized_PnL: 已实现盈亏
- Currency: 货币
- Exchange_Rate: 汇率（动态汇率模式）
- Realized_PnL_CNY: 人民币盈亏
- Commission_CNY: 人民币佣金

#### Sheet 2: Dividends（股息明细）
- Symbol: 股票代码
- Date: 发放日期
- Amount: 股息金额
- Currency: 货币
- Exchange_Rate: 汇率（动态汇率模式）
- Amount_CNY: 人民币金额

#### Sheet 3: Withholding_Tax（预扣税明细）
- Date: 日期
- Amount: 预扣税金额
- Currency: 货币
- Exchange_Rate: 汇率（动态汇率模式）
- Amount_CNY: 人民币金额

#### Sheet 4: Summary（汇总数据）
- Trade_Summary: 交易汇总
  - Total_Trades: 总交易笔数
  - Realized_PnL_USD: 美元盈亏
  - Realized_PnL_CNY: 人民币盈亏
  - Total_Commission_USD: 美元佣金
  - Total_Commission_CNY: 人民币佣金
  - Net_PnL_CNY: 净盈亏（人民币）
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

### 2. 原始数据

**文件名格式**：`raw_data_YYYYMMDD_HHMMSS.json`

从 IBKR Flex Query API 获取的原始 JSON 数据，用于调试和审计。

### 3. 汇总数据

**文件名格式**：`summary_YYYYMMDD_HHMMSS.json`

包含所有汇总统计数据的 JSON 格式文件，便于其他工具或脚本读取。

## 开发指南

### 项目结构

```
ibkr-tax/
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
2. 对比原始数据文件（raw_data_*.json）
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
uv run ibkr-tax --year 2025

# 查询 2024 年数据
uv run ibkr-tax --year 2024
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
uv run ibkr-tax --from-year 2020
```

方法 2：使用 `--all` 参数（推荐）
```bash
# 1. 在 .env 文件中设置首次交易年份
echo "FIRST_TRADE_YEAR=2020" >> .env

# 2. 运行工具
uv run ibkr-tax --all
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

## 许可证

MIT License

## 免责声明

本工具仅供个人学习和税务申报参考使用。不保证数据的绝对准确性，税务申报请咨询专业税务顾问。

## 贡献

欢迎提交 Issue 和 Pull Request！

## 联系方式

如有问题或建议，请在 GitHub 上提交 Issue。
