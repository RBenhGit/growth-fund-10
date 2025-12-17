"""
Financial Modeling Prep API Data Source
מקור נתונים מבוסס על FMP API
"""

import requests
from typing import List, Dict, Optional
from models import FinancialData, MarketData, Stock
from .base_data_source import BaseDataSource
from config import settings


class FMPDataSource(BaseDataSource):
    """מקור נתונים מבוסס FMP API"""

    def __init__(self, api_key: Optional[str] = None):
        """
        אתחול מקור נתונים FMP

        Args:
            api_key: מפתח API (אם לא צוין - ייקח מהגדרות)
        """
        self.api_key = api_key or settings.FMP_API_KEY
        self.base_url = "https://financialmodelingprep.com/api/v3"

        if not self.api_key:
            raise ValueError("FMP_API_KEY חסר בהגדרות")

    def login(self) -> bool:
        """
        בדיקת תקינות החיבור ל-API

        Returns:
            bool: True אם החיבור תקין
        """
        try:
            url = f"{self.base_url}/profile/AAPL?apikey={self.api_key}"
            response = requests.get(url, timeout=10)
            return response.status_code == 200
        except Exception:
            return False

    def logout(self):
        """לא נדרש עבור FMP API"""
        pass

    def get_index_constituents(self, index_name: str) -> List[Dict]:
        """
        שליפת רשימת רכיבי מדד

        Args:
            index_name: שם המדד (TASE125/SP500)

        Returns:
            List[Dict]: רשימת מניות עם פרטים בסיסיים
        """
        if index_name == "SP500":
            url = f"{self.base_url}/sp500_constituent?apikey={self.api_key}"
        elif index_name == "TASE125":
            # FMP לא תומך ישירות במדד ת"א 125
            # נחזיר רשימה ריקה או נזרוק שגיאה
            raise NotImplementedError("FMP API אינו תומך במדד TASE125")
        else:
            raise ValueError(f"מדד לא נתמך: {index_name}")

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            constituents = response.json()

            return [
                {
                    "symbol": stock["symbol"],
                    "name": stock["name"],
                    "sector": stock.get("sector", ""),
                    "sub_sector": stock.get("subSector", "")
                }
                for stock in constituents
            ]

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"שגיאה בשליפת רכיבי המדד: {e}")

    def get_stock_financials(self, symbol: str, years: int = 5) -> FinancialData:
        """
        שליפת נתונים פיננסיים למניה

        Args:
            symbol: סימול המניה
            years: מספר שנים לשלוף

        Returns:
            FinancialData: נתונים פיננסיים
        """
        try:
            # 1. Income Statement
            income_url = f"{self.base_url}/income-statement/{symbol}?limit={years}&apikey={self.api_key}"
            income_response = requests.get(income_url, timeout=30)
            income_response.raise_for_status()
            income_statements = income_response.json()

            # 2. Balance Sheet
            balance_url = f"{self.base_url}/balance-sheet-statement/{symbol}?limit=1&apikey={self.api_key}"
            balance_response = requests.get(balance_url, timeout=30)
            balance_response.raise_for_status()
            balance_sheets = balance_response.json()

            # 3. Cash Flow
            cashflow_url = f"{self.base_url}/cash-flow-statement/{symbol}?limit={years}&apikey={self.api_key}"
            cashflow_response = requests.get(cashflow_url, timeout=30)
            cashflow_response.raise_for_status()
            cashflow_statements = cashflow_response.json()

            # 4. Profile (for current price and market cap)
            profile_url = f"{self.base_url}/profile/{symbol}?apikey={self.api_key}"
            profile_response = requests.get(profile_url, timeout=30)
            profile_response.raise_for_status()
            profile_data = profile_response.json()[0] if profile_response.json() else {}

            # בניית אובייקט FinancialData
            revenues = {}
            net_incomes = {}
            operating_incomes = {}
            operating_cash_flows = {}

            for stmt in income_statements:
                year = int(stmt['date'][:4])
                revenues[year] = float(stmt.get('revenue', 0))
                net_incomes[year] = float(stmt.get('netIncome', 0))
                operating_incomes[year] = float(stmt.get('operatingIncome', 0))

            for stmt in cashflow_statements:
                year = int(stmt['date'][:4])
                operating_cash_flows[year] = float(stmt.get('operatingCashFlow', 0))

            # נתוני מאזן (אחרון)
            total_debt = None
            total_equity = None
            if balance_sheets:
                latest_balance = balance_sheets[0]
                total_debt = float(latest_balance.get('totalDebt', 0))
                total_equity = float(latest_balance.get('totalStockholdersEquity', 0))

            return FinancialData(
                symbol=symbol,
                revenues=revenues,
                net_incomes=net_incomes,
                operating_incomes=operating_incomes,
                operating_cash_flows=operating_cash_flows,
                total_debt=total_debt,
                total_equity=total_equity,
                market_cap=profile_data.get('mktCap'),
                current_price=profile_data.get('price'),
                pe_ratio=profile_data.get('pe')
            )

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"שגיאה בשליפת נתונים פיננסיים עבור {symbol}: {e}")
        except (KeyError, IndexError, ValueError) as e:
            raise RuntimeError(f"שגיאה בעיבוד נתונים עבור {symbol}: {e}")

    def get_stock_market_data(self, symbol: str) -> MarketData:
        """
        שליפת נתוני שוק למניה

        Args:
            symbol: סימול המניה

        Returns:
            MarketData: נתוני שוק
        """
        try:
            # Profile data
            profile_url = f"{self.base_url}/profile/{symbol}?apikey={self.api_key}"
            profile_response = requests.get(profile_url, timeout=30)
            profile_response.raise_for_status()
            profile_data = profile_response.json()[0]

            # Historical prices (last year)
            history_url = f"{self.base_url}/historical-price-full/{symbol}?apikey={self.api_key}"
            history_response = requests.get(history_url, timeout=30)
            history_response.raise_for_status()
            history_data = history_response.json()

            price_history = {}
            if 'historical' in history_data:
                # קח רק את השנה האחרונה
                for entry in history_data['historical'][:365]:
                    price_history[entry['date']] = float(entry['close'])

            return MarketData(
                symbol=symbol,
                name=profile_data['companyName'],
                market_cap=float(profile_data['mktCap']),
                current_price=float(profile_data['price']),
                pe_ratio=float(profile_data['pe']) if profile_data.get('pe') else None,
                price_history=price_history
            )

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"שגיאה בשליפת נתוני שוק עבור {symbol}: {e}")
        except (KeyError, IndexError, ValueError) as e:
            raise RuntimeError(f"שגיאה בעיבוד נתוני שוק עבור {symbol}: {e}")

    def get_index_pe_ratio(self, index_name: str) -> Optional[float]:
        """
        שליפת P/E ממוצע של המדד

        Args:
            index_name: שם המדד

        Returns:
            Optional[float]: P/E ממוצע או None
        """
        # FMP לא מספק P/E ממוצע למדד
        # נחשב אותו בעצמנו מרכיבי המדד
        try:
            constituents = self.get_index_constituents(index_name)
            pe_ratios = []

            for stock in constituents[:50]:  # נדגם רק 50 ראשונות כדי לחסוך בקריאות API
                try:
                    profile_url = f"{self.base_url}/profile/{stock['symbol']}?apikey={self.api_key}"
                    response = requests.get(profile_url, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        if data and data[0].get('pe'):
                            pe_ratios.append(float(data[0]['pe']))
                except Exception:
                    continue

            if pe_ratios:
                return sum(pe_ratios) / len(pe_ratios)
            return None

        except Exception:
            return None
