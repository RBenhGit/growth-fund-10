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
    # Options: twelvedata, alphavantage
    US_FINANCIAL_DATA_SOURCE = os.getenv("US_FINANCIAL_DATA_SOURCE", "")

    # US Stocks (SP500) - Pricing Data
    # Options: yfinance, twelvedata, alphavantage
    US_PRICING_DATA_SOURCE = os.getenv("US_PRICING_DATA_SOURCE", "yfinance")

    # TASE Stocks (TA-125) - Financial Data
    # Options: twelvedata
    TASE_FINANCIAL_DATA_SOURCE = os.getenv("TASE_FINANCIAL_DATA_SOURCE", "")

    # TASE Stocks (TA-125) - Pricing Data
    # Options: yfinance, twelvedata
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
    FINANCIAL_DATA_SOURCE = US_FINANCIAL_DATA_SOURCE or TASE_FINANCIAL_DATA_SOURCE or "twelvedata"
    PRICING_DATA_SOURCE = US_PRICING_DATA_SOURCE or "yfinance"

    # Alpha Vantage API
    ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")
    ALPHAVANTAGE_RATE_LIMIT = os.getenv("ALPHAVANTAGE_RATE_LIMIT", "paid")

    # Twelve Data API
    TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY")
    # Rate limit overrides (0 = auto-detect from API)
    TWELVEDATA_CREDITS_PER_MINUTE = int(os.getenv("TWELVEDATA_CREDITS_PER_MINUTE", "0"))
    TWELVEDATA_MAX_STOCKS_PER_MINUTE = int(os.getenv("TWELVEDATA_MAX_STOCKS_PER_MINUTE", "0"))

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
        if cls.FINANCIAL_DATA_SOURCE == "alphavantage":
            if not cls.ALPHAVANTAGE_API_KEY:
                raise ValueError(
                    "ALPHAVANTAGE_API_KEY must be set in .env when using Alpha Vantage"
                )

        if cls.FINANCIAL_DATA_SOURCE == "twelvedata":
            if not cls.TWELVEDATA_API_KEY:
                raise ValueError(
                    "TWELVEDATA_API_KEY must be set in .env when using Twelve Data"
                )

        # בדיקת מקור מחירים
        # yfinance לא דורש API key, אבל מקורות אחרים כן
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
            if source == "alphavantage" and not cls.ALPHAVANTAGE_API_KEY:
                missing.append(f"{source} requires ALPHAVANTAGE_API_KEY")
            elif source == "twelvedata" and not cls.TWELVEDATA_API_KEY:
                missing.append(f"{source} requires TWELVEDATA_API_KEY")


        if missing:
            raise ValueError(f"Missing API keys:\n  - " + "\n  - ".join(missing))


# יצירת instance יחיד
settings = Settings()
