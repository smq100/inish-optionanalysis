from data import store as o
from utils import utils as utils

logger = utils.get_logger()


class ScoringAnalysis:
    def __init__(self, ticker):
        if (o.is_symbol_valid(ticker)):
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
