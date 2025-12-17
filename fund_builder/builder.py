"""
Fund Builder - לוגיקת בניית קרן
"""

from typing import List, Dict, Tuple, Optional
from models import Stock, Fund, FundPosition
from config import settings
import math
import logging
from functools import reduce

logger = logging.getLogger(__name__)


class FundBuilder:
    """מחלקה לבניית קרן"""

    def __init__(self, index_name: str):
        """
        אתחול

        Args:
            index_name: שם המדד (TASE125/SP500)
        """
        self.index_name = index_name
        self.all_stocks: List[Stock] = []
        self.base_candidates: List[Stock] = []
        self.potential_candidates: List[Stock] = []
        self.selected_base: List[Stock] = []
        self.selected_potential: List[Stock] = []

    def calculate_growth_rate(self, values: Dict[int, float], years: int = 3) -> Optional[float]:
        """
        חישוב שיעור צמיחה ממוצע שנתי (CAGR)

        Args:
            values: מילון של ערכים לפי שנה
            years: מספר שנים לחישוב

        Returns:
            Optional[float]: שיעור צמיחה באחוזים או None
        """
        if not values or len(values) < years:
            return None

        sorted_years = sorted(values.keys(), reverse=True)
        if len(sorted_years) < years:
            return None

        recent_years = sorted_years[:years]
        start_value = values[recent_years[-1]]
        end_value = values[recent_years[0]]

        if start_value <= 0:
            return None

        # CAGR formula: ((end_value / start_value) ^ (1 / years)) - 1
        try:
            cagr = (pow(end_value / start_value, 1 / (years - 1)) - 1) * 100
            return cagr
        except (ZeroDivisionError, ValueError):
            return None

    def normalize_score(self, values: List[float]) -> List[float]:
        """
        נרמול ציונים לטווח 0-100

        Args:
            values: רשימת ערכים

        Returns:
            List[float]: ערכים מנורמלים
        """
        if not values:
            return []

        min_val = min(values)
        max_val = max(values)

        if max_val == min_val:
            return [50.0] * len(values)

        return [((v - min_val) / (max_val - min_val)) * 100 for v in values]

    def calculate_base_score(self, stock: Stock) -> float:
        """
        חישוב ציון מניית בסיס

        משקולות:
        - צמיחת רווח נקי: 40%
        - צמיחת הכנסות: 35%
        - גודל חברה (שווי שוק): 25%

        Args:
            stock: מניה

        Returns:
            float: ציון סופי
        """
        if not stock.financial_data:
            return 0.0

        # צמיחת רווח נקי
        net_income_growth = self.calculate_growth_rate(stock.financial_data.net_incomes, 3)
        if net_income_growth is None:
            net_income_growth = 0.0

        # צמיחת הכנסות
        revenue_growth = self.calculate_growth_rate(stock.financial_data.revenues, 3)
        if revenue_growth is None:
            revenue_growth = 0.0

        # גודל חברה (שווי שוק)
        market_cap_score = stock.market_cap or 0.0

        return {
            "net_income_growth": net_income_growth,
            "revenue_growth": revenue_growth,
            "market_cap": market_cap_score
        }

    def calculate_potential_score(self, stock: Stock, index_pe: Optional[float] = None) -> Dict[str, float]:
        """
        חישוב ציון מניית פוטנציאל

        משקולות:
        - צמיחה עתידית: 50%
        - מומנטום: 30%
        - שווי: 20%

        Args:
            stock: מניה
            index_pe: P/E ממוצע של המדד

        Returns:
            Dict[str, float]: ציונים עבור כל קריטריון
        """
        if not stock.financial_data or not stock.market_data:
            return {"future_growth": 0.0, "momentum": 0.0, "valuation": 0.0}

        # צמיחה עתידית (מבוסס על צמיחה ב-2 שנים אחרונות)
        future_growth = self.calculate_growth_rate(stock.financial_data.net_incomes, 2) or 0.0

        # מומנטום (שינוי מחיר בשנה האחרונה)
        momentum_raw = stock.market_data.calculate_momentum(365)
        if momentum_raw is None:
            logger.debug(f"{stock.symbol}: No price history - momentum will use default (0.0)")
            momentum = 0.0
        else:
            momentum = momentum_raw

        # שווי (P/E יחסי למדד)
        valuation_score = 0.0
        if stock.pe_ratio and index_pe and index_pe > 0:
            # ציון גבוה יותר למניות עם P/E נמוך יחסית למדד
            relative_pe = stock.pe_ratio / index_pe
            valuation_score = (2 - relative_pe) * 50  # נרמול לטווח 0-100
        else:
            if not stock.pe_ratio:
                logger.debug(f"{stock.symbol}: Missing P/E ratio - valuation will use default (0.0)")
            elif not index_pe or index_pe <= 0:
                logger.debug(f"{stock.symbol}: Invalid index P/E ({index_pe}) - valuation will use default (0.0)")

        return {
            "future_growth": future_growth,
            "momentum": momentum,
            "valuation": valuation_score
        }

    def score_and_rank_base_stocks(self, stocks: List[Stock]) -> List[Stock]:
        """
        ציון ודירוג מניות בסיס

        Args:
            stocks: רשימת מניות

        Returns:
            List[Stock]: מניות ממוינות לפי ציון
        """
        scored_stocks = []

        for stock in stocks:
            scores = self.calculate_base_score(stock)
            if scores:
                stock._raw_scores = scores
                scored_stocks.append(stock)

        # נרמול ציונים
        if scored_stocks:
            net_income_scores = [s._raw_scores["net_income_growth"] for s in scored_stocks]
            revenue_scores = [s._raw_scores["revenue_growth"] for s in scored_stocks]
            market_cap_scores = [s._raw_scores["market_cap"] for s in scored_stocks]

            normalized_net_income = self.normalize_score(net_income_scores)
            normalized_revenue = self.normalize_score(revenue_scores)
            normalized_market_cap = self.normalize_score(market_cap_scores)

            for i, stock in enumerate(scored_stocks):
                final_score = (
                    normalized_net_income[i] * settings.BASE_SCORE_WEIGHTS["net_income_growth"] +
                    normalized_revenue[i] * settings.BASE_SCORE_WEIGHTS["revenue_growth"] +
                    normalized_market_cap[i] * settings.BASE_SCORE_WEIGHTS["market_cap"]
                )
                stock.base_score = final_score
                # שמירת ציונים משנה
                stock.base_scores_detail = {
                    "net_income_growth_raw": stock._raw_scores["net_income_growth"],
                    "revenue_growth_raw": stock._raw_scores["revenue_growth"],
                    "market_cap_raw": stock._raw_scores["market_cap"],
                    "net_income_growth_normalized": normalized_net_income[i],
                    "revenue_growth_normalized": normalized_revenue[i],
                    "market_cap_normalized": normalized_market_cap[i]
                }

                # Verify assignment
                if stock.base_score is None:
                    logger.error(f"BUG: Failed to assign base_score to {stock.symbol}")
                elif i < 5:  # Log first 5 stocks
                    logger.debug(f"{stock.symbol}: base_score={stock.base_score:.2f}")

        # מיון לפי ציון סופי
        scored_stocks.sort(key=lambda s: s.base_score or 0, reverse=True)
        return scored_stocks

    def score_and_rank_potential_stocks(self, stocks: List[Stock], index_pe: Optional[float]) -> List[Stock]:
        """
        ציון ודירוג מניות פוטנציאל

        Args:
            stocks: רשימת מניות
            index_pe: P/E ממוצע של המדד

        Returns:
            List[Stock]: מניות ממוינות לפי ציון
        """
        scored_stocks = []

        for stock in stocks:
            scores = self.calculate_potential_score(stock, index_pe)
            if scores:
                stock._raw_scores = scores
                scored_stocks.append(stock)

        # נרמול ציונים
        if scored_stocks:
            future_growth_scores = [s._raw_scores["future_growth"] for s in scored_stocks]
            momentum_scores = [s._raw_scores["momentum"] for s in scored_stocks]
            valuation_scores = [s._raw_scores["valuation"] for s in scored_stocks]

            normalized_growth = self.normalize_score(future_growth_scores)
            normalized_momentum = self.normalize_score(momentum_scores)
            normalized_valuation = self.normalize_score(valuation_scores)

            for i, stock in enumerate(scored_stocks):
                final_score = (
                    normalized_growth[i] * settings.POTENTIAL_SCORE_WEIGHTS["future_growth"] +
                    normalized_momentum[i] * settings.POTENTIAL_SCORE_WEIGHTS["momentum"] +
                    normalized_valuation[i] * settings.POTENTIAL_SCORE_WEIGHTS["valuation"]
                )
                stock.potential_score = final_score
                # שמירת ציונים משנה
                stock.potential_scores_detail = {
                    "future_growth_raw": stock._raw_scores["future_growth"],
                    "momentum_raw": stock._raw_scores["momentum"],
                    "valuation_raw": stock._raw_scores["valuation"],
                    "future_growth_normalized": normalized_growth[i],
                    "momentum_normalized": normalized_momentum[i],
                    "valuation_normalized": normalized_valuation[i]
                }

                # Verify assignment
                if stock.potential_score is None:
                    logger.error(f"BUG: Failed to assign potential_score to {stock.symbol}")
                elif i < 5:  # Log first 5 stocks
                    logger.debug(f"{stock.symbol}: potential_score={stock.potential_score:.2f}")

        # מיון לפי ציון סופי
        scored_stocks.sort(key=lambda s: s.potential_score or 0, reverse=True)
        return scored_stocks

    def calculate_lcm(self, numbers: List[int]) -> int:
        """
        חישוב המכפלה המשותפת הקטנה ביותר

        Args:
            numbers: רשימת מספרים

        Returns:
            int: LCM
        """
        def lcm(a, b):
            return abs(a * b) // math.gcd(a, b)

        return reduce(lcm, numbers)

    def calculate_minimum_fund_cost(self, positions: List[Tuple[Stock, float]]) -> Tuple[float, Dict[str, int]]:
        """
        חישוב עלות מינימלית ליחידת קרן

        גישה: המניה היקרה ביותר מקבלת מניה אחת, והשאר מותאמים יחסית למשקל הרצוי.

        Args:
            positions: רשימת טאפלים של (מניה, משקל)

        Returns:
            Tuple[float, Dict[str, int]]: (עלות מינימלית, מספר מניות לכל חברה לפי סימול)
        """
        if not positions:
            return 0.0, {}

        # מציאת המניה היקרה ביותר
        max_price = 0.0
        max_price_weight = 0.0

        for stock, weight in positions:
            price = stock.current_price or 0
            if price > max_price:
                max_price = price
                max_price_weight = weight

        if max_price <= 0 or max_price_weight <= 0:
            return 0.0, {}

        # חישוב עלות הקרן כך שהמניה היקרה תקבל מניה אחת
        # 1 × max_price = fund_cost × max_price_weight
        # fund_cost = max_price / max_price_weight
        fund_cost = max_price / max_price_weight

        # חישוב מספר מניות לכל פוזיציה
        shares_per_stock = {}
        actual_cost = 0.0

        for stock, weight in positions:
            price = stock.current_price or 0
            if price > 0:
                # חישוב מספר מניות על בסיס המשקל
                target_value = fund_cost * weight
                num_shares = round(target_value / price)

                # וידוא לפחות מניה אחת
                if num_shares < 1:
                    num_shares = 1

                shares_per_stock[stock.symbol] = num_shares
                actual_cost += num_shares * price

        return actual_cost, shares_per_stock

    def validate_fund(self, fund: Fund) -> List[str]:
        """
        אימות תקינות הקרן

        Args:
            fund: הקרן לאימות

        Returns:
            List[str]: רשימת שגיאות (ריקה אם הכל תקין)
        """
        errors = []

        # 1. בדיקת סכום משקלים
        total_weight = sum(pos.weight for pos in fund.positions)
        if abs(total_weight - 1.0) > 0.001:
            errors.append(f"סכום המשקלים אינו 100%: {total_weight * 100:.2f}%")

        # 2. בדיקת מספר מניות
        if len(fund.positions) != 10:
            errors.append(f"מספר מניות בקרן: {len(fund.positions)} (צריך להיות 10)")

        # 3. בדיקת כשירות מניות בסיס
        base_count = sum(1 for pos in fund.positions if pos.position_type == "בסיס")
        if base_count != 6:
            errors.append(f"מספר מניות בסיס: {base_count} (צריך להיות 6)")

        # 4. בדיקת כשירות מניות פוטנציאל
        potential_count = sum(1 for pos in fund.positions if pos.position_type == "פוטנציאל")
        if potential_count != 4:
            errors.append(f"מספר מניות פוטנציאל: {potential_count} (צריך להיות 4)")

        # 5. בדיקת חפיפה
        symbols = [pos.stock.symbol for pos in fund.positions]
        if len(symbols) != len(set(symbols)):
            errors.append("קיימת חפיפה בין מניות בקרן")

        # 6. בדיקת מספר מניות שלם
        for pos in fund.positions:
            if pos.shares_per_unit and not float(pos.shares_per_unit).is_integer():
                errors.append(f"מספר מניות של {pos.stock.symbol} אינו שלם: {pos.shares_per_unit}")

        return errors
