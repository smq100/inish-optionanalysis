import sys
import collections
from concurrent import futures

import pandas as pd

import strategies as s
from strategies.strategy import Strategy
from strategies.call import Call
from strategies.put import Put
from strategies.vertical import Vertical
from strategies.iron_condor import IronCondor
from strategies.iron_butterfly import IronButterfly
from utils import logger


_logger = logger.get_logger()

strategy_type = collections.namedtuple('strategy_type', [
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
            name = f'{strategy.direction.name} {strategy.type.value}'
            strategy_msg = ''
            strikes = [leg.option.strike for leg in strategy.legs]
            strategy.analysis.set_strategy(name, strikes, strategy.expiry, strategy.initial_spot)

            strategy.analyze()

            strategy = pd.concat([strategy.analysis.strategy, strategy.analysis.analysis], axis=1)
            strategy_results = pd.concat([strategy_results, strategy], axis=0)
        else:
            strategy_errors += [strategy.error]
            _logger.warning(f'{__name__}: Error analyzing strategy: {strategy.error}')

        strategy_completed += 1

    strategy_total = len(strategies)
    if strategy_total > 0:
        strategy_state = 'Creating'
        item: Strategy
        items: list[Strategy] = []

        try:
            for strategy in strategies:
                decorator = ' *' if strategy.load_contracts else ''
                if strategy.strategy == s.StrategyType.Call:
                    strategy_msg = f'{strategy.ticker}: ${strategy.strike:.2f} {strategy.direction.name} {strategy.product.name}{decorator}'
                    item = Call(strategy.ticker, s.ProductType.Call, strategy.direction, strategy.strike, quantity=1,
                                expiry=strategy.expiry, volatility=strategy.volatility, load_contracts=strategy.load_contracts)
                    item.set_score_screen(strategy.score_screen)
                    items += [item]
                elif strategy.strategy == s.StrategyType.Put:
                    strategy_msg = f'{strategy.ticker}: ${strategy.strike:.2f} {strategy.direction.name} {strategy.product.name}{decorator}'
                    item = Put(strategy.ticker, s.ProductType.Put, strategy.direction, strategy.strike, quantity=1,
                               expiry=strategy.expiry, volatility=strategy.volatility, load_contracts=strategy.load_contracts)
                    item.set_score_screen(strategy.score_screen)
                    items += [item]
                elif strategy.strategy == s.StrategyType.Vertical:
                    strategy_msg = f'{strategy.ticker}: ${strategy.strike:.2f} {strategy.direction.name} {strategy.strategy.value} {strategy.product.name}{decorator}'
                    item = Vertical(strategy.ticker, strategy.product, strategy.direction, strategy.strike, width=strategy.width1, quantity=1,
                                    expiry=strategy.expiry, volatility=strategy.volatility, load_contracts=strategy.load_contracts)
                    item.set_score_screen(strategy.score_screen)
                    items += [item]
                elif strategy.strategy == s.StrategyType.IronCondor:
                    strategy_msg = f'{strategy.ticker}: ${strategy.strike:.2f}{decorator}'
                    item = IronCondor(strategy.ticker, s.ProductType.Hybrid, strategy.direction, strategy.strike, width1=strategy.width1, width2=strategy.width2, quantity=1,
                                      expiry=strategy.expiry, volatility=strategy.volatility, load_contracts=strategy.load_contracts)
                    item.set_score_screen(strategy.score_screen)
                    items += [item]
                elif strategy.strategy == s.StrategyType.IronButterfly:
                    strategy_msg = f'{strategy.ticker}: ${strategy.strike:.2f}{decorator}'
                    item = IronButterfly(strategy.ticker, s.ProductType.Hybrid, strategy.direction, strategy.strike, width1=strategy.width1, quantity=1,
                                         expiry=strategy.expiry, volatility=strategy.volatility, load_contracts=strategy.load_contracts)
                    item.set_score_screen(strategy.score_screen)
                    items += [item]
        except Exception as e:
            strategy_state = f'{__name__}: {items[-1].ticker}: {str(sys.exc_info()[1])}'
            items = []
        else:
            if len(items) > 0:
                strategy_state = 'Analyzing'
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
