"""
Backtest Module for Growth Fund
מודול בדיקה רטרוספקטיבית של קרן הצמיחה
"""

import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import yfinance as yf
import pandas as pd
import numpy as np
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
import matplotlib.pyplot as plt
from pathlib import Path

# Fix Hebrew encoding for Windows console
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

console = Console()


class FundBacktest:
    """
    מחלקה לביצוע בדיקה רטרוספקטיבית של קרן
    """

    def __init__(self, fund_file: str, years: int = 10):
        """
        אתחול בדיקה רטרוספקטיבית

        Args:
            fund_file: נתיב לקובץ המגדיר את הקרן
            years: מספר שנים לבדיקה רטרוספקטיבית
        """
        self.fund_file = fund_file
        self.years = years
        self.portfolio = {}
        self.weights = {}
        self.benchmarks = {}

        # תאריכים
        self.end_date = datetime.now()
        self.start_date = self.end_date - timedelta(days=years * 365)

    def parse_fund_file(self):
        """
        קריאת קובץ הקרן וחילוץ פרטי המניות והמשקלות
        """
        console.print(f"[cyan]קורא קובץ קרן: {self.fund_file}[/cyan]")

        with open(self.fund_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # חיפוש טבלת המניות
        in_table = False
        for line in lines:
            if '| שם חברה |' in line:
                in_table = True
                continue
            if in_table and line.startswith('|') and not line.startswith('|---'):
                parts = [p.strip() for p in line.split('|')[1:-1]]
                if len(parts) >= 4 and parts[0] and parts[1]:
                    symbol = parts[1]  # סימול
                    weight_str = parts[3].replace('%', '').strip()  # משקל
                    try:
                        weight = float(weight_str) / 100.0
                        # המרה לפורמט yfinance (הסרת .US)
                        yf_symbol = symbol.split('.')[0] if '.' in symbol else symbol
                        self.portfolio[yf_symbol] = {
                            'name': parts[0],
                            'weight': weight,
                            'original_symbol': symbol
                        }
                        self.weights[yf_symbol] = weight
                    except ValueError:
                        continue
            if in_table and line.startswith('**עלות'):
                break

        console.print(f"[green]נמצאו {len(self.portfolio)} מניות בקרן[/green]")
        return self.portfolio

    def fetch_historical_data(self, symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        שליפת נתונים היסטוריים למניה

        Args:
            symbol: סימול המניה (פורמט yfinance)
            start_date: תאריך התחלה
            end_date: תאריך סיום

        Returns:
            pd.DataFrame: נתונים היסטוריים
        """
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(
                start=start_date.strftime('%Y-%m-%d'),
                end=end_date.strftime('%Y-%m-%d')
            )
            return hist
        except Exception as e:
            console.print(f"[red]שגיאה בשליפת נתונים עבור {symbol}: {e}[/red]")
            return pd.DataFrame()

    def fetch_all_data(self):
        """
        שליפת כל הנתונים ההיסטוריים - מניות ומדדים
        """
        console.print("\n[cyan]שליפת נתונים היסטוריים...[/cyan]")

        all_data = {}

        with Progress() as progress:
            # שליפת נתוני מניות
            task1 = progress.add_task(
                "[cyan]שולף נתוני מניות...",
                total=len(self.portfolio)
            )

            for symbol in self.portfolio.keys():
                hist = self.fetch_historical_data(symbol, self.start_date, self.end_date)
                if not hist.empty:
                    all_data[symbol] = hist['Close']
                progress.update(task1, advance=1)

            # שליפת נתוני מדדים
            task2 = progress.add_task("[cyan]שולף נתוני מדדים...", total=2)

            # S&P 500
            sp500 = self.fetch_historical_data('^GSPC', self.start_date, self.end_date)
            if not sp500.empty:
                self.benchmarks['S&P 500'] = sp500['Close']
            progress.update(task2, advance=1)

            # NASDAQ
            nasdaq = self.fetch_historical_data('^IXIC', self.start_date, self.end_date)
            if not nasdaq.empty:
                self.benchmarks['NASDAQ'] = nasdaq['Close']
            progress.update(task2, advance=1)

        # יצירת DataFrame מאוחד
        if all_data:
            self.stock_data = pd.DataFrame(all_data)
            console.print(f"[green]נשלפו נתונים עבור {len(all_data)} מניות[/green]")

            # Track actual date range from fetched data
            self.actual_start_date = self.stock_data.index.min()
            self.actual_end_date = self.stock_data.index.max()
            self.actual_days = len(self.stock_data)
        else:
            console.print("[red]לא נשלפו נתונים[/red]")
            self.stock_data = pd.DataFrame()
            # Fallback to requested dates if no data
            self.actual_start_date = self.start_date
            self.actual_end_date = self.end_date
            self.actual_days = 0

    def calculate_portfolio_returns(self) -> pd.Series:
        """
        חישוב תשואות הקרן

        Returns:
            pd.Series: תשואות יומיות של הקרן
        """
        if self.stock_data.empty:
            return pd.Series()

        # חישוב תשואות יומיות לכל מניה
        returns = self.stock_data.pct_change()

        # חישוב תשואות משוקללות של הקרן
        portfolio_returns = pd.Series(0, index=returns.index)
        for symbol, weight in self.weights.items():
            if symbol in returns.columns:
                portfolio_returns += returns[symbol] * weight

        return portfolio_returns

    def calculate_metrics(self, returns: pd.Series, benchmark_returns: pd.Series = None) -> Dict:
        """
        חישוב מדדי ביצועים מתקדמים

        Args:
            returns: סדרת תשואות
            benchmark_returns: תשואות בנצ'מרק (לחישוב בטא ואלפא)

        Returns:
            Dict: מילון של מדדי ביצועים
        """
        if returns.empty or len(returns) == 0:
            return {}

        # הסרת NaN
        returns = returns.dropna()

        if len(returns) == 0:
            return {}

        # תשואה מצטברת
        cumulative_return = (1 + returns).prod() - 1

        # תשואה שנתית ממוצעת
        annual_return = (1 + cumulative_return) ** (252 / len(returns)) - 1

        # סטיית תקן שנתית (תנודתיות)
        annual_volatility = returns.std() * np.sqrt(252)

        # יחס שארפ (בהנחת ריבית חסרת סיכון של 2%)
        risk_free_rate = 0.02
        sharpe_ratio = (annual_return - risk_free_rate) / annual_volatility if annual_volatility > 0 else 0

        # מקסימום ירידה (Max Drawdown)
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()

        # Sortino Ratio (תנודתיות ירידה בלבד)
        downside_returns = returns[returns < 0]
        downside_deviation = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
        sortino_ratio = (annual_return - risk_free_rate) / downside_deviation if downside_deviation > 0 else 0

        # Calmar Ratio (תשואה / ירידה מקסימלית)
        calmar_ratio = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0

        # Win Rate (אחוז ימים רווחיים)
        win_rate = (returns > 0).sum() / len(returns) if len(returns) > 0 else 0

        # Best and Worst Days
        best_day = returns.max()
        worst_day = returns.min()

        # Positive/Negative Months
        monthly_returns = (1 + returns).resample('M').prod() - 1
        positive_months = (monthly_returns > 0).sum()
        total_months = len(monthly_returns)
        monthly_win_rate = positive_months / total_months if total_months > 0 else 0

        metrics = {
            'cumulative_return': cumulative_return,
            'annual_return': annual_return,
            'annual_volatility': annual_volatility,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio,
            'max_drawdown': max_drawdown,
            'downside_deviation': downside_deviation,
            'win_rate': win_rate,
            'best_day': best_day,
            'worst_day': worst_day,
            'monthly_win_rate': monthly_win_rate,
            'positive_months': positive_months,
            'total_months': total_months
        }

        # חישוב בטא ואלפא אם יש בנצ'מרק
        if benchmark_returns is not None and not benchmark_returns.empty:
            benchmark_returns = benchmark_returns.dropna()
            # יישור התאריכים
            aligned_returns = returns.align(benchmark_returns, join='inner')
            if len(aligned_returns[0]) > 0:
                returns_aligned = aligned_returns[0]
                benchmark_aligned = aligned_returns[1]

                # בטא - רגרסיה לינארית
                covariance = returns_aligned.cov(benchmark_aligned)
                benchmark_variance = benchmark_aligned.var()
                beta = covariance / benchmark_variance if benchmark_variance != 0 else 0

                # אלפא (Jensen's Alpha)
                benchmark_annual = (1 + benchmark_aligned).prod() ** (252 / len(benchmark_aligned)) - 1
                alpha = annual_return - (risk_free_rate + beta * (benchmark_annual - risk_free_rate))

                metrics['beta'] = beta
                metrics['alpha'] = alpha

        return metrics

    def analyze_individual_stocks(self) -> Dict:
        """
        ניתוח ביצועים של כל מניה בנפרד

        Returns:
            Dict: ביצועי כל מניה
        """
        if self.stock_data.empty:
            return {}

        stock_performance = {}

        # חישוב תשואות לכל מניה
        for symbol in self.stock_data.columns:
            stock_returns = self.stock_data[symbol].pct_change().dropna()

            if len(stock_returns) > 0:
                # חישוב מדדים בסיסיים
                cumulative_return = (1 + stock_returns).prod() - 1
                annual_return = (1 + cumulative_return) ** (252 / len(stock_returns)) - 1
                annual_volatility = stock_returns.std() * np.sqrt(252)

                stock_performance[symbol] = {
                    'name': self.portfolio[symbol]['name'],
                    'weight': self.portfolio[symbol]['weight'],
                    'cumulative_return': cumulative_return,
                    'annual_return': annual_return,
                    'volatility': annual_volatility,
                    'returns': stock_returns
                }

        return stock_performance

    def run_backtest(self):
        """
        הרצת בדיקה רטרוספקטיבית מלאה
        """
        # קריאת הקרן
        self.parse_fund_file()

        # שליפת נתונים
        self.fetch_all_data()

        if self.stock_data.empty:
            console.print("[red]לא ניתן להריץ בדיקה רטרוספקטיבית - אין נתונים[/red]")
            return None

        # חישוב תשואות
        console.print("\n[cyan]מחשב תשואות...[/cyan]")
        portfolio_returns = self.calculate_portfolio_returns()

        # חישוב מדדים
        results = {}

        # קבלת תשואות S&P 500 לחישוב בטא ואלפא
        sp500_returns = None
        if 'S&P 500' in self.benchmarks:
            sp500_returns = self.benchmarks['S&P 500'].pct_change().dropna()

        # מדדי הקרן (עם בטא ואלפא לעומת S&P 500)
        results['Fund'] = self.calculate_metrics(portfolio_returns, sp500_returns)
        results['Fund']['returns'] = portfolio_returns

        # מדדי בנצ'מרק
        for name, prices in self.benchmarks.items():
            benchmark_returns = prices.pct_change().dropna()
            results[name] = self.calculate_metrics(benchmark_returns)
            results[name]['returns'] = benchmark_returns

        # ניתוח מניות בודדות
        results['individual_stocks'] = self.analyze_individual_stocks()

        return results

    def generate_report(self, results: Dict):
        """
        יצירת דוח תוצאות

        Args:
            results: תוצאות הבדיקה הרטרוספקטיבית
        """
        if not results:
            return

        console.print("\n[bold cyan]תוצאות בדיקה רטרוספקטיבית - {} שנים[/bold cyan]".format(self.years))
        console.print(f"[dim]תאריך מבוקש: {self.start_date.strftime('%Y-%m-%d')} עד {self.end_date.strftime('%Y-%m-%d')}[/dim]")
        console.print(f"[dim]תאריך בפועל: {self.actual_start_date.strftime('%Y-%m-%d')} עד {self.actual_end_date.strftime('%Y-%m-%d')} ({self.actual_days} ימי מסחר)[/dim]")

        # Add warning if dates differ significantly
        requested_days = (self.end_date - self.start_date).days
        actual_days = (self.actual_end_date - self.actual_start_date).days
        if actual_days < requested_days * 0.9:  # More than 10% difference
            console.print(f"[yellow]⚠ הנתונים הזמינים מכסים {actual_days/365.25:.1f} שנים בלבד (לא {self.years} שנים מלאים)[/yellow]\n")
        else:
            console.print()

        # טבלת השוואה
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("מדד", style="cyan", width=20)
        table.add_column("תשואה מצטברת", justify="right")
        table.add_column("תשואה שנתית", justify="right")
        table.add_column("תנודתיות", justify="right")
        table.add_column("יחס שארפ", justify="right")
        table.add_column("ירידה מקסימלית", justify="right")

        for name, metrics in results.items():
            if 'cumulative_return' in metrics:
                table.add_row(
                    name,
                    f"{metrics['cumulative_return']*100:.2f}%",
                    f"{metrics['annual_return']*100:.2f}%",
                    f"{metrics['annual_volatility']*100:.2f}%",
                    f"{metrics['sharpe_ratio']:.2f}",
                    f"{metrics['max_drawdown']*100:.2f}%"
                )

        console.print(table)

        # טבלת מדדים מתקדמים
        if 'Fund' in results:
            console.print("\n[bold cyan]מדדי סיכון נוספים:[/bold cyan]")
            adv_table = Table(show_header=True, header_style="bold magenta")
            adv_table.add_column("מדד", style="cyan", width=20)
            adv_table.add_column("Sortino Ratio", justify="right")
            adv_table.add_column("Calmar Ratio", justify="right")
            adv_table.add_column("Win Rate", justify="right")
            adv_table.add_column("Best Day", justify="right")
            adv_table.add_column("Worst Day", justify="right")

            for name, metrics in results.items():
                if 'sortino_ratio' in metrics:
                    adv_table.add_row(
                        name,
                        f"{metrics['sortino_ratio']:.2f}",
                        f"{metrics['calmar_ratio']:.2f}",
                        f"{metrics['win_rate']*100:.1f}%",
                        f"{metrics['best_day']*100:.2f}%",
                        f"{metrics['worst_day']*100:.2f}%"
                    )

            console.print(adv_table)

            # מדדי בטא ואלפא
            fund_metrics = results['Fund']
            if 'beta' in fund_metrics and 'alpha' in fund_metrics:
                console.print("\n[bold cyan]ניתוח ביצועים מתואם:[/bold cyan]")
                console.print(f"[yellow]Beta (vs S&P 500):[/yellow] {fund_metrics['beta']:.2f}")
                console.print(f"[yellow]Alpha (annual):[/yellow] {fund_metrics['alpha']*100:.2f}%")
                if fund_metrics['beta'] > 1:
                    console.print(f"  הקרן תנודתית יותר מהשוק ({fund_metrics['beta']:.2f}x)")
                else:
                    console.print(f"  הקרן פחות תנודתית מהשוק ({fund_metrics['beta']:.2f}x)")

        # השוואת ביצועים
        console.print("\n[bold cyan]השוואת ביצועים:[/bold cyan]")
        if 'Fund' in results and 'S&P 500' in results:
            fund_return = results['Fund']['annual_return']
            sp500_return = results['S&P 500']['annual_return']
            outperformance = (fund_return - sp500_return) * 100
            if outperformance > 0:
                console.print(f"[green]הקרן עלתה על ה-S&P 500 ב-{outperformance:.2f}% שנתית[/green]")
            else:
                console.print(f"[red]הקרן נמוכה מ-S&P 500 ב-{abs(outperformance):.2f}% שנתית[/red]")

        if 'Fund' in results and 'NASDAQ' in results:
            fund_return = results['Fund']['annual_return']
            nasdaq_return = results['NASDAQ']['annual_return']
            outperformance = (fund_return - nasdaq_return) * 100
            if outperformance > 0:
                console.print(f"[green]הקרן עלתה על ה-NASDAQ ב-{outperformance:.2f}% שנתית[/green]")
            else:
                console.print(f"[red]הקרן נמוכה מ-NASDAQ ב-{abs(outperformance):.2f}% שנתית[/red]")

        # ביצועי מניות בודדות
        if 'individual_stocks' in results and results['individual_stocks']:
            console.print("\n[bold cyan]ביצועי מניות בודדות:[/bold cyan]")

            # מיון לפי תשואה שנתית
            sorted_stocks = sorted(
                results['individual_stocks'].items(),
                key=lambda x: x[1]['annual_return'],
                reverse=True
            )

            stock_table = Table(show_header=True, header_style="bold magenta")
            stock_table.add_column("מניה", style="cyan", width=25)
            stock_table.add_column("משקל", justify="right", width=8)
            stock_table.add_column("תשואה שנתית", justify="right", width=12)
            stock_table.add_column("vs S&P 500", justify="right", width=12)
            stock_table.add_column("vs NASDAQ", justify="right", width=12)
            stock_table.add_column("תנודתיות", justify="right", width=10)

            sp500_return = results['S&P 500']['annual_return'] if 'S&P 500' in results else 0
            nasdaq_return = results['NASDAQ']['annual_return'] if 'NASDAQ' in results else 0

            for symbol, metrics in sorted_stocks:
                vs_sp500 = (metrics['annual_return'] - sp500_return) * 100
                vs_nasdaq = (metrics['annual_return'] - nasdaq_return) * 100

                # צבע לפי ביצועים
                vs_sp500_str = f"[green]+{vs_sp500:.1f}%[/green]" if vs_sp500 > 0 else f"[red]{vs_sp500:.1f}%[/red]"
                vs_nasdaq_str = f"[green]+{vs_nasdaq:.1f}%[/green]" if vs_nasdaq > 0 else f"[red]{vs_nasdaq:.1f}%[/red]"

                stock_table.add_row(
                    f"{metrics['name']} ({symbol})",
                    f"{metrics['weight']*100:.0f}%",
                    f"{metrics['annual_return']*100:.1f}%",
                    vs_sp500_str,
                    vs_nasdaq_str,
                    f"{metrics['volatility']*100:.1f}%"
                )

            console.print(stock_table)

    def plot_results(self, results: Dict, output_dir: str = "Fund_Docs"):
        """
        יצירת גרפים של התוצאות

        Args:
            results: תוצאות הבדיקה הרטרוספקטיבית
            output_dir: תיקיית פלט
        """
        if not results:
            return

        # יצירת תיקייה אם לא קיימת
        Path(output_dir).mkdir(exist_ok=True)

        # הכנת הנתונים
        cumulative_returns = {}
        for name, metrics in results.items():
            if 'returns' in metrics:
                cumulative_returns[name] = (1 + metrics['returns']).cumprod()

        if not cumulative_returns:
            return

        # יצירת גרף
        plt.figure(figsize=(14, 8))

        for name, cum_ret in cumulative_returns.items():
            plt.plot(cum_ret.index, cum_ret.values, label=name, linewidth=2)

        plt.title(f'Cumulative Returns: Fund vs Benchmarks ({self.years} Years)',
                  fontsize=16, fontweight='bold')
        plt.xlabel('Date', fontsize=12)
        plt.ylabel('Cumulative Return (Base = 1)', fontsize=12)
        plt.legend(fontsize=10)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        # שמירת הגרף
        output_file = os.path.join(output_dir, f'backtest_{self.years}years.png')
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        console.print(f"\n[green]גרף נשמר: {output_file}[/green]")

        plt.close()

    def save_report_to_file(self, results: Dict, output_dir: str = "Fund_Docs"):
        """
        שמירת דוח מפורט לקובץ

        Args:
            results: תוצאות הבדיקה הרטרוספקטיבית
            output_dir: תיקיית פלט
        """
        if not results:
            return

        Path(output_dir).mkdir(exist_ok=True)

        fund_name = Path(self.fund_file).stem
        output_file = os.path.join(output_dir, f'{fund_name}_Backtest_{self.years}Y.md')

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# Backtest Report: {fund_name}\n\n")
            f.write(f"**תקופה מבוקשת:** {self.start_date.strftime('%Y-%m-%d')} עד {self.end_date.strftime('%Y-%m-%d')} ({self.years} שנים)\n\n")

            # Calculate actual years
            actual_years = (self.actual_end_date - self.actual_start_date).days / 365.25
            f.write(f"**תקופה בפועל:** {self.actual_start_date.strftime('%Y-%m-%d')} עד {self.actual_end_date.strftime('%Y-%m-%d')} ")
            f.write(f"({actual_years:.1f} שנים, {self.actual_days} ימי מסחר)\n\n")

            # Add data availability note if dates differ
            requested_days = (self.end_date - self.start_date).days
            actual_days = (self.actual_end_date - self.actual_start_date).days
            if actual_days < requested_days * 0.9:
                f.write(f"**⚠ הערה:** הנתונים הזמינים מכסים {actual_years:.1f} שנים בלבד, לא {self.years} שנים מלאים.\n\n")

            f.write(f"**תאריך יצירת הדוח:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")

            # הרכב הקרן
            f.write("## הרכב הקרן\n\n")
            f.write("| מניה | משקל |\n")
            f.write("|------|------|\n")
            for symbol, info in self.portfolio.items():
                f.write(f"| {info['name']} ({symbol}) | {info['weight']*100:.1f}% |\n")
            f.write("\n")

            # תוצאות
            f.write("## תוצאות ביצועים\n\n")
            f.write("| מדד | תשואה מצטברת | תשואה שנתית | תנודתיות שנתית | יחס שארפ | ירידה מקסימלית |\n")
            f.write("|------|---------------|--------------|----------------|----------|------------------|\n")

            for name, metrics in results.items():
                if 'cumulative_return' in metrics:
                    f.write(f"| {name} | ")
                    f.write(f"{metrics['cumulative_return']*100:.2f}% | ")
                    f.write(f"{metrics['annual_return']*100:.2f}% | ")
                    f.write(f"{metrics['annual_volatility']*100:.2f}% | ")
                    f.write(f"{metrics['sharpe_ratio']:.2f} | ")
                    f.write(f"{metrics['max_drawdown']*100:.2f}% |\n")

            f.write("\n")

            # מדדים מתקדמים
            f.write("## מדדי סיכון מתקדמים\n\n")
            f.write("| מדד | Sortino Ratio | Calmar Ratio | Win Rate | Monthly Win Rate | Best Day | Worst Day |\n")
            f.write("|------|---------------|--------------|----------|------------------|----------|----------|\n")

            for name, metrics in results.items():
                if 'sortino_ratio' in metrics:
                    f.write(f"| {name} | ")
                    f.write(f"{metrics['sortino_ratio']:.2f} | ")
                    f.write(f"{metrics['calmar_ratio']:.2f} | ")
                    f.write(f"{metrics['win_rate']*100:.1f}% | ")
                    f.write(f"{metrics['monthly_win_rate']*100:.1f}% | ")
                    f.write(f"{metrics['best_day']*100:.2f}% | ")
                    f.write(f"{metrics['worst_day']*100:.2f}% |\n")

            f.write("\n")

            # בטא ואלפא
            if 'Fund' in results:
                fund_metrics = results['Fund']
                if 'beta' in fund_metrics and 'alpha' in fund_metrics:
                    f.write("### ניתוח ביצועים מתואם (vs S&P 500)\n\n")
                    f.write(f"- **Beta:** {fund_metrics['beta']:.2f}\n")
                    f.write(f"- **Alpha (annual):** {fund_metrics['alpha']*100:.2f}%\n")
                    if fund_metrics['beta'] > 1:
                        f.write(f"- הקרן תנודתית יותר מהשוק ({fund_metrics['beta']:.2f}x)\n")
                    else:
                        f.write(f"- הקרן פחות תנודתית מהשוק ({fund_metrics['beta']:.2f}x)\n")
                    f.write("\n")

            # השוואות
            f.write("## השוואת ביצועים\n\n")
            if 'Fund' in results:
                fund_return = results['Fund']['annual_return']

                if 'S&P 500' in results:
                    sp500_return = results['S&P 500']['annual_return']
                    diff = (fund_return - sp500_return) * 100
                    f.write(f"- **לעומת S&P 500:** ")
                    if diff > 0:
                        f.write(f"הקרן עלתה ב-{diff:.2f}% שנתית\n")
                    else:
                        f.write(f"הקרן נמוכה ב-{abs(diff):.2f}% שנתית\n")

                if 'NASDAQ' in results:
                    nasdaq_return = results['NASDAQ']['annual_return']
                    diff = (fund_return - nasdaq_return) * 100
                    f.write(f"- **לעומת NASDAQ:** ")
                    if diff > 0:
                        f.write(f"הקרן עלתה ב-{diff:.2f}% שנתית\n")
                    else:
                        f.write(f"הקרן נמוכה ב-{abs(diff):.2f}% שנתית\n")

            # ביצועי מניות בודדות
            if 'individual_stocks' in results and results['individual_stocks']:
                f.write("\n## ביצועי מניות בודדות\n\n")
                f.write("| מניה | משקל | תשואה שנתית | vs S&P 500 | vs NASDAQ | תנודתיות |\n")
                f.write("|------|------|--------------|------------|-----------|----------|\n")

                sp500_return = results['S&P 500']['annual_return'] if 'S&P 500' in results else 0
                nasdaq_return = results['NASDAQ']['annual_return'] if 'NASDAQ' in results else 0

                # מיון לפי תשואה שנתית
                sorted_stocks = sorted(
                    results['individual_stocks'].items(),
                    key=lambda x: x[1]['annual_return'],
                    reverse=True
                )

                for symbol, metrics in sorted_stocks:
                    vs_sp500 = (metrics['annual_return'] - sp500_return) * 100
                    vs_nasdaq = (metrics['annual_return'] - nasdaq_return) * 100

                    f.write(f"| {metrics['name']} ({symbol}) | ")
                    f.write(f"{metrics['weight']*100:.0f}% | ")
                    f.write(f"{metrics['annual_return']*100:.1f}% | ")
                    f.write(f"{vs_sp500:+.1f}% | ")
                    f.write(f"{vs_nasdaq:+.1f}% | ")
                    f.write(f"{metrics['volatility']*100:.1f}% |\n")

                f.write("\n")

                # תובנות על המניות
                f.write("### תובנות:\n\n")
                best_stock = sorted_stocks[0]
                worst_stock = sorted_stocks[-1]

                f.write(f"- **המניה הטובה ביותר:** {best_stock[1]['name']} ({best_stock[0]}) ")
                f.write(f"עם תשואה שנתית של {best_stock[1]['annual_return']*100:.1f}%\n")

                f.write(f"- **המניה החלשה ביותר:** {worst_stock[1]['name']} ({worst_stock[0]}) ")
                f.write(f"עם תשואה שנתית של {worst_stock[1]['annual_return']*100:.1f}%\n")

                # ספירת מניות שעולות על הבנצ'מרק
                outperform_sp500 = sum(1 for _, m in results['individual_stocks'].items()
                                      if m['annual_return'] > sp500_return)
                outperform_nasdaq = sum(1 for _, m in results['individual_stocks'].items()
                                       if m['annual_return'] > nasdaq_return)

                f.write(f"- **{outperform_sp500} מתוך {len(results['individual_stocks'])} מניות** ")
                f.write(f"עלו על ה-S&P 500\n")
                f.write(f"- **{outperform_nasdaq} מתוך {len(results['individual_stocks'])} מניות** ")
                f.write(f"עלו על ה-NASDAQ\n")

            f.write("\n## גרף ביצועים\n\n")
            f.write(f"![Backtest Results](backtest_{self.years}years.png)\n\n")

            # ניתוח סיכונים
            f.write("## ניתוח סיכונים\n\n")
            if 'Fund' in results:
                fund_vol = results['Fund']['annual_volatility'] * 100
                fund_dd = results['Fund']['max_drawdown'] * 100
                f.write(f"- **תנודתיות הקרן:** {fund_vol:.2f}%\n")
                f.write(f"- **ירידה מקסימלית:** {fund_dd:.2f}%\n")

                if 'S&P 500' in results:
                    sp500_vol = results['S&P 500']['annual_volatility'] * 100
                    vol_diff = fund_vol - sp500_vol
                    if vol_diff > 0:
                        f.write(f"- הקרן תנודתית יותר מ-S&P 500 ב-{vol_diff:.2f}%\n")
                    else:
                        f.write(f"- הקרן פחות תנודתית מ-S&P 500 ב-{abs(vol_diff):.2f}%\n")

            f.write("\n---\n")
            f.write("*דוח זה נוצר באמצעות Claude Code*\n")

        console.print(f"[green]דוח נשמר: {output_file}[/green]")


def main():
    """פונקציה ראשית"""
    import argparse

    parser = argparse.ArgumentParser(
        description='ביצוע בדיקה רטרוספקטיבית של קרן צמיחה'
    )
    parser.add_argument(
        'fund_file',
        help='נתיב לקובץ הקרן (למשל: Fund_Docs/Fund_8_SP500_Q4_2025.md)'
    )
    parser.add_argument(
        '--years',
        type=int,
        default=10,
        help='מספר שנים לבדיקה רטרוספקטיבית (ברירת מחדל: 10)'
    )
    parser.add_argument(
        '--output-dir',
        default=None,
        help='תיקיית פלט לדוחות וגרפים (ברירת מחדל: אותה תיקייה כמו קובץ הקרן)'
    )

    args = parser.parse_args()

    # בדיקת קיום הקובץ
    if not os.path.exists(args.fund_file):
        console.print(f"[red]שגיאה: קובץ הקרן לא נמצא: {args.fund_file}[/red]")
        return

    # Default output dir = same directory as fund file
    output_dir = args.output_dir or str(Path(args.fund_file).parent)

    # הרצת הבדיקה הרטרוספקטיבית
    console.print("[bold cyan]מתחיל בדיקה רטרוספקטיבית של קרן הצמיחה...[/bold cyan]\n")

    backtest = FundBacktest(args.fund_file, years=args.years)
    results = backtest.run_backtest()

    if results:
        backtest.generate_report(results)
        backtest.plot_results(results, output_dir)
        backtest.save_report_to_file(results, output_dir)
        console.print("\n[bold green]הבדיקה הרטרוספקטיבית הושלמה בהצלחה![/bold green]")
    else:
        console.print("\n[bold red]הבדיקה הרטרוספקטיבית נכשלה[/bold red]")


if __name__ == "__main__":
    main()
