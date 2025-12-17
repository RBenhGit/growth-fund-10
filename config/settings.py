"""
הגדרות קונפיגורציה למערכת בניית קרן צמיחה 10
קריאת הגדרות מקובץ .env
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

# טעינת משתני סביבה מ-.env
# override=True מבטיח שערכים מ-.env ידרסו משתני סביבה קיימים
load_dotenv(override=True)


class Settings:
    """מחלקת הגדרות המערכת"""

    # נתיבים
    BASE_DIR = Path(__file__).parent.parent
    OUTPUT_DIR = BASE_DIR / os.getenv("OUTPUT_DIRECTORY", "./Fund_Docs")
    CACHE_DIR = BASE_DIR / "cache"

    # מקורות נתונים
    # מקור לנתונים פיננסיים (דוחות כספיים, fundamentals)
    FINANCIAL_DATA_SOURCE = os.getenv("FINANCIAL_DATA_SOURCE", "eodhd")
    # מקור למחירים היסטוריים
    PRICING_DATA_SOURCE = os.getenv("PRICING_DATA_SOURCE", "yfinance")

    # Legacy: תמיכה לאחור - אם DATA_SOURCE מוגדר, השתמש בו לשני המקורות
    if os.getenv("DATA_SOURCE"):
        FINANCIAL_DATA_SOURCE = os.getenv("DATA_SOURCE")
        PRICING_DATA_SOURCE = os.getenv("DATA_SOURCE")

    # Investing.com credentials
    INVESTING_EMAIL = os.getenv("INVESTING_EMAIL")
    INVESTING_PASSWORD = os.getenv("INVESTING_PASSWORD")

    # EOD Historical Data API
    EODHD_API_KEY = os.getenv("EODHD_API_KEY")

    # Alpha Vantage API
    ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")

    # Financial Modeling Prep API
    FMP_API_KEY = os.getenv("FMP_API_KEY")

    # הגדרות קרן
    FUND_QUARTER: Optional[str] = os.getenv("FUND_QUARTER") or None
    FUND_YEAR: Optional[int] = int(os.getenv("FUND_YEAR")) if os.getenv("FUND_YEAR") else None
    FUND_DATE: Optional[str] = os.getenv("FUND_DATE") or None

    # הגדרות כלליות
    USE_CACHE = os.getenv("USE_CACHE", "true").lower() == "true"
    DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"

    # משקלות קרן (קבועים) - 10 מניות: 6 בסיס + 4 פוטנציאל
    FUND_WEIGHTS = [0.18, 0.16, 0.16, 0.10, 0.10, 0.10, 0.06, 0.06, 0.04, 0.04]

    # משקלות לחישוב ציון בסיס
    BASE_SCORE_WEIGHTS = {
        "net_income_growth": 0.40,
        "revenue_growth": 0.35,
        "market_cap": 0.25
    }

    # משקלות לחישוב ציון פוטנציאל
    POTENTIAL_SCORE_WEIGHTS = {
        "future_growth": 0.50,
        "momentum": 0.30,
        "valuation": 0.20
    }

    # קריטריוני סינון מניות בסיס
    BASE_ELIGIBILITY = {
        "min_profitable_years": 5,
        "min_operating_profit_years": 4,
        "max_debt_to_equity": 0.60
    }

    # קריטריוני סינון מניות פוטנציאל
    POTENTIAL_ELIGIBILITY = {
        "min_profitable_years": 2
    }

    @classmethod
    def validate(cls) -> bool:
        """
        בדיקת תקינות הגדרות
        Returns:
            bool: True אם ההגדרות תקינות
        """
        # בדיקת מקור נתונים פיננסיים
        if cls.FINANCIAL_DATA_SOURCE == "eodhd":
            if not cls.EODHD_API_KEY:
                raise ValueError(
                    "EODHD_API_KEY must be set in .env when using EODHD for financial data"
                )

        if cls.FINANCIAL_DATA_SOURCE == "fmp":
            if not cls.FMP_API_KEY:
                raise ValueError(
                    "FMP_API_KEY must be set in .env when using FMP for financial data"
                )

        if cls.FINANCIAL_DATA_SOURCE == "investing":
            if not cls.INVESTING_EMAIL or not cls.INVESTING_PASSWORD:
                raise ValueError(
                    "INVESTING_EMAIL and INVESTING_PASSWORD must be set in .env when using Investing.com"
                )

        if cls.FINANCIAL_DATA_SOURCE == "alphavantage":
            if not cls.ALPHAVANTAGE_API_KEY:
                raise ValueError(
                    "ALPHAVANTAGE_API_KEY must be set in .env when using Alpha Vantage"
                )

        # בדיקת מקור מחירים
        # yfinance לא דורש API key, אבל מקורות אחרים כן
        if cls.PRICING_DATA_SOURCE == "eodhd":
            if not cls.EODHD_API_KEY:
                raise ValueError(
                    "EODHD_API_KEY must be set in .env when using EODHD for pricing"
                )

        if cls.PRICING_DATA_SOURCE == "alphavantage":
            if not cls.ALPHAVANTAGE_API_KEY:
                raise ValueError(
                    "ALPHAVANTAGE_API_KEY must be set in .env when using Alpha Vantage for pricing"
                )

        # יצירת תיקיות אם לא קיימות
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        cls.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        (cls.CACHE_DIR / "stocks_data").mkdir(exist_ok=True)
        (cls.CACHE_DIR / "index_constituents").mkdir(exist_ok=True)

        return True


# יצירת instance יחיד
settings = Settings()
