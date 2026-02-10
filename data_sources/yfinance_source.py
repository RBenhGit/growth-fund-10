"""
YFinance Data Source - Free pricing data from Yahoo Finance
"""

import yfinance as yf
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from models import FinancialData, MarketData
from data_sources.base_data_source import BaseDataSource
import logging

logger = logging.getLogger(__name__)


class YFinanceSource(BaseDataSource):
    """
    Lightweight wrapper for yfinance (Yahoo Finance).
    Best used for PRICING DATA ONLY - doesn't provide detailed fundamentals.

    יתרונות:
    - חינמי - ללא הגבלת קריאות
    - מהימן - ממשק Yahoo Finance רשמי
    - כיסוי גלובלי - תומך במניות ישראליות ואמריקאיות

    חסרונות:
    - לא מספק נתונים פיננסיים היסטוריים מפורטים
    - לא מתאים לבניית קרן (השתמש ב-TwelveData או Alpha Vantage למידע פיננסי)
    """

    def __init__(self):
        self.name = "yfinance"

    def login(self) -> bool:
        """No authentication needed for yfinance"""
        try:
            # Test with a simple ticker
            test = yf.Ticker("AAPL")
            info = test.info  # Force a request
            if info:
                logger.info("yfinance connection test successful")
                return True
            return False
        except Exception as e:
            logger.error(f"yfinance test failed: {e}")
            return False

    def logout(self):
        """No logout needed for yfinance"""
        pass

    def get_index_constituents(self, index_name: str) -> List[Dict]:
        """
        yfinance doesn't provide index constituent lists.
        Raise error - use a different source for constituents.

        Args:
            index_name: שם המדד (TASE125/SP500)

        Raises:
            NotImplementedError: yfinance לא תומך ברשימות רכיבי מדד
        """
        raise NotImplementedError(
            f"yfinance doesn't provide index constituents for {index_name}. "
            "Please use twelvedata or alphavantage for constituent lists."
        )

    def get_stock_financials(self, symbol: str, years: int = 5) -> FinancialData:
        """
        שליפת נתונים פיננסיים - מוגבל!

        yfinance מספק נתונים פיננסיים בסיסיים אבל לא מפורטים מספיק לבניית קרן.
        השתמש ב-TwelveData או Alpha Vantage למידע פיננסי מקיף.

        Args:
            symbol: סימול המניה
            years: מספר שנים (לא בשימוש - yfinance לא מספק היסטוריה)

        Returns:
            FinancialData: נתונים פיננסיים בסיסיים בלבד
        """
        logger.warning(
            f"yfinance provides limited financial data for {symbol}. "
            "Consider using twelvedata or alphavantage for comprehensive fundamentals."
        )

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            # yfinance provides very limited historical fundamentals
            # Return minimal FinancialData - NOT recommended for fund building
            return FinancialData(
                symbol=symbol,
                revenues={},  # yfinance doesn't provide historical revenue easily
                net_incomes={},  # yfinance doesn't provide historical net income easily
                operating_incomes={},
                operating_cash_flows={},
                total_debt=info.get("totalDebt"),
                total_equity=info.get("totalStockholdersEquity"),
                market_cap=info.get("marketCap"),
                current_price=info.get("currentPrice") or info.get("regularMarketPrice"),
                pe_ratio=info.get("trailingPE")
            )
        except Exception as e:
            logger.error(f"Error fetching financial data for {symbol} from yfinance: {e}")
            # Return empty FinancialData
            return FinancialData(
                symbol=symbol,
                revenues={},
                net_incomes={},
                operating_incomes={},
                operating_cash_flows={},
                total_debt=None,
                total_equity=None,
                market_cap=None,
                current_price=None,
                pe_ratio=None
            )

    def get_stock_market_data(self, symbol: str, fiscal_dates: Optional[List[str]] = None) -> MarketData:
        """
        שליפת נתוני שוק - מחירי סגירה לתאריכי fiscal בלבד

        שולף מחיר נוכחי + מחיר סגירה לכל תאריך fiscal year-end.
        התוצאה: ~6 נקודות מחיר בדידות (לא היסטוריה רציפה).

        Args:
            symbol: סימול המניה
            fiscal_dates: רשימת תאריכי סוף שנת כספים (e.g., ['2025-11-30', '2024-12-31'])
                         כאשר לא מסופק, נופל חזרה לשליפה גנרית

        Returns:
            MarketData: נתוני שוק עם מחירי סגירה לתאריכי fiscal + מחיר נוכחי
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            current_price = float(info.get("currentPrice") or info.get("regularMarketPrice", 0)) if (info.get("currentPrice") or info.get("regularMarketPrice")) else 0
            market_cap = float(info.get("marketCap", 0)) if info.get("marketCap") else 0
            pe_ratio = float(info.get("trailingPE")) if info.get("trailingPE") else None
            stock_name = info.get("longName", symbol)

            price_history = {}

            # Fetch close price for each fiscal date
            if fiscal_dates:
                for fiscal_date in fiscal_dates:
                    price = self._get_price_for_date(ticker, fiscal_date)
                    if price is not None:
                        price_history[fiscal_date] = price
                    else:
                        logger.warning(f"Could not fetch price for {symbol} near {fiscal_date}")

            return MarketData(
                symbol=symbol,
                name=stock_name,
                market_cap=market_cap,
                current_price=current_price,
                pe_ratio=pe_ratio,
                price_history=price_history
            )
        except Exception as e:
            logger.error(f"Error fetching market data for {symbol} from yfinance: {e}")
            return MarketData(
                symbol=symbol,
                name=symbol,
                market_cap=0,
                current_price=0,
                pe_ratio=None,
                price_history={}
            )

    def _get_price_for_date(self, ticker, target_date_str: str) -> Optional[float]:
        """
        שליפת מחיר סגירה לתאריך ספציפי, עם fallback לימי עסקים קרובים

        אם התאריך נופל על סוף שבוע/חג, מנסה עד 4 ימים אחורה.

        Args:
            ticker: אובייקט yfinance Ticker
            target_date_str: תאריך יעד בפורמט YYYY-MM-DD

        Returns:
            Optional[float]: מחיר סגירה, או None אם לא נמצא
        """
        try:
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d")

            # Fetch a 7-day window ending after the target date to handle weekends/holidays
            start = target_date - timedelta(days=5)
            end = target_date + timedelta(days=2)
            hist = ticker.history(start=start, end=end)

            if hist.empty:
                logger.debug(f"No price data for {ticker.ticker} in window around {target_date_str}")
                return None

            # Find the closest trading day on or before the target date
            for day_offset in range(0, 5):
                check_date = target_date - timedelta(days=day_offset)
                check_str = check_date.strftime("%Y-%m-%d")
                for idx_date, row in hist.iterrows():
                    if str(idx_date.date()) == check_str:
                        price = float(row['Close'])
                        if day_offset > 0:
                            logger.debug(f"Price for {ticker.ticker} on {check_str} (fallback from {target_date_str}): {price}")
                        return price

            # If no exact match found, take the last available price before target
            hist_before_target = hist[hist.index.date <= target_date.date()]
            if not hist_before_target.empty:
                last_row = hist_before_target.iloc[-1]
                return float(last_row['Close'])

            return None
        except Exception as e:
            logger.debug(f"Error fetching price for {ticker.ticker} on {target_date_str}: {e}")
            return None

    def get_stock_data(self, symbol: str, years: int = 5) -> tuple[FinancialData, MarketData]:
        """
        שליפת כל נתוני המניה - מתודה מאוחדת

        אזהרה: yfinance מתאים רק לנתוני מחירים!
        שקול להשתמש במקורות נפרדים:
        - מקור פיננסי: TwelveData/Alpha Vantage
        - מקור מחירים: yfinance (חינמי!)

        Args:
            symbol: סימול המניה
            years: מספר שנים לשלוף

        Returns:
            tuple[FinancialData, MarketData]: נתונים פיננסיים (מוגבלים!) ונתוני שוק
        """
        financial_data = self.get_stock_financials(symbol, years)
        market_data = self.get_stock_market_data(symbol)
        return financial_data, market_data

    def get_index_pe_ratio(self, index_name: str) -> Optional[float]:
        """
        שליפת P/E ממוצע של המדד

        yfinance לא מספק נתוני P/E ברמת המדד.

        Args:
            index_name: שם המדד

        Returns:
            None: תמיד מחזיר None - לא זמין
        """
        logger.warning(f"yfinance doesn't provide P/E for {index_name}")
        return None
