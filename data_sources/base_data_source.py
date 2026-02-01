"""
Abstract Base Class למקורות נתונים
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from models import FinancialData, MarketData, Stock


class BaseDataSource(ABC):
    """מחלקת בסיס למקורות נתונים"""

    @abstractmethod
    def login(self) -> bool:
        """
        התחברות למקור הנתונים

        Returns:
            bool: True אם ההתחברות הצליחה
        """
        pass

    @abstractmethod
    def logout(self):
        """ניתוק מהמקור"""
        pass

    @abstractmethod
    def get_index_constituents(self, index_name: str) -> List[Dict]:
        """
        שליפת רשימת רכיבי מדד

        Args:
            index_name: שם המדד (TASE125/SP500)

        Returns:
            List[Dict]: רשימת מניות עם פרטים בסיסיים
        """
        pass

    @abstractmethod
    def get_stock_financials(self, symbol: str, years: int = 5) -> FinancialData:
        """
        שליפת נתונים פיננסיים למניה

        Args:
            symbol: סימול המניה
            years: מספר שנים לשלוף

        Returns:
            FinancialData: נתונים פיננסיים
        """
        pass

    @abstractmethod
    def get_stock_market_data(self, symbol: str) -> MarketData:
        """
        שליפת נתוני שוק למניה

        Args:
            symbol: סימול המניה

        Returns:
            MarketData: נתוני שוק
        """
        pass

    @abstractmethod
    def get_index_pe_ratio(self, index_name: str) -> Optional[float]:
        """
        שליפת P/E ממוצע של המדד

        Args:
            index_name: שם המדד

        Returns:
            Optional[float]: P/E ממוצע או None
        """
        pass

    @abstractmethod
    def get_stock_data(self, symbol: str, years: int = 5) -> tuple['FinancialData', 'MarketData']:
        """
        שליפת כל נתוני המניה - פיננסיים ושוק

        מתודה מאוחדת המחזירה גם נתונים פיננסיים וגם נתוני שוק בקריאה אחת.
        מקורות נתונים יכולים למטב על ידי ביצוע שתי הקריאות במקביל.

        Args:
            symbol: סימול המניה (עם סיומת בורסה, למשל AAPL.US)
            years: מספר שנים של נתונים פיננסיים לשלוף

        Returns:
            tuple[FinancialData, MarketData]: נתונים פיננסיים ונתוני שוק

        Note:
            מתודה זו חובה לכל מקור נתונים. ניתן ליישם אותה פשוט על ידי
            קריאה ל-get_stock_financials() ו-get_stock_market_data().
        """
        pass
