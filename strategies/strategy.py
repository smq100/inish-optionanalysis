import abc
from abc import ABC
import datetime as dt
import math
from numpy import load

import pandas as pd

from base import Threaded
from . import STRATEGIES
import strategies as s
from strategies.leg import Leg
from strategies.analysis import Analysis
from options.chain import Chain
import pricing as p
from data import store
from utils import math as m
from utils import ui, logger


_logger = logger.get_logger()


class Strategy(ABC, Threaded):
    def __init__(self,
            ticker: str,
            product: str,
            direction: str,
            strike: float,
            *,
            width1: int,
            width2: int,
            quantity: int,
            expiry: dt.datetime | None, # None = use next month's expiry. Otherwise use specified
            volatility: tuple[float, float], # < 0.0 use latest implied volatility, = 0.0 use calculated, > 0.0 use specified
            load_contracts: bool):

        if not store.is_ticker(ticker):
            raise ValueError('Invalid ticker')
        if product not in s.PRODUCTS:
            raise ValueError('Invalid product')
        if direction not in s.DIRECTIONS:
            raise ValueError('Invalid direction')
        if strike < 0.0:
            raise ValueError('Invalid strike')
        if quantity < 1:
            raise ValueError('Invalid quantity')
        if not (isinstance(expiry, dt.datetime) or expiry is None):
            raise TypeError('Expiry must be a datetime or None')

        if not load_contracts and volatility[0] < 0.0:
            volatility = (0.0, volatility[1])

        self.name = ''
        self.ticker = ticker.upper()
        self.product = product
        self.direction = direction
        self.strike = strike
        self.width1 = width1
        self.width2 = width2
        self.quantity = quantity
        self.expiry = expiry
        self.volatility = volatility
        self.load_contracts = load_contracts

        self.pricing_method = p.PRICING_METHODS[0] # black-scholes
        self.chain: Chain = Chain(self.ticker)
        self.analysis = Analysis(ticker=self.ticker)
        self.legs: list[Leg] = []
        self.initial_spot = store.get_last_price(self.ticker)
        self.error = ''

        # Default expiry is third Friday of next month, otherwise set it and check validity
        if expiry is None:
            self.expiry = m.third_friday()
        else:
            self.expiry.replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow = dt.datetime.today() + dt.timedelta(days=1)
            if self.expiry < tomorrow:
                raise ValueError('Invalid option expiry')

        self.analysis.credit_debit = 'debit' if direction == 'long' else 'credit'

    def __str__(self):
        return f'{self.legs[0].direction} {self.name}'

    def calculate(self) -> None:
        for leg in self.legs:
            leg.calculate()

    @Threaded.threaded
    def analyze(self) -> None:
        # Works for one-legged strategies. Override for others
        if self.validate():
            self.task_state = 'None'
            self.task_message = self.legs[0].option.ticker

            self.legs[0].calculate()

            self.analysis.credit_debit = 'debit' if self.direction == 'long' else 'credit'
            self.analysis.total = self.legs[0].option.price_eff * self.quantity

            self.generate_profit_table()
            self.calculate_metrics()
            self.calculate_breakeven()
            self.calculate_pop()
            self.calculate_score()
            self.analysis.summarize()

            _logger.info(f'{__name__}: {self.ticker}: p={self.legs[0].option.price_eff:.2f}, g={self.analysis.max_gain:.2f}, \
                l={self.analysis.max_loss:.2f} b={self.analysis.breakeven[0] :.2f}')
        else:
            _logger.warning(f'{__name__}: Unable to analyze strategy for {self.ticker}: {self.error}')

        self.task_state = 'Done'

    def reset(self) -> None:
        self.analysis = Analysis()

    def update_expiry(self, date: dt.datetime) -> None:
        for leg in self.legs:
            leg.option.expiry = date

    def add_leg(self, quantity: int, product: str, direction: str, strike: float, expiry: dt.datetime, volatility: tuple[float, float]) -> int:
        leg = Leg(self.ticker, quantity, product, direction, strike, expiry, volatility)
        self.legs += [leg]

        return len(self.legs)

    def set_pricing_method(self, method: str):
        if method in p.PRICING_METHODS:
            self.pricing_method = method
            for leg in self.legs:
                leg.pricing_method = method
        else:
            raise ValueError('Invalid pricing method')

    def fetch_contracts(self, expiry: dt.datetime, strike: float = -1.0) -> list[tuple[str, pd.DataFrame]]:
        # Works for one-legged strategies. Override for others
        expiry_tuple = self.chain.get_expiry()

        # Calculate expiry
        if not expiry_tuple:
            raise ValueError('No option expiry dates')

        # Get the closest date to expiry
        expiry_list = [dt.datetime.strptime(item, ui.DATE_FORMAT) for item in expiry_tuple]
        self.expiry = min(expiry_list, key=lambda d: abs(d - expiry))
        self.chain.expire = self.expiry

        # Get the option chain
        contract = ''
        chain_index = -1
        product = self.legs[0].option.product
        chain = self.chain.get_chain(product)

        # Calculate the index into the option chain
        if chain.empty:
            _logger.warning(f'{__name__}: Error fetching option chain for {self.ticker}')
        elif strike <= 0.0:
            chain_index = self.chain.get_index_itm()
        else:
            chain_index = self.chain.get_index_strike(strike)

        # Add the option contract
        if chain_index < 0:
            _logger.warning(f'{__name__}: Error fetching default contract for {self.ticker}')
        elif chain_index >= len(chain):
            _logger.warning(f'{__name__}: Insufficient options for {self.ticker}')
        else:
            contract = chain.iloc[chain_index]['contractSymbol']

        items = [(contract, chain)]
        return items

    @abc.abstractmethod
    def generate_profit_table(self) -> bool:
        return False

    @abc.abstractmethod
    def calculate_metrics(self) -> bool:
        return False

    @abc.abstractmethod
    def calculate_breakeven(self) -> bool:
        return False

    def calculate_pop(self) -> bool:
        # Works for one-legged strategies. Override for others
        pop = abs(self.legs[0].option.delta)
        if self.legs[0].direction == 'short':
            pop = 1.0 - pop

        self.analysis.pop = pop

        return True

    def calculate_score(self) -> bool:
        # Works for one-legged strategies. Override for others
        self.analysis.score_options = self.analysis.pop

        return True

    def set_score_screen(self, score: float):
        self.analysis.score_screen = score

    def validate(self) -> bool:
        # Works for one-legged strategies. Override for others
        if self.error:
            pass # Return existing error
        elif len(self.legs) < 1:
            self.error = 'Incorrect number of legs'

        return not bool(self.error)

if __name__ == '__main__':
    import logging
    from strategies.call import Call
    from strategies.put import Put
    from strategies.vertical import Vertical
    from utils import logger

    # logger.get_logger(logging.DEBUG)

    # strategy = Vertical('AAPL', 'call', 'long', 1, 1, True)
    strategy = Call('NVDA', 'call', 'long', 1, 1, True)
    # strategy = Put('IBM', 'put', 'long', 1, 1, True)
    strategy.analyze()

    # print(strategy)
    # print(strategy.analysis)
    # print(strategy.legs[0].value)
    # print(strategy.legs[1].value)
    print(strategy.analysis.profit_table)
    print(strategy.analysis.analysis)
