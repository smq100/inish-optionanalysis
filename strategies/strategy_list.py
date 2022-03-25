import sys
from concurrent import futures
import collections

import pandas as pd

from strategies.strategy import Strategy
from strategies.call import Call
from strategies.put import Put
from strategies.vertical import Vertical
from strategies.iron_condor import IronCondor
from utils import logger

_logger = logger.get_logger()

strategy_type = collections.namedtuple('strategy', ['ticker', 'strategy', 'product', 'direction', 'strike'])
strategy_error = ''
strategy_msg = ''
strategy_results = pd.DataFrame()
strategy_legs = []
strategy_total = 0
strategy_completed = 0
strategy_futures = []


def analyze_list(strategies: list[strategy_type]) -> None:
    global strategy_error
    global strategy_msg
    global strategy_results
    global strategy_legs
    global strategy_total
    global strategy_completed
    global strategy_futures

    def analyze(strategy: Strategy) -> None:
        global strategy_results, strategy_legs, strategy_msg, strategy_completed

        strategy_msg = strategy.ticker
        strategy.analyze()
        strategy_results = pd.concat([strategy_results, strategy.analysis.summary])
        strategy_legs += [f'{str(leg)}' for leg in strategy.legs]
        strategy_completed += 1

    strategy_total = len(strategies)
    if strategy_total > 0:
        strategy_error = 'None'
        items = []

        try:
            for s in strategies:
                strategy_msg = f'{s.ticker}: ${s.strike:.2f} {s.direction} {s.product}'

                if s.strategy == 'call':
                    items += [Call(s.ticker, 'call', s.direction, s.strike, 1, 1, 1, load_contracts=True)]
                elif s.strategy == 'put':
                    items += [Put(s.ticker, 'put', s.direction, s.strike, 1, 1, 1, load_contracts=True)]
                elif s.strategy == 'vert':
                    items += [Vertical(s.ticker, s.product, s.direction, s.strike, 1, 1, 1, load_contracts=True)]
                elif s.strategy == 'ic':
                    items += [IronCondor(s.ticker, 'hybrid', s.direction, s.strike, 1, 1, 1, load_contracts=True)]
        except Exception as e:
            items = []
            strategy_error = str(sys.exc_info()[1])

        if len(items) > 0:
            strategy_error = 'Next'
            with futures.ThreadPoolExecutor(max_workers=strategy_total) as executor:
                strategy_futures = [executor.submit(analyze, item) for item in items]

                for future in futures.as_completed(strategy_futures):
                    _logger.info(f'{__name__}: Thread completed: {future.result()}')

            strategy_results.sort_values('pop', ascending=False, inplace=True)
            strategy_error = 'Done'
    else:
        strategy_error = 'No tickers'


def reset():
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
