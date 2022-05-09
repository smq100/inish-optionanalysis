from dataclasses import dataclass, field
import datetime as dt
import re
import collections

import pandas as pd

from data import store as store
from utils import ui, logger

_logger = logger.get_logger()
contract_type = collections.namedtuple('contract_type', ['ticker', 'expiry', 'product', 'strike'])

MIN_CONTRACT_SIZE = 16


@dataclass(order=True)
class Option:
    ticker: str = ''
    product: str = ''
    strike: float = 0.0
    expiry: dt.datetime = dt.datetime.now()
    volatility_user: float = 0.0
    volatility_delta: float = 0.0

    # Calculated
    price_calc: float = 0.0
    price_eff: float = 0.0
    volatility_calc: float = 0.0
    volatility_eff: float = 0.0
    time_to_maturity: float = 0.0
    rate: float = 0.0
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0
    rho: float = 0.0

    # Fetched online
    chain: pd.DataFrame = pd.DataFrame()
    contract: str = ''
    last_trade_date: str = ''
    price_last: float = 0.0
    bid: float = 0.0
    ask: float = 0.0
    change: float = 0.0
    percent_change: float = 0.0
    volume: float = 0.0
    open_interest: float = 0.0
    volatility_implied: float = 0.0
    itm: bool = False
    contract_size: str = ''
    currency: str = ''

    def __init__(self, ticker: str, product: str, strike: float, expiry: dt.datetime, volatility: tuple[float, float]):
        self.ticker = ticker
        self.product = product
        self.strike = strike
        self.expiry = expiry
        self.volatility_user = volatility[0]
        self.volatility_delta = volatility[1]

    def __post_init__(self):
         self.sort_index = self.price_eff

    def load_contract(self, contract_name: str, chain: pd.DataFrame) -> bool:
        ret = False

        if len(contract_name) >= MIN_CONTRACT_SIZE:
            self.chain = chain
            contract = self.get_contract(contract_name)

            if not contract.empty:
                self.contract = contract['contractSymbol']
                self.strike = contract['strike']
                self.price_last = contract['lastPrice']
                self.volume = contract['volume']
                self.volatility_implied = contract['impliedVolatility']
                self.itm = contract['inTheMoney']

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
        self.expiry = dt.datetime.strptime(parsed.expiry, ui.DATE_FORMAT)
        self.strike = parsed.strike

        try:
            if self.chain.empty:
                self.chain = store.get_option_chain(self.ticker, self.expiry)

            if not self.chain.empty:
                contract = self.chain.loc[self.chain['contractSymbol'] == contract_name].iloc[0]
            else:
                _logger.info(f'{__name__}: No contract available')
        except Exception as e:
            _logger.warning(f'{__name__}: {contract_name} {str(e)}')

        return contract


def parse_contract_name(contract_name: str) -> contract_type:
    regex = r'([\d]{6})([PC])'  # ex: MSFT210305C00237500 or MSFT--210305C00237500
    parsed = re.split(regex, contract_name)

    ticker = parsed[0].replace('-', '')
    expiry = f'20{parsed[1][:2]}-{parsed[1][2:4]}-{parsed[1][4:]}'
    product = 'call' if 'C' in parsed[2].upper() else 'put'
    strike = float(parsed[3][:5]) + (float(parsed[3][5:]) / 1000.0)
    ret = contract_type(ticker, expiry, product, strike)

    return ret
