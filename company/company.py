
import datetime as dt

from analysis.technical import Technical
from data import store as o
from utils import utils as u

logger = u.get_logger()

class Company:
    def __init__(self, ticker, days=0):
        self.ticker = ticker.upper()
        self.days = days
        self.company = None
        self.history = None
        self.ta = None

        if days < 1:
            raise ValueError('Invalid number of days')

        if o.is_symbol_valid(ticker):
            self.ta = Technical(self.ticker, self.days)
            self.history = self.ta.history
        else:
            raise ValueError('Invalid ticker')

    def __str__(self):
        output = f'{self.ticker}'
        return output

    def get_current_price(self):
        return self.history['close'][-1]

    def get_high(self):
        return self.history['high']

    def get_low(self):
        return self.history['low']

    def get_close(self):
        return self.history['close']

    def get_volume(self):
        return self.history['volume']


if __name__ == '__main__':
    company = Company('AAPL', days=365)
    val = company.get_close()
    print(val)
