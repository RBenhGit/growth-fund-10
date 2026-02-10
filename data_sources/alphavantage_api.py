"""
Alpha Vantage API Data Source
מקור נתונים מבוסס על Alpha Vantage API - תומך רק במניות אמריקאיות
"""

import requests
import time
import logging
import yfinance as yf
from typing import List, Dict, Optional
from datetime import datetime
from collections import deque
from models import FinancialData, MarketData
from .base_data_source import BaseDataSource
from config import settings

logger = logging.getLogger(__name__)


class AlphaVantageSource(BaseDataSource):
    """מקור נתונים מבוסס Alpha Vantage API - US stocks only"""

    def __init__(self, api_key: Optional[str] = None, rate_limit: Optional[str] = None):
        """
        אתחול מקור נתונים Alpha Vantage

        Args:
            api_key: מפתח API (אם לא צוין - ייקח מהגדרות)
            rate_limit: דרגת rate limit - "paid" או "free" (אם לא צוין - ייקח מהגדרות)
        """
        self.api_key = api_key or settings.ALPHAVANTAGE_API_KEY
        self.rate_limit = rate_limit or settings.ALPHAVANTAGE_RATE_LIMIT
        self.base_url = "https://www.alphavantage.co/query"

        if not self.api_key:
            raise ValueError("ALPHAVANTAGE_API_KEY חסר בהגדרות")

        # Track API requests for rate limiting
        self.request_times = deque(maxlen=100)

        # Rate limits
        if self.rate_limit == "paid":
            self.requests_per_minute = 75
        else:  # free
            self.requests_per_minute = 5

        logger.info(f"אתחול Alpha Vantage API (rate limit: {self.rate_limit} - {self.requests_per_minute} req/min)")

    def _enforce_rate_limit(self):
        """אכיפת rate limit - sleep אם צריך"""
        now = time.time()

        # Remove requests older than 60 seconds
        while self.request_times and (now - self.request_times[0]) > 60:
            self.request_times.popleft()

        # If we're at the limit, wait
        if len(self.request_times) >= self.requests_per_minute:
            sleep_time = 60 - (now - self.request_times[0])
            if sleep_time > 0:
                logger.debug(f"Rate limit reached, sleeping for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)
                # Clear old requests after sleeping
                self._enforce_rate_limit()
                return

        # Record this request
        self.request_times.append(time.time())

    def login(self) -> bool:
        """
        בדיקת תקינות החיבור ל-API

        Returns:
            bool: True אם החיבור תקין
        """
        try:
            # Test with OVERVIEW function for AAPL
            self._enforce_rate_limit()
            params = {
                "function": "OVERVIEW",
                "symbol": "AAPL",
                "apikey": self.api_key
            }
            response = requests.get(self.base_url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                # Check if we got valid data (not an error message)
                if "Symbol" in data:
                    logger.info("התחברות ל-Alpha Vantage הצליחה")
                    return True
                else:
                    logger.error(f"Alpha Vantage API returned error: {data}")
                    return False
            else:
                logger.error(f"התחברות ל-Alpha Vantage נכשלה: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"שגיאה בהתחברות ל-Alpha Vantage: {e}")
            return False

    def logout(self):
        """לא נדרש עבור Alpha Vantage API (stateless)"""
        pass

    def get_index_constituents(self, index_name: str) -> List[Dict]:
        """
        שליפת רשימת רכיבי מדד

        Args:
            index_name: שם המדד

        Returns:
            List[Dict]: רשימת מניות עם פרטים בסיסיים

        Note:
            Alpha Vantage לא מספק רשימת רכיבי מדד.
            השתמש ב-TwelveData במקום.
        """
        raise NotImplementedError(
            f"Alpha Vantage לא מספק רשימת רכיבי מדד עבור {index_name}. "
            "השתמש ב-TwelveData או yfinance"
        )

    def _parse_annual_reports(self, reports: list, field_name: str, years: int) -> Dict[int, float]:
        """
        חילוץ ערכים מ-annualReports

        Args:
            reports: רשימת דוחות שנתיים
            field_name: שם השדה לחלץ
            years: מספר שנים

        Returns:
            Dict[int, float]: מיפוי שנה -> ערך
        """
        result = {}

        for report in reports[:years]:
            try:
                fiscal_date = report.get("fiscalDateEnding", "")
                year = int(fiscal_date[:4])  # "2024-09-30" -> 2024

                value = report.get(field_name)
                if value and value != "None":
                    result[year] = float(value)
                elif field_name in ["operatingIncome", "ebitda"] and not value:
                    # Try alternative field
                    alt_value = report.get("ebitda" if field_name == "operatingIncome" else "operatingIncome")
                    if alt_value and alt_value != "None":
                        result[year] = float(alt_value)

            except (ValueError, TypeError, KeyError):
                continue

        return result

    def get_stock_financials(self, symbol: str, years: int = 5) -> FinancialData:
        """
        שליפת נתונים פיננסיים למניה

        Args:
            symbol: סימול המניה (ללא סיומת, למשל AAPL)
            years: מספר שנים לשלוף

        Returns:
            FinancialData: נתונים פיננסיים
        """
        try:
            # Clean symbol (remove .US suffix if present)
            clean_symbol = symbol.split('.')[0]

            # 1. Income Statement
            logger.debug(f"מושך Income Statement עבור {clean_symbol}")
            self._enforce_rate_limit()

            income_params = {
                "function": "INCOME_STATEMENT",
                "symbol": clean_symbol,
                "apikey": self.api_key
            }
            income_response = requests.get(self.base_url, params=income_params, timeout=30)
            income_response.raise_for_status()
            income_data = income_response.json()

            # 2. Balance Sheet
            logger.debug(f"מושך Balance Sheet עבור {clean_symbol}")
            self._enforce_rate_limit()

            balance_params = {
                "function": "BALANCE_SHEET",
                "symbol": clean_symbol,
                "apikey": self.api_key
            }
            balance_response = requests.get(self.base_url, params=balance_params, timeout=30)
            balance_response.raise_for_status()
            balance_data = balance_response.json()

            # 3. Cash Flow
            logger.debug(f"מושך Cash Flow עבור {clean_symbol}")
            self._enforce_rate_limit()

            cashflow_params = {
                "function": "CASH_FLOW",
                "symbol": clean_symbol,
                "apikey": self.api_key
            }
            cashflow_response = requests.get(self.base_url, params=cashflow_params, timeout=30)
            cashflow_response.raise_for_status()
            cashflow_data = cashflow_response.json()

            # Parse annual reports
            income_reports = income_data.get("annualReports", [])
            balance_reports = balance_data.get("annualReports", [])
            cashflow_reports = cashflow_data.get("annualReports", [])

            # Extract financial data
            revenues = self._parse_annual_reports(income_reports, "totalRevenue", years)
            net_incomes = self._parse_annual_reports(income_reports, "netIncome", years)
            operating_incomes = self._parse_annual_reports(income_reports, "operatingIncome", years)
            operating_cash_flows = self._parse_annual_reports(cashflow_reports, "operatingCashflow", years)

            # Extract latest balance sheet data
            total_debt = 0.0
            total_equity = 0.0

            if balance_reports:
                latest_balance = balance_reports[0]
                debt = latest_balance.get("totalLiabilities")
                if debt and debt != "None":
                    total_debt = float(debt)

                equity = latest_balance.get("totalShareholderEquity")
                if equity and equity != "None":
                    total_equity = float(equity)

            # Get market data from yfinance (free, no API limit)
            current_price = None
            market_cap = None
            pe_ratio = None

            try:
                ticker = yf.Ticker(clean_symbol)
                info = ticker.info
                current_price = info.get('currentPrice') or info.get('regularMarketPrice')
                market_cap = info.get('marketCap')
                pe_ratio = info.get('trailingPE') or info.get('forwardPE')

                if current_price:
                    current_price = float(current_price)
                if market_cap:
                    market_cap = float(market_cap)
                if pe_ratio:
                    pe_ratio = float(pe_ratio)
            except Exception as e:
                logger.warning(f"Failed to get market data from yfinance for {clean_symbol}: {e}")

            # Build FinancialData object
            financial_data = FinancialData(
                symbol=symbol,
                revenues=revenues,
                net_incomes=net_incomes,
                operating_incomes=operating_incomes,
                operating_cash_flows=operating_cash_flows,
                total_debt=total_debt,
                total_equity=total_equity,
                market_cap=market_cap,
                current_price=current_price,
                pe_ratio=pe_ratio
            )

            logger.info(f"נתונים פיננסיים נשלפו בהצלחה עבור {clean_symbol}")
            return financial_data

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"שגיאה בשליפת נתונים פיננסיים עבור {symbol}: {e}")
        except (KeyError, ValueError) as e:
            raise RuntimeError(f"שגיאה בעיבוד נתונים פיננסיים עבור {symbol}: {e}")

    def get_stock_market_data(self, symbol: str, fiscal_dates=None) -> MarketData:
        """
        שליפת נתוני שוק למניה

        Args:
            symbol: סימול המניה
            fiscal_dates: רשימת תאריכי fiscal (אופציונלי, לא בשימוש כרגע)

        Returns:
            MarketData: נתוני שוק
        """
        try:
            # Clean symbol
            clean_symbol = symbol.split('.')[0]

            # Get overview data from Alpha Vantage
            self._enforce_rate_limit()

            overview_params = {
                "function": "OVERVIEW",
                "symbol": clean_symbol,
                "apikey": self.api_key
            }
            response = requests.get(self.base_url, params=overview_params, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Extract data
            name = data.get("Name", clean_symbol)
            market_cap = data.get("MarketCapitalization")
            pe_ratio = data.get("PERatio")

            if market_cap and market_cap != "None":
                market_cap = float(market_cap)
            else:
                market_cap = 0.0

            if pe_ratio and pe_ratio != "None":
                pe_ratio = float(pe_ratio)
            else:
                pe_ratio = None

            # Get current price from yfinance (free)
            current_price = 0.0
            price_history = {}

            try:
                ticker = yf.Ticker(clean_symbol)
                info = ticker.info
                current_price = info.get('currentPrice') or info.get('regularMarketPrice')
                if current_price:
                    current_price = float(current_price)

            except Exception:
                pass

            # Build MarketData object
            market_data = MarketData(
                symbol=symbol,
                name=name,
                market_cap=market_cap,
                current_price=current_price,
                pe_ratio=pe_ratio,
                price_history=price_history
            )

            logger.info(f"נתוני שוק נשלפו עבור {clean_symbol}")
            return market_data

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"שגיאה בשליפת נתוני שוק עבור {symbol}: {e}")
        except (KeyError, ValueError) as e:
            raise RuntimeError(f"שגיאה בעיבוד נתוני שוק עבור {symbol}: {e}")

    def get_index_pe_ratio(self, index_name: str) -> Optional[float]:
        """
        שליפת P/E ממוצע של המדד

        Args:
            index_name: שם המדד

        Returns:
            Optional[float]: P/E ממוצע או None (לא זמין ב-Alpha Vantage)
        """
        # Alpha Vantage doesn't provide index-level P/E
        logger.warning("P/E ממוצע של המדד לא זמין ב-Alpha Vantage API")
        return None

    def get_stock_data(self, symbol: str, years: int = 5) -> tuple[FinancialData, MarketData]:
        """
        שליפת כל נתוני המניה - מתודה מאוחדת

        שימוש בהגבלת קצב (rate limiting) לשתי הקריאות.

        Args:
            symbol: סימול המניה
            years: מספר שנים לשלוף

        Returns:
            tuple[FinancialData, MarketData]: נתונים פיננסיים ונתוני שוק
        """
        financial_data = self.get_stock_financials(symbol, years)
        market_data = self.get_stock_market_data(symbol)
        return financial_data, market_data
