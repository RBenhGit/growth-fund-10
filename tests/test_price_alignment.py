"""
Test script to verify price history includes the most recent fiscal year-end
even if financial statements aren't filed yet
"""

import sys
from datetime import datetime
from data_sources.router import DataSourceRouter
from data_sources.adapter import DataSourceAdapter
from config import settings

# Fix Hebrew output on Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

def test_price_vs_financial_alignment():
    """
    Test that price history extends beyond available financial data

    Expected behavior:
    - Financial data: May only have FY2024 (if 10-K not filed yet)
    - Price data: Should have 2025-12-31 (market data always available)
    """

    print("=" * 80)
    print(f"📅 Today: {datetime.now().strftime('%Y-%m-%d')}")
    print("=" * 80)

    router = DataSourceRouter()
    adapter = DataSourceAdapter()

    # Test calendar year-end stocks (Dec 31)
    test_symbols = [
        ("NDAQ", "2025-12-31"),  # Nasdaq Inc
        ("AEP", "2025-12-31"),   # American Electric Power
    ]

    index_name = "SP500"
    financial_source = router.get_financial_source(index_name)
    pricing_source = router.get_pricing_source(index_name)

    financial_source_name = financial_source.__class__.__name__
    pricing_source_name = pricing_source.__class__.__name__

    _source_name_map = {
        'YFinanceSource': 'yfinance',
        'TwelveDataSource': 'twelvedata',
        'AlphaVantageSource': 'alphavantage'
    }

    print(f"\nData Sources: {financial_source_name} (financial), {pricing_source_name} (pricing)")

    for symbol, expected_latest_price_date in test_symbols:
        print(f"\n{'=' * 80}")
        print(f"🔍 Testing {symbol}")
        print(f"   Expected latest price date: {expected_latest_price_date}")
        print("=" * 80)

        try:
            full_symbol = f"{symbol}.US"

            # Fetch financial data
            print(f"\n📊 Financial Data:")
            financial_data = financial_source.get_stock_financials(full_symbol, years=5)

            revenue_years = sorted(financial_data.revenues.keys(), reverse=True)
            print(f"   Revenue years: {revenue_years}")

            # Get fiscal dates from financial source
            fiscal_dates = None
            if hasattr(financial_source, '_last_fiscal_dates'):
                fiscal_dates = financial_source._last_fiscal_dates.get(full_symbol, [])
                print(f"   Fiscal dates from financials: {fiscal_dates}")

            # Fetch pricing data - CRITICAL: normalize symbol first (as build_fund.py does)
            print(f"\n💰 Pricing Data:")
            pricing_symbol = adapter.normalize_symbol(
                full_symbol,
                index_name,
                _source_name_map.get(pricing_source_name, 'yfinance')
            )
            print(f"   Symbol normalization: {full_symbol} -> {pricing_symbol}")
            market_data = pricing_source.get_stock_market_data(pricing_symbol, fiscal_dates=fiscal_dates)

            if market_data.price_history:
                price_dates = sorted(market_data.price_history.keys(), reverse=True)
                print(f"   Price history dates: {price_dates}")
                print(f"   Latest price date: {price_dates[0]}")

                # Check if we have the expected latest date
                if expected_latest_price_date in market_data.price_history:
                    print(f"   ✅ GOOD: Has price for {expected_latest_price_date}")
                else:
                    print(f"   ❌ MISSING: No price for {expected_latest_price_date}")
                    print(f"   🔍 This is a problem - market data should be available!")
            else:
                print(f"   ❌ No price history at all!")

            # Summary
            print(f"\n📋 Alignment Check:")
            latest_financial_year = revenue_years[0] if revenue_years else None
            latest_price_date = sorted(market_data.price_history.keys(), reverse=True)[0] if market_data.price_history else None

            print(f"   Latest financial year: {latest_financial_year}")
            print(f"   Latest price date: {latest_price_date}")

            if latest_price_date and latest_price_date.startswith("2025"):
                print(f"   ✅ Price data extends into 2025")
            else:
                print(f"   ⚠️  WARNING: Price data may be outdated")

        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 80)

if __name__ == "__main__":
    test_price_vs_financial_alignment()
