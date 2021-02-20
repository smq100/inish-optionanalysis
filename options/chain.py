from pricing.fetcher import validate_ticker, get_company
from utils import utils as u

logger = u.get_logger()

class Chain():
    def __init__(self, ticker):
        logger.info('Initializing Chain...')

        self.ticker = ticker
        self.company = None
        self.expire = None
        self.width = 1

    def get_expiry(self):
        value = self.company = None
        if validate_ticker(self.ticker):
            self.company = get_company(self.ticker)
            value = self.company.options

        return value

    def get_chain(self, product):
        value = self.company = None
        if validate_ticker(self.ticker):
            self.company = get_company(self.ticker)
            value = self.company.option_chain(date=self.expire)
            if product == 'call':
                value = value.calls
            elif product == 'put':
                value = value.puts
            else:
                value = None

        return value
