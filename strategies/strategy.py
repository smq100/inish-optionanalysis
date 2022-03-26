import abc
from abc import ABC
import datetime as dt
import math

import pandas as pd

from base import Threaded
import strategies as s
from strategies.leg import Leg
from strategies.analysis import Analysis
from options.chain import Chain
import pricing as p
from data import store
from utils import math as m
from utils import logger


_logger = logger.get_logger()


class Strategy(ABC, Threaded):
    def __init__(self, ticker: str, product: str, direction: str, strike: float, width1: int, width2: int, quantity: int = 1, load_contracts: bool = False):
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

        self.name = ''
        self.ticker = ticker.upper()
        self.product = product
        self.direction = direction
        self.strike = strike
        self.quantity = quantity
        self.width1 = width1
        self.width2 = width2
        self.pricing_method = 'black-scholes'
        self.chain: Chain = Chain(self.ticker)
        self.analysis = Analysis(self.ticker)
        self.legs: list[Leg] = []
        self.initial_spot = 0.0
        self.initial_spot = self.get_current_spot(roundup=True)

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
            self.task_error = 'None'
            self.task_message = self.legs[0].option.ticker

            self.legs[0].calculate()
            self.legs[0].option.eff_price = self.legs[0].option.last_price if self.legs[0].option.last_price > 0.0 else self.legs[0].option.calc_price

            self.analysis.credit_debit = 'debit' if self.direction == 'long' else 'credit'
            self.analysis.total = self.legs[0].option.eff_price * self.quantity

            self.analysis.max_gain, self.analysis.max_loss, self.analysis.upside, self.analysis.sentiment = self.calculate_gain_loss()
            self.analysis.table = self.generate_profit_table()
            self.analysis.breakeven = self.calculate_breakeven()
            self.analysis.pop = self.calculate_pop()
            self.analysis.summarize()

            _logger.info(f'{__name__}: {self.ticker}: p={self.legs[0].option.eff_price:.2f}, g={self.analysis.max_gain:.2f}, \
                l={self.analysis.max_loss:.2f} b={self.analysis.breakeven[0] :.2f}')

        self.task_error = 'Done'

    def reset(self) -> None:
        self.analysis = Analysis()

    def update_expiry(self, date: dt.datetime) -> None:
        for leg in self.legs:
            leg.option.expiry = date

    def add_leg(self, quantity: int, product: str, direction: str, strike: float, expiry: dt.datetime) -> int:
        leg = Leg(self.ticker, quantity, product, direction, strike, expiry)
        self.legs += [leg]

        return len(self.legs)

    def get_current_spot(self, roundup: bool = False) -> float:
        history = store.get_history(self.ticker, days=30)
        spot = history.iloc[-1]['close']

        if roundup:
            spot = math.ceil(spot)

        return spot

    def set_pricing_method(self, method: str):
        if method in p.PRICING_METHODS:
            self.pricing_method = method
            for leg in self.legs:
                leg.pricing_method = method
        else:
            raise ValueError('Invalid pricing method')

    def fetch_contracts(self, strike: float = -1.0, distance: int = 1, weeks: int = -1) -> tuple[str, int, list[str]]:
        # Works for one-legged strategies. Override for others
        if distance < 0:
            raise ValueError('Invalid distance')

        contract = ''
        expiry = self.chain.get_expiry()

        if not expiry:
            raise ValueError('No option expiry dates')
        elif weeks < 0:
            # Default to next month's option date
            third = f'{m.third_friday():%Y-%m-%d}'
            self.chain.expire = third if third in expiry else expiry[0]
        elif len(expiry) > weeks:
            self.chain.expire = expiry[weeks]
        else:
            self.chain.expire = expiry[0]

        product = self.legs[0].option.product
        options = self.chain.get_chain(product)

        if strike <= 0.0:
            chain_index = self.chain.get_index_itm()
        else:
            chain_index = self.chain.get_index_strike(strike)

        if chain_index >= 0:
            contract = options.iloc[chain_index]['contractSymbol']
        else:
            _logger.error(f'{__name__}: Error fetching default contract for {self.ticker}')

        return product, chain_index, [contract]

    @abc.abstractmethod
    def calculate_gain_loss(self) -> tuple[float, float, float, str]:
        return (0.0, 0.0, 0.0, '')

    @abc.abstractmethod
    def generate_profit_table(self) -> pd.DataFrame:
        return pd.DataFrame()

    @abc.abstractmethod
    def calculate_breakeven(self) -> list[float]:
        return [0.0]

    def calculate_pop(self) -> float:
        # Works for one-legged strategies. Override for others
        pop = abs(self.legs[0].option.delta)
        if self.legs[0].direction == 'short':
            pop = 1.0 - pop

        return pop

    def get_errors(self) -> str:
        return ''

    def validate(self):
        return len(self.legs) > 0


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
    print(strategy.analysis.table)
    print(strategy.analysis.summary)
