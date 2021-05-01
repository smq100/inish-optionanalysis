from data import store as s
from fetcher import fetcher as f
from utils import utils as u

logger = u.get_logger()

class Chain:
    def __init__(self, ticker):
        if not s.is_ticker_valid(ticker):
            logger.error(f'Error initializing {__class__}')
        else:
            self.ticker = ticker
            self.company = None
            self.expire = None
            self.width = 1

    def get_expiry(self):
        self.company = f.get_company_ex(self.ticker)
        value = self.company.options

        return value

    def get_chain(self, product):
        value = f.get_option_chain(self.ticker)(date=self.expire)

        if product == 'call':
            value = value.calls
        elif product == 'put':
            value = value.puts
        else:
            value = None

        return value
