"""
Test script to verify price history only contains financial report dates + current price
"""
import sys
import codecs
import json

# Fix Windows console encoding for Hebrew
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

from data_sources.eodhd_api import EODHDDataSource
from config import settings

# Initialize EODHD data source
ds = EODHDDataSource()

print("Testing price history for AAPL.US...")
print("=" * 60)

# Fetch stock data (5 years by default)
financial_data, market_data = ds.get_stock_data("AAPL.US", years=5)

print(f"\nFinancial Data Years:")
print(f"  Revenues: {sorted(financial_data.revenues.keys())}")
print(f"  Net Incomes: {sorted(financial_data.net_incomes.keys())}")

print(f"\nPrice History:")
print(f"  Number of dates: {len(market_data.price_history)}")
print(f"  Dates: {sorted(market_data.price_history.keys())}")

print(f"\nPrice Details:")
for date in sorted(market_data.price_history.keys()):
    price = market_data.price_history[date]
    print(f"  {date}: ${price:.2f}")

print(f"\nValidation:")
expected_count = len(financial_data.revenues) + 1  # Financial years + current price
actual_count = len(market_data.price_history)
print(f"  Expected: {expected_count} prices ({len(financial_data.revenues)} financial reports + 1 current)")
print(f"  Actual: {actual_count} prices")

if actual_count == expected_count:
    print("  ✅ SUCCESS: Price history contains correct number of prices!")
elif actual_count > expected_count:
    print(f"  ⚠️ WARNING: Too many prices (extra {actual_count - expected_count})")
elif actual_count < expected_count:
    print(f"  ❌ ERROR: Too few prices (missing {expected_count - actual_count})")

print("\n" + "=" * 60)
print("Testing with smaller data set (3 years)...")
print("=" * 60)

financial_data2, market_data2 = ds.get_stock_data("MSFT.US", years=3)

print(f"\nFinancial Data Years (MSFT):")
print(f"  Revenues: {sorted(financial_data2.revenues.keys())}")

print(f"\nPrice History (MSFT):")
print(f"  Number of dates: {len(market_data2.price_history)}")
print(f"  Dates: {sorted(market_data2.price_history.keys())}")

expected_count2 = len(financial_data2.revenues) + 1
actual_count2 = len(market_data2.price_history)
print(f"\nValidation:")
print(f"  Expected: {expected_count2} prices")
print(f"  Actual: {actual_count2} prices")

if actual_count2 == expected_count2:
    print("  ✅ SUCCESS: Price history contains correct number of prices!")
else:
    print(f"  ❌ ERROR: Mismatch in price count")
