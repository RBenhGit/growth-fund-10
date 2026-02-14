"""
Test script to verify we're getting the most recent financial data
Checks if APIs have FY2025 data available (we're in Q1 2026)
"""

import sys
from datetime import datetime
from data_sources.router import DataSourceRouter
from config import settings

# Fix Hebrew output on Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

def test_us_stock_data_freshness():
    """Test if we're getting the latest fiscal year data for US stocks"""

    print("=" * 80)
    print(f"📅 Current Date: {datetime.now().strftime('%Y-%m-%d')}")
    print(f"📅 Expected Latest FY: 2025 (for most companies by Q1 2026)")
    print("=" * 80)

    router = DataSourceRouter()

    # Test symbols from different sectors
    test_symbols = [
        ("NDAQ", "Financial Services"),
        ("AAPL", "Technology"),
        ("MSFT", "Technology"),
        ("AEP", "Utilities")
    ]

    for symbol, sector in test_symbols:
        print(f"\n🔍 Testing {symbol} ({sector}):")
        print("-" * 60)

        try:
            # Get US financial source
            financial_source = router.get_financial_source("SP500")
            source_name = getattr(financial_source, 'name', financial_source.__class__.__name__)
            print(f"   Source: {source_name}")

            # Fetch financial data
            financial_data = financial_source.get_stock_financials(f"{symbol}.US", years=5)

            # Check what years we got
            revenue_years = sorted(financial_data.revenues.keys(), reverse=True)
            income_years = sorted(financial_data.net_incomes.keys(), reverse=True)

            latest_revenue_year = revenue_years[0] if revenue_years else None
            latest_income_year = income_years[0] if income_years else None

            print(f"   ✓ Revenue years: {revenue_years}")
            print(f"   ✓ Income years: {income_years}")

            # Check fiscal dates if available
            if hasattr(financial_source, '_last_fiscal_dates'):
                fiscal_dates = financial_source._last_fiscal_dates.get(f"{symbol}.US", [])
                print(f"   ✓ Fiscal dates: {fiscal_dates}")

                if fiscal_dates:
                    latest_fiscal = fiscal_dates[0]
                    print(f"   📅 Latest fiscal date: {latest_fiscal}")

                    # Parse the date
                    latest_year = int(latest_fiscal.split("-")[0])
                    if latest_year >= 2025:
                        print(f"   ✅ GOOD: Has FY2025+ data")
                    else:
                        print(f"   ⚠️  WARNING: Latest FY is {latest_year}, expected 2025+")

        except Exception as e:
            print(f"   ❌ Error: {e}")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    test_us_stock_data_freshness()