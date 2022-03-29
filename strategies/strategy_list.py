import sys
from concurrent import futures
import collections

import pandas as pd

from strategies.strategy import Strategy
from strategies.call import Call
from strategies.put import Put
from strategies.vertical import Vertical
from strategies.iron_condor import IronCondor
from strategies.iron_butterfly import IronButterfly
from utils import logger

_logger = logger.get_logger()

strategy_type = collections.namedtuple('strategy', ['ticker', 'strategy', 'product', 'direction', 'strike'])
strategy_state = ''
strategy_msg = ''
strategy_results = pd.DataFrame()
strategy_legs = []
strategy_total = 0
strategy_completed = 0
strategy_errors = []
strategy_futures = []


def analyze(strategies: list[strategy_type]) -> None:
    global strategy_state
    global strategy_msg
    global strategy_results
    global strategy_legs
    global strategy_total
    global strategy_completed
    global strategy_errors
    global strategy_futures

    def process(strategy: Strategy) -> None:
        global strategy_results, strategy_legs, strategy_msg, strategy_completed, strategy_errors

        if not strategy.error:
            strategy_msg = strategy.ticker
            strategy.analyze()
            strategy_results = pd.concat([strategy_results, strategy.analysis.summary])
            strategy_legs += [f'{str(leg)}' for leg in strategy.legs]
        else:
            strategy_errors += [strategy.error]
            _logger.warning(f'{__name__}: Error analyzing strategy: {strategy.error}')

        strategy_completed += 1

    strategy_total = len(strategies)
    if strategy_total > 0:
        strategy_state = 'None'
        items: list[Strategy] = []

        try:
            for s in strategies:
                if s.strategy == 'call':
                    strategy_msg = f'{s.ticker}: ${s.strike:.2f} {s.direction} {s.product}'
                    items += [Call(s.ticker, 'call', s.direction, s.strike, 0, 0, 1, load_contracts=True)]
                elif s.strategy == 'put':
                    strategy_msg = f'{s.ticker}: ${s.strike:.2f} {s.direction} {s.product}'
                    items += [Put(s.ticker, 'put', s.direction, s.strike, 0, 0, 1, load_contracts=True)]
                elif s.strategy == 'vert':
                    items += [Vertical(s.ticker, s.product, s.direction, s.strike, 1, 0, 1, load_contracts=True)]
                    strategy_msg = f'{s.ticker}: ${items[-1].legs[0].option.strike:.2f}/{items[-1].legs[1].option.strike:.2f} {s.product}'
                elif s.strategy == 'ic':
                    strategy_msg = f'{s.ticker}'
                    items += [IronCondor(s.ticker, 'hybrid', s.direction, s.strike, 1, 1, 1, load_contracts=True)]
                elif s.strategy == 'ib':
                    strategy_msg = f'{s.ticker}'
                    items += [IronButterfly(s.ticker, 'hybrid', s.direction, s.strike, 1, 0, 1, load_contracts=True)]
        except Exception as e:
            strategy_state = f'{__name__}: {items[-1].ticker}: {str(sys.exc_info()[1])}'
            items = []
        else:
            if len(items) > 0:
                strategy_state = 'Next'
                with futures.ThreadPoolExecutor(max_workers=strategy_total) as executor:
                    strategy_futures = [executor.submit(process, item) for item in items]

                    for future in futures.as_completed(strategy_futures):
                        _logger.info(f'{__name__}: Thread completed: {future.result()}')

                if not strategy_results.empty:
                    strategy_results.sort_values('pop', ascending=False, inplace=True)

            strategy_state = 'Done'
    else:
        strategy_state = 'No tickers'


def reset():
    global strategy_state
    global strategy_msg
    global strategy_results
    global strategy_legs
    global strategy_total
    global strategy_completed
    global strategy_futures

    strategy_state = ''
    strategy_msg = ''
    strategy_results = pd.DataFrame()
    strategy_legs = []
    strategy_total = 0
    strategy_completed = 0
    strategy_futures = []
