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

        # CAGR formula: ((end_value / start_value) ^ (1 / period)) - 1
        # Use explicit (years - 1) as period to ensure a consistent annualization
        # regardless of calendar year gaps (e.g. after LTM merging adds a non-consecutive year).
        # With years=5 this always computes a 4-year CAGR.
        try:
            period = years - 1
            if period <= 0:
                return None
            cagr = (pow(end_value / start_value, 1 / period) - 1) * 100
            return cagr
        except (ZeroDivisionError, ValueError):
            return None

    def calculate_growth_stability(self, values: Dict[int, float], years: int = 5) -> Optional[float]:
        """
        R² of log(value) ~ year_index for the most-recent `years` data points.
        R²=1.0 = perfect log-linear compounder; R²≈0 = chaotic/boom-bust path.
        Rewards steady growth, penalizes volatility.

        Args:
            values: dict of {year: value}
            years: number of most-recent points to use (up to 5)

        Returns:
            Optional[float]: R² (0-1), None if < 2 positive values
        """
        sorted_years = sorted(values.keys(), reverse=True)[:years]
        points = sorted([(yr, values[yr]) for yr in sorted_years if values[yr] > 0])

        if len(points) < 2:
            return None

        xs = list(range(len(points)))  # year index 0..n-1
        ys = [math.log(v) for _, v in points]
        n = len(xs)

        x_mean = sum(xs) / n
        y_mean = sum(ys) / n

        ss_xx = sum((x - x_mean) ** 2 for x in xs)
        if ss_xx == 0:
            return 1.0  # constant x — degenerate case

        b = sum((xs[i] - x_mean) * (ys[i] - y_mean) for i in range(n)) / ss_xx
        a = y_mean - b * x_mean

        ss_tot = sum((y - y_mean) ** 2 for y in ys)
        if ss_tot == 0:
            return 1.0  # perfectly flat log series

        ss_res = sum((ys[i] - (a + b * xs[i])) ** 2 for i in range(n))
        return max(0.0, 1.0 - ss_res / ss_tot)

    def rank_percentile(self, values: List[float]) -> List[float]:
        """
        Rank-percentile normalization. Tied values get average rank. Returns 0-100 scale.

        Args:
            values: list of numeric values

        Returns:
            List[float]: percentile ranks (0-100), tied values share average rank
        """
        n = len(values)
        if n == 0:
            return []
        if n == 1:
            return [50.0]

        indexed = sorted(enumerate(values), key=lambda x: x[1])
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j < n - 1 and indexed[j][1] == indexed[j + 1][1]:
                j += 1
            # indices i..j have the same value; assign average rank
            avg_rank = (i + j) / 2
            for k in range(i, j + 1):
                ranks[indexed[k][0]] = avg_rank / (n - 1) * 100
            i = j + 1
        return ranks

    def calculate_base_score(self, stock: Stock) -> Dict[str, float]:
        """
        חישוב ציון מניית בסיס עם מדדי גדילה ויציבות

        משקולות:
        - צמיחת רווח נקי (CAGR): 40%
        - צמיחת הכנסות (CAGR): 35%
        - גודל חברה (שווי שוק): 25%

        כל ציר צמיחה משולב: 70% CAGR + 30% R² stability

        Args:
            stock: מניה

        Returns:
            Dict[str, float]: ציונים עבור כל קריטריון (growth, stability, market_cap)
        """
        if not stock.financial_data:
            return {
                "net_income_growth": 0.0,
                "net_income_stability": 0.0,
                "revenue_growth": 0.0,
                "revenue_stability": 0.0,
                "market_cap": 0.0
            }

        # צמיחת רווח נקי (BASE_GROWTH_YEARS נקודות נתונים → CAGR של 4 שנים)
        years = settings.BASE_GROWTH_YEARS
        net_income_growth = self.calculate_growth_rate(stock.financial_data.net_incomes, years) or 0.0

        # יציבות רווח נקי (R² of log-linear regression)
        net_income_stability = self.calculate_growth_stability(stock.financial_data.net_incomes, years) or 0.0

        # צמיחת הכנסות (BASE_GROWTH_YEARS נקודות נתונים → CAGR של 4 שנים)
        revenue_growth = self.calculate_growth_rate(stock.financial_data.revenues, years) or 0.0

        # יציבות הכנסות
        revenue_stability = self.calculate_growth_stability(stock.financial_data.revenues, years) or 0.0

        # גודל חברה (שווי שוק)
        market_cap_score = stock.market_cap or 0.0

        return {
            "net_income_growth": net_income_growth,
            "net_income_stability": net_income_stability,
            "revenue_growth": revenue_growth,
            "revenue_stability": revenue_stability,
            "market_cap": market_cap_score
        }

    def calculate_potential_score(self, stock: Stock) -> Dict[str, float]:
        """
        חישוב ציון מניית פוטנציאל

        משקולות:
        - צמיחה עתידית (CAGR 2 שנים): 80%
        - מומנטום: 20%

        Args:
            stock: מניה

        Returns:
            Dict[str, float]: ציונים עבור כל קריטריון
        """
        if not stock.financial_data or not stock.market_data:
            return {"future_growth": 0.0, "momentum": 0.0}

        # צמיחה עתידית (3 נקודות נתונים → CAGR של 2 שנים, מונע עיוות מאירועים חד-פעמיים)
        future_growth = self.calculate_growth_rate(stock.financial_data.net_incomes, 3) or 0.0

        # מומנטום (שינוי מחיר מאז הנתון ההיסטורי הישן ביותר הזמין)
        momentum_raw = stock.market_data.calculate_momentum(365)
        if momentum_raw is None:
            logger.debug(f"{stock.symbol}: No price history - momentum will use default (0.0)")
            momentum = 0.0
        else:
            momentum = momentum_raw

        return {
            "future_growth": future_growth,
            "momentum": momentum,
        }

    def score_and_rank_base_stocks(self, stocks: List[Stock]) -> List[Stock]:
        """
        ציון ודירוג מניות בסיס עם יציבות צמיחה

        Blending formula per growth axis:
          NI_blended   = 0.70 × NI_CAGR_rank   + 0.30 × NI_stability_rank
          Rev_blended  = 0.70 × Rev_CAGR_rank  + 0.30 × Rev_stability_rank

        Final base score:
          base_score = 0.40 × NI_blended + 0.35 × Rev_blended + 0.25 × MarketCap_rank

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

        # Rank-percentile normalization for each component
        if scored_stocks:
            ni_cagr_ranks    = self.rank_percentile([s._raw_scores["net_income_growth"] for s in scored_stocks])
            ni_stab_ranks    = self.rank_percentile([s._raw_scores["net_income_stability"] for s in scored_stocks])
            rev_cagr_ranks   = self.rank_percentile([s._raw_scores["revenue_growth"] for s in scored_stocks])
            rev_stab_ranks   = self.rank_percentile([s._raw_scores["revenue_stability"] for s in scored_stocks])
            mcap_ranks       = self.rank_percentile([s._raw_scores["market_cap"] for s in scored_stocks])

            for i, stock in enumerate(scored_stocks):
                # Blended sub-scores: 70% CAGR rank + 30% stability rank
                ni_blended  = 0.7 * ni_cagr_ranks[i]  + 0.3 * ni_stab_ranks[i]
                rev_blended = 0.7 * rev_cagr_ranks[i] + 0.3 * rev_stab_ranks[i]

                # Final weighted score
                final_score = (
                    settings.BASE_SCORE_WEIGHTS["net_income_growth"] * ni_blended  +
                    settings.BASE_SCORE_WEIGHTS["revenue_growth"] * rev_blended +
                    settings.BASE_SCORE_WEIGHTS["market_cap"] * mcap_ranks[i]
                )
                stock.base_score = final_score

                # שמירת ציונים משנה
                stock.base_scores_detail = {
                    "net_income_growth_raw": stock._raw_scores["net_income_growth"],
                    "net_income_stability_raw": stock._raw_scores["net_income_stability"],
                    "revenue_growth_raw": stock._raw_scores["revenue_growth"],
                    "revenue_stability_raw": stock._raw_scores["revenue_stability"],
                    "market_cap_raw": stock._raw_scores["market_cap"],
                    "ni_cagr_rank": ni_cagr_ranks[i],
                    "ni_stab_rank": ni_stab_ranks[i],
                    "ni_blended": ni_blended,
                    "rev_cagr_rank": rev_cagr_ranks[i],
                    "rev_stab_rank": rev_stab_ranks[i],
                    "rev_blended": rev_blended,
                    "mcap_rank": mcap_ranks[i]
                }

                # Verify assignment
                if stock.base_score is None:
                    logger.error(f"BUG: Failed to assign base_score to {stock.symbol}")
                elif i < 5:  # Log first 5 stocks
                    logger.debug(f"{stock.symbol}: base_score={stock.base_score:.2f}")

        # מיון לפי ציון סופי
        scored_stocks.sort(key=lambda s: s.base_score or 0, reverse=True)
        return scored_stocks

    def score_and_rank_potential_stocks(self, stocks: List[Stock]) -> List[Stock]:
        """
        ציון ודירוג מניות פוטנציאל (growth-focused, no stability blend)

        Final potential score:
          potential_score = 0.80 × FutureGrowth_rank + 0.20 × Momentum_rank

        Args:
            stocks: רשימת מניות

        Returns:
            List[Stock]: מניות ממוינות לפי ציון
        """
        scored_stocks = []

        for stock in stocks:
            scores = self.calculate_potential_score(stock)
            if scores:
                stock._raw_scores = scores
                scored_stocks.append(stock)

        # Rank-percentile normalization for each component
        if scored_stocks:
            growth_ranks   = self.rank_percentile([s._raw_scores["future_growth"] for s in scored_stocks])
            momentum_ranks = self.rank_percentile([s._raw_scores["momentum"] for s in scored_stocks])

            for i, stock in enumerate(scored_stocks):
                final_score = (
                    settings.POTENTIAL_SCORE_WEIGHTS["future_growth"] * growth_ranks[i] +
                    settings.POTENTIAL_SCORE_WEIGHTS["momentum"] * momentum_ranks[i]
                )
                stock.potential_score = final_score

                # שמירת ציונים משנה
                stock.potential_scores_detail = {
                    "future_growth_raw": stock._raw_scores["future_growth"],
                    "momentum_raw": stock._raw_scores["momentum"],
                    "growth_rank": growth_ranks[i],
                    "momentum_rank": momentum_ranks[i],
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
