"""
מודלים לנתונים פיננסיים
"""

from pydantic import BaseModel, Field
from typing import Dict, Optional, List


class FinancialData(BaseModel):
    """נתונים פיננסיים למניה"""

    symbol: str = Field(..., description="סימול המניה")

    # Income Statement (דוח רווח והפסד)
    revenues: Dict[int, float] = Field(default_factory=dict, description="הכנסות לפי שנה")
    net_incomes: Dict[int, float] = Field(default_factory=dict, description="רווח נקי לפי שנה")
    operating_incomes: Dict[int, float] = Field(default_factory=dict, description="רווח תפעולי לפי שנה")

    # Balance Sheet (מאזן)
    total_debt: Optional[float] = Field(None, description="חוב כולל")
    total_equity: Optional[float] = Field(None, description="הון עצמי")

    # Cash Flow Statement (תזרים מזומנים)
    operating_cash_flows: Dict[int, float] = Field(default_factory=dict, description="תזרים מפעילות שוטפת לפי שנה")

    # נתונים נוספים
    market_cap: Optional[float] = Field(None, description="שווי שוק")
    current_price: Optional[float] = Field(None, description="מחיר נוכחי")
    pe_ratio: Optional[float] = Field(None, description="יחס P/E")

    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "AAPL",
                "revenues": {2024: 385000000000, 2023: 394000000000},
                "net_incomes": {2024: 97000000000, 2023: 99000000000},
                "market_cap": 3000000000000,
                "current_price": 185.50
            }
        }

    @property
    def debt_to_equity_ratio(self) -> Optional[float]:
        """חישוב יחס חוב/הון"""
        if self.total_equity and self.total_equity > 0:
            return self.total_debt / self.total_equity if self.total_debt else 0.0
        return None

    def has_profitable_years(self, num_years: int) -> bool:
        """
        בדיקה האם יש רווח נקי חיובי במספר שנים רצוף

        Args:
            num_years: מספר השנים לבדיקה

        Returns:
            bool: True אם יש רווח חיובי בכל השנים
        """
        if len(self.net_incomes) < num_years:
            return False

        # בדיקת שנים רצופות
        sorted_years = sorted(self.net_incomes.keys(), reverse=True)
        recent_years = sorted_years[:num_years]

        return all(self.net_incomes[year] > 0 for year in recent_years)

    def has_operating_profit_years(self, required_years: int, total_years: int) -> bool:
        """
        בדיקה האם יש רווח תפעולי חיובי במספר שנים מתוך סך כולל

        Args:
            required_years: מספר השנים הנדרש (לדוגמה 4)
            total_years: סך כל השנים לבדיקה (לדוגמה 5)

        Returns:
            bool: True אם יש רווח תפעולי חיובי במספר השנים הנדרש
        """
        if len(self.operating_incomes) < total_years:
            return False

        sorted_years = sorted(self.operating_incomes.keys(), reverse=True)
        recent_years = sorted_years[:total_years]

        positive_years = sum(1 for year in recent_years if self.operating_incomes[year] > 0)
        return positive_years >= required_years

    def has_positive_cash_flow(self) -> bool:
        """
        בדיקה האם יש תזרים מזומנים חיובי ברוב השנים

        Returns:
            bool: True אם יש תזרים חיובי ב-50%+ מהשנים
        """
        if not self.operating_cash_flows:
            return False

        positive_years = sum(1 for cf in self.operating_cash_flows.values() if cf > 0)
        return positive_years / len(self.operating_cash_flows) > 0.5


class MarketData(BaseModel):
    """נתוני שוק למניה"""

    symbol: str = Field(..., description="סימול המניה")
    name: str = Field(..., description="שם החברה")
    market_cap: float = Field(..., description="שווי שוק")
    current_price: float = Field(..., description="מחיר נוכחי")
    pe_ratio: Optional[float] = Field(None, description="יחס P/E")
    price_history: Dict[str, float] = Field(default_factory=dict, description="היסטוריית מחירים (תאריך: מחיר)")

    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "AAPL",
                "name": "Apple Inc",
                "market_cap": 3000000000000,
                "current_price": 185.50,
                "pe_ratio": 30.5,
                "price_history": {"2024-11-27": 185.50, "2023-11-27": 175.00}
            }
        }

    def get_price_on_date(self, date_str: str) -> Optional[float]:
        """
        מחזיר מחיר בתאריך מסוים

        Args:
            date_str: תאריך בפורמט YYYY-MM-DD

        Returns:
            Optional[float]: מחיר או None
        """
        return self.price_history.get(date_str)

    def calculate_momentum(self, days_ago: int = 365) -> Optional[float]:
        """
        חישוב מומנטום - שינוי מחיר באחוזים

        Args:
            days_ago: מספר ימים אחורה

        Returns:
            Optional[float]: מומנטום באחוזים או None
        """
        if not self.price_history:
            return None

        # למצוא את המחיר הכי קרוב לתאריך המבוקש
        sorted_dates = sorted(self.price_history.keys(), reverse=True)
        if len(sorted_dates) < 2:
            return None

        old_price = self.price_history[sorted_dates[-1]]  # המחיר הכי ישן
        return ((self.current_price - old_price) / old_price) * 100 if old_price > 0 else None


class PricePoint(BaseModel):
    """נקודת מחיר"""

    date: str = Field(..., description="תאריך (YYYY-MM-DD)")
    price: float = Field(..., description="מחיר")
