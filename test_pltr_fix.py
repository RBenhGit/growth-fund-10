#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script for PLTR price history fix
"""

import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from data_sources.eodhd_api import EODHDDataSource
from config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_pltr():
    """Test fetching PLTR data with new price history implementation"""
    logger.info("Testing PLTR data fetch with price history fixes...")

    # Initialize data source
    data_source = EODHDDataSource()

    # Fetch PLTR data
    symbol = "PLTR.US"
    logger.info(f"Fetching data for {symbol}...")

    financial_data, market_data = data_source.get_stock_data(symbol, years=5)

    # Check results
    logger.info(f"\n{'='*60}")
    logger.info(f"PLTR Data Fetch Results:")
    logger.info(f"{'='*60}")

    logger.info(f"Symbol: {financial_data.symbol}")
    logger.info(f"Current Price: ${market_data.current_price}")
    logger.info(f"Market Cap: ${market_data.market_cap:,.0f}")
    logger.info(f"P/E Ratio: {market_data.pe_ratio}")

    logger.info(f"\nRevenues (last 5 years):")
    for year in sorted(financial_data.revenues.keys(), reverse=True):
        logger.info(f"  {year}: ${financial_data.revenues[year]:,.0f}")

    logger.info(f"\nNet Income (last 5 years):")
    for year in sorted(financial_data.net_incomes.keys(), reverse=True):
        logger.info(f"  {year}: ${financial_data.net_incomes[year]:,.0f}")

    # KEY TEST: Price history
    logger.info(f"\n{'='*60}")
    logger.info(f"PRICE HISTORY TEST:")
    logger.info(f"{'='*60}")
    logger.info(f"Number of price points: {len(market_data.price_history)}")

    if market_data.price_history:
        dates = sorted(market_data.price_history.keys())
        logger.info(f"Date range: {dates[0]} to {dates[-1]}")
        logger.info(f"First 5 prices:")
        for date in dates[:5]:
            logger.info(f"  {date}: ${market_data.price_history[date]:.2f}")
        logger.info(f"Last 5 prices:")
        for date in dates[-5:]:
            logger.info(f"  {date}: ${market_data.price_history[date]:.2f}")

        # Calculate momentum
        momentum = market_data.calculate_momentum(365)
        logger.info(f"\nMomentum (1 year): {momentum:.2f}%" if momentum else "\nMomentum: None (no price history)")

        # SUCCESS CRITERIA
        if len(market_data.price_history) >= 200:
            logger.info(f"\n✅ SUCCESS: Price history populated ({len(market_data.price_history)} days)")
            logger.info("✅ Momentum calculation will work correctly")
            return True
        else:
            logger.warning(f"\n⚠️  WARNING: Insufficient price history ({len(market_data.price_history)} days)")
            return False
    else:
        logger.error("\n❌ FAIL: Price history is EMPTY")
        logger.error("❌ Momentum and valuation will use default values (50.0)")
        return False

if __name__ == "__main__":
    success = test_pltr()
    sys.exit(0 if success else 1)
