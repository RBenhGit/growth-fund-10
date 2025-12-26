"""
Data Source Router
ניתוב חכם למקור נתונים מתאים לפי מדד
"""

import logging
from typing import Optional
from .base_data_source import BaseDataSource
from .eodhd_api import EODHDDataSource
from .fmp_api import FMPDataSource
from .tase_data_hub_api import TASEDataHubSource
from .alphavantage_api import AlphaVantageSource
from config import settings

logger = logging.getLogger(__name__)


class DataSourceRouter:
    """ניתוב חכם למקורות נתונים לפי מדד"""

    def get_data_source(self, index_name: str) -> BaseDataSource:
        """
        בחירת מקור נתונים מתאים לפי מדד

        Args:
            index_name: שם המדד (TASE125 או SP500)

        Returns:
            BaseDataSource: מקור נתונים מוכן לשימוש

        Raises:
            ValueError: אם אין מקור נתונים זמין למדד

        Logic:
            1. אם FINANCIAL_DATA_SOURCE מוגדר במפורש ב-.env → השתמש בו
            2. אחרת, ניתוב אוטומטי:
               - TASE125 → TASE Data Hub (אם מוגדר) → EODHD (fallback)
               - SP500 → Alpha Vantage (אם מוגדר) → EODHD או FMP (fallback)
        """
        # Explicit configuration takes precedence
        if settings.FINANCIAL_DATA_SOURCE:
            source = self._get_explicit_source(settings.FINANCIAL_DATA_SOURCE)
            logger.info(f"שימוש במקור נתונים מפורש: {settings.FINANCIAL_DATA_SOURCE}")
            return source

        # Auto-routing based on index
        logger.info(f"ניתוב אוטומטי למקור נתונים עבור {index_name}")

        if index_name == "TASE125":
            return self._route_tase125()
        elif index_name == "SP500":
            return self._route_sp500()
        else:
            raise ValueError(f"מדד לא מוכר: {index_name}")

    def _route_tase125(self) -> BaseDataSource:
        """ניתוב למקור נתונים עבור TASE125"""

        # First choice: TASE Data Hub (official TASE API)
        if settings.TASE_DATA_HUB_API_KEY:
            logger.info("ניתוב TASE125 → TASE Data Hub (רשמי)")
            return TASEDataHubSource()

        # Fallback: EODHD (supports both TASE and US)
        if settings.EODHD_API_KEY:
            logger.info("ניתוב TASE125 → EODHD (fallback)")
            return EODHDDataSource()

        # No source available
        raise ValueError(
            "אין מקור נתונים זמין עבור TASE125. "
            "הגדר TASE_DATA_HUB_API_KEY או EODHD_API_KEY ב-.env"
        )

    def _route_sp500(self) -> BaseDataSource:
        """ניתוב למקור נתונים עבור SP500"""

        # First choice: Alpha Vantage (specialized for US stocks)
        if settings.ALPHAVANTAGE_API_KEY:
            logger.info("ניתוב SP500 → Alpha Vantage")
            return AlphaVantageSource()

        # Second choice: EODHD (universal)
        if settings.EODHD_API_KEY:
            logger.info("ניתוב SP500 → EODHD (fallback)")
            return EODHDDataSource()

        # Third choice: FMP (US only)
        if settings.FMP_API_KEY:
            logger.info("ניתוב SP500 → FMP (fallback)")
            return FMPDataSource()

        # No source available
        raise ValueError(
            "אין מקור נתונים זמין עבור SP500. "
            "הגדר ALPHAVANTAGE_API_KEY, EODHD_API_KEY או FMP_API_KEY ב-.env"
        )

    def _get_explicit_source(self, source_name: str) -> BaseDataSource:
        """
        קבלת מקור נתונים לפי שם

        Args:
            source_name: שם מקור הנתונים

        Returns:
            BaseDataSource: מקור נתונים

        Raises:
            ValueError: אם שם מקור הנתונים לא מוכר
        """
        if source_name == "eodhd":
            return EODHDDataSource()
        elif source_name == "fmp":
            return FMPDataSource()
        elif source_name == "tase_data_hub":
            return TASEDataHubSource()
        elif source_name == "alphavantage":
            return AlphaVantageSource()
        else:
            raise ValueError(f"מקור נתונים לא מוכר: {source_name}")
