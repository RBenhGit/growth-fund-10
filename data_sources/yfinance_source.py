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
    - לא מתאים לבניית קרן (השתמש ב-FMP, EODHD, או TASE Data Hub למידע פיננסי)
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
            "Please use eodhd, fmp, or tase_data_hub for constituent lists."
        )

    def get_stock_financials(self, symbol: str, years: int = 5) -> FinancialData:
        """
        שליפת נתונים פיננסיים - מוגבל!

        yfinance מספק נתונים פיננסיים בסיסיים אבל לא מפורטים מספיק לבניית קרן.
        השתמש ב-FMP, EODHD, או TASE Data Hub למידע פיננסי מקיף.

        Args:
            symbol: סימול המניה
            years: מספר שנים (לא בשימוש - yfinance לא מספק היסטוריה)

        Returns:
            FinancialData: נתונים פיננסיים בסיסיים בלבד
        """
        logger.warning(
            f"yfinance provides limited financial data for {symbol}. "
            "Consider using fmp, eodhd, or tase_data_hub for comprehensive fundamentals."
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

    def get_stock_market_data(self, symbol: str) -> MarketData:
        """
        שליפת נתוני שוק - כאן yfinance מצטיין!

        זה השימוש המומלץ ב-yfinance - מחירים היסטוריים ונתוני שוק.

        Args:
            symbol: סימול המניה

        Returns:
            MarketData: נתוני שוק עם היסטוריית מחירים
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            # Get 1 year of historical prices (252 trading days)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)
            hist = ticker.history(start=start_date, end=end_date)

            # Convert to dict
            price_history = {
                date.date(): float(row['Close'])
                for date, row in hist.iterrows()
            }

            return MarketData(
                symbol=symbol,
                name=info.get("longName", symbol),
                market_cap=float(info.get("marketCap", 0)) if info.get("marketCap") else 0,
                current_price=float(info.get("currentPrice") or info.get("regularMarketPrice", 0)) if (info.get("currentPrice") or info.get("regularMarketPrice")) else 0,
                pe_ratio=float(info.get("trailingPE")) if info.get("trailingPE") else None,
                price_history=price_history
            )
        except Exception as e:
            logger.error(f"Error fetching market data for {symbol} from yfinance: {e}")
            # Return minimal MarketData
            return MarketData(
                symbol=symbol,
                name=symbol,
                market_cap=0,
                current_price=0,
                pe_ratio=None,
                price_history={}
            )

    def get_stock_data(self, symbol: str, years: int = 5) -> tuple[FinancialData, MarketData]:
        """
        שליפת כל נתוני המניה - מתודה מאוחדת

        אזהרה: yfinance מתאים רק לנתוני מחירים!
        שקול להשתמש במקורות נפרדים:
        - מקור פיננסי: FMP/EODHD/TASE Data Hub
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
