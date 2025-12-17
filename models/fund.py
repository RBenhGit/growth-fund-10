"""
מודל קרן
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from .stock import Stock


class FundPosition(BaseModel):
    """פוזיציה בקרן (מניה + משקל + כמות)"""

    stock: Stock = Field(..., description="המניה")
    weight: float = Field(..., description="משקל בקרן (0-1)")
    shares_per_unit: int = Field(..., description="מספר מניות ליחידת קרן")
    position_type: str = Field(..., description="סוג הפוזיציה (base/potential)")

    class Config:
        json_schema_extra = {
            "example": {
                "stock": {"symbol": "AAPL", "name": "Apple Inc"},
                "weight": 0.25,
                "shares_per_unit": 10,
                "position_type": "base"
            }
        }

    @property
    def position_value_per_unit(self) -> float:
        """ערך הפוזיציה ליחידת קרן"""
        if self.stock.current_price:
            return self.shares_per_unit * self.stock.current_price
        return 0.0


class Fund(BaseModel):
    """מחלקת קרן"""

    name: str = Field(..., description="שם הקרן")
    index: str = Field(..., description="מדד הבסיס (TASE125/SP500)")
    quarter: str = Field(..., description="רבעון (Q1-Q4)")
    year: int = Field(..., description="שנה")
    creation_date: Optional[str] = Field(None, description="תאריך יצירה")

    # פוזיציות
    positions: List[FundPosition] = Field(default_factory=list, description="פוזיציות בקרן")

    # מטה-נתונים
    minimum_cost: Optional[float] = Field(None, description="עלות מינימלית ליחידת קרן")
    total_weight: float = Field(0.0, description="סך משקלים (צריך להיות 1.0)")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Fund_10_SP500_Q4_2025",
                "index": "SP500",
                "quarter": "Q4",
                "year": 2025,
                "minimum_cost": 10000.0
            }
        }

    def add_position(
        self,
        stock: Stock,
        weight: float,
        shares_per_unit: int,
        position_type: str
    ) -> None:
        """
        הוספת פוזיציה לקרן

        Args:
            stock: המניה
            weight: משקל (0-1)
            shares_per_unit: מספר מניות ליחידת קרן
            position_type: סוג (base/potential)
        """
        position = FundPosition(
            stock=stock,
            weight=weight,
            shares_per_unit=shares_per_unit,
            position_type=position_type
        )
        self.positions.append(position)
        self.total_weight += weight

    def get_base_positions(self) -> List[FundPosition]:
        """מחזיר את מניות הבסיס"""
        return [p for p in self.positions if p.position_type == "base"]

    def get_potential_positions(self) -> List[FundPosition]:
        """מחזיר את מניות הפוטנציאל"""
        return [p for p in self.positions if p.position_type == "potential"]

    def calculate_total_value_per_unit(self) -> float:
        """חישוב ערך כולל ליחידת קרן"""
        return sum(p.position_value_per_unit for p in self.positions)

    def get_stocks_summary(self) -> Dict:
        """סיכום מניות הקרן"""
        return {
            "total_positions": len(self.positions),
            "base_stocks": len(self.get_base_positions()),
            "potential_stocks": len(self.get_potential_positions()),
            "total_weight": round(self.total_weight, 4),
            "minimum_cost": self.minimum_cost
        }

    def to_markdown(self) -> str:
        """
        המרת הקרן לטבלת Markdown

        Returns:
            str: טבלת Markdown
        """
        lines = []
        lines.append("| שם חברה | סימול | סוג | משקל | ציון | מחיר נוכחי | מספר מניות ליחידת קרן |")
        lines.append("|---------|-------|-----|------|------|------------|---------------------|")

        for pos in self.positions:
            current_price = pos.stock.current_price if pos.stock.current_price else 0.0

            # בחר את הציון הרלוונטי לפי סוג המניה
            if pos.position_type == "בסיס":
                score = pos.stock.base_score if pos.stock.base_score else 0.0
            else:  # פוטנציאל
                score = pos.stock.potential_score if pos.stock.potential_score else 0.0

            lines.append(
                f"| {pos.stock.name} | {pos.stock.symbol} | {pos.position_type} | "
                f"{pos.weight * 100:.1f}% | "
                f"{score:.2f} | "
                f"{current_price:.2f} | "
                f"{pos.shares_per_unit} |"
            )

        return "\n".join(lines)

    def __str__(self) -> str:
        return f"Fund({self.name} - {len(self.positions)} positions)"

    def __repr__(self) -> str:
        return self.__str__()
