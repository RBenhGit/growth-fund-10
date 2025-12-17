"""
EOD Historical Data API Data Source
מקור נתונים מבוסס על EODHD API
"""

import requests
import yfinance as yf
import logging
from typing import List, Dict, Optional
from models import FinancialData, MarketData, Stock
from .base_data_source import BaseDataSource
from config import settings

logger = logging.getLogger(__name__)


class EODHDDataSource(BaseDataSource):
    """מקור נתונים מבוסס EODHD API"""

    def __init__(self, api_key: Optional[str] = None):
        """
        אתחול מקור נתונים EODHD

        Args:
            api_key: מפתח API (אם לא צוין - ייקח מהגדרות)
        """
        self.api_key = api_key or settings.EODHD_API_KEY
        self.base_url = "https://eodhd.com/api"

        if not self.api_key:
            raise ValueError("EODHD_API_KEY חסר בהגדרות")

    def login(self) -> bool:
        """
        בדיקת תקינות החיבור ל-API

        Returns:
            bool: True אם החיבור תקין
        """
        try:
            url = f"{self.base_url}/fundamentals/AAPL.US"
            params = {"api_token": self.api_key, "fmt": "json"}
            response = requests.get(url, params=params, timeout=10)
            return response.status_code == 200
        except Exception:
            return False

    def logout(self):
        """לא נדרש עבור EODHD API"""
        pass

    def _get_exchange_suffix(self, index_name: str) -> str:
        """
        החזרת סיומת הבורסה לפי שם המדד

        Args:
            index_name: שם המדד

        Returns:
            str: סיומת הבורסה (.US או .TA)
        """
        if index_name == "SP500":
            return ".US"
        elif index_name == "TASE125":
            return ".TA"
        else:
            raise ValueError(f"מדד לא נתמך: {index_name}")

    def get_index_constituents(self, index_name: str) -> List[Dict]:
        """
        שליפת רשימת רכיבי מדד

        Args:
            index_name: שם המדד (TASE125/SP500)

        Returns:
            List[Dict]: רשימת מניות עם פרטים בסיסיים
        """
        try:
            if index_name == "SP500":
                # עבור S&P 500 - נשלוף את רשימת המניות מ-index composition
                # EODHD מספק את הרכב המדד דרך fundamentals API
                url = f"{self.base_url}/fundamentals/GSPC.INDX"
                params = {
                    "api_token": self.api_key,
                    "fmt": "json",
                    "filter": "Components"
                }
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()

                # המרה לפורמט אחיד
                # EODHD מחזיר dict עם מפתחות מספריים ('0', '1', '2'...)
                # וערכים שמכילים Code, Name, Sector, Industry
                constituents = []
                if isinstance(data, dict):
                    for key, info in data.items():
                        # השתמש ב-Code (סימול המניה) ולא במפתח המספרי
                        if isinstance(info, dict) and "Code" in info:
                            constituents.append({
                                "symbol": info["Code"],  # זה הסימול האמיתי כמו AAPL, MSFT
                                "name": info.get("Name", info["Code"]),
                                "sector": info.get("Sector", ""),
                                "sub_sector": info.get("Industry", "")
                            })
                return constituents

            elif index_name == "TASE125":
                # עבור ת"א 125 - נשתמש ב-fundamentals API
                url = f"{self.base_url}/fundamentals/TA125.INDX"
                params = {
                    "api_token": self.api_key,
                    "fmt": "json",
                    "filter": "Components"
                }
                response = requests.get(url, params=params, timeout=30)

                if response.status_code == 200:
                    data = response.json()
                    constituents = []
                    if isinstance(data, dict):
                        for key, info in data.items():
                            if isinstance(info, dict) and "Code" in info:
                                constituents.append({
                                    "symbol": info["Code"],
                                    "name": info.get("Name", info["Code"]),
                                    "sector": info.get("Sector", ""),
                                    "sub_sector": info.get("Industry", "")
                                })
                    return constituents
                else:
                    # אם TA125.INDX לא זמין, נשתמש ב-exchange list
                    url = f"{self.base_url}/exchange-symbol-list/TA"
                    params = {
                        "api_token": self.api_key,
                        "fmt": "json",
                        "type": "common_stock"
                    }
                    response = requests.get(url, params=params, timeout=30)
                    response.raise_for_status()
                    all_stocks = response.json()

                    # נקח את המניות הגדולות ביותר
                    constituents = []
                    for stock in all_stocks[:125]:
                        constituents.append({
                            "symbol": stock["Code"],
                            "name": stock["Name"],
                            "sector": "",
                            "sub_sector": ""
                        })
                    return constituents
            else:
                raise ValueError(f"מדד לא נתמך: {index_name}")

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"שגיאה בשליפת רכיבי המדד: {e}")

    def get_stock_data(self, symbol: str, years: int = 5) -> tuple[FinancialData, MarketData]:
        """
        שליפת כל נתוני המניה (מיטוב - 2 EODHD API calls + yfinance חינם)

        Args:
            symbol: סימול המניה (כולל סיומת בורסה, למשל AAPL.US)
            years: מספר שנים לשלוף

        Returns:
            tuple[FinancialData, MarketData]: נתונים פיננסיים ונתוני שוק
        """
        try:
            # EODHD API Call #1: Fundamentals (מכיל הכל - financials, general, highlights)
            fund_url = f"{self.base_url}/fundamentals/{symbol}"
            fund_params = {"api_token": self.api_key, "fmt": "json"}
            fund_response = requests.get(fund_url, params=fund_params, timeout=30)
            fund_response.raise_for_status()
            data = fund_response.json()

            # חילוץ נתונים פיננסיים
            financials = data.get("Financials", {})
            income_statements = financials.get("Income_Statement", {}).get("yearly", {})
            balance_sheets = financials.get("Balance_Sheet", {}).get("yearly", {})
            cashflow_statements = financials.get("Cash_Flow", {}).get("yearly", {})
            highlights = data.get("Highlights", {})
            general = data.get("General", {})

            # בניית מבני נתונים פיננסיים
            revenues = {}
            net_incomes = {}
            operating_incomes = {}
            operating_cash_flows = {}

            sorted_years = sorted(income_statements.keys(), reverse=True)[:years]
            for year in sorted_years:
                year_int = int(year.split("-")[0])
                stmt = income_statements[year]
                rev = stmt.get("totalRevenue", 0)
                revenues[year_int] = float(rev) if rev is not None else 0.0
                ni = stmt.get("netIncome", 0)
                net_incomes[year_int] = float(ni) if ni is not None else 0.0
                ebitda = stmt.get("ebitda", 0)
                operating_incomes[year_int] = float(ebitda) if ebitda is not None else 0.0

            for year in sorted(cashflow_statements.keys(), reverse=True)[:years]:
                year_int = int(year.split("-")[0])
                stmt = cashflow_statements[year]
                ocf = stmt.get("totalCashFromOperatingActivities", 0)
                operating_cash_flows[year_int] = float(ocf) if ocf is not None else 0.0

            # נתוני מאזן אחרונים
            total_debt = 0.0
            total_equity = 0.0
            if balance_sheets:
                latest_year = sorted(balance_sheets.keys(), reverse=True)[0]
                latest_balance = balance_sheets[latest_year]
                td = latest_balance.get("totalDebt", 0)
                total_debt = float(td) if td is not None else 0.0
                te = latest_balance.get("totalStockholderEquity", 0)
                total_equity = float(te) if te is not None else 0.0

            # נתוני שוק מ-highlights
            mc = highlights.get("MarketCapitalization")
            market_cap = float(mc) if mc is not None and mc != 0 else None
            pe = highlights.get("PERatio")
            pe_ratio = float(pe) if pe is not None and pe != 0 else None

            # Get current price from yfinance (free, no API limit)
            current_price = None
            try:
                # Convert EODHD symbol to yfinance format (remove .US, .TA suffix)
                yf_symbol = symbol.split('.')[0]
                ticker = yf.Ticker(yf_symbol)
                info = ticker.info
                current_price = info.get('currentPrice') or info.get('regularMarketPrice')
                if current_price:
                    current_price = float(current_price)
            except Exception:
                pass

            # EODHD API Call #2: Historical prices for financial report dates only
            # Get prices for each year's financial report date + current price
            from datetime import datetime

            price_history = {}

            # Extract financial report dates from income statements
            report_dates = sorted(income_statements.keys(), reverse=True)[:years]

            # Fetch price for each financial report date
            for report_date in report_dates:
                try:
                    # EODHD endpoint for specific date: /eod/{SYMBOL}?from=DATE&to=DATE
                    hist_url = f"{self.base_url}/eod/{symbol}"
                    hist_params = {
                        "api_token": self.api_key,
                        "fmt": "json",
                        "from": report_date,
                        "to": report_date
                    }

                    hist_response = requests.get(hist_url, params=hist_params, timeout=10)
                    hist_response.raise_for_status()

                    hist_data = hist_response.json()
                    if hist_data and isinstance(hist_data, list) and len(hist_data) > 0:
                        close = hist_data[0].get("close")
                        if close is not None:
                            price_history[report_date] = float(close)
                            logger.debug(f"Fetched price for {symbol} on {report_date}: {close}")
                    else:
                        logger.warning(f"No price data for {symbol} on {report_date}")

                except requests.exceptions.RequestException as e:
                    logger.error(f"EODHD API failed for {symbol} on {report_date}: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error fetching price for {symbol} on {report_date}: {e}")

            # Add current price (already fetched from yfinance above)
            if current_price:
                current_date = datetime.now().strftime("%Y-%m-%d")
                price_history[current_date] = current_price
                logger.debug(f"Added current price for {symbol}: {current_price}")

            # Fallback to yfinance if EODHD failed for some/all dates
            if len(price_history) < len(report_dates):
                missing_dates = [d for d in report_dates if d not in price_history]
                logger.info(f"Falling back to yfinance for {symbol} missing dates: {missing_dates}")

                try:
                    yf_symbol = symbol.split('.')[0]
                    ticker = yf.Ticker(yf_symbol)

                    for report_date in missing_dates:
                        # Get historical data around that date
                        from datetime import timedelta
                        import pandas as pd

                        date_obj = datetime.strptime(report_date, "%Y-%m-%d")
                        start_date = (date_obj - timedelta(days=7)).strftime("%Y-%m-%d")
                        end_date = (date_obj + timedelta(days=7)).strftime("%Y-%m-%d")

                        hist_df = ticker.history(start=start_date, end=end_date)

                        if not hist_df.empty:
                            # Make date_obj timezone-aware to match hist_df index
                            target_date = pd.Timestamp(date_obj).tz_localize('UTC')

                            # Find the closest date to report_date
                            if target_date in hist_df.index:
                                row = hist_df.loc[target_date]
                                price_history[report_date] = float(row['Close'])
                                logger.info(f"yfinance exact match for {symbol} on {report_date}: {row['Close']}")
                            else:
                                # Find nearest date
                                idx = hist_df.index.get_indexer([target_date], method='nearest')[0]
                                if idx >= 0 and idx < len(hist_df):
                                    row = hist_df.iloc[idx]
                                    actual_date = hist_df.index[idx].strftime("%Y-%m-%d")
                                    price_history[report_date] = float(row['Close'])
                                    logger.info(f"yfinance nearest match for {symbol}: {report_date} -> {actual_date}: {row['Close']}")
                        else:
                            logger.warning(f"yfinance returned no data for {symbol} on {report_date}")

                except Exception as e:
                    logger.error(f"yfinance fallback failed for {symbol}: {e}")

            # Final validation
            if not price_history:
                logger.warning(f"No price history available for {symbol} - momentum/valuation will use defaults")

            # בניית אובייקטי FinancialData ו-MarketData
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

            market_data = MarketData(
                symbol=symbol,
                name=general.get("Name", symbol),
                market_cap=float(mc) if mc is not None else 0.0,
                current_price=current_price if current_price and current_price > 0 else 0.0,
                pe_ratio=pe_ratio,
                price_history=price_history
            )

            return financial_data, market_data

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"שגיאה בשליפת נתונים עבור {symbol}: {e}")
        except (KeyError, ValueError) as e:
            raise RuntimeError(f"שגיאה בעיבוד נתונים עבור {symbol}: {e}")

    def get_stock_financials(self, symbol: str, years: int = 5) -> FinancialData:
        """
        שליפת נתונים פיננסיים למניה
        (שימוש ב-get_stock_data למניעת כפילויות)

        Args:
            symbol: סימול המניה (כולל סיומת בורסה, למשל AAPL.US)
            years: מספר שנים לשלוף

        Returns:
            FinancialData: נתונים פיננסיים
        """
        financial_data, _ = self.get_stock_data(symbol, years)
        return financial_data

    def get_stock_market_data(self, symbol: str) -> MarketData:
        """
        שליפת נתוני שוק למניה
        (שימוש ב-get_stock_data למניעת כפילויות)

        Args:
            symbol: סימול המניה (כולל סיומת בורסה)

        Returns:
            MarketData: נתוני שוק
        """
        _, market_data = self.get_stock_data(symbol, years=5)
        return market_data

    def get_index_pe_ratio(self, index_name: str) -> Optional[float]:
        """
        שליפת P/E ממוצע של המדד

        Args:
            index_name: שם המדד

        Returns:
            Optional[float]: P/E ממוצע או None
        """
        try:
            if index_name == "SP500":
                # P/E עבור S&P 500
                url = f"{self.base_url}/fundamentals/GSPC.INDX"
                params = {"api_token": self.api_key, "fmt": "json"}
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    highlights = data.get("Highlights", {})
                    pe = highlights.get("PERatio")
                    return float(pe) if pe is not None and pe != 0 else None
            return None
        except Exception:
            return None
