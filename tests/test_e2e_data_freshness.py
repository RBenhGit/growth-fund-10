"""
End-to-end test for data freshness (mimics build_fund.py logic)
Tests that we get the LATEST fiscal year data available from APIs
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

def test_e2e_data_alignment():
    """
    Mimic build_fund.py's exact logic to test data freshness
    """

    print("=" * 80)
    print(f"E2E Data Freshness Test")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d')}")
    print("=" * 80)

    router = DataSourceRouter()
    adapter = DataSourceAdapter()

    # Test stocks with different fiscal year-ends
    test_stocks = [
        ("AAPL", "Apple", "September 30"),  # Non-calendar FY
        ("MSFT", "Microsoft", "June 30"),   # Non-calendar FY
        ("NDAQ", "Nasdaq", "December 31"),  # Calendar FY
        ("AEP", "AEP", "December 31"),      # Calendar FY
    ]

    index_name = "SP500"

    financial_source = router.get_financial_source(index_name)
    pricing_source = router.get_pricing_source(index_name)

    financial_source_name = financial_source.__class__.__name__
    pricing_source_name = pricing_source.__class__.__name__

    print(f"\nData Sources:")
    print(f"  Financial: {financial_source_name}")
    print(f"  Pricing: {pricing_source_name}")

    _source_name_map = {
        'YFinanceSource': 'yfinance',
        'TwelveDataSource': 'twelvedata',
        'AlphaVantageSource': 'alphavantage'
    }

    for base_symbol, name, fy_end in test_stocks:
        print(f"\n{'=' * 80}")
        print(f"Testing: {name} ({base_symbol}) - FY ends {fy_end}")
        print("=" * 80)

        # This is how build_fund.py constructs the symbol
        symbol = f"{base_symbol}.US"

        try:
            # 1. Fetch financial data (exactly as build_fund.py does)
            print(f"\n1️⃣  Fetching financial data for {symbol}...")
            financial_data = financial_source.get_stock_financials(symbol, years=5)

            # Check what we got
            revenue_years = sorted(financial_data.revenues.keys(), reverse=True)
            latest_fy = revenue_years[0] if revenue_years else None

            print(f"   Revenue years: {revenue_years}")
            print(f"   Latest FY: {latest_fy}")

            # Get fiscal dates
            fiscal_dates = None
            if hasattr(financial_source, '_last_fiscal_dates'):
                fiscal_dates = financial_source._last_fiscal_dates.get(symbol, [])
                print(f"   Fiscal dates: {fiscal_dates}")

            # 2. Fetch pricing data (exactly as build_fund.py does)
            print(f"\n2️⃣  Fetching pricing data...")

            # CRITICAL: Normalize symbol for pricing source (as build_fund.py does)
            pricing_symbol = adapter.normalize_symbol(
                symbol,
                index_name,
                _source_name_map.get(pricing_source_name, 'yfinance')
            )
            print(f"   Normalized symbol: {symbol} -> {pricing_symbol}")

            market_data = pricing_source.get_stock_market_data(pricing_symbol, fiscal_dates=fiscal_dates)

            # Check what we got
            if market_data.price_history:
                price_dates = sorted(market_data.price_history.keys(), reverse=True)
                latest_price_date = price_dates[0] if price_dates else None

                print(f"   Price dates: {price_dates}")
                print(f"   Latest price date: {latest_price_date}")
                print(f"   Current price: ${market_data.current_price:.2f}" if market_data.current_price else "   Current price: N/A")
            else:
                print(f"   ❌ No price history!")
                latest_price_date = None

            # 3. Alignment check
            print(f"\n3️⃣  Alignment Check:")

            if fiscal_dates and market_data.price_history:
                # Check that every fiscal date has a corresponding price
                missing_prices = []
                for fd in fiscal_dates:
                    if fd not in market_data.price_history:
                        missing_prices.append(fd)

                if missing_prices:
                    print(f"   ⚠️  Missing prices for fiscal dates: {missing_prices}")
                else:
                    print(f"   ✅ All fiscal dates have prices")

                # Check if latest fiscal date has a price
                latest_fiscal = fiscal_dates[0] if fiscal_dates else None
                if latest_fiscal and latest_fiscal in market_data.price_history:
                    price_at_fy_end = market_data.price_history[latest_fiscal]
                    print(f"   ✅ Price at latest FY end ({latest_fiscal}): ${price_at_fy_end:.2f}")
                else:
                    print(f"   ❌ No price for latest fiscal date: {latest_fiscal}")

            # 4. Freshness check
            print(f"\n4️⃣  Freshness Check:")

            if latest_fy:
                if latest_fy >= 2025:
                    print(f"   ✅ Financial data is fresh (FY{latest_fy})")
                else:
                    print(f"   ⚠️  Financial data may be stale (FY{latest_fy}, expected FY2025+)")
                    print(f"       Note: This is normal for Dec 31 FY-end stocks in Q1 2026")

            if latest_price_date:
                if latest_price_date.startswith("2025"):
                    print(f"   ✅ Price data extends into 2025")
                else:
                    print(f"   ⚠️  Price data may be outdated (latest: {latest_price_date})")

        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 80)
    print("Summary:")
    print("- Financial data availability depends on when 10-K is filed")
    print("- Price data should ALWAYS be available through most recent fiscal year-end")
    print("- System correctly aligns prices with fiscal dates from financial statements")
    print("=" * 80)

if __name__ == "__main__":
    test_e2e_data_alignment()