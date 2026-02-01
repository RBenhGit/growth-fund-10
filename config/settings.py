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
    FINANCIAL_DATA_SOURCE = os.getenv("FINANCIAL_DATA_SOURCE", "twelvedata")
    # מקור למחירים היסטוריים
    PRICING_DATA_SOURCE = os.getenv("PRICING_DATA_SOURCE", "twelvedata")

    # ====================================================================
    # Advanced Data Source Configuration (2x2 Matrix)
    # ====================================================================
    # Configure SEPARATE data sources for:
    #   - US stocks (SP500) vs Israeli stocks (TASE125)
    #   - Financial data (fundamentals) vs Pricing data (market prices)

    # US Stocks (SP500) - Financial Data
    # Options: fmp, alphavantage, eodhd
    US_FINANCIAL_DATA_SOURCE = os.getenv("US_FINANCIAL_DATA_SOURCE", "")

    # US Stocks (SP500) - Pricing Data
    # Options: yfinance, eodhd, alphavantage
    US_PRICING_DATA_SOURCE = os.getenv("US_PRICING_DATA_SOURCE", "yfinance")

    # TASE Stocks (TA-125) - Financial Data
    # Options: tase_data_hub, eodhd, investing
    TASE_FINANCIAL_DATA_SOURCE = os.getenv("TASE_FINANCIAL_DATA_SOURCE", "")

    # TASE Stocks (TA-125) - Pricing Data
    # Options: yfinance, eodhd, investing
    TASE_PRICING_DATA_SOURCE = os.getenv("TASE_PRICING_DATA_SOURCE", "yfinance")

    # ====================================================================
    # Fallback to Legacy Configuration (Backwards Compatibility)
    # ====================================================================

    # If old FINANCIAL_DATA_SOURCE is set, use it for both markets
    if os.getenv("FINANCIAL_DATA_SOURCE"):
        legacy_source = os.getenv("FINANCIAL_DATA_SOURCE")
        US_FINANCIAL_DATA_SOURCE = US_FINANCIAL_DATA_SOURCE or legacy_source
        TASE_FINANCIAL_DATA_SOURCE = TASE_FINANCIAL_DATA_SOURCE or legacy_source

    # If old PRICING_DATA_SOURCE is set, use it for both markets
    if os.getenv("PRICING_DATA_SOURCE"):
        legacy_pricing = os.getenv("PRICING_DATA_SOURCE")
        US_PRICING_DATA_SOURCE = US_PRICING_DATA_SOURCE or legacy_pricing
        TASE_PRICING_DATA_SOURCE = TASE_PRICING_DATA_SOURCE or legacy_pricing

    # Even older legacy: DATA_SOURCE for everything
    if os.getenv("DATA_SOURCE"):
        legacy_all = os.getenv("DATA_SOURCE")
        US_FINANCIAL_DATA_SOURCE = US_FINANCIAL_DATA_SOURCE or legacy_all
        US_PRICING_DATA_SOURCE = US_PRICING_DATA_SOURCE or legacy_all
        TASE_FINANCIAL_DATA_SOURCE = TASE_FINANCIAL_DATA_SOURCE or legacy_all
        TASE_PRICING_DATA_SOURCE = TASE_PRICING_DATA_SOURCE or legacy_all

    # Keep legacy variables for backwards compatibility
    FINANCIAL_DATA_SOURCE = US_FINANCIAL_DATA_SOURCE or TASE_FINANCIAL_DATA_SOURCE or "eodhd"
    PRICING_DATA_SOURCE = US_PRICING_DATA_SOURCE or "yfinance"

    # Investing.com credentials
    INVESTING_EMAIL = os.getenv("INVESTING_EMAIL")
    INVESTING_PASSWORD = os.getenv("INVESTING_PASSWORD")

    # EOD Historical Data API
    EODHD_API_KEY = os.getenv("EODHD_API_KEY")

    # Alpha Vantage API
    ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")
    ALPHAVANTAGE_RATE_LIMIT = os.getenv("ALPHAVANTAGE_RATE_LIMIT", "paid")

    # Financial Modeling Prep API
    FMP_API_KEY = os.getenv("FMP_API_KEY")

    # Twelve Data API
    TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY")

    # TASE Data Hub API (Israel Stock Exchange - Official)
    TASE_DATA_HUB_API_KEY = os.getenv("TASE_DATA_HUB_API_KEY")

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

        if cls.FINANCIAL_DATA_SOURCE == "tase_data_hub":
            if not cls.TASE_DATA_HUB_API_KEY:
                raise ValueError(
                    "TASE_DATA_HUB_API_KEY must be set in .env when using TASE Data Hub"
                )

        if cls.FINANCIAL_DATA_SOURCE == "twelvedata":
            if not cls.TWELVEDATA_API_KEY:
                raise ValueError(
                    "TWELVEDATA_API_KEY must be set in .env when using Twelve Data"
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

        if cls.PRICING_DATA_SOURCE == "twelvedata":
            if not cls.TWELVEDATA_API_KEY:
                raise ValueError(
                    "TWELVEDATA_API_KEY must be set in .env when using Twelve Data for pricing"
                )

        # יצירת תיקיות אם לא קיימות
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        cls.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        (cls.CACHE_DIR / "stocks_data").mkdir(exist_ok=True)
        (cls.CACHE_DIR / "index_constituents").mkdir(exist_ok=True)

        return True

    @classmethod
    def validate_source_configuration(cls):
        """
        אימות תצורת מקורות נתונים מתקדמת (מטריצה 2x2)

        בודק שמפתחות API נדרשים קיימים עבור מקורות שהוגדרו.

        Raises:
            ValueError: אם חסרים מפתחות API נדרשים
        """
        sources_needed = set()

        # אסוף את כל המקורות המוגדרים
        if cls.US_FINANCIAL_DATA_SOURCE:
            sources_needed.add(cls.US_FINANCIAL_DATA_SOURCE)
        if cls.US_PRICING_DATA_SOURCE and cls.US_PRICING_DATA_SOURCE != "yfinance":
            sources_needed.add(cls.US_PRICING_DATA_SOURCE)
        if cls.TASE_FINANCIAL_DATA_SOURCE:
            sources_needed.add(cls.TASE_FINANCIAL_DATA_SOURCE)
        if cls.TASE_PRICING_DATA_SOURCE and cls.TASE_PRICING_DATA_SOURCE != "yfinance":
            sources_needed.add(cls.TASE_PRICING_DATA_SOURCE)

        # בדוק מפתחות API עבור כל מקור
        missing = []
        for source in sources_needed:
            if source == "eodhd" and not cls.EODHD_API_KEY:
                missing.append(f"{source} requires EODHD_API_KEY")
            elif source == "fmp" and not cls.FMP_API_KEY:
                missing.append(f"{source} requires FMP_API_KEY")
            elif source == "tase_data_hub" and not cls.TASE_DATA_HUB_API_KEY:
                missing.append(f"{source} requires TASE_DATA_HUB_API_KEY")
            elif source == "alphavantage" and not cls.ALPHAVANTAGE_API_KEY:
                missing.append(f"{source} requires ALPHAVANTAGE_API_KEY")
            elif source == "investing" and not (cls.INVESTING_EMAIL and cls.INVESTING_PASSWORD):
                missing.append(f"{source} requires INVESTING_EMAIL and INVESTING_PASSWORD")

        if missing:
            raise ValueError(f"Missing API keys:\n  - " + "\n  - ".join(missing))


# יצירת instance יחיד
settings = Settings()
