import datetime as dt
import re

from data import store as store
from utils import utils

PRODUCTS = ('call', 'put')
DIRECTIONS = ('long', 'short')

_logger = utils.get_logger()


class Option:
    def __init__(self, ticker, product, strike, expiry):
        # Specified
        self.ticker = ticker
        self.product = product
        self.strike = strike
        self.expiry = expiry
        self.spot = 0.0

        # Calculated
        self.calc_price = 0.0
        self.calc_volatility = 0.0
        self.time_to_maturity = 0.0
        self.rate = 0.0
        self.delta = 0.0
        self.gamma = 0.0
        self.theta = 0.0
        self.vega = 0.0
        self.rho = 0.0

        # Fetched online with YFinance
        self.contract_ticker = ''
        self.last_trade_date = ''
        self.last_price = 0.0
        self.bid = 0.0
        self.ask = 0.0
        self.change = 0.0
        self.percent_change = 0.0
        self.volume = 0.0
        self.open_interest = 0.0
        self.implied_volatility = 0.0
        self.itm = False
        self.contract_size = ''
        self.currency = ''

    def __str__(self):
        ticker = self.contract_ticker if self.contract_ticker else 'No contract selected'
        return f'Contract:{ticker}\n'\
            f'Ticker: {self.ticker}\n'\
            f'Product: {self.product.title()}\n'\
            f'Expiry: {self.expiry:%Y-%m-%d} ({self.time_to_maturity*365:.0f}/{self.time_to_maturity:.5f})\n'\
            f'Strike: {self.strike:.2f}\n'\
            f'Spot: {self.spot:.2f}\n'\
            f'Rate: {self.rate:.3f}\n'\
            f'Last Trade: {self.last_trade_date}\n'\
            f'Calc Price: {self.calc_price:.2f}\n'\
            f'Last Price: {self.last_price:.2f}\n'\
            f'Bid: {self.bid:.2f}\n'\
            f'Ask: {self.ask:.2f}\n'\
            f'Change: {self.change}\n'\
            f'Change%: {self.percent_change}\n'\
            f'Volume: {self.volume}\n'\
            f'Open Interest: {self.open_interest}\n'\
            f'Calc Volitility: {self.calc_volatility:.4f}\n'\
            f'Impl Volitility: {self.implied_volatility:.4f}\n'\
            f'ITM: {self.itm}\n'\
            f'Size: {self.contract_size}\n'\
            f'Currency: {self.currency}\n'\
            f'Delta: {self.delta:.5f}\n'\
            f'Gamma: {self.gamma:.5f}\n'\
            f'Theta: {self.theta:.5f}\n'\
            f'Vega: {self.vega:.5f}\n'\
            f'Rho: {self.rho:.5f}'

    def load_contract(self, contract_name):
        ret = True
        parsed = _parse_contract_name(contract_name)

        self.ticker = parsed['ticker']
        self.product = parsed['product']
        self.expiry = dt.datetime.strptime(parsed['expiry'], '%Y-%m-%d')
        self.strike = parsed['strike']

        contract = _get_contract(contract_name)

        if contract is not None:
            self.contract_ticker = contract['contractSymbol']
            self.last_trade_date = contract['lastTradeDate']
            self.strike = contract['strike']
            self.last_price = contract['lastPrice']
            self.bid = contract['bid']
            self.ask = contract['ask']
            self.change = contract['change']
            self.percent_change = contract['percentChange']
            self.volume = contract['volume']
            self.open_interest = contract['openInterest']
            self.implied_volatility = contract['impliedVolatility']
            self.itm = contract['inTheMoney']
            self.contract_size = contract['contractSize']
            self.currency = contract['currency']

            if self.last_price > 0.0:
                diff = self.calc_price / self.last_price
                if diff > 1.25 or diff < 0.75:
                    _logger.debug(f'{__name__}: The calculated price is significantly different than the last traded price')

        else:
            ret = False

        return ret

def _get_contract(contract_ticker):
    parsed = _parse_contract_name(contract_ticker)

    ticker = parsed['ticker']
    product = parsed['product']
    expiry = parsed['expiry']
    strike = parsed['strike']

    try:
        if product == 'call':
            chain = store.get_option_chain(ticker)(expiry).calls
        else:
            chain = store.get_option_chain(ticker)(expiry).puts

        contract = chain.loc[chain['contractSymbol'] == contract_ticker]
        return contract.iloc[0]
    except Exception as e:
        print(str(e))
        return None

def _parse_contract_name(contract_name):
    # ex: MSFT210305C00237500
    regex = r'([\d]{6})([PC])'
    parsed = re.split(regex, contract_name)

    ticker = parsed[0]
    expiry = f'20{parsed[1][:2]}-{parsed[1][2:4]}-{parsed[1][4:]}'

    product = 'call' if 'C' in parsed[2].upper() else 'put'

    strike = float(parsed[3][:5]) + (float(parsed[3][5:]) / 1000.0)

    return {'ticker':ticker, 'expiry':expiry, 'product':product, 'strike':strike}
