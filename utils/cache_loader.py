"""
טעינת נתוני מניות מקבצי cache

טוען אובייקטי Stock שלמים מקבצי JSON ב-cache/stocks_data/.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from models.stock import Stock

logger = logging.getLogger(__name__)


def load_cached_stock(symbol: str, cache_dir: Path) -> Optional[Stock]:
    """
    טוען מניה בודדת מ-cache

    Args:
        symbol: סימול המניה (e.g., NVDA.US)
        cache_dir: תיקיית cache/stocks_data

    Returns:
        Stock object, או None אם לא נמצא
    """
    # Convert symbol to filename: NVDA.US -> NVDA_US.json
    filename = symbol.replace(".", "_") + ".json"
    filepath = cache_dir / filename

    if not filepath.exists():
        logger.warning(f"Cache file not found: {filepath.name}")
        return None

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Stock(**data)
    except Exception as e:
        logger.error(f"Failed to load cache for {symbol}: {e}")
        return None


def load_cached_stocks(symbols: list[str], cache_dir: Path) -> dict[str, Stock]:
    """
    טוען מניות מרובות מ-cache

    Args:
        symbols: רשימת סימולים (e.g., ["NVDA.US", "CRM.US"])
        cache_dir: תיקיית cache/stocks_data

    Returns:
        dict mapping symbol -> Stock (only successfully loaded)
    """
    stocks = {}
    missing = []

    for symbol in symbols:
        stock = load_cached_stock(symbol, cache_dir)
        if stock is not None:
            stocks[symbol] = stock
        else:
            missing.append(symbol)

    if missing:
        logger.warning(f"Missing cache files for {len(missing)} stocks: {missing[:5]}{'...' if len(missing) > 5 else ''}")

    logger.info(f"Loaded {len(stocks)}/{len(symbols)} stocks from cache")
    return stocks
