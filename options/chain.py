from data import store as store
from data import store as store
from utils import utils as utils

_logger = utils.get_logger()

class Chain:
    def __init__(self, ticker):
        if not store.is_ticker(ticker):
            _logger.error(f'Error initializing {__class__}')
        else:
            self.ticker = ticker
            self.company = None
            self.expire = None
            self.width = 1

    def get_expiry(self):
        return store.get_option_expiry(self.ticker)

    def get_chain(self, product):
        value = store.get_option_chain(self.ticker)(date=self.expire)

        if product == 'call':
            value = value.calls
        elif product == 'put':
            value = value.puts
        else:
            value = None

        return value
