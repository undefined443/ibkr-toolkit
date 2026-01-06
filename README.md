# IBKR Tax Tool

自动获取 Interactive Brokers (IBKR) 交易数据并生成中国税务申报报表的工具。

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
cd ibkr

# 安装项目（开发模式）
pip install -e .

# 或使用 uv（推荐）
uv pip install -e .
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
```

### 3. 运行

```bash
# 使用命令行工具
ibkr-tax

# 或直接运行模块
python -m ibkr_tax.cli
```

## 详细文档

- [设置指南](docs/SETUP_GUIDE.md) - 如何在 IBKR 中配置 Flex Query
- [项目结构](docs/PROJECT_STRUCTURE.md) - 代码组织说明

## 输出文件

脚本会在 `data/output/` 目录生成：

1. **Excel 报表** - `ibkr_report_YYYYMMDD_HHMMSS.xlsx`

   - Trades: 交易明细
   - Dividends: 股息明细
   - Withholding_Tax: 预扣税明细
   - Summary: 汇总数据

1. **原始数据** - `raw_data_YYYYMMDD_HHMMSS.json`

1. **汇总数据** - `summary_YYYYMMDD_HHMMSS.json`

## 税务计算

自动计算：

- 交易盈亏（美元和人民币）
- 股息收入
- 境外预扣税
- 应纳税所得额
- 应纳税额（20%）
- 可抵免税额
- 应补税额

## 开发

### 运行测试

```bash
pytest
```

### 代码格式化

```bash
ruff format src tests
```

### 代码检查

```bash
ruff check src tests
```

## 许可证

MIT License

## 免责声明

本工具仅供个人学习和税务申报使用。不保证数据的绝对准确性，税务申报请咨询专业税务顾问。
