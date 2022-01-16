import abc
from abc import ABC
import datetime as dt
from logging import raiseExceptions
import math
from dataclasses import dataclass

import pandas as pd

from base import Threaded
import strategies as s
from strategies.leg import Leg
from options.chain import Chain
import pricing as p
from pricing.blackscholes import BlackScholes
from pricing.montecarlo import MonteCarlo
from data import store
from utils import math as m
from utils import ui, logger


_logger = logger.get_logger()


class Strategy(ABC, Threaded):
    def __init__(self, ticker: str, product: str, direction: str, width: int, quantity: int, load_default: bool = False):
        if not store.is_ticker(ticker):
            raise ValueError('Invalid ticker')
        if product not in s.PRODUCTS:
            raise ValueError('Invalid product')
        if direction not in s.DIRECTIONS:
            raise ValueError('Invalid direction')
        if width < 0:
            raise ValueError('Invalid width')
        if quantity < 1:
            raise ValueError('Invalid quantity')

        self.name = ''
        self.ticker = ticker.upper()
        self.product = product
        self.direction = direction
        self.quantity = quantity
        self.width = width
        self.pricing_method = 'black-scholes'
        self.chain: Chain = Chain(self.ticker)
        self.analysis = Analysis()
        self.legs: list[Leg] = []
        self.initial_spot = 0.0
        self.initial_spot = self.get_current_spot(ticker, roundup=True)

        self.analysis.credit_debit = 'debit' if direction == 'long' else 'credit'

    def calculate(self) -> None:
        for leg in self.legs:
            leg.calculate()

    @abc.abstractmethod
    def analyze(self) -> None:
        pass

    def reset(self) -> None:
        self.analysis = Analysis()

    def update_expiry(self, date: dt.datetime) -> None:
        for leg in self.legs:
            leg.option.expiry = date

    def add_leg(self, quantity: int, product: str, direction: str, strike: float, expiry: dt.datetime) -> int:
        leg = Leg(self.ticker, quantity, product, direction, strike, expiry)
        self.legs += [leg]

        return len(self.legs)

    def get_current_spot(self, ticker: str, roundup: bool = False) -> float:
        expiry = dt.datetime.today() + dt.timedelta(days=10)

        if self.pricing_method == 'black-scholes':
            pricer = BlackScholes(ticker, expiry, self.initial_spot)
        elif self.pricing_method == 'monte-carlo':
            pricer = MonteCarlo(ticker, expiry, self.initial_spot)
        else:
            raise ValueError('Unknown pricing model')

        if roundup:
            spot = math.ceil(pricer.spot_price)
        else:
            spot = pricer.spot_price

        return spot

    def set_pricing_method(self, method: str):
        if method in p.PRICING_METHODS:
            self.pricing_method = method
            for leg in self.legs:
                leg.pricing_method = method
        else:
            raise ValueError('Invalid pricing method')

    def fetch_default_contracts(self, distance: int = 1, weeks: int = -1) -> tuple[str, int, list[str]]:
        # Works for strategies with one leg. Multiple-leg strategies should be overridden
        if distance < 0:
            raise ValueError('Invalid distance')

        contract = ''
        expiry = self.chain.get_expiry()

        if not expiry:
            raise KeyError('No option expiry dates')
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

        index = self.chain.get_itm()
        if index >= 0:
            contract = options.iloc[index]['contractSymbol']
        else:
            _logger.error(f'{__name__}: Error fetching default contract')

        _logger.debug(f'{__name__}: {options}')
        _logger.debug(f'{__name__}: {index=}')

        return product, index, [contract]

    @abc.abstractmethod
    def generate_profit_table(self) -> pd.DataFrame:
        return pd.DataFrame()

    @abc.abstractmethod
    def calculate_gain_loss(self) -> tuple[float, float, float, str]:
        return (0.0, 0.0, 0.0, '')

    @abc.abstractmethod
    def calculate_breakeven(self) -> float:
        return 0.0

    def get_errors(self) -> str:
        return ''

    def validate(self):
        return len(self.legs) > 0


@dataclass
class Analysis:
    table: pd.DataFrame = None
    credit_debit = ''
    sentiment = ''
    amount = 0.0
    max_gain = 0.0
    max_loss = 0.0
    breakeven = 0.0
    upside = 0.0

    def __str__(self):
        if self.table is not None:
            gain = 'Unlimited' if self.max_gain < 0.0 else f'${self.max_gain:.2f}'
            loss = 'Unlimited' if self.max_loss < 0.0 else f'${self.max_loss:.2f}'

            output = \
                f'Type:      {self.credit_debit.title()}\n'\
                f'Sentiment: {self.sentiment.title()}\n'\
                f'Amount:    ${abs(self.amount):.2f} {self.credit_debit}\n'\
                f'Max Gain:  {gain}\n'\
                f'Max Loss:  {loss}\n'\
                f'Breakeven: ${self.breakeven:.2f} at expiry\n'\
                f'Upside:    {self.upside:.2f}\n'
        else:
            output = 'Not yet analyzed'

        return output


if __name__ == '__main__':
    import logging
    from strategies.call import Call
    from strategies.put import Put
    from strategies.vertical import Vertical

    ui.get_logger(logging.DEBUG)

    strategy = Vertical('AAPL', 'call', 'long', 1, 1, True)
    # strategy = Call('NVDA', 'call', 'long', 1, 1, True)
    # strategy = Put('AAPL', 'call', 'long', 1, 1, True)
    strategy.analyze()

    # print(strategy)
    print(strategy.analysis)
    print(strategy.legs[0].value)
    # print(strategy.legs[1].value)
    print(strategy.analysis.table)
