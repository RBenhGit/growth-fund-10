"""
Twelve Data API Data Source
מקור נתונים מבוסס על Twelve Data API - https://twelvedata.com/
תומך במניות ישראליות (TASE) ואמריקאיות (US)
"""

import requests
import time
import logging
from typing import List, Dict, Optional, Tuple
from models import FinancialData, MarketData
from .base_data_source import BaseDataSource
from config import settings

logger = logging.getLogger(__name__)

# Twelve Data returns TASE prices in ILA (agorot). 100 agorot = 1 ILS.
# Financial statements are reported in ILS.
ILA_TO_ILS = 100


class TwelveDataSource(BaseDataSource):
    """מקור נתונים מבוסס Twelve Data API"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.TWELVEDATA_API_KEY
        self.base_url = "https://api.twelvedata.com"
        self._request_delay = 0.15  # minimum delay between requests
        self._credits_per_minute = 1500  # stay under the 1597 limit
        self._credits_used_estimate = 0
        self._minute_start = time.time()
        self._stocks_this_minute = 0
        self._max_stocks_per_minute = 4  # ~350 credits/stock, 1597 limit

        if not self.api_key:
            raise ValueError("TWELVEDATA_API_KEY חסר בהגדרות")

    def _get_exchange(self, symbol: str) -> Optional[str]:
        """
        קביעת הבורסה לפי סיומת הסימול

        Args:
            symbol: סימול המניה (e.g., LUMI.TA, AAPL.US)

        Returns:
            Optional[str]: שם הבורסה או None
        """
        if symbol.endswith(".TA"):
            return "TASE"
        elif symbol.endswith(".US"):
            return None  # US stocks don't need exchange param
        return None

    def _clean_symbol(self, symbol: str) -> str:
        """
        הסרת סיומת בורסה מהסימול

        Args:
            symbol: סימול עם סיומת (e.g., LUMI.TA)

        Returns:
            str: סימול נקי (e.g., LUMI)
        """
        for suffix in [".TA", ".US"]:
            if symbol.endswith(suffix):
                return symbol[:-len(suffix)]
        return symbol

    def _wait_for_rate_limit(self):
        """Wait if we've processed max stocks for this minute window"""
        if self._stocks_this_minute >= self._max_stocks_per_minute:
            elapsed = time.time() - self._minute_start
            if elapsed < 62:
                wait_time = 62 - elapsed
                logger.info(
                    f"Rate limit: processed {self._stocks_this_minute} stocks this minute. "
                    f"Waiting {wait_time:.0f}s for next minute..."
                )
                time.sleep(wait_time)
            self._stocks_this_minute = 0
            self._minute_start = time.time()

    def _notify_stock_complete(self):
        """Call after all API calls for a single stock are done"""
        self._stocks_this_minute += 1

    def _api_request(self, endpoint: str, params: dict) -> dict:
        """
        שליחת בקשה ל-API עם rate limiting

        Args:
            endpoint: נתיב ה-API (e.g., /income_statement)
            params: פרמטרים לבקשה

        Returns:
            dict: תשובת ה-API

        Raises:
            RuntimeError: אם הבקשה נכשלה
        """
        params["apikey"] = self.api_key
        url = f"{self.base_url}{endpoint}"

        time.sleep(self._request_delay)

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Twelve Data error format
            if data.get("status") == "error" or data.get("code"):
                error_msg = data.get("message", "Unknown error")
                raise RuntimeError(f"Twelve Data API error: {error_msg}")

            return data
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Twelve Data API request failed: {e}")

    def _is_tase_symbol(self, symbol: str) -> bool:
        return symbol.endswith(".TA")

    def _convert_price_to_ils(self, price_agorot: float, symbol: str) -> float:
        """
        המרת מחיר מאגורות לשקלים (רק עבור מניות TASE)

        Twelve Data מחזיר מחירי TASE באגורות (ILA).
        """
        if self._is_tase_symbol(symbol):
            return price_agorot / ILA_TO_ILS
        return price_agorot

    def login(self) -> bool:
        """בדיקת תקינות החיבור ל-API"""
        try:
            data = self._api_request("/api_usage", {})
            plan = data.get("plan_category", "unknown")
            usage = data.get("current_usage", "?")
            limit = data.get("plan_limit", "?")
            logger.info(f"Twelve Data: plan={plan}, usage={usage}/{limit}")
            return True
        except Exception as e:
            logger.error(f"Twelve Data login failed: {e}")
            return False

    def logout(self):
        """לא נדרש עבור Twelve Data API"""
        pass

    def get_index_constituents(self, index_name: str) -> List[Dict]:
        """
        שליפת רשימת רכיבי מדד

        Twelve Data אינו מספק API ייעודי לרכיבי מדד TA-125.
        נשתמש ברשימת מניות TASE מ-cache או מ-API הבורסה.
        עבור SP500 נשתמש ברשימה מ-cache.

        Args:
            index_name: שם המדד

        Returns:
            List[Dict]: רשימת מניות
        """
        import json
        from pathlib import Path

        # Try to load from existing cache first (any quarter)
        cache_dir = settings.CACHE_DIR / "index_constituents"
        if cache_dir.exists():
            for cache_file in sorted(cache_dir.glob(f"{index_name}_*.json"), reverse=True):
                try:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        constituents = json.load(f)
                    if constituents:
                        logger.info(f"Loaded {len(constituents)} constituents from cache: {cache_file.name}")
                        return constituents
                except Exception:
                    continue

        # Fallback: fetch TASE stock list from Twelve Data
        if index_name == "TASE125":
            data = self._api_request("/stocks", {"exchange": "TASE", "type": "Common Stock"})
            stocks = data.get("data", [])

            constituents = []
            for stock in stocks:
                # Skip numeric-only symbols (not real stock tickers)
                if stock["symbol"].isdigit():
                    continue
                constituents.append({
                    "symbol": stock["symbol"],
                    "name": stock.get("name", stock["symbol"]),
                    "sector": "",
                    "sub_sector": ""
                })

            logger.info(f"Fetched {len(constituents)} TASE stocks from Twelve Data")
            return constituents

        elif index_name == "SP500":
            # Twelve Data doesn't provide SP500 constituents directly
            raise RuntimeError(
                "Twelve Data does not provide S&P 500 index constituents. "
                "Use cached data or another source."
            )

        raise ValueError(f"מדד לא נתמך: {index_name}")

    def get_stock_data(self, symbol: str, years: int = 5) -> Tuple[FinancialData, MarketData]:
        """
        שליפת כל נתוני המניה - פיננסיים ומחירים

        Args:
            symbol: סימול המניה (כולל סיומת בורסה)
            years: מספר שנים לשלוף

        Returns:
            Tuple[FinancialData, MarketData]: נתונים פיננסיים ונתוני שוק
        """
        self._wait_for_rate_limit()
        financial_data = self.get_stock_financials(symbol, years)
        market_data = self.get_stock_market_data(symbol)
        self._notify_stock_complete()
        return financial_data, market_data

    def get_stock_financials(self, symbol: str, years: int = 5) -> FinancialData:
        """
        שליפת נתונים פיננסיים למניה

        3 API calls: income_statement, balance_sheet, cash_flow

        Args:
            symbol: סימול המניה (e.g., LUMI.TA)
            years: מספר שנים לשלוף

        Returns:
            FinancialData: נתונים פיננסיים
        """
        clean_sym = self._clean_symbol(symbol)
        exchange = self._get_exchange(symbol)

        params = {"symbol": clean_sym, "period": "annual"}
        if exchange:
            params["exchange"] = exchange

        # API Call 1: Income Statement
        try:
            income_data = self._api_request("/income_statement", params)
        except RuntimeError as e:
            logger.error(f"Failed to fetch income statement for {symbol}: {e}")
            raise

        statements = income_data.get("income_statement", [])

        revenues = {}
        net_incomes = {}
        operating_incomes = {}

        for stmt in statements[:years]:
            fiscal_date = stmt.get("fiscal_date", "")
            year = int(fiscal_date.split("-")[0]) if fiscal_date else None
            if year is None:
                continue

            # Revenue (sales)
            sales = stmt.get("sales")
            revenues[year] = float(sales) if sales is not None else 0.0

            # Net income
            ni = stmt.get("net_income")
            net_incomes[year] = float(ni) if ni is not None else 0.0

            # Operating income (preferred over EBITDA - fixes the bank/insurance issue)
            oi = stmt.get("operating_income")
            if oi is not None:
                operating_incomes[year] = float(oi)
            else:
                # Fallback: use pretax_income as proxy for companies without operating_income
                pretax = stmt.get("pretax_income")
                if pretax is not None:
                    operating_incomes[year] = float(pretax)
                else:
                    # Last resort: EBITDA
                    ebitda = stmt.get("ebitda")
                    operating_incomes[year] = float(ebitda) if ebitda is not None else 0.0

        # API Call 2: Balance Sheet
        total_debt = 0.0
        total_equity = 0.0
        try:
            balance_data = self._api_request("/balance_sheet", params)
            sheets = balance_data.get("balance_sheet", [])
            if sheets:
                latest = sheets[0]

                liabilities = latest.get("liabilities", {})
                non_current = liabilities.get("non_current_liabilities", {})
                ltd = non_current.get("long_term_debt")
                total_debt = float(ltd) if ltd is not None else 0.0

                equity_section = latest.get("shareholders_equity", {})
                te = equity_section.get("total_shareholders_equity")
                if te is not None:
                    total_equity = float(te)
                else:
                    # Try alternate path
                    common = equity_section.get("common_stock_equity")
                    total_equity = float(common) if common is not None else 0.0
        except RuntimeError as e:
            logger.warning(f"Failed to fetch balance sheet for {symbol}: {e}")

        # API Call 3: Cash Flow
        operating_cash_flows = {}
        try:
            cf_data = self._api_request("/cash_flow", params)
            flows = cf_data.get("cash_flow", [])
            for flow in flows[:years]:
                fiscal_date = flow.get("fiscal_date", "")
                year = int(fiscal_date.split("-")[0]) if fiscal_date else None
                if year is None:
                    continue

                ops = flow.get("operating_activities", {})
                ocf = ops.get("operating_cash_flow")
                operating_cash_flows[year] = float(ocf) if ocf is not None else 0.0
        except RuntimeError as e:
            logger.warning(f"Failed to fetch cash flow for {symbol}: {e}")

        return FinancialData(
            symbol=symbol,
            revenues=revenues,
            net_incomes=net_incomes,
            operating_incomes=operating_incomes,
            operating_cash_flows=operating_cash_flows,
            total_debt=total_debt,
            total_equity=total_equity
        )

    def get_stock_market_data(self, symbol: str) -> MarketData:
        """
        שליפת נתוני שוק למניה

        2 API calls: quote (current price) + statistics (market cap, P/E)
        + time_series for price history

        Args:
            symbol: סימול המניה

        Returns:
            MarketData: נתוני שוק
        """
        clean_sym = self._clean_symbol(symbol)
        exchange = self._get_exchange(symbol)
        is_tase = self._is_tase_symbol(symbol)

        params = {"symbol": clean_sym}
        if exchange:
            params["exchange"] = exchange

        # API Call 1: Quote (current price, name)
        current_price = 0.0
        stock_name = clean_sym
        try:
            quote_data = self._api_request("/quote", params)
            close = quote_data.get("close")
            if close is not None:
                raw_price = float(close)
                current_price = raw_price / ILA_TO_ILS if is_tase else raw_price
            stock_name = quote_data.get("name", clean_sym)
        except RuntimeError as e:
            logger.warning(f"Failed to fetch quote for {symbol}: {e}")

        # API Call 2: Statistics (market cap, P/E)
        market_cap = 0.0
        pe_ratio = None
        try:
            stats_data = self._api_request("/statistics", params)
            stats = stats_data.get("statistics", {})

            valuations = stats.get("valuations_metrics", {})
            mc = valuations.get("market_capitalization")
            if mc is not None:
                market_cap = float(mc)
                # TASE market cap from statistics is in ILA, convert to ILS
                if is_tase:
                    market_cap = market_cap / ILA_TO_ILS

            pe = valuations.get("trailing_pe")
            if pe is not None and pe > 0:
                pe_ratio = float(pe)
        except RuntimeError as e:
            logger.warning(f"Failed to fetch statistics for {symbol}: {e}")

        # API Call 3: Time series for price history (last 2 years, monthly)
        price_history = {}
        try:
            ts_params = dict(params)
            ts_params["interval"] = "1month"
            ts_params["outputsize"] = "24"  # 2 years of monthly data
            ts_data = self._api_request("/time_series", ts_params)
            values = ts_data.get("values", [])
            for entry in values:
                date_str = entry.get("datetime", "")
                close_val = entry.get("close")
                if date_str and close_val is not None:
                    raw = float(close_val)
                    price_history[date_str] = raw / ILA_TO_ILS if is_tase else raw
        except RuntimeError as e:
            logger.warning(f"Failed to fetch time series for {symbol}: {e}")

        # Add current price to history
        if current_price > 0:
            from datetime import datetime
            today = datetime.now().strftime("%Y-%m-%d")
            price_history[today] = current_price

        return MarketData(
            symbol=symbol,
            name=stock_name,
            market_cap=market_cap,
            current_price=current_price,
            pe_ratio=pe_ratio,
            price_history=price_history
        )

    def get_index_pe_ratio(self, index_name: str) -> Optional[float]:
        """
        חישוב P/E ממוצע של המדד

        Twelve Data אינו מספק P/E ישירות למדדים ישראליים.
        נחשב ממוצע משוקלל מנתוני המניות.

        Args:
            index_name: שם המדד

        Returns:
            Optional[float]: P/E ממוצע או None
        """
        # For SP500 try index statistics
        if index_name == "SP500":
            try:
                data = self._api_request("/statistics", {"symbol": "SPX"})
                stats = data.get("statistics", {})
                pe = stats.get("valuations_metrics", {}).get("trailing_pe")
                if pe:
                    return float(pe)
            except Exception:
                pass

        # Default: return a reasonable estimate
        # TA-125 historical P/E typically ranges 10-18
        if index_name == "TASE125":
            logger.info("Using estimated TASE125 P/E ratio of 14.0")
            return 14.0

        return None
