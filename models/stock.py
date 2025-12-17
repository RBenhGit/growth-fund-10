"""
מודל מניה
"""

from pydantic import BaseModel, Field
from typing import Optional
from .financial_data import FinancialData, MarketData


class Stock(BaseModel):
    """מחלקת מניה"""

    symbol: str = Field(..., description="סימול המניה")
    name: str = Field(..., description="שם החברה")
    index: str = Field(..., description="שם המדד (TASE125/SP500)")

    # נתונים פיננסיים
    financial_data: Optional[FinancialData] = Field(None, description="נתונים פיננסיים")
    market_data: Optional[MarketData] = Field(None, description="נתוני שוק")

    # ציונים
    base_score: Optional[float] = Field(None, description="ציון מניית בסיס")
    potential_score: Optional[float] = Field(None, description="ציון מניית פוטנציאל")

    # ציונים משנה (פירוט)
    base_scores_detail: Optional[dict] = Field(None, description="פירוט ציוני בסיס: net_income_growth, revenue_growth, market_cap")
    potential_scores_detail: Optional[dict] = Field(None, description="פירוט ציוני פוטנציאל: future_growth, momentum, valuation")

    # מטא-נתונים
    is_eligible_for_base: bool = Field(False, description="כשירה כמניית בסיס")
    is_eligible_for_potential: bool = Field(False, description="כשירה כמניית פוטנציאל")

    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "AAPL",
                "name": "Apple Inc",
                "index": "SP500",
                "base_score": 85.5,
                "is_eligible_for_base": True
            }
        }

    @property
    def current_price(self) -> Optional[float]:
        """מחיר נוכחי"""
        if self.market_data:
            return self.market_data.current_price
        elif self.financial_data:
            return self.financial_data.current_price
        return None

    @property
    def market_cap(self) -> Optional[float]:
        """שווי שוק"""
        if self.market_data:
            return self.market_data.market_cap
        elif self.financial_data:
            return self.financial_data.market_cap
        return None

    @property
    def pe_ratio(self) -> Optional[float]:
        """יחס P/E"""
        if self.market_data:
            return self.market_data.pe_ratio
        elif self.financial_data:
            return self.financial_data.pe_ratio
        return None

    def check_base_eligibility(
        self,
        min_profitable_years: int = 5,
        min_operating_profit_years: int = 4,
        max_debt_to_equity: float = 0.60
    ) -> bool:
        """
        בדיקת כשירות כמניית בסיס

        Args:
            min_profitable_years: מינימום שנות רווחיות
            min_operating_profit_years: מינימום שנות רווח תפעולי
            max_debt_to_equity: מקסימום יחס חוב/הון

        Returns:
            bool: True אם המניה כשירה
        """
        if not self.financial_data:
            return False

        # 1. רווחיות יציבה - 5 שנים רצופות
        if not self.financial_data.has_profitable_years(min_profitable_years):
            return False

        # 2. יציבות תפעולית - 4 מתוך 5 שנים
        if not self.financial_data.has_operating_profit_years(min_operating_profit_years, min_profitable_years):
            return False

        # 3. תזרים מזומנים חיובי
        if not self.financial_data.has_positive_cash_flow():
            return False

        # 4. יחס חוב/הון
        debt_ratio = self.financial_data.debt_to_equity_ratio
        if debt_ratio is not None and debt_ratio > max_debt_to_equity:
            return False

        self.is_eligible_for_base = True
        return True

    def check_potential_eligibility(
        self,
        min_profitable_years: int = 2
    ) -> bool:
        """
        בדיקת כשירות כמניית פוטנציאל

        Args:
            min_profitable_years: מינימום שנות רווחיות (ברירת מחדל: 2)

        Returns:
            bool: True אם המניה כשירה

        Note:
            has_profitable_years בודקת את השנים האחרונות ביותר (most recent),
            ולא רק שיש 2 שנים כלשהן עם רווח.
        """
        if not self.financial_data:
            return False

        # רווחיות בסיסית - רווח חיובי ב-2 השנים האחרונות
        if not self.financial_data.has_profitable_years(min_profitable_years):
            return False

        # יש נתוני צמיחה מלאים
        if len(self.financial_data.revenues) < 2 or len(self.financial_data.net_incomes) < 2:
            return False

        self.is_eligible_for_potential = True
        return True

    def __str__(self) -> str:
        return f"Stock({self.symbol} - {self.name})"

    def __repr__(self) -> str:
        return self.__str__()
