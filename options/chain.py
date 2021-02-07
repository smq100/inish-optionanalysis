'''TODO'''

from pricing.fetcher import validate_ticker, get_company_info
from utils import utils as u


class Chain():
    '''TODO'''

    def __init__(self, ticker):
        self.ticker = ticker
        self.company = None
        self.expire = None

    def get_expiry(self):
        ret = self.company = None
        if validate_ticker(self.ticker):
            self.company = get_company_info(self.ticker)
            ret = self.company.options

        return ret

    def get_chain(self, product):
        ret = self.company = None
        if validate_ticker(self.ticker):
            self.company = get_company_info(self.ticker)
            ret = self.company.option_chain(date=self.expire)
            if product == 'call':
                ret = ret.calls
            elif product == 'put':
                ret = ret.puts
            else:
                ret = None

        return ret
