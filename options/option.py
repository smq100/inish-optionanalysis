import datetime as dt
import re
import collections

import pandas as pd

from data import store as store
from utils import logger

_logger = logger.get_logger()
contract_type = collections.namedtuple('contract', ['ticker', 'expiry', 'product', 'strike'])

MIN_CONTRACT_SIZE = 16


class Option:
    def __init__(self, ticker: str, product: str, strike: str, expiry: dt.datetime, volatility: tuple[float, float]):
        # Specified
        self.ticker = ticker
        self.product = product
        self.strike = strike
        self.expiry = expiry
        self.volatility_user = volatility[0]
        self.volatility_delta = volatility[1]

        # Calculated
        self.price_calc = 0.0
        self.price_eff = 0.0
        self.volatility_calc = 0.0
        self.volatility_eff = 0.0
        self.time_to_maturity = 0.0
        self.rate = 0.0
        self.delta = 0.0
        self.gamma = 0.0
        self.theta = 0.0
        self.vega = 0.0
        self.rho = 0.0

        # Fetched online
        self.contract = ''
        self.last_trade_date = ''
        self.price_last = 0.0
        self.bid = 0.0
        self.ask = 0.0
        self.change = 0.0
        self.percent_change = 0.0
        self.volume = 0.0
        self.open_interest = 0.0
        self.volatility_implied = 0.0
        self.itm = False
        self.contract_size = ''
        self.currency = ''

    def __str__(self):
        name = self.contract if self.contract else 'No contract selected'
        return f'Contract:{name}\n'\
            f'Ticker: {self.ticker}\n'\
            f'Product: {self.product.title()}\n'\
            f'Expiry: {self.expiry:%Y-%m-%d} ({self.time_to_maturity*365:.0f}/{self.time_to_maturity:.5f})\n'\
            f'Strike: {self.strike:.2f}\n'\
            f'Rate: {self.rate:.3f}\n'\
            f'Last Trade: {self.last_trade_date}\n'\
            f'Calc Price: {self.price_calc:.2f}\n'\
            f'Last Price: {self.price_last:.2f}\n'\
            f'Eff Price: {self.price_eff:.2f}\n'\
            f'Bid: {self.bid:.2f}\n'\
            f'Ask: {self.ask:.2f}\n'\
            f'Change: {self.change}\n'\
            f'Change%: {self.percent_change}\n'\
            f'Volume: {self.volume}\n'\
            f'Open Interest: {self.open_interest}\n'\
            f'User Volitility: {self.volatility_user:.4f}\n'\
            f'Delta Volitility: {self.volatility_delta:.4f}\n'\
            f'Calc Volitility: {self.volatility_calc:.4f}\n'\
            f'Impl Volitility: {self.volatility_implied:.4f}\n'\
            f'Effective Volitility: {self.volatility_eff:.4f}\n'\
            f'ITM: {self.itm}\n'\
            f'Size: {self.contract_size}\n'\
            f'Currency: {self.currency}\n'\
            f'Delta: {self.delta:.5f}\n'\
            f'Gamma: {self.gamma:.5f}\n'\
            f'Theta: {self.theta:.5f}\n'\
            f'Vega: {self.vega:.5f}\n'\
            f'Rho: {self.rho:.5f}'

    def load_contract(self, contract_name: str) -> bool:
        ret = False

        if len(contract_name) >= MIN_CONTRACT_SIZE:
            contract = self.get_contract(contract_name)

            if not contract.empty:
                self.contract = contract['contractSymbol']
                self.last_trade_date = contract['lastTradeDate']
                self.strike = contract['strike']
                self.price_last = contract['lastPrice']
                self.bid = contract['bid']
                self.ask = contract['ask']
                self.change = contract['change']
                self.percent_change = contract['percentChange']
                self.volume = contract['volume']
                self.open_interest = contract['openInterest']
                self.volatility_implied = contract['impliedVolatility']
                self.itm = contract['inTheMoney']
                self.contract_size = contract['contractSize']
                self.currency = contract['currency']

                _logger.info(f'{__name__}: Loaded contract {contract_name}')

                if self.price_last > 0.0:
                    diff = self.price_calc / self.price_last
                    if diff > 1.25 or diff < 0.75:
                        _logger.info(f'{__name__}: The calculated price is significantly different than the last traded price')

                ret = True

        return ret


    def get_contract(self, contract_name: str) -> pd.Series:
        contract = pd.Series(dtype=float)
        parsed = parse_contract_name(contract_name)

        self.ticker = parsed.ticker
        self.product = parsed.product
        self.expiry = dt.datetime.strptime(parsed.expiry, '%Y-%m-%d')
        self.strike = parsed.strike

        try:
            if self.product == 'call':
                chain = store.get_option_chain(self.ticker, uselast=True)(str(self.expiry.date())).calls
            else:
                chain = store.get_option_chain(self.ticker, uselast=True)(str(self.expiry.date())).puts

            if not chain.empty:
                contract = chain.loc[chain['contractSymbol'] == contract_name].iloc[0]
            else:
                _logger.info(f'{__name__}: No contract available')
        except Exception as e:
            _logger.warning(f'{__name__}: {contract_name} {str(e)}')

        return contract


def parse_contract_name(contract_name: str) -> tuple[str, str, str, float]:
    regex = r'([\d]{6})([PC])' # ex: MSFT210305C00237500
    parsed = re.split(regex, contract_name)

    ticker = parsed[0]
    expiry = f'20{parsed[1][:2]}-{parsed[1][2:4]}-{parsed[1][4:]}'
    product = 'call' if 'C' in parsed[2].upper() else 'put'
    strike = float(parsed[3][:5]) + (float(parsed[3][5:]) / 1000.0)

    return contract_type(ticker, expiry, product, strike)
