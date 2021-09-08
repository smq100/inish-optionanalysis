
import pandas as pd

from analysis.technical import Technical
from data import store as store
from utils import utils as utils


class Company:
    def __init__(self, ticker:str, days:int, end:int=0, lazy:bool=True, live:bool=False):
        self.ticker = ticker.upper()
        self.days = days
        self.end = end
        self.live = live
        self.info = {}
        self.history:pd.DataFrame = pd.DataFrame()
        self.company = {}
        self.spot = 0.0
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

    def __str__(self):
        output = f'{self.ticker}'
        return output

    def get_last_price(self) -> float:
        if self.history.empty:
            self._load_history()

        return self.history.iloc[-1]['close']

    def get_high(self) -> pd.Series:
        if self.history.empty:
            self._load_history()

        return self.history['high']

    def get_low(self) -> pd.Series:
        if self.history.empty:
            self._load_history()

        return self.history['low']

    def get_close(self) -> pd.Series:
        if self.history.empty:
            self._load_history()

        return self.history['close']

    def get_volume(self) -> pd.Series:
        if self.history.empty:
            self._load_history()

        return self.history['volume']

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

    def _load_history(self) -> None:
        self.history = store.get_history(self.ticker, self.days, end=self.end, live=self.live)
        if self.history is None:
            raise RuntimeError(f'No history for {self.ticker}')

        self.ta = Technical(self.ticker, self.history, self.days, live=self.live)

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
