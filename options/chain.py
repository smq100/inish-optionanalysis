from pricing.fetcher import validate_ticker, get_company
from utils import utils as u

logger = u.get_logger()

class Chain:
    def __init__(self, ticker):
        if not validate_ticker(ticker):
            logger.error(f'Error initializing {__class__}')
        else:
            self.ticker = ticker
            self.company = None
            self.expire = None
            self.width = 1

    def get_expiry(self):
        self.company = get_company(self.ticker)
        value = self.company.options

        return value

    def get_chain(self, product):
        self.company = get_company(self.ticker)
        value = self.company.option_chain(date=self.expire)
        if product == 'call':
            value = value.calls
        elif product == 'put':
            value = value.puts
        else:
            value = None

        return value
