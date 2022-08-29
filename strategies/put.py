import datetime as dt

import pandas as pd

import strategies as s
from strategies.strategy import Strategy
from utils import logger


_logger = logger.get_logger()


class Put(Strategy):
    def __init__(self,
                 ticker: str,
                 product: s.ProductType,
                 direction: s.DirectionType,
                 strike: float,
                 *,
                 quantity: int = 1,
                 expiry: dt.datetime = dt.datetime.now(),
                 volatility: tuple[float, float] = (-1.0, 0.0),
                 load_contracts: bool = False):

        # Initialize the base strategy
        super().__init__(
            ticker,
            product,
            direction,
            strike,
            width1=0,
            width2=0,
            quantity=quantity,
            expiry=expiry,
            volatility=volatility,
            load_contracts=load_contracts)

        self.type = s.StrategyType.Put

        self.add_leg(self.quantity, self.product, self.direction, self.strike, self.expiry, self.volatility)

        if load_contracts:
            items = self.fetch_contracts(self.expiry, strike=self.strike)
            if items:
                if not self.legs[0].option.load_contract(items[0][0], items[0][1]):
                    self.error = f'Unable to load put contract for {self.legs[0].company.ticker}'
                    _logger.warning(f'{__name__}: Error fetching contracts for {self.ticker}: {self.error}')
            else:
                _logger.warning(f'{__name__}: Error fetching contracts for {self.ticker}. Using calculated values')

    def generate_profit_table(self) -> bool:
        profit = pd.DataFrame()

        if self.legs[0].direction == s.DirectionType.Long:
            profit = self.legs[0].value_table - self.legs[0].option.price_eff
            profit = profit.applymap(lambda x: x if x > -self.legs[0].option.price_eff else -self.legs[0].option.price_eff)
        else:
            profit = self.legs[0].value_table
            profit = profit.applymap(lambda x: (self.legs[0].option.price_eff - x) if x < self.legs[0].option.price_eff else -(x - self.legs[0].option.price_eff))

        self.analysis.profit_table = profit

        return True

    def calculate_metrics(self) -> bool:
        if self.legs[0].direction == s.DirectionType.Long:
            self.analysis.max_gain = (self.legs[0].option.strike - self.legs[0].option.price_eff) * self.quantity
            self.analysis.max_loss = self.legs[0].option.price_eff * self.quantity
            self.analysis.sentiment = s.SentimentType.Bearish
        else:
            self.analysis.max_gain = self.legs[0].option.price_eff * self.quantity
            self.analysis.max_loss = (self.legs[0].option.strike - self.legs[0].option.price_eff) * self.quantity
            self.analysis.sentiment = s.SentimentType.Bullish

        self.analysis.upside = self.analysis.max_gain / self.analysis.max_loss if self.analysis.max_loss > 0.0 else 0.0
        self.analysis.score_options = 0.0

        return True

    def calculate_breakeven(self) -> bool:
        if self.legs[0].direction == s.DirectionType.Long:
            breakeven = self.legs[0].option.strike - self.analysis.total
        else:
            breakeven = self.legs[0].option.strike + self.analysis.total

        self.analysis.breakeven = [breakeven]

        return True


if __name__ == '__main__':
    # import logging
    # logger.get_logger(logging.INFO)
    import math
    from data import store

    pd.options.display.float_format = '{:,.2f}'.format

    ticker = 'AAPL'
    strike = float(math.floor(store.get_last_price(ticker)))
    put = Put(ticker, s.ProductType.Put, s.DirectionType.Long, strike)
    put.analyze()

    print(put.legs[0])
    # print(put.legs[0].value_table)
