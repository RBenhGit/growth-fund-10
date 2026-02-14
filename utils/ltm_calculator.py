"""
מחשבון LTM (Last Twelve Months)

ממיר נתונים רבעוניים מ-TwelveData לערכי LTM (סכום 4 רבעונים אחרונים)
ומשלב אותם באובייקט Stock קיים מ-cache.
"""

import copy
import logging
from datetime import datetime

from models.stock import Stock
from models.financial_data import FinancialData, MarketData

logger = logging.getLogger(__name__)


def calculate_ltm(quarterly_data: dict) -> dict:
    """
    מחשב ערכי LTM מנתונים רבעוניים

    סוכם 4 רבעונים אחרונים עבור כל מדד פיננסי.

    Args:
        quarterly_data: תוצאה מ-TwelveDataSource.get_quarterly_financials()

    Returns:
        dict עם:
            ltm_revenue: float
            ltm_net_income: float
            ltm_operating_income: float
            ltm_operating_cash_flow: float
            total_debt: float
            total_equity: float
            ltm_year: int (שנת ה-LTM — שנת הרבעון האחרון)
            quarters_used: int (מספר רבעונים שנכללו)
            fiscal_dates: list[str] (תאריכי הרבעונים)
    """
    def _sum_quarters(entries: list[tuple]) -> float:
        """Sum values from list of (fiscal_date, amount) tuples"""
        return sum(amount for _, amount in entries)

    revenues = quarterly_data.get("quarterly_revenues", [])
    net_incomes = quarterly_data.get("quarterly_net_incomes", [])
    operating_incomes = quarterly_data.get("quarterly_operating_incomes", [])
    cash_flows = quarterly_data.get("quarterly_operating_cash_flows", [])

    quarters_used = len(revenues)
    if quarters_used == 0:
        raise ValueError("No quarterly data available for LTM calculation")

    # Determine LTM year from the most recent quarter's fiscal date
    latest_fiscal_date = revenues[0][0]  # e.g., "2025-12-31"
    ltm_year = int(latest_fiscal_date.split("-")[0])

    fiscal_dates = [entry[0] for entry in revenues]

    return {
        "ltm_revenue": _sum_quarters(revenues),
        "ltm_net_income": _sum_quarters(net_incomes),
        "ltm_operating_income": _sum_quarters(operating_incomes),
        "ltm_operating_cash_flow": _sum_quarters(cash_flows),
        "total_debt": quarterly_data.get("total_debt", 0.0),
        "total_equity": quarterly_data.get("total_equity", 0.0),
        "ltm_year": ltm_year,
        "quarters_used": quarters_used,
        "fiscal_dates": fiscal_dates,
    }


def merge_ltm_into_stock(
    stock: Stock,
    ltm_data: dict,
    current_price: float = None,
    market_cap: float = None,
    pe_ratio: float = None,
) -> Stock:
    """
    משלב ערכי LTM לתוך Stock קיים מ-cache

    מוסיף את ה-LTM כשנה חדשה (ltm_year) בנתונים הפיננסיים,
    מעדכן debt/equity מהמאזן האחרון, ומעדכן נתוני שוק.

    Args:
        stock: אובייקט Stock מ-cache
        ltm_data: תוצאה מ-calculate_ltm()
        current_price: מחיר נוכחי (מ-yfinance)
        market_cap: שווי שוק נוכחי (מ-yfinance)
        pe_ratio: יחס P/E נוכחי (מ-yfinance)

    Returns:
        Stock חדש עם נתוני LTM משולבים
    """
    # Deep copy to avoid mutating the original
    updated = stock.model_copy(deep=True)

    ltm_year = ltm_data["ltm_year"]

    # Add LTM values as the most recent year
    if updated.financial_data:
        fd = updated.financial_data
        fd.revenues[ltm_year] = ltm_data["ltm_revenue"]
        fd.net_incomes[ltm_year] = ltm_data["ltm_net_income"]
        fd.operating_incomes[ltm_year] = ltm_data["ltm_operating_income"]
        fd.operating_cash_flows[ltm_year] = ltm_data["ltm_operating_cash_flow"]

        # Update debt/equity from latest quarterly balance sheet
        fd.total_debt = ltm_data["total_debt"]
        fd.total_equity = ltm_data["total_equity"]

        logger.debug(
            f"{stock.symbol}: Merged LTM year {ltm_year} — "
            f"revenue={ltm_data['ltm_revenue']:.0f}, "
            f"net_income={ltm_data['ltm_net_income']:.0f}, "
            f"quarters={ltm_data['quarters_used']}"
        )

    # Update market data
    if updated.market_data:
        if current_price is not None:
            updated.market_data.current_price = current_price
        if market_cap is not None:
            updated.market_data.market_cap = market_cap
        if pe_ratio is not None:
            updated.market_data.pe_ratio = pe_ratio

        # Add current price to price history for the LTM date
        if current_price is not None:
            today_str = datetime.now().strftime("%Y-%m-%d")
            updated.market_data.price_history[today_str] = current_price
    elif current_price is not None or market_cap is not None:
        # Create market data if it doesn't exist
        updated.market_data = MarketData(
            symbol=stock.symbol.replace(".US", "").replace(".TA", ""),
            name=stock.name,
            market_cap=market_cap or 0.0,
            current_price=current_price or 0.0,
            pe_ratio=pe_ratio,
            price_history={},
        )

    # Reset scores (will be recalculated)
    updated.base_score = None
    updated.potential_score = None
    updated.base_scores_detail = None
    updated.potential_scores_detail = None

    return updated
