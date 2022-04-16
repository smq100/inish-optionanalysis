import sys
import collections
from concurrent import futures

import pandas as pd

from . import STRATEGIES
from strategies.strategy import Strategy
from strategies.call import Call
from strategies.put import Put
from strategies.vertical import Vertical
from strategies.iron_condor import IronCondor
from strategies.iron_butterfly import IronButterfly
from utils import logger


_logger = logger.get_logger()

strategy_type = collections.namedtuple('strategy', [
    'ticker',
    'strategy',
    'product',
    'direction',
    'strike',
    'width1',
    'width2',
    'expiry',
    'volatility',
    'score_screen',
    'load_contracts'])

strategy_state = ''
strategy_msg = ''
strategy_parameters = pd.DataFrame()
strategy_results = pd.DataFrame()
strategy_total = 0
strategy_completed = 0
strategy_errors = []
strategy_futures = []


def analyze(strategies: list[strategy_type]) -> None:
    global strategy_state
    global strategy_msg
    global strategy_parameters
    global strategy_results
    global strategy_total
    global strategy_completed
    global strategy_errors
    global strategy_futures

    def process(strategy: Strategy) -> None:
        global strategy_results, strategy_msg, strategy_completed, strategy_errors

        if not strategy.error:
            strategy_msg = strategy.ticker
            name = f'{strategy.direction} {strategy.name}'
            strikes = [leg.option.strike for leg in strategy.legs]
            strategy.analysis.set_strategy(name, strikes, strategy.expiry)

            strategy.analyze()

            strategy = pd.concat([strategy.analysis.strategy, strategy.analysis.analysis], axis=1)
            strategy_results = pd.concat([strategy_results, strategy], axis=0)
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
                decorator = ' *' if s.load_contracts else ''
                if s.strategy == STRATEGIES[0]: # Call
                    strategy_msg = f'{s.ticker}: ${s.strike:.2f} {s.direction} {s.product}{decorator}'
                    item = Call(s.ticker, 'call', s.direction, s.strike, quantity=1,
                        expiry=s.expiry, volatility=s.volatility, load_contracts=s.load_contracts)
                    item.set_score_screen(s.score_screen)
                    items += [item]
                elif s.strategy == STRATEGIES[1]: # Put
                    strategy_msg = f'{s.ticker}: ${s.strike:.2f} {s.direction} {s.product}{decorator}'
                    item = Put(s.ticker, 'put', s.direction, s.strike, quantity=1,
                        expiry=s.expiry, volatility=s.volatility, load_contracts=s.load_contracts)
                    item.set_score_screen(s.score_screen)
                    items += [item]
                elif s.strategy == STRATEGIES[2]: # Vertical
                    strategy_msg = f'{s.ticker}: ${s.strike:.2f} {s.direction} {s.product}{decorator}'
                    item = Vertical(s.ticker, s.product, s.direction, s.strike, width=1, quantity=1,
                        expiry=s.expiry, volatility=s.volatility, load_contracts=s.load_contracts)
                    item.set_score_screen(s.score_screen)
                    items += [item]
                elif s.strategy == STRATEGIES[3]: # Iron condor
                    strategy_msg = f'{s.ticker}: ${s.strike:.2f}{decorator}'
                    item = IronCondor(s.ticker, 'hybrid', s.direction, s.strike, width1=1, width2=1, quantity=1,
                        expiry=s.expiry, volatility=s.volatility, load_contracts=s.load_contracts)
                    item.set_score_screen(s.score_screen)
                    items += [item]
                elif s.strategy == STRATEGIES[4]: # Iron butterfly
                    strategy_msg = f'{s.ticker}: ${s.strike:.2f}{decorator}'
                    item = IronButterfly(s.ticker, 'hybrid', s.direction, s.strike, width1=1, width2=0, quantity=1,
                        expiry=s.expiry, volatility=s.volatility, load_contracts=s.load_contracts)
                    item.set_score_screen(s.score_screen)
                    items += [item]
        except Exception as e:
            strategy_state = f'{__name__}: {items[-1].ticker}: {str(sys.exc_info()[1])}'
            items = []
        else:
            if len(items) > 0:
                strategy_state = 'Next'
                with futures.ThreadPoolExecutor(max_workers=strategy_total) as executor:
                    strategy_futures = [executor.submit(process, item) for item in items if not item.error]

                    for future in futures.as_completed(strategy_futures):
                        _logger.info(f'{__name__}: Thread completed: {future.result()}')

                if not strategy_results.empty:
                    strategy_results.sort_values('score_total', ascending=False, inplace=True)

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
