"""
Application-wide constants.

All magic numbers and configuration constants are defined here with clear documentation
about which modules use them and what changing them affects.

Philosophy: Every constant should be documented with:
1. What it controls
2. Which modules/functions call it
3. What happens when you change it
"""

# ==============================================================================
# PRICING PRECISION
# ==============================================================================

# Called by: response_handlers.py, calculate_option_price.py, aggregate_strategy_price.py
# Effect: Controls decimal places in all price displays ($12.34 vs $12.3456)
# Higher value = more precision but less readable. 2 is industry standard for USD.
PRICE_DECIMAL_PLACES = 2


# ==============================================================================
# MONEYNESS CLASSIFICATION
# ==============================================================================

# Called by: utils/moneyness.py (classify_moneyness function)
# Effect: Threshold for classifying option as "at-the-money"
# If |spot - strike| / strike < AT_THE_MONEY_THRESHOLD, option is considered ATM
# Example: Strike $100, spot $101.50 -> 1.5% difference -> ATM
# Lower value = stricter ATM classification, more options classified as ITM/OTM
AT_THE_MONEY_THRESHOLD = 0.02  # 2% threshold


# ==============================================================================
# HISTORICAL DATA & CHARTING
# ==============================================================================

# Called by: graph_nodes/classify_intent.py (_display_chart_if_ticker function)
# Effect: Number of trading days to show in price history charts
# 252 = ~1 year of trading days (52 weeks * 5 days/week)
# Higher value = longer history but slower chart generation
CHART_LOOKBACK_DAYS = 252

# Called by: market_data/sql_data_provider.py, langchain_tools/volatility_tool.py
# Effect: Days of historical data to fetch when ticker not in database
# 730 = ~2 years (730 days, not trading days)
# Higher value = better volatility estimation but slower initial fetch
DATABASE_HISTORICAL_LOOKBACK_DAYS = 730


# ==============================================================================
# TICKER VALIDATION
# ==============================================================================

# Called by: utils/ticker_validation.py (validate_ticker function)
# Effect: Timeout for yfinance API calls to prevent hanging
# Lower value = faster failures but may miss slow responses
# Higher value = more reliability but worse UX for invalid tickers
TICKER_VALIDATION_TIMEOUT_SECONDS = 5

# Called by: utils/ticker_validation.py (LRU cache decorator)
# Effect: Maximum number of ticker validations to cache in memory
# Higher value = less API calls but more memory usage
# 1000 tickers ~= 50KB memory (negligible)
TICKER_VALIDATION_CACHE_SIZE = 1000

# Called by: utils/charting.py (create_price_chart function)
# Effect: Timeout for yfinance data download when creating charts
# Lower value = faster failures but may miss slow responses
CHART_DATA_DOWNLOAD_TIMEOUT_SECONDS = 10


# ==============================================================================
# FALLBACK VALUES (Last Resort)
# ==============================================================================

# Called by: graph_nodes/execute_parallel_tasks.py (volatility estimation failure)
# Effect: Default volatility when SQL database AND yfinance both fail
# This is a reasonable middle-ground volatility for equities
# IMPORTANT: Only used as last resort fallback, not for actual pricing
DEFAULT_VOLATILITY_FALLBACK = 0.25  # 25% annualized

# Called by: graph_nodes/execute_parallel_tasks.py (rate estimation failure)
# Effect: Default risk-free rate when config AND estimation both fail
# 5% is approximate current 1-year treasury rate
# IMPORTANT: Only used as last resort fallback
DEFAULT_RISK_FREE_RATE_FALLBACK = 0.05  # 5% annual


# ==============================================================================
# MOCK DATA (Development/Testing Only)
# ==============================================================================

# Called by: langchain_tools/volatility_tool.py (fallback when database empty)
# Effect: Provides realistic volatility estimates for testing
# IMPORTANT: These are approximations for development only
# Production should always use SQL database with historical calculations
MOCK_VOLATILITIES = {
    "AAPL": 0.25,   # Apple - moderate tech volatility
    "TSLA": 0.45,   # Tesla - high volatility growth stock
    "SPY": 0.18,    # S&P 500 ETF - low volatility broad market
    "GOOGL": 0.30,  # Google - tech with moderate volatility
    "MSFT": 0.22,   # Microsoft - stable large cap
    "AMZN": 0.35    # Amazon - higher volatility e-commerce
}


# ==============================================================================
# VALIDATION & ERROR HANDLING
# ==============================================================================

# Called by: graph_state_schema.py (BaseAgentState default)
# Effect: Maximum number of times to retry validation before giving up
# Higher value = more attempts to fix issues but slower failures
# 2 attempts allows: initial validation + 1 retry
MAX_VALIDATION_RETRIES = 2


