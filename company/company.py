
import pandas as pd

from analysis.technical import Technical
from data import store as store
from utils import ui

_logger = ui.get_logger()


class Company:
    def __init__(self, ticker: str, days: int, end: int = 0, lazy: bool = True, live: bool = False):
        self.ticker = ticker.upper()
        self.days = days
        self.end = end
        self.live = live if store.is_database_connected() else True
        self.info = {}
        self.history: pd.DataFrame = pd.DataFrame()
        self.company = {}
        self.price = 0.0
        self.volatility = 0.0
        self.ta = None

        if not store.is_ticker(ticker):
            raise ValueError(f'Invalid ticker {ticker}')
        if days < 1:
            raise ValueError('Invalid number of days')
        if end < 0:
            raise ValueError('Invalid "end" days')

        if not lazy:
            self._load_history()
            self._load_company()

    def __repr__(self):
        return f'<Company ({self.ticker})>'

    def __str__(self):
        return f'{self.ticker}'

    def get_last_price(self) -> float:
        value = -1.0
        if self.history.empty:
            if self._load_history():
                value = self.history.iloc[-1]['close']
        else:
            value = self.history.iloc[-1]['close']

        return value

    def get_high(self) -> pd.Series:
        value = pd.Series(dtype=float)
        if self.history.empty:
            if self._load_history():
                value = self.history['high']
        else:
            value = self.history['high']

        return value

    def get_low(self) -> pd.Series:
        value = pd.Series(dtype=float)
        if self.history.empty:
            if self._load_history():
                value = self.history['low']
        else:
            value = self.history['low']

        return value

    def get_close(self) -> pd.Series:
        value = pd.Series(dtype=float)
        if self.history.empty:
            if self._load_history():
                value = self.history['close']
        else:
            value = self.history['close']

        return value

    def get_volume(self) -> pd.Series:
        value = pd.Series(dtype=float)
        if self.history.empty:
            if self._load_history():
                value = self.history['volume']
        else:
            value = self.history['volume']

        return value

    def get_beta(self) -> float:
        if not self.company:
            self._load_company()

        return self.company['beta']

    def get_rating(self) -> float:
        if not self.company:
            self._load_company()

        return self.company['rating']

    def get_marketcap(self) -> int:
        if not self.company:
            self._load_company()

        return self.company['marketcap']

    def get_liveinfo(self) -> dict:
        self.info = store.get_company(self.ticker, live=True)

        return self.info

    def _load_history(self) -> bool:
        success = False
        self.history = store.get_history(self.ticker, self.days, end=self.end, live=self.live)
        if self.history is None:
            _logger.warning(f'{__name__}: No history for {self.ticker}')
        elif self.history.empty:
            _logger.warning(f'{__name__}: Empty history for {self.ticker}')
        else:
            self.ta = Technical(self.ticker, self.history, self.days, end=self.end, live=self.live)
            success = True

            _logger.info(f'{__name__}: Fetched {len(self.history)} items from {self.ticker}. '
                         f'{self.days} days from {self.history.iloc[0]["date"]} to {self.history.iloc[-1]["date"]} (end={self.end})')

        return success

    def _load_company(self) -> None:
        self.company = store.get_company(self.ticker, live=self.live)
        if not self.company:
            raise RuntimeError(f'No company info for {self.ticker}')


if __name__ == '__main__':
    company = Company('IBM', days=365, end=30)
    val = company.get_close()
    print(val)
    val = company.get_last_price()
    print(val)
