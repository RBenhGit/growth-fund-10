"""Test symbol normalization for different sources"""

from data_sources.adapter import DataSourceAdapter
from data_sources.yfinance_source import YFinanceSource

adapter = DataSourceAdapter()

# Test cases
test_cases = [
    ("NDAQ.US", "SP500", "yfinance"),
    ("AEP.US", "SP500", "yfinance"),
    ("AAPL.US", "SP500", "yfinance"),
]

print("=" * 80)
print("Symbol Normalization Test")
print("=" * 80)

for symbol, index, source in test_cases:
    normalized = adapter.normalize_symbol(symbol, index, source)
    print(f"{symbol:15s} + {source:15s} + {index:10s} -> {normalized}")

# Test actual yfinance class name
yf_source = YFinanceSource()
print(f"\nYFinanceSource class name: {yf_source.__class__.__name__}")

# Test the mapping
_source_name_map = {
    'YFinanceSource': 'yfinance',
    'TwelveDataSource': 'twelvedata',
    'AlphaVantageSource': 'alphavantage'
}
class_name = yf_source.__class__.__name__
mapped_name = _source_name_map.get(class_name, 'yfinance')
print(f"Mapped name: {mapped_name}")

# Test normalization with mapped name
test_symbol = "NDAQ.US"
normalized = adapter.normalize_symbol(test_symbol, "SP500", mapped_name)
print(f"\nFinal result: {test_symbol} -> {normalized}")
print(f"Expected: NDAQ")
print(f"Match: {'✅' if normalized == 'NDAQ' else '❌'}")
