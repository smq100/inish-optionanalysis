import abc
from abc import ABC
import datetime as dt
import math
from concurrent import futures

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
    def __init__(self, ticker: str, product: str, direction: str, strike: float, width: int, quantity: int = 1, load_contracts: bool = False):
        if not store.is_ticker(ticker):
            raise ValueError('Invalid ticker')
        if product not in s.PRODUCTS:
            raise ValueError('Invalid product')
        if direction not in s.DIRECTIONS:
            raise ValueError('Invalid direction')
        if strike < 0.0:
            raise ValueError('Invalid strike')
        if width < 0:
            raise ValueError('Invalid width')
        if quantity < 1:
            raise ValueError('Invalid quantity')

        self.name = ''
        self.ticker = ticker.upper()
        self.product = product
        self.direction = direction
        self.strike = strike
        self.quantity = quantity
        self.width = width
        self.pricing_method = 'black-scholes'
        self.chain: Chain = Chain(self.ticker)
        self.analysis = Analysis(self.ticker)
        self.legs: list[Leg] = []
        self.initial_spot = 0.0
        self.initial_spot = self.get_current_spot(roundup=True)

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

    @abc.abstractmethod
    def fetch_contracts(self, strike: float = -1.0, distance: int = 1, weeks: int = -1) -> tuple[str, int, list[str]]:
        pass
        # return 0, 0, []

    @abc.abstractmethod
    def generate_profit_table(self) -> pd.DataFrame:
        return pd.DataFrame()

    @abc.abstractmethod
    def calculate_gain_loss(self) -> tuple[float, float, float, str]:
        return (0.0, 0.0, 0.0, '')

    @abc.abstractmethod
    def calculate_breakeven(self) -> list[float]:
        return [0.0]

    def get_errors(self) -> str:
        return ''

    def validate(self):
        return len(self.legs) > 0


strategy_error = ''
strategy_msg = ''
strategy_results = pd.DataFrame()
strategy_legs = []
strategy_total = 0
strategy_completed = 0
strategy_futures = []


def analyze_list(strategies: list[Strategy]) -> None:
    global strategy_error
    global strategy_msg
    global strategy_results
    global strategy_legs
    global strategy_total
    global strategy_completed
    global strategy_futures

    strategy_error = ''
    strategy_msg = ''
    strategy_results = pd.DataFrame()
    strategy_legs = []
    strategy_total = 0
    strategy_completed = 0
    strategy_futures = []

    def analyze(strategy: Strategy):
        global strategy_results, strategy_legs, strategy_msg, strategy_completed
        strategy_msg = strategy.ticker

        strategy.analyze()
        strategy_results = pd.concat([strategy_results, strategy.analysis.summary])
        strategy_legs += [f'{str(leg)}' for leg in strategy.legs]
        strategy_completed += 1

    strategy_total = len(strategies)
    if strategy_total > 0:
        strategy_error = 'None'
        with futures.ThreadPoolExecutor(max_workers=strategy_total) as executor:
            strategy_futures = [executor.submit(analyze, item) for item in strategies]

            for future in futures.as_completed(strategy_futures):
                _logger.info(f'{__name__}: Thread completed: {future.result()}')

        strategy_results.sort_values('upside', ascending=False, inplace=True)
        strategy_error = 'Done'
    else:
        strategy_error = 'No tickers'



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
