import pandas as pd
import numpy as np
from ta import trend
import random
from concurrent import futures
from sklearn.preprocessing import MinMaxScaler

from analysis.technical import Technical
from base import Threaded
from data import store as store
from utils import ui, logger


_logger = logger.get_logger()


class Divergence(Threaded):
    def __init__(self, tickers: list[str], window: int = 15, days: int = 100):
        self.tickers: list[str] = tickers
        self.window: int = window
        self.days: int = days
        self.results: list[pd.DataFrame] = []
        self.analysis: list[pd.DataFrame] = []
        self.type: str = 'rsi'
        self.interval: int = 14
        self.periods: int = days // 50
        self.streak: int = 5
        self.concurrency: int = 10

        for ticker in tickers:
            if not store.is_ticker(ticker):
                raise ValueError(f'{__name__}: Not a valid ticker: {ticker}')

    @Threaded.threaded
    def calculate(self) -> None:
        if not self.tickers:
            assert ValueError('No valid tickers specified')

        self.results = []
        self.task_total = len(self.tickers)
        self.task_state = 'None'

        # Break up the tickers and run concurrently if a large list, otherwise just run the single list
        random.shuffle(self.tickers)
        if len(self.tickers) > 100:
            tickers: list[np.ndarray] = np.array_split(self.tickers, self.concurrency)
            tickers = [i.tolist() for i in tickers]

            with futures.ThreadPoolExecutor(max_workers=self.concurrency) as executor:
                self.task_futures = [executor.submit(self._run, list) for list in tickers]

                for future in futures.as_completed(self.task_futures):
                    _logger.info(f'{__name__}: Thread completed: {future.result()}')
        else:
            self._run(self.tickers)

        self.task_state = 'Done'

    def analyze(self, streak: int = 5) -> None:
        if not self.results:
            assert ValueError('No valid results specified')

        self.streak = streak
        self.analysis = pd.DataFrame()
        for result in self.results:
            idx = result[::-1]['streak'].idxmax()
            date = result.iloc[idx]['date']
            max = result.iloc[idx]['streak']
            if max >= streak:
                data = [[result.index.name, date, max]]
                df = pd.DataFrame(data, columns=['ticker', 'date', 'streak'])
                self.analysis = pd.concat([self.analysis, df], ignore_index=True)

        if len(self.analysis) > 0:
            self.analysis.reset_index()
            self.analysis.sort_values(by=['streak'], ascending=False, inplace=True)

    def _run(self, tickers:list[str]) -> None:
        for ticker in tickers:
            ta = Technical(ticker, None, self.days)
            history = ta.history
            scaler = MinMaxScaler(feature_range=(0, 1))
            result = pd.DataFrame()

            # Calculate 0-1 scaled series of day-to-day price differences
            dates = history['date'][self.interval:].reset_index(drop=True)
            price = history['close'][self.interval:].reset_index(drop=True)

            if not history.empty and not price.empty:
                self.task_ticker = ticker

                price.name = 'price'
                price_sma = trend.sma_indicator(price, window=self.window, fillna=True).reset_index(drop=True)
                price_sma.name = 'price_sma'
                price_sma_diff = price_sma.diff(periods=self.periods).fillna(0.0)
                price_sma_diff.name = 'price_sma_diff'
                scaled = scaler.fit_transform(price_sma.values.reshape(-1, 1))
                scaled = [value[0] for value in scaled]
                price_sma_scaled = pd.Series(scaled, name='price_sma_scaled')
                price_sma_scaled_diff = price_sma_scaled.diff(periods=self.periods).fillna(0.0)
                price_sma_scaled_diff.name = 'price_sma_scaled_diff'

                # Calculate 0-1 scaled series of day-to-day rsi differences
                technical = ta.calc_rsi(self.interval)[self.interval:]
                technical_sma = trend.sma_indicator(technical, window=self.window, fillna=True).reset_index(drop=True)
                technical_sma.name = f'{self.type}_sma'
                technical_sma_diff = technical_sma.diff(periods=self.periods).fillna(0.0)
                technical_sma_diff.name = f'{self.type}_sma_diff'
                scaled = scaler.fit_transform(technical_sma.values.reshape(-1, 1))
                scaled = [value[0] for value in scaled]
                technical_sma_scaled = pd.Series(scaled, name=f'{self.type}_sma_scaled')
                technical_sma_scaled_diff = technical_sma_scaled.diff(periods=self.periods).fillna(0.0)
                technical_sma_scaled_diff.name = f'{self.type}_sma_scaled_diff'

                # Calculate differences in the slopes between prices and RSI's
                divergence = price_sma_scaled_diff - technical_sma_scaled_diff
                divergence.name = 'diff'

                # Calculate differences in the slopes between prices and RSI's for opposite slopes only
                div = []
                for i in range(len(price_sma_scaled_diff)):
                    p = price_sma_scaled_diff[i]
                    t = technical_sma_scaled_diff[i]
                    div += [p - t if p * t < 0.0 else np.NaN]
                divergence_only = pd.Series(div, name='div')

                # Begin overall result dataframe with the dates
                result = dates

                # Price data
                result = pd.concat([result, price], axis=1)
                result = pd.concat([result, price_sma], axis=1)
                result = pd.concat([result, price_sma_diff], axis=1)
                result = pd.concat([result, price_sma_scaled], axis=1)
                result = pd.concat([result, price_sma_scaled_diff], axis=1)

                # Technical data
                tech = technical.reset_index(drop=True)
                result = pd.concat([result, tech], axis=1)
                result = pd.concat([result, technical_sma], axis=1)
                result = pd.concat([result, technical_sma_diff], axis=1)
                result = pd.concat([result, technical_sma_scaled], axis=1)
                result = pd.concat([result, technical_sma_scaled_diff], axis=1)
                result = pd.concat([result, divergence], axis=1)
                result = pd.concat([result, divergence_only], axis=1)

                # Streak data
                analysis = result.loc[:, ('date', 'div')]
                analysis['tmp1'] = analysis['div'].notna() == True
                analysis['tmp2'] = analysis['tmp1'].ne(analysis['tmp1'].shift())
                analysis['tmp3'] = analysis['tmp2'].cumsum()
                analysis['tmp4'] = analysis.groupby('tmp3').cumcount() + 1
                analysis['streak'] = np.where(analysis['tmp1'] == True, analysis['tmp4'], 0)
                result = pd.concat([result, analysis['streak']], axis=1)

                result.index.name = f'{ticker.upper()}'

                if not result.empty:
                    self.results += [result]

            self.task_completed += 1


if __name__ == '__main__':
    import sys
    from tabulate import tabulate
    from utils import logger

    ticker = sys.argv[1].upper() if len(sys.argv) > 1 else 'IBM'

    div = Divergence([ticker])
    div.calculate()
    results = div.results[0][['date', 'price', 'rsi', 'div', 'streak']]
    headers = ui.format_headers(results.columns, case='lower')
    print(tabulate(results, headers=headers, tablefmt=ui.TABULATE_FORMAT, floatfmt='.2f'))

    div.analyze()
    print(div.analysis)
