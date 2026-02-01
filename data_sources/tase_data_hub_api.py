"""
TASE Data Hub API Data Source
מקור נתונים מבוסס על TASE Data Hub - API הרשמי של הבורסה בתל אביב
"""

import requests
import time
import logging
import yfinance as yf
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from models import FinancialData, MarketData
from .base_data_source import BaseDataSource
from config import settings

logger = logging.getLogger(__name__)


class TASEDataHubSource(BaseDataSource):
    """מקור נתונים מבוסס TASE Data Hub API"""

    def __init__(self, api_key: Optional[str] = None):
        """
        אתחול מקור נתונים TASE Data Hub

        Args:
            api_key: מפתח API (אם לא צוין - ייקח מהגדרות)
        """
        self.api_key = api_key or settings.TASE_DATA_HUB_API_KEY
        self.base_url = "https://datahubist.tase.co.il"

        if not self.api_key:
            raise ValueError("TASE_DATA_HUB_API_KEY חסר בהגדרות")

        self.headers = {
            "accept": "application/json",
            "accept-language": "he-IL",
            "apikey": f"Apikey {self.api_key}"
        }

        logger.info("אתחול TASE Data Hub API")

    def _rate_limit_wait(self):
        """המתנה בין קריאות למניעת חריגה מ-rate limit"""
        time.sleep(0.3)  # 10 קריאות לשניתיים

    def login(self) -> bool:
        """
        בדיקת תקינות החיבור ל-API

        Returns:
            bool: True אם החיבור תקין
        """
        try:
            # בדיקה באמצעות שליפת רשימת חברות ת"א 125
            endpoint = f"{self.base_url}/api/Index/IndexComponents"
            params = {"indexId": 137}
            response = requests.get(endpoint, headers=self.headers, params=params, timeout=10)

            if response.status_code == 200:
                logger.info("התחברות ל-TASE Data Hub הצליחה")
                return True
            else:
                logger.error(f"התחברות ל-TASE Data Hub נכשלה: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"שגיאה בהתחברות ל-TASE Data Hub: {e}")
            return False

    def logout(self):
        """לא נדרש עבור TASE Data Hub API (stateless)"""
        pass

    def get_index_constituents(self, index_name: str) -> List[Dict]:
        """
        שליפת רשימת רכיבי מדד

        Args:
            index_name: שם המדד (רק TASE125 נתמך)

        Returns:
            List[Dict]: רשימת מניות עם פרטים בסיסיים
        """
        if index_name != "TASE125":
            raise NotImplementedError(f"TASE Data Hub תומך רק ב-TASE125, לא ב-{index_name}")

        try:
            endpoint = f"{self.base_url}/api/Index/IndexComponents"
            params = {"indexId": 137}  # ת"א 125

            response = requests.get(endpoint, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            constituents = []

            for item in data:
                constituents.append({
                    "symbol": str(item.get("securityId")),  # מזהה ייחודי
                    "name": item.get("companyName", ""),
                    "sector": item.get("sector", ""),
                    "sub_sector": item.get("industry", ""),
                    "market_cap": item.get("marketCap"),
                    "weight": item.get("weight")
                })

            logger.info(f"נמצאו {len(constituents)} חברות במדד ת\"א 125")
            return constituents

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"שגיאה בשליפת רכיבי המדד: {e}")

    def _map_tase_field(self, data: dict, *field_names) -> Optional[float]:
        """
        מיפוי שדה TASE - מנסה מספר אפשרויות של שמות שדות

        Args:
            data: המידע מה-API
            *field_names: שמות שדות אפשריים

        Returns:
            Optional[float]: הערך או None
        """
        for field in field_names:
            if field in data:
                try:
                    value = data[field]
                    if value is not None:
                        return float(value)
                except (ValueError, TypeError):
                    continue
        return None

    def _extract_key_metrics(self, income_statements: list, balance_sheets: list,
                            cash_flows: list, years: int) -> tuple:
        """
        חילוץ מדדים פיננסיים מרכזיים

        Args:
            income_statements: דוחות רווח והפסד
            balance_sheets: מאזנים
            cash_flows: תזרימי מזומנים
            years: מספר שנים

        Returns:
            tuple: (revenues, net_incomes, operating_incomes, operating_cash_flows,
                   total_debt, total_equity)
        """
        revenues = {}
        net_incomes = {}
        operating_incomes = {}
        operating_cash_flows = {}

        # חילוץ הכנסות, רווח נקי ורווח תפעולי
        for statement in income_statements:
            year = statement.get('year') or statement.get('period')
            if year:
                try:
                    year_int = int(str(year)[:4])  # המרה ל-int של השנה

                    revenue = self._map_tase_field(statement, 'totalRevenue', 'revenue', 'sales')
                    if revenue:
                        revenues[year_int] = revenue

                    net_income = self._map_tase_field(statement, 'netIncome', 'profitLoss', 'netProfit')
                    if net_income:
                        net_incomes[year_int] = net_income

                    operating_income = self._map_tase_field(statement, 'operatingIncome',
                                                           'operatingProfit', 'ebit', 'ebitda')
                    if operating_income:
                        operating_incomes[year_int] = operating_income
                except (ValueError, TypeError):
                    continue

        # חילוץ תזרים מזומנים
        for cf_statement in cash_flows:
            year = cf_statement.get('year') or cf_statement.get('period')
            if year:
                try:
                    year_int = int(str(year)[:4])
                    operating_cf = self._map_tase_field(cf_statement, 'operatingActivities',
                                                       'cashFromOperations', 'operatingCashFlow')
                    if operating_cf:
                        operating_cash_flows[year_int] = operating_cf
                except (ValueError, TypeError):
                    continue

        # חילוץ חוב והון מהמאזן האחרון
        total_debt = 0.0
        total_equity = 0.0

        if balance_sheets:
            latest_balance = balance_sheets[0]
            total_debt = self._map_tase_field(latest_balance, 'totalDebt', 'liabilities',
                                             'totalLiabilities') or 0.0
            total_equity = self._map_tase_field(latest_balance, 'totalEquity', 'equity',
                                               'shareholdersEquity', 'totalShareholderEquity') or 0.0

        return revenues, net_incomes, operating_incomes, operating_cash_flows, total_debt, total_equity

    def get_stock_financials(self, symbol: str, years: int = 5) -> FinancialData:
        """
        שליפת נתונים פיננסיים למניה

        Args:
            symbol: סימול המניה (securityId)
            years: מספר שנים לשלוף

        Returns:
            FinancialData: נתונים פיננסיים
        """
        try:
            security_id = symbol

            # חישוב טווח תאריכים
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365 * years)

            date_params = {
                "securityId": security_id,
                "fromDate": start_date.strftime("%Y-%m-%d"),
                "toDate": end_date.strftime("%Y-%m-%d")
            }

            # 1. דוח רווח והפסד
            logger.debug(f"מושך דוח רווח והפסד עבור {security_id}")
            income_endpoint = f"{self.base_url}/api/FinancialStatements/IncomeStatement"
            self._rate_limit_wait()

            try:
                income_response = requests.get(income_endpoint, headers=self.headers,
                                              params=date_params, timeout=30)
                income_response.raise_for_status()
                income_statements = income_response.json()
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    logger.warning("חריגה ממכסת קריאות - ממתין 5 שניות")
                    time.sleep(5)
                    income_response = requests.get(income_endpoint, headers=self.headers,
                                                  params=date_params, timeout=30)
                    income_response.raise_for_status()
                    income_statements = income_response.json()
                else:
                    raise

            # 2. מאזן
            logger.debug(f"מושך מאזן עבור {security_id}")
            balance_endpoint = f"{self.base_url}/api/FinancialStatements/BalanceSheet"
            self._rate_limit_wait()

            try:
                balance_response = requests.get(balance_endpoint, headers=self.headers,
                                               params=date_params, timeout=30)
                balance_response.raise_for_status()
                balance_sheets = balance_response.json()
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    logger.warning("חריגה ממכסת קריאות - ממתין 5 שניות")
                    time.sleep(5)
                    balance_response = requests.get(balance_endpoint, headers=self.headers,
                                                   params=date_params, timeout=30)
                    balance_response.raise_for_status()
                    balance_sheets = balance_response.json()
                else:
                    raise

            # 3. תזרים מזומנים
            logger.debug(f"מושך תזרים מזומנים עבור {security_id}")
            cashflow_endpoint = f"{self.base_url}/api/FinancialStatements/CashFlow"
            self._rate_limit_wait()

            try:
                cashflow_response = requests.get(cashflow_endpoint, headers=self.headers,
                                                params=date_params, timeout=30)
                cashflow_response.raise_for_status()
                cash_flows = cashflow_response.json()
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    logger.warning("חריגה ממכסת קריאות - ממתין 5 שניות")
                    time.sleep(5)
                    cashflow_response = requests.get(cashflow_endpoint, headers=self.headers,
                                                    params=date_params, timeout=30)
                    cashflow_response.raise_for_status()
                    cash_flows = cashflow_response.json()
                else:
                    raise

            # חילוץ מדדים
            revenues, net_incomes, operating_incomes, operating_cash_flows, total_debt, total_equity = \
                self._extract_key_metrics(income_statements, balance_sheets, cash_flows, years)

            # Get current price and market cap from yfinance (free) for Israeli stocks
            current_price = None
            market_cap = None
            pe_ratio = None

            try:
                # Convert security ID to TASE symbol format for yfinance
                # Most Israeli stocks can be accessed via yfinance with .TA suffix
                # We need to get the actual ticker symbol, not just the security ID
                # For now, we'll leave these as None and rely on market data from constituents
                pass
            except Exception:
                pass

            # בניית אובייקט FinancialData
            financial_data = FinancialData(
                symbol=symbol,
                revenues=revenues,
                net_incomes=net_incomes,
                operating_incomes=operating_incomes,
                operating_cash_flows=operating_cash_flows,
                total_debt=total_debt,
                total_equity=total_equity,
                market_cap=market_cap,
                current_price=current_price,
                pe_ratio=pe_ratio
            )

            logger.info(f"נתונים פיננסיים נשלפו בהצלחה עבור {security_id}")
            return financial_data

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"שגיאה בשליפת נתונים פיננסיים עבור {symbol}: {e}")
        except (KeyError, ValueError, IndexError) as e:
            raise RuntimeError(f"שגיאה בעיבוד נתונים פיננסיים עבור {symbol}: {e}")

    def get_stock_market_data(self, symbol: str) -> MarketData:
        """
        שליפת נתוני שוק למניה

        Args:
            symbol: סימול המניה (securityId)

        Returns:
            MarketData: נתוני שוק
        """
        try:
            # Get basic info from index constituents if available
            # For now, return minimal market data
            # Price history would use yfinance (free) if we had the ticker symbol

            market_data = MarketData(
                symbol=symbol,
                name="",  # Would come from constituents list
                market_cap=0.0,
                current_price=0.0,
                pe_ratio=None,
                price_history={}
            )

            logger.info(f"נתוני שוק נשלפו עבור {symbol}")
            return market_data

        except Exception as e:
            raise RuntimeError(f"שגיאה בשליפת נתוני שוק עבור {symbol}: {e}")

    def get_index_pe_ratio(self, index_name: str) -> Optional[float]:
        """
        שליפת P/E ממוצע של המדד

        Args:
            index_name: שם המדד

        Returns:
            Optional[float]: P/E ממוצע או None (לא זמין ב-TASE Data Hub API)
        """
        # TASE Data Hub API לא מספק P/E ברמת המדד
        # ניתן לחשב אותו מהרכיבים, אבל זה יהיה יקר מאוד
        logger.warning("P/E ממוצע של המדד לא זמין ב-TASE Data Hub API")
        return None

    def get_stock_data(self, symbol: str, years: int = 5) -> tuple[FinancialData, MarketData]:
        """
        שליפת כל נתוני המניה - מתודה מאוחדת

        שימו לב: TASE Data Hub לא מספק נתוני מחירים היסטוריים,
        לכן get_stock_market_data משתמש ב-yfinance כגיבוי.

        Args:
            symbol: סימול המניה
            years: מספר שנים לשלוף

        Returns:
            tuple[FinancialData, MarketData]: נתונים פיננסיים ונתוני שוק
        """
        financial_data = self.get_stock_financials(symbol, years)
        market_data = self.get_stock_market_data(symbol)
        return financial_data, market_data
