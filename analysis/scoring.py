from data import store as o
from utils import utils as u

logger = u.get_logger()


class ScoringAnalysis:
    def __init__(self, ticker):
        if (o.is_ticker_valid(ticker)):
            self.ticker = ticker.upper()
            self.ema = {}
            self.rsa = None
            self.vwap = None
            self.macd = None
            self.bb = None
        else:
            logger.error(f'Error initializing {__class__}')

    def __str__(self):
        return f'Scoring Analysis for {self.ticker}'
