"""
Constants and configuration defaults for IBKR Tax Tool
"""

# API Configuration
IBKR_FLEX_API_URL = (
    "https://gdcdyn.interactivebrokers.com/Universal/servlet/FlexStatementService.SendRequest"
)
IBKR_FLEX_STATEMENT_URL = (
    "https://gdcdyn.interactivebrokers.com/Universal/servlet/FlexStatementService.GetStatement"
)

# Exchange Rate Configuration
DEFAULT_USD_CNY_RATE = 7.2
EXCHANGE_RATE_API_URL = "https://api.exchangerate-api.com/v4/latest/USD"
EXCHANGE_RATE_CACHE_FILE = "data/cache/exchange_rates_cache.json"
EXCHANGE_RATE_CACHE_DAYS = 1

# Tax Configuration
CHINA_DIVIDEND_TAX_RATE = 0.20  # 20% tax rate for dividends in China

# Output Configuration
DEFAULT_OUTPUT_DIR = "./data/output"
DEFAULT_CACHE_DIR = "./data/cache"

# File Naming
EXCEL_REPORT_PREFIX = "ibkr_report"
JSON_SUMMARY_PREFIX = "summary"
RAW_DATA_PREFIX = "raw_data"
TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"

# Logging Configuration
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_LOG_LEVEL = "INFO"

# API Retry Configuration
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
RETRY_BACKOFF = 2  # exponential backoff multiplier
