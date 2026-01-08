# AGENTS.md

This file provides guidance to Qoder (qoder.com) when working with code in this repository.

## Commands

### Development

```bash
# Run the tool (uses default date range from Flex Query)
uv run ibkr-tax

# Run with specific year (recommended for tax reporting)
uv run ibkr-tax --year 2025

# Run from a starting year to current year
uv run ibkr-tax --from-year 2020

# Run all data from FIRST_TRADE_YEAR (in .env) to current
uv run ibkr-tax --all
```

### Testing

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_data_parser.py

# Run tests with coverage report
uv run pytest --cov=ibkr_tax --cov-report=term-missing
```

### Code Quality

```bash
# Format code
ruff format src tests

# Lint and auto-fix
ruff check --fix src tests

# Lint without fixing
ruff check src tests
```

### Pre-commit

```bash
# Install pre-commit hooks
uv run pre-commit install

# Run manually on all files
uv run pre-commit run --all-files
```

## Architecture

### Core Components

**CLI Entry (`cli.py`):**

- Command-line interface with argument parsing for date ranges (`--year`, `--from-year`, `--all`)
- Multi-year query orchestration: automatically splits multi-year requests into per-year queries
- Account data aggregation: handles both single and multiple IBKR accounts
- Excel/JSON export with multi-sheet structure (Trades, Dividends, Withholding_Tax, Summary)

**API Client (`api/flex_query.py`):**

- IBKR Flex Query API integration with retry mechanism
- Date override capability: `fd` (from date) and `td` (to date) parameters override Flex Query defaults
- Returns dict for single account or list for multiple accounts
- XML to dict conversion using xmltodict

**Data Parser (`parsers/data_parser.py`):**

- Parses trades, dividends, and withholding tax from IBKR data
- Tax calculation logic (20% fixed rate defined in `constants.py:20`)
- Formulas:
  - Taxable Income = Net Trading PnL + Dividends
  - Tax Due = Taxable Income × 20%
  - Foreign Tax Credit = min(Foreign Tax Withheld, Dividends × 20%)
  - Tax Payable = Tax Due - Foreign Tax Credit

**Exchange Rate Service (`services/exchange_rate.py`):**

- Dynamic mode: fetches daily rates from API with local JSON cache
- Fixed mode: uses configured rate from .env
- API fallback chain: exchangerate-api.com → Frankfurter API → default rate

### Data Flow

1. CLI parses arguments and determines date range(s)
2. For multi-year queries, CLI loops through years calling API client per year
3. API client requests report from IBKR and polls until ready
4. Parser extracts trades/dividends/taxes and applies exchange rates
5. Summary calculator computes tax obligations
6. Exporter creates Excel with 4 sheets and JSON files

### Configuration

All config managed via `.env` file and loaded through `config.py`:

- `IBKR_FLEX_TOKEN`, `IBKR_QUERY_ID`: API credentials (required)
- `USD_CNY_RATE`: fallback rate (default 7.2)
- `USE_DYNAMIC_EXCHANGE_RATES`: dynamic vs fixed (default true)
- `FIRST_TRADE_YEAR`: for `--all` parameter
- `OUTPUT_DIR`: output location (default ./data/output)

### Important Constraints

- IBKR API limit: 365 days per query (enforced by IBKR, not this tool)
- Multi-year queries split into yearly chunks to respect this limit
- Trading loss can offset dividend income in tax calculation
- Exchange rates are daily rates, not monthly averages
- Only realized PnL included (closed positions only)

## Special Notes

- Tax rate is 20% fixed (China dividend tax rate) defined in `constants.py:20`
- Pre-commit hooks prevent committing .env files, output files (contains financial data), and cache files
- Code must use English; user-facing logs/docs use Chinese
- When making tax calculation changes, update both parser logic and README documentation
