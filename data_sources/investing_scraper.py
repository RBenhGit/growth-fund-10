"""
Investing.com Web Scraper
שליפת נתונים פיננסיים מ-Investing.com באמצעות Selenium
"""

import time
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from loguru import logger

from .base_data_source import BaseDataSource
from models import FinancialData, MarketData


class InvestingScraper(BaseDataSource):
    """Scraper לשליפת נתונים מ-Investing.com"""

    # URLs
    BASE_URL = "https://www.investing.com"
    LOGIN_URL = f"{BASE_URL}/members-admin/auth/signIn"

    # Index URLs
    INDEX_URLS = {
        "TASE125": f"{BASE_URL}/indices/ta-125-components",
        "SP500": f"{BASE_URL}/indices/us-spx-500-components"
    }

    def __init__(self, email: str, password: str, headless: bool = False):
        """
        אתחול Scraper

        Args:
            email: אימייל Investing.com
            password: סיסמה
            headless: האם להריץ בלי חלון דפדפן
        """
        self.email = email
        self.password = password
        self.headless = headless
        self.driver: Optional[webdriver.Chrome] = None
        self.is_logged_in = False

        logger.info("Investing.com Scraper initialized")

    def _init_driver(self):
        """אתחול Chrome WebDriver"""
        if self.driver is not None:
            return

        logger.info("Initializing Chrome WebDriver...")

        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")

        # הגדרות נוספות
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

        # השבתת התראות
        chrome_options.add_experimental_option("prefs", {
            "profile.default_content_setting_values.notifications": 2
        })

        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.maximize_window()
            logger.info("Chrome WebDriver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            raise

    def _handle_cookie_consent(self):
        """טיפול בחלון הסכמה לעוגיות"""
        try:
            # ניסיון למצוא ולסגור חלון cookies
            cookie_selectors = [
                "button#onetrust-accept-btn-handler",
                "button.accept-cookies",
                "button[id*='cookie'][id*='accept']",
                "button[class*='cookie'][class*='accept']"
            ]

            for selector in cookie_selectors:
                try:
                    cookie_btn = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    cookie_btn.click()
                    logger.info(f"Clicked cookie consent button: {selector}")
                    time.sleep(1)
                    return True
                except:
                    continue
        except Exception as e:
            logger.debug(f"No cookie consent found or already handled: {e}")
        return False

    def login(self) -> bool:
        """
        התחברות ל-Investing.com

        Returns:
            bool: True אם ההתחברות הצליחה
        """
        if self.is_logged_in:
            logger.info("Already logged in")
            return True

        self._init_driver()

        try:
            logger.info(f"Navigating to login page: {self.LOGIN_URL}")
            self.driver.get(self.LOGIN_URL)
            time.sleep(3)

            # טיפול בחלון cookies
            self._handle_cookie_consent()

            # שמירת screenshot לדיבוג
            try:
                self.driver.save_screenshot("login_page_debug.png")
                logger.info("Saved screenshot: login_page_debug.png")
            except:
                pass

            # המתן לטעינת דף
            wait = WebDriverWait(self.driver, 15)

            # ניסיון למצוא שדה אימייל עם מספר אפשרויות
            logger.info("Looking for email field...")
            email_field = None
            email_selectors = [
                (By.ID, "loginFormUser_email"),
                (By.NAME, "email"),
                (By.CSS_SELECTOR, "input[type='email']"),
                (By.CSS_SELECTOR, "input[name='email']"),
                (By.XPATH, "//input[@type='email' or @name='email']")
            ]

            for by_type, selector in email_selectors:
                try:
                    email_field = wait.until(
                        EC.presence_of_element_located((by_type, selector))
                    )
                    logger.info(f"Found email field using: {by_type}={selector}")
                    break
                except TimeoutException:
                    continue

            if not email_field:
                logger.error("Could not find email field with any selector")
                logger.error(f"Current URL: {self.driver.current_url}")
                logger.error(f"Page source length: {len(self.driver.page_source)}")
                return False

            email_field.clear()
            email_field.send_keys(self.email)
            logger.info("Email entered successfully")

            # מציאת שדה סיסמה
            logger.info("Looking for password field...")
            password_field = None
            password_selectors = [
                (By.ID, "loginForm_password"),
                (By.NAME, "password"),
                (By.CSS_SELECTOR, "input[type='password']"),
                (By.XPATH, "//input[@type='password']")
            ]

            for by_type, selector in password_selectors:
                try:
                    password_field = self.driver.find_element(by_type, selector)
                    logger.info(f"Found password field using: {by_type}={selector}")
                    break
                except NoSuchElementException:
                    continue

            if not password_field:
                logger.error("Could not find password field")
                return False

            password_field.clear()
            password_field.send_keys(self.password)
            logger.info("Password entered successfully")

            # לחיצה על כפתור התחברות
            logger.info("Looking for login button...")
            login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_button.click()
            logger.info("Clicked login button")

            # המתן לטעינת דף הבית
            time.sleep(5)

            # בדיקה אם ההתחברות הצליחה
            current_url = self.driver.current_url
            logger.info(f"Current URL after login: {current_url}")

            if "members-admin" not in current_url:
                self.is_logged_in = True
                logger.info("Login successful!")
                return True
            else:
                logger.error("Login failed - still on login page")
                # שמירת screenshot נוספת
                try:
                    self.driver.save_screenshot("login_failed_debug.png")
                    logger.info("Saved failed login screenshot: login_failed_debug.png")
                except:
                    pass
                return False

        except TimeoutException as e:
            logger.error(f"Timeout during login: {e}")
            logger.error(f"Current URL: {self.driver.current_url if self.driver else 'N/A'}")
            return False
        except Exception as e:
            logger.error(f"Error during login: {e}")
            if self.driver:
                logger.error(f"Current URL: {self.driver.current_url}")
            return False

    def logout(self):
        """ניתוק וסגירת הדפדפן"""
        if self.driver:
            logger.info("Closing WebDriver...")
            self.driver.quit()
            self.driver = None
            self.is_logged_in = False
            logger.info("WebDriver closed")

    def get_index_constituents(self, index_name: str) -> List[Dict]:
        """
        שליפת רשימת רכיבי מדד

        Args:
            index_name: שם המדד (TASE125/SP500)

        Returns:
            List[Dict]: רשימת מניות עם פרטים בסיסיים
        """
        if not self.is_logged_in:
            if not self.login():
                raise Exception("Failed to login")

        if index_name not in self.INDEX_URLS:
            raise ValueError(f"Unknown index: {index_name}. Must be TASE125 or SP500")

        url = self.INDEX_URLS[index_name]
        logger.info(f"Fetching constituents for {index_name} from {url}")

        try:
            self.driver.get(url)
            time.sleep(3)

            # המתן לטעינת טבלה
            wait = WebDriverWait(self.driver, 10)
            table = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.genTbl"))
            )

            # שליפת כל השורות
            rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")
            logger.info(f"Found {len(rows)} stocks in {index_name}")

            constituents = []
            for row in rows:
                try:
                    # שליפת תאים
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) < 3:
                        continue

                    # שם המניה וסימול
                    name_cell = cells[1]
                    name = name_cell.text.strip()

                    # ניסיון לשלוף את הסימול מה-link
                    link = name_cell.find_element(By.TAG_NAME, "a")
                    href = link.get_attribute("href")
                    symbol = href.split("/")[-1] if href else name

                    constituents.append({
                        "symbol": symbol,
                        "name": name,
                        "index": index_name,
                        "url": href
                    })

                except Exception as e:
                    logger.warning(f"Failed to parse row: {e}")
                    continue

            logger.info(f"Successfully fetched {len(constituents)} constituents")
            return constituents

        except TimeoutException:
            logger.error(f"Timeout while fetching {index_name} constituents")
            raise
        except Exception as e:
            logger.error(f"Error fetching constituents: {e}")
            raise

    def get_stock_financials(self, symbol: str, years: int = 5) -> FinancialData:
        """
        שליפת נתונים פיננסיים למניה

        Args:
            symbol: סימול המניה
            years: מספר שנים לשלוף

        Returns:
            FinancialData: נתונים פיננסיים
        """
        if not self.is_logged_in:
            if not self.login():
                raise Exception("Failed to login")

        logger.info(f"Fetching financials for {symbol} ({years} years)")

        # TODO: מימוש מלא של שליפת נתונים פיננסיים
        # כרגע מחזיר אובייקט ריק
        financial_data = FinancialData(symbol=symbol)

        logger.warning(f"Financial data fetching not fully implemented yet for {symbol}")
        return financial_data

    def get_stock_market_data(self, symbol: str) -> MarketData:
        """
        שליפת נתוני שוק למניה

        Args:
            symbol: סימול המניה

        Returns:
            MarketData: נתוני שוק
        """
        if not self.is_logged_in:
            if not self.login():
                raise Exception("Failed to login")

        logger.info(f"Fetching market data for {symbol}")

        # TODO: מימוש מלא של שליפת נתוני שוק
        # כרגע מחזיר אובייקט עם ערכי דמה
        market_data = MarketData(
            symbol=symbol,
            name=f"{symbol} Inc",
            market_cap=1000000000.0,
            current_price=100.0
        )

        logger.warning(f"Market data fetching not fully implemented yet for {symbol}")
        return market_data

    def get_index_pe_ratio(self, index_name: str) -> Optional[float]:
        """
        שליפת P/E ממוצע של המדד

        Args:
            index_name: שם המדד

        Returns:
            Optional[float]: P/E ממוצע או None
        """
        logger.info(f"Fetching P/E ratio for {index_name}")

        # TODO: מימוש שליפת P/E של המדד
        # כרגע מחזיר ערך דמה
        logger.warning(f"Index P/E fetching not fully implemented yet for {index_name}")
        return 25.0

    def __enter__(self):
        """Context manager entry"""
        self.login()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.logout()

    def __del__(self):
        """Destructor"""
        self.logout()
