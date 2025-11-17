"""
SQLite data provider for market data (backward compatibility wrapper).

This module re-exports components for backward compatibility.
The actual implementation has been refactored into:
- data/market_data/data_provider_protocol.py: MarketDataProvider protocol
- data/market_data/database_schema.py: Schema initialization
- data/market_data/ticker_fetcher.py: Ticker data fetching
- data/market_data/price_provider.py: Price and volatility calculations
"""

from derivatives_gpt_core.data.market_data.data_provider_protocol import MarketDataProvider
from derivatives_gpt_core.data.market_data.price_provider import (
    SQLPriceProvider as SQLDataProvider,
    create_price_provider as create_sql_provider
)

# Re-export for backward compatibility
__all__ = ['MarketDataProvider', 'SQLDataProvider', 'create_sql_provider']
