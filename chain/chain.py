'''TODO'''

from pricing.fetcher import validate_ticker, get_company_info


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
