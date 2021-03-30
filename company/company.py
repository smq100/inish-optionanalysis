
import datetime

from analysis.technical import Technical
from fetcher import fetcher as f
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

        self.company = f.get_company(ticker)
        if self.company is not None:
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
        return self.history['Close'][-1]

    def get_high(self):
        if self.history is None:
            if not self._load_history():
                raise AssertionError(assert_msg)
        return self.history['High']

    def get_low(self):
        if self.history is None:
            if not self._load_history():
                raise AssertionError(assert_msg)
        return self.history['Low']

    def get_close(self):
        if self.history is None:
            if not self._load_history():
                raise AssertionError(assert_msg)
        return self.history['Close']

    def get_volume(self):
        if self.history is None:
            if not self._load_history():
                raise AssertionError(assert_msg)
        return self.history['Volume']

    def get_info(self, item):
        if self.history is None:
            if not self._load_history():
                raise AssertionError(assert_msg)
        else:
            value = 0
            try:
                value = self.company.info[item]
            except KeyError as e:
                raise ValueError(f'Invalid YFinance info key: {e}')

        return value

    def _load_history(self):
        valid = False
        if self.days > 1:
            start = datetime.datetime.today() - datetime.timedelta(days=self.days)
            self.history = self.company.history(start=f'{start:%Y-%m-%d}')
            self.ta = Technical(self.ticker, start)
            valid = True

        return valid

if __name__ == '__main__':
    f.initialize()
    company = Company('AAPL', history=365)
    val = company.get_info('marketCap')
    print(val)