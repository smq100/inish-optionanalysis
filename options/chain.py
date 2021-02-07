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


def get_contract(contract_symbol):
    parsed = u.parse_contract_name(contract_symbol)

    ticker = parsed['ticker']
    product = parsed['product']
    expiry = parsed['expiry']
    strike = parsed['strike']

    company = get_company_info(ticker)
    if product == 'call':
        chain = company.option_chain(expiry).calls
    else:
        chain = company.option_chain(expiry).puts
    contract = chain.loc[chain['contractSymbol'] == contract_symbol]

    return contract.iloc[0]
