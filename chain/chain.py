'''TODO'''

from pricing.fetcher import validate_ticker, get_company_info


class Chain():
    '''TODO'''

    def __init__(self, ticker):
        self.ticker = ticker
        self.company = None

    def get(self):
        self.company = None
        if validate_ticker(self.ticker):
            self.company = get_company_info(self.ticker)

        return self.company.options
