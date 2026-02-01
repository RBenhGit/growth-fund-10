"""
Data Source Router - Advanced Version with Dual-Source Support
ניתוב חכם למקורות נתונים נפרדים למידע פיננסי ומחירים
"""

import logging
from typing import Optional
from .base_data_source import BaseDataSource
from .eodhd_api import EODHDDataSource
from .fmp_api import FMPDataSource
from .tase_data_hub_api import TASEDataHubSource
from .alphavantage_api import AlphaVantageSource
from .twelvedata_api import TwelveDataSource
from .yfinance_source import YFinanceSource
from config import settings

logger = logging.getLogger(__name__)


class DataSourceRouter:
    """
    Router for selecting appropriate data sources based on index and data type.
    Supports separate sources for financial data vs pricing data.

    ניתוב חכם למקורות נתונים עם תמיכה במקורות נפרדים:
    - מקור למידע פיננסי (דוחות כספיים, fundamentals)
    - מקור למחירים (נתוני שוק, מחירים היסטוריים)
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def get_financial_source(self, index_name: str) -> BaseDataSource:
        """
        Get data source for financial/fundamental data (income statements, balance sheets, etc.)

        קבלת מקור נתונים למידע פיננסי

        Args:
            index_name: Index name (TASE125 or SP500)

        Returns:
            BaseDataSource instance configured for financial data

        Logic:
            1. אם מקור מוגדר במפורש (US_FINANCIAL_DATA_SOURCE/TASE_FINANCIAL_DATA_SOURCE) → השתמש בו
            2. אחרת, בחירה אוטומטית מרשימת מקורות מומלצים:
               - SP500: FMP → Alpha Vantage → EODHD
               - TASE125: TASE Data Hub → EODHD
        """
        if index_name == "SP500":
            source_name = settings.US_FINANCIAL_DATA_SOURCE
            default_chain = ["fmp", "alphavantage", "eodhd"]
        elif index_name == "TASE125":
            source_name = settings.TASE_FINANCIAL_DATA_SOURCE
            default_chain = ["tase_data_hub", "eodhd"]
        else:
            raise ValueError(f"Unsupported index: {index_name}")

        # Explicit configuration wins
        if source_name:
            self.logger.info(f"שימוש במקור פיננסי מוגדר עבור {index_name}: {source_name}")
            return self._create_source(source_name)

        # Auto-select from chain
        self.logger.info(f"בחירה אוטומטית של מקור פיננסי עבור {index_name}")
        for source in default_chain:
            if self._validate_source_availability(source):
                self.logger.info(f"נבחר מקור פיננסי: {source}")
                return self._create_source(source)

        raise ValueError(
            f"No financial data source available for {index_name}.\n"
            f"Please configure one of: {', '.join(default_chain)}\n"
            f"אין מקור נתונים פיננסיים זמין עבור {index_name}"
        )

    def get_pricing_source(self, index_name: str) -> BaseDataSource:
        """
        Get data source for pricing/market data (stock prices, market cap, etc.)

        קבלת מקור נתונים למחירים ונתוני שוק

        Args:
            index_name: Index name (TASE125 or SP500)

        Returns:
            BaseDataSource instance configured for pricing data

        Logic:
            1. אם מקור מוגדר במפורש (US_PRICING_DATA_SOURCE/TASE_PRICING_DATA_SOURCE) → השתמש בו
            2. אחרת, בחירה אוטומטית מרשימת מקורות מומלצים:
               - SP500: yfinance (חינמי!) → EODHD → Alpha Vantage
               - TASE125: yfinance (חינמי!) → EODHD
        """
        if index_name == "SP500":
            source_name = settings.US_PRICING_DATA_SOURCE
            default_chain = ["yfinance", "eodhd", "alphavantage"]
        elif index_name == "TASE125":
            source_name = settings.TASE_PRICING_DATA_SOURCE
            default_chain = ["yfinance", "eodhd"]
        else:
            raise ValueError(f"Unsupported index: {index_name}")

        # yfinance is special - doesn't need API key
        if source_name == "yfinance":
            self.logger.info(f"שימוש ב-yfinance למחירי {index_name} (חינמי)")
            return self._create_yfinance_source()

        # Explicit configuration
        if source_name:
            self.logger.info(f"שימוש במקור מחירים מוגדר עבור {index_name}: {source_name}")
            return self._create_source(source_name)

        # Auto-select from chain
        self.logger.info(f"בחירה אוטומטית של מקור מחירים עבור {index_name}")
        for source in default_chain:
            if source == "yfinance":
                self.logger.info(f"נבחר מקור מחירים: yfinance (חינמי)")
                return self._create_yfinance_source()
            elif self._validate_source_availability(source):
                self.logger.info(f"נבחר מקור מחירים: {source}")
                return self._create_source(source)

        raise ValueError(
            f"No pricing data source available for {index_name}.\n"
            f"Please configure one of: {', '.join(default_chain)}\n"
            f"אין מקור נתוני מחירים זמין עבור {index_name}"
        )

    def get_data_source(self, index_name: str) -> BaseDataSource:
        """
        Legacy method - returns financial data source.
        Use get_financial_source() and get_pricing_source() instead.

        מתודה מיושנת - מחזירה מקור נתונים פיננסיים.
        עדיף להשתמש ב-get_financial_source() ו-get_pricing_source().

        Args:
            index_name: שם המדד

        Returns:
            BaseDataSource: מקור נתונים פיננסיים
        """
        self.logger.warning(
            "get_data_source() is deprecated. "
            "Use get_financial_source() and get_pricing_source() instead."
        )
        return self.get_financial_source(index_name)

    def _validate_source_availability(self, source_name: str) -> bool:
        """
        Check if a data source has required API keys configured

        בדיקה האם למקור נתונים יש מפתח API מוגדר

        Args:
            source_name: שם המקור

        Returns:
            bool: True אם המקור זמין לשימוש
        """
        api_key_map = {
            "eodhd": settings.EODHD_API_KEY,
            "fmp": settings.FMP_API_KEY,
            "tase_data_hub": settings.TASE_DATA_HUB_API_KEY,
            "alphavantage": settings.ALPHAVANTAGE_API_KEY,
            "investing": settings.INVESTING_EMAIL and settings.INVESTING_PASSWORD,
            "twelvedata": settings.TWELVEDATA_API_KEY,
            "yfinance": True  # No API key needed
        }
        return bool(api_key_map.get(source_name))

    def _create_source(self, source_name: str) -> BaseDataSource:
        """
        Factory method to create data source instance

        יצירת instance של מקור נתונים

        Args:
            source_name: שם המקור (eodhd, fmp, tase_data_hub, alphavantage, investing)

        Returns:
            BaseDataSource: instance מוכן לשימוש

        Raises:
            ValueError: אם שם המקור לא מוכר
        """
        source_map = {
            "eodhd": EODHDDataSource,
            "fmp": FMPDataSource,
            "tase_data_hub": TASEDataHubSource,
            "alphavantage": AlphaVantageSource,
            "twelvedata": TwelveDataSource,
            "yfinance": YFinanceSource
        }

        source_class = source_map.get(source_name)
        if not source_class:
            raise ValueError(f"Unknown data source: {source_name} / מקור נתונים לא מוכר")

        return source_class()

    def _create_yfinance_source(self) -> BaseDataSource:
        """
        Create a yfinance wrapper source

        יצירת instance של yfinance

        Returns:
            YFinanceSource: מקור נתונים חינמי למחירים
        """
        return YFinanceSource()

    # ====================================================================
    # Legacy methods for backwards compatibility
    # מתודות ישנות לתמיכה לאחור
    # ====================================================================

    def _route_tase125(self) -> BaseDataSource:
        """
        Legacy: ניתוב למקור נתונים עבור TASE125
        Use get_financial_source("TASE125") instead
        """
        return self.get_financial_source("TASE125")

    def _route_sp500(self) -> BaseDataSource:
        """
        Legacy: ניתוב למקור נתונים עבור SP500
        Use get_financial_source("SP500") instead
        """
        return self.get_financial_source("SP500")

    def _get_explicit_source(self, source_name: str) -> BaseDataSource:
        """
        Legacy: קבלת מקור נתונים לפי שם
        Use _create_source() instead
        """
        return self._create_source(source_name)
