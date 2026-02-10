"""
Twelve Data API Data Source
מקור נתונים מבוסס על Twelve Data API - https://twelvedata.com/
תומך במניות ישראליות (TASE) ואמריקאיות (US)
"""

import requests
import time
import logging
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
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
        self._request_delay = 0.5  # Increased from 0.15s to 0.5s for better rate limiting
        self._minute_start = time.time()
        self._stocks_this_minute = 0
        self._credits_used_this_minute = 0
        self._last_request_time = 0  # Track last API call for throttling
        self._credits_remaining = None  # Actual remaining credits from API headers

        # These will be set by _detect_plan_limits()
        self._credits_per_minute = 0
        self._max_stocks_per_minute = 0

        # Cache for fiscal dates to avoid duplicate API calls
        # Maps symbol -> list of fiscal dates
        self._last_fiscal_dates: Dict[str, List[str]] = {}

        if not self.api_key:
            raise ValueError("TWELVEDATA_API_KEY חסר בהגדרות")

        # Auto-detect plan and configure rate limits
        self._detect_plan_limits()

    def _detect_plan_limits(self):
        """
        Detect API plan tier and set appropriate rate limits

        Calculates optimal max_stocks_per_minute based on:
        - Plan tier credits/minute
        - 65% safety headroom (proven safe with deterministic 300 credits/stock)
        - Estimated credits per stock based on ACTUAL API response headers:
          * Financial only (3 calls): ~300 credits/stock (recommended config with yfinance for pricing)
          * Pricing only (2+N calls): ~700+ credits/stock
          * Both unified (worst case): ~360 credits/stock

        NOTE: Each TwelveData financial API call costs ~100 credits.
        3 financial calls (income, balance, cashflow) = ~300 credits/stock.
        The 429 retry logic and real-time credit tracking provide safety nets.

        Respects manual overrides from .env if set.
        """
        # Check for manual overrides first
        if settings.TWELVEDATA_CREDITS_PER_MINUTE > 0:
            self._credits_per_minute = settings.TWELVEDATA_CREDITS_PER_MINUTE
            self._max_stocks_per_minute = settings.TWELVEDATA_MAX_STOCKS_PER_MINUTE or int((self._credits_per_minute * 0.65) / 300)
            logger.info(
                f"✓ TwelveData: Using manual override from .env: "
                f"{self._credits_per_minute} credits/min, {self._max_stocks_per_minute} stocks/min"
            )
            return

        try:
            # Note: _api_request can't be used before init is complete, so we make a direct call
            params = {"apikey": self.api_key}
            url = f"{self.base_url}/api_usage"
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            plan = data.get("plan_category", "basic").lower()
            plan_limit = data.get("plan_limit", 0)  # Credits per minute from API

            # Set limits based on detected plan
            if "basic" in plan or "free" in plan:
                self._credits_per_minute = 8
                self._max_stocks_per_minute = 0  # Will warn user
                logger.warning(
                    "⚠️  TwelveData Basic plan detected - NOT SUITABLE for fund building!\n"
                    "   Basic plan (8 credits/min) would take 3-12 hours per run.\n"
                    "   Please upgrade to Pro 610 or higher."
                )
            elif "pro" in plan:
                # Pro plans: Pro 610, Pro 1000, Pro 1597, etc.
                # Use actual limit from API, or conservative default
                self._credits_per_minute = plan_limit if plan_limit > 0 else 610
                # Financial only (3 calls: income, balance, cashflow): ~300 credits/stock
                # With yfinance handling pricing, TwelveData only does financials
                # Formula: (credits * 0.65) / 300 = max stocks/min with 65% safety margin
                self._max_stocks_per_minute = max(1, int((self._credits_per_minute * 0.65) / 300))
                estimated_minutes = 125 / max(self._max_stocks_per_minute, 1)
                logger.info(
                    f"✓ TwelveData Pro plan detected: {self._credits_per_minute} credits/min, "
                    f"{self._max_stocks_per_minute} stocks/min (with 65% safety margin, ~300 credits/stock)\n"
                    f"  TASE125 (~125 stocks) will take ~{estimated_minutes:.0f} minutes"
                )
            else:  # Grow, Enterprise, etc.
                self._credits_per_minute = plan_limit if plan_limit > 0 else 1500
                self._max_stocks_per_minute = max(1, int((self._credits_per_minute * 0.65) / 300))
                logger.info(
                    f"✓ TwelveData {plan.title()} plan detected: {self._credits_per_minute} credits/min, "
                    f"{self._max_stocks_per_minute} stocks/min (with 65% safety margin)\n"
                    f"  TASE125 (~125 stocks) will take ~{125 / max(self._max_stocks_per_minute, 1):.0f} minutes"
                )

        except Exception as e:
            logger.warning(f"Could not detect plan, using Pro 610 defaults: {e}")
            # Fallback to Pro 610 defaults (safe for most users)
            # Each financial call costs ~100 credits, 3 calls/stock = ~300 credits
            self._credits_per_minute = 610
            self._max_stocks_per_minute = max(1, int((610 * 0.65) / 300))  # = 1

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
        """
        CONSERVATIVE: Wait if processing next stock would exceed safe threshold

        Uses TWO signals for throttle decisions:
        1. Stock count vs max_stocks_per_minute
        2. Actual credits remaining from API response headers (api-credits-left)

        Each financial API call costs ~100 credits. A full stock with 3 financial
        calls costs ~300 credits. This method ensures we don't start a new stock
        if we don't have enough credits remaining.
        """
        elapsed = time.time() - self._minute_start

        # Check if we should reset counters (new minute)
        if elapsed >= 62:
            logger.debug(f"✅ Minute reset: {self._stocks_this_minute} stocks, {self._credits_used_this_minute} credits")
            self._stocks_this_minute = 0
            self._credits_used_this_minute = 0
            self._credits_remaining = self._credits_per_minute  # Reset remaining
            self._minute_start = time.time()
            return

        # Check stock limit
        if self._stocks_this_minute >= self._max_stocks_per_minute:
            wait_time = 62 - elapsed
            logger.info(
                f"⏱️  Stock limit reached: {self._stocks_this_minute}/{self._max_stocks_per_minute} stocks "
                f"({self._credits_used_this_minute} credits). "
                f"Waiting {wait_time:.0f}s for next minute..."
            )
            time.sleep(wait_time)
            self._stocks_this_minute = 0
            self._credits_used_this_minute = 0
            self._credits_remaining = self._credits_per_minute
            self._minute_start = time.time()
            return

        # LOOK-AHEAD using ACTUAL remaining credits from API headers
        # Each stock needs ~300 credits for 3 financial calls (when yfinance handles pricing)
        estimated_credits_per_stock = 300
        # Use actual remaining credits if available, otherwise estimate
        if self._credits_remaining is not None and self._credits_remaining > 0:
            if self._credits_remaining < estimated_credits_per_stock:
                wait_time = 62 - elapsed
                logger.warning(
                    f"⏸️  CREDIT THROTTLE: Only {self._credits_remaining} credits remaining "
                    f"(need ~{estimated_credits_per_stock} for next stock). "
                    f"Waiting {wait_time:.0f}s for next minute..."
                )
                time.sleep(wait_time)
                self._stocks_this_minute = 0
                self._credits_used_this_minute = 0
                self._credits_remaining = self._credits_per_minute
                self._minute_start = time.time()
                return

        # Fallback: estimate-based threshold (65% safety margin)
        safe_threshold = int(self._credits_per_minute * 0.65)
        projected_credits = self._credits_used_this_minute + estimated_credits_per_stock

        if projected_credits > safe_threshold:
            wait_time = 62 - elapsed
            logger.warning(
                f"⏸️  ESTIMATED THROTTLE: {self._credits_used_this_minute} credits used, "
                f"next stock needs ~{estimated_credits_per_stock} more (total: {projected_credits}). "
                f"Safe limit: {safe_threshold}/{self._credits_per_minute}. "
                f"Waiting {wait_time:.0f}s for next minute..."
            )
            time.sleep(wait_time)
            self._stocks_this_minute = 0
            self._credits_used_this_minute = 0
            self._credits_remaining = self._credits_per_minute
            self._minute_start = time.time()

    def _notify_stock_complete(self):
        """Call after all API calls for a single stock are done"""
        self._stocks_this_minute += 1

    def _api_request(self, endpoint: str, params: dict, retry_count: int = 0) -> dict:
        """
        שליחת בקשה ל-API עם rate limiting, credit tracking, and 429 retry

        Args:
            endpoint: נתיב ה-API (e.g., /income_statement)
            params: פרמטרים לבקשה
            retry_count: מספר ניסיונות חוזרים (internal use)

        Returns:
            dict: תשובת ה-API

        Raises:
            RuntimeError: אם הבקשה נכשלה
        """
        params["apikey"] = self.api_key
        url = f"{self.base_url}{endpoint}"

        # Enforce minimum delay between requests
        if self._last_request_time > 0:
            elapsed_since_last = time.time() - self._last_request_time
            if elapsed_since_last < self._request_delay:
                sleep_time = self._request_delay - elapsed_since_last
                time.sleep(sleep_time)

        self._last_request_time = time.time()

        try:
            response = requests.get(url, params=params, timeout=30)

            # Handle 429 Rate Limit with exponential backoff
            if response.status_code == 429:
                if retry_count < 3:
                    wait_time = 2 ** retry_count  # Exponential: 1s, 2s, 4s
                    logger.warning(
                        f"⚠️  Rate limit exceeded (429), waiting {wait_time}s before retry {retry_count + 1}/3..."
                    )
                    time.sleep(wait_time)
                    return self._api_request(endpoint, params, retry_count + 1)
                else:
                    raise RuntimeError(
                        "Rate limit exceeded after 3 retries. "
                        "This should not happen with proper rate limiting. "
                        "Please check your plan limits or reduce max_stocks_per_minute."
                    )

            response.raise_for_status()

            # Track actual credits from response headers
            # Note: 'api-credits-used' is CUMULATIVE (total used this minute), not per-call
            credits_used_total = int(response.headers.get('api-credits-used', 0))
            credits_left = int(response.headers.get('api-credits-left', 0))

            # Calculate credits for THIS call only
            if self._credits_used_this_minute > 0:
                credits_this_call = credits_used_total - self._credits_used_this_minute
            else:
                credits_this_call = credits_used_total

            self._credits_used_this_minute = credits_used_total
            self._credits_remaining = credits_left  # Track actual remaining for throttle decisions

            # Progressive warnings based on remaining credits
            if credits_left == 0:
                logger.error(f"🛑 OUT OF CREDITS! Used {credits_used_total}/{self._credits_per_minute}")
            elif credits_left < 200:  # Changed from 100 - more aggressive warning
                logger.warning(f"🔴 DANGER: Only {credits_left} credits remaining! ({credits_used_total} used)")
            elif credits_left < 400:  # Changed from 300 - earlier warning
                logger.warning(f"🟡 WARNING: {credits_left} credits remaining ({credits_used_total}/{self._credits_per_minute} used)")
            elif credits_left < 600:  # New tier - informational
                logger.info(f"🟢 {credits_left} credits remaining ({credits_used_total}/{self._credits_per_minute} used)")

            logger.debug(f"API call: {endpoint}, this_call={credits_this_call}, total_used={credits_used_total}, left={credits_left}")

            # Enhanced debug mode logging with emoji stats
            if settings.DEBUG_MODE:
                logger.debug(
                    f"📊 API Stats: endpoint={endpoint}, "
                    f"credits_this_call={credits_this_call}, "
                    f"cumulative={credits_used_total}, "
                    f"remaining={credits_left}, "
                    f"stocks_this_minute={self._stocks_this_minute}"
                )

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

        Optimized to avoid duplicate /income_statement API call by reusing fiscal dates.

        Args:
            symbol: סימול המניה (כולל סיומת בורסה)
            years: מספר שנים לשלוף

        Returns:
            Tuple[FinancialData, MarketData]: נתונים פיננסיים ונתוני שוק
        """
        self._wait_for_rate_limit()

        # Get financials AND fiscal dates in one call (internal method)
        financial_data, fiscal_dates = self._get_financials_with_dates(symbol, years)

        # Pass fiscal_dates to avoid duplicate API call
        market_data = self.get_stock_market_data(symbol, fiscal_dates)

        self._notify_stock_complete()
        return financial_data, market_data

    def get_stock_financials(self, symbol: str, years: int = 5) -> FinancialData:
        """
        שליפת נתונים פיננסיים למניה (public interface method)

        Follows BaseDataSource interface contract by returning only FinancialData.
        Internally caches fiscal dates for potential reuse in get_stock_market_data().

        3 API calls: income_statement, balance_sheet, cash_flow (~300 credits total)

        Args:
            symbol: סימול המניה (e.g., LUMI.TA)
            years: מספר שנים לשלוף

        Returns:
            FinancialData: נתונים פיננסיים
        """
        self._wait_for_rate_limit()

        financial_data, fiscal_dates = self._get_financials_with_dates(symbol, years)

        # Cache fiscal dates for potential reuse in get_stock_market_data()
        self._last_fiscal_dates[symbol] = fiscal_dates

        self._notify_stock_complete()
        return financial_data

    def _get_financials_with_dates(self, symbol: str, years: int = 5) -> Tuple[FinancialData, List[str]]:
        """
        שליפת נתונים פיננסיים למניה (internal method with fiscal dates)

        3 API calls: income_statement, balance_sheet, cash_flow

        Args:
            symbol: סימול המניה (e.g., LUMI.TA)
            years: מספר שנים לשלוף

        Returns:
            Tuple[FinancialData, List[str]]: נתונים פיננסיים ורשימת תאריכי fiscal
                                              (to avoid duplicate API call in get_stock_market_data)
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
        fiscal_dates = []  # Collect fiscal dates to avoid duplicate API call later

        for stmt in statements[:years]:
            fiscal_date = stmt.get("fiscal_date", "")
            year = int(fiscal_date.split("-")[0]) if fiscal_date else None
            if year is None:
                continue

            # Save fiscal date for price history fetching
            if fiscal_date:
                fiscal_dates.append(fiscal_date)

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

        # CRITICAL FIX: Extend fiscal_dates to include most recent completed fiscal year
        # Even if financial statements aren't filed yet, we need price data for alignment
        # Example: In Q1 2026, Dec 31 FY-end stocks may have FY2024 financials but we need 2025-12-31 price
        if fiscal_dates:
            from datetime import datetime, timedelta
            from dateutil.relativedelta import relativedelta

            # Determine the fiscal year-end month/day from the most recent fiscal date
            latest_fiscal = fiscal_dates[0]  # e.g., "2024-12-31"
            latest_date = datetime.strptime(latest_fiscal, "%Y-%m-%d")
            latest_year = latest_date.year

            # Calculate what the next fiscal year-end date would be
            next_fy_end = latest_date + relativedelta(years=1)

            # Only add it if it's in the past (completed fiscal year)
            today = datetime.now()
            if next_fy_end < today:
                next_fiscal_str = next_fy_end.strftime("%Y-%m-%d")
                if next_fiscal_str not in fiscal_dates:
                    fiscal_dates.insert(0, next_fiscal_str)  # Add to front (most recent)
                    logger.info(
                        f"{symbol}: Extended fiscal dates to include {next_fiscal_str} "
                        f"(FY{next_fy_end.year} ended but financials not yet available)"
                    )

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

        financial_data = FinancialData(
            symbol=symbol,
            revenues=revenues,
            net_incomes=net_incomes,
            operating_incomes=operating_incomes,
            operating_cash_flows=operating_cash_flows,
            total_debt=total_debt,
            total_equity=total_equity
        )

        # Return both financial data and fiscal dates (to avoid duplicate API call)
        return financial_data, fiscal_dates

    def get_stock_market_data(self, symbol: str, fiscal_dates: Optional[List[str]] = None) -> MarketData:
        """
        שליפת נתוני שוק למניה

        2 API calls: quote (current price) + statistics (market cap, P/E)
        + N API calls for price history (1 per fiscal date)

        Args:
            symbol: סימול המניה
            fiscal_dates: רשימת תאריכי fiscal (אופציונלי - אם לא מסופק, יבצע שאילתה נוספת)

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

        # Fetch price for each fiscal year end date
        price_history = {}
        try:
            # Use provided fiscal_dates if available (saves 1 API call!)
            if fiscal_dates is None:
                # Check if we have cached fiscal dates from a recent get_stock_financials() call
                fiscal_dates = self._last_fiscal_dates.get(symbol)

            if fiscal_dates is None:
                # Fallback: Get fiscal dates from income statements (1 additional API call)
                income_params = {"symbol": clean_sym, "period": "annual"}
                if exchange:
                    income_params["exchange"] = exchange

                income_data = self._api_request("/income_statement", income_params)
                statements = income_data.get("income_statement", [])

                # Extract fiscal dates from statements (up to 5 years)
                fiscal_dates = []
                for stmt in statements[:5]:
                    fiscal_date = stmt.get("fiscal_date", "")
                    if fiscal_date:
                        fiscal_dates.append(fiscal_date)

                logger.debug(f"Found {len(fiscal_dates)} fiscal dates for {symbol} via API: {fiscal_dates}")
            else:
                logger.debug(f"Using cached/provided fiscal dates for {symbol}: {fiscal_dates}")

            # Fetch EOD price for each fiscal date
            # If a date falls on a weekend/holiday, try nearby business days
            from datetime import datetime as _dt, timedelta as _td
            for fiscal_date in fiscal_dates:
                fetched = False
                # Try the fiscal date itself, then up to 3 previous days (to handle weekends/holidays)
                for day_offset in range(0, 4):
                    try:
                        attempt_date = (_dt.strptime(fiscal_date, "%Y-%m-%d") - _td(days=day_offset)).strftime("%Y-%m-%d")
                        eod_params = {
                            "symbol": clean_sym,
                            "date": attempt_date
                        }
                        if exchange:
                            eod_params["exchange"] = exchange

                        eod_data = self._api_request("/eod", eod_params)
                        close_val = eod_data.get("close")

                        if close_val is not None:
                            raw = float(close_val)
                            price_history[fiscal_date] = raw / ILA_TO_ILS if is_tase else raw
                            if day_offset > 0:
                                logger.debug(f"Fetched price for {symbol} on {attempt_date} (fallback from {fiscal_date}): {price_history[fiscal_date]}")
                            else:
                                logger.debug(f"Fetched price for {symbol} on {fiscal_date}: {price_history[fiscal_date]}")
                            fetched = True
                            break
                    except RuntimeError as e:
                        if day_offset < 3:
                            logger.debug(f"No data for {symbol} on {attempt_date}, trying previous day...")
                            continue
                        else:
                            logger.warning(f"Failed to fetch price for {symbol} near {fiscal_date} after {day_offset+1} attempts: {e}")

                if not fetched:
                    logger.warning(f"Could not fetch price for {symbol} near {fiscal_date}")

        except Exception as e:
            logger.warning(f"Failed to fetch price history for {symbol}: {e}")

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
