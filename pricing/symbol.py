
import datetime

from analysis.technical import TechnicalAnalysis
from pricing import fetcher as f
from utils import utils as u

logger = u.get_logger()

class Symbol:
    def __init__(self, ticker, history=0):
        self.company = None
        self.ticker = ticker
        self.history = history
        self.ta = None

        self.company = f.get_company(ticker)
        if self.company is not None:
            if history > 0:
                start = datetime.datetime.today() - datetime.timedelta(days=self.history)
                self.ta = TechnicalAnalysis(self.ticker, start, valid=True)
        else:
            raise ValueError

    def __str__(self):
        output = f'{self.ticker}'
        return output
