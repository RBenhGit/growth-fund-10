"""
Data Source Router - Advanced Version with Dual-Source Support
ניתוב חכם למקורות נתונים נפרדים למידע פיננסי ומחירים
"""

import logging
from typing import Dict, Optional
from .base_data_source import BaseDataSource
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
        # Cache created instances so the same source object is reused.
        # This is critical for TwelveDataSource: when both financial and pricing
        # sources are "twelvedata", reusing the same instance ensures:
        # 1. financial_source == pricing_source → True → unified call path is used
        # 2. Credit tracking is shared (single _credits_used_this_minute counter)
        # 3. Rate limiting works correctly across both data types
        self._instance_cache: Dict[str, BaseDataSource] = {}

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
               - SP500: TwelveData → Alpha Vantage
               - TASE125: TwelveData
        """
        if index_name == "SP500":
            source_name = settings.US_FINANCIAL_DATA_SOURCE
            default_chain = ["twelvedata", "alphavantage"]
        elif index_name == "TASE125":
            source_name = settings.TASE_FINANCIAL_DATA_SOURCE
            default_chain = ["twelvedata"]
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
               - SP500: yfinance (חינמי!) → TwelveData → Alpha Vantage
               - TASE125: yfinance (חינמי!) → TwelveData
        """
        if index_name == "SP500":
            source_name = settings.US_PRICING_DATA_SOURCE
            default_chain = ["yfinance", "twelvedata", "alphavantage"]
        elif index_name == "TASE125":
            source_name = settings.TASE_PRICING_DATA_SOURCE
            default_chain = ["yfinance", "twelvedata"]
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
            "alphavantage": settings.ALPHAVANTAGE_API_KEY,

            "twelvedata": settings.TWELVEDATA_API_KEY,
            "yfinance": True  # No API key needed
        }
        return bool(api_key_map.get(source_name))

    def _create_source(self, source_name: str) -> BaseDataSource:
        """
        Factory method to create (or reuse) data source instance

        Returns cached instance if one already exists for this source_name.
        This is critical for TwelveDataSource so that financial and pricing
        calls share the same credit counter and rate limiter.

        Args:
            source_name: שם המקור (alphavantage, twelvedata, yfinance)

        Returns:
            BaseDataSource: instance מוכן לשימוש

        Raises:
            ValueError: אם שם המקור לא מוכר
        """
        # Return cached instance if available
        if source_name in self._instance_cache:
            self.logger.debug(f"Reusing cached {source_name} instance")
            return self._instance_cache[source_name]

        source_map = {
            "alphavantage": AlphaVantageSource,
            "twelvedata": TwelveDataSource,
            "yfinance": YFinanceSource
        }

        source_class = source_map.get(source_name)
        if not source_class:
            raise ValueError(f"Unknown data source: {source_name} / מקור נתונים לא מוכר")

        instance = source_class()
        self._instance_cache[source_name] = instance
        return instance

    def _create_yfinance_source(self) -> BaseDataSource:
        """
        Create (or reuse) a yfinance wrapper source

        יצירת instance של yfinance

        Returns:
            YFinanceSource: מקור נתונים חינמי למחירים
        """
        return self._create_source("yfinance")

