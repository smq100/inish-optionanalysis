from data import store as store
from data import store as store
from utils import utils

_logger = utils.get_logger()

class Chain:
    def __init__(self, ticker:str):
        if not store.is_ticker(ticker):
            raise ValueError('Not a valid ticker')
        else:
            self.ticker:str = ticker
            self.expire:str = ''

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
