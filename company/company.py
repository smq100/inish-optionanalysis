
import datetime as dt

from analysis.technical import Technical
from data import store as o
from utils import utils as u

logger = u.get_logger()

assert_msg = 'Must instantiate Company class with a history value'

class Company:
    def __init__(self, ticker, history=0, lazy=True):
        self.ticker = ticker.upper()
        self.days = history
        self.company = None
        self.history = None
        self.ta = None

        if o.is_symbol_valid(ticker):
            if history > 1 and not lazy:
                self._load_history()
        else:
            raise ValueError('Invalid ticker')

    def __str__(self):
        output = f'{self.ticker}'
        return output

    def get_current_price(self):
        if self.history is None:
            if not self._load_history():
                raise AssertionError(assert_msg)
        return self.history['close'][-1]

    def get_high(self):
        if self.history is None:
            if not self._load_history():
                raise AssertionError(assert_msg)
        return self.history['high']

    def get_low(self):
        if self.history is None:
            if not self._load_history():
                raise AssertionError(assert_msg)
        return self.history['low']

    def get_close(self):
        if self.history is None:
            if not self._load_history():
                raise AssertionError(assert_msg)
        return self.history['close']

    def get_volume(self):
        if self.history is None:
            if not self._load_history():
                raise AssertionError(assert_msg)
        return self.history['volume']

    def _load_history(self):
        valid = False
        if self.days > 1:
            self.history = o.get_history(self.ticker, self.days)
            start = dt.datetime.today() - dt.timedelta(days=self.days)
            self.ta = Technical(self.ticker, start)
            valid = True

        return valid

if __name__ == '__main__':
    company = Company('AAPL', history=365, lazy=False)
    val = company.get_close()
    print(val)
