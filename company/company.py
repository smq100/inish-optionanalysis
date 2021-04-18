
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

        if not o.is_symbol_valid(ticker):
            raise ValueError('Invalid ticker')

        if not lazy:
            self._load_history()

    def __str__(self):
        output = f'{self.ticker}'
        return output

    def get_current_price(self):
        if self.history is None:
            self._load_history()

        price = 'close' if not self.live else 'Close'
        return self.history[price][-1]

    def get_high(self):
        if self.history is None:
            self._load_history()

        price = 'high' if not self.live else 'High'
        return self.history[price]

    def get_low(self):
        if self.history is None:
            self._load_history()

        price = 'low' if not self.live else 'Low'
        return self.history[price]

    def get_close(self):
        if self.history is None:
            self._load_history()

        price = 'close' if not self.live else 'Close'
        return self.history[price]

    def get_volume(self):
        if self.history is None:
            self._load_history()

        price = 'volume' if not self.live else 'Volume'
        return self.history[price]

    def _load_history(self):
        self.history = o.get_history(self.ticker, self.days, live=self.live)
        self.ta = Technical(self.ticker, self.history, self.days, live=self.live)


if __name__ == '__main__':
    company = Company('AAPL', days=365)
    val = company.get_close()
    print(val)
