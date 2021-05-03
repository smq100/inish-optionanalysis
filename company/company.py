
from analysis.technical import Technical
from data import store as o
from utils import utils as u

logger = u.get_logger()

class Company:
    def __init__(self, ticker, days, lazy=True, live=False):
        self.ticker = ticker.upper()
        self.days = days
        self.live = live
        self.company = None
        self.history = None
        self.ta = None

        if days < 1:
            raise ValueError('Invalid number of days')

        if not o.is_ticker_valid(ticker):
            raise ValueError('Invalid ticker')

        if not lazy:
            self._load_history()

    def __str__(self):
        output = f'{self.ticker}'
        return output

    def get_current_price(self):
        if self.history is None:
            self._load_history()

        return self.history['close'][-1]

    def get_high(self):
        if self.history is None:
            self._load_history()

        return self.history['high']

    def get_low(self):
        if self.history is None:
            self._load_history()

        return self.history['low']

    def get_close(self):
        if self.history is None:
            self._load_history()

        return self.history['close']

    def get_volume(self):
        if self.history is None:
            self._load_history()

        return self.history['volume']

    def _load_history(self):
        self.history = o.get_history(self.ticker, self.days, live=self.live)
        if self.history is None:
            raise RuntimeError('history is None')

        self.ta = Technical(self.ticker, self.history, self.days, live=self.live)


if __name__ == '__main__':
    company = Company('ADRA', days=365, live=True)
    val = company.get_current_price()
    print(val)
    val = company.get_close()
    print(val)
