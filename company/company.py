
import pandas as pd

from analysis.technical import Technical
from data import store as store
from utils import utils as utils


class Company:
    def __init__(self, ticker:str, days:int, lazy:bool=True, live:bool=False):
        self.ticker = ticker.upper()
        self.days = days
        self.live = live
        self.company = None
        self.history = None
        self.ta = None

        if days < 1:
            raise ValueError('Invalid number of days')

        if not store.is_ticker_valid(ticker):
            raise ValueError('Invalid ticker')

        if not lazy:
            self._load_history()

    def __str__(self):
        output = f'{self.ticker}'
        return output

    def get_current_price(self) -> float:
        if self.history is None:
            self._load_history()

        return self.history['close'][-1]

    def get_high(self) -> pd.Series:
        if self.history is None:
            self._load_history()

        return self.history['high']

    def get_low(self) -> pd.Series:
        if self.history is None:
            self._load_history()

        return self.history['low']

    def get_close(self) -> pd.Series:
        if self.history is None:
            self._load_history()

        return self.history['close']

    def get_volume(self) -> pd.Series:
        if self.history is None:
            self._load_history()

        return self.history['volume']

    def get_beta(self) -> float:
        company = store.get_company(self.ticker, live=True)

        return company['beta']

    def _load_history(self, info=False):
        self.history = store.get_history(self.ticker, self.days, live=self.live)
        if self.history is None:
            raise RuntimeError('history is None')

        self.ta = Technical(self.ticker, self.history, self.days, live=self.live)

        if info:
            self.company = store.get_company(self.ticker, live=True)


if __name__ == '__main__':
    company = Company('ADRA', days=365, live=True)
    val = company.get_current_price()
    print(val)
    val = company.get_close()
    print(val)
