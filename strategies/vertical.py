import datetime as dt

import pandas as pd

from strategies.strategy import Strategy, STRATEGIES
from utils import utils as utils

_logger = utils.get_logger()

class Vertical(Strategy):
    def __init__(self, ticker, product, direction, quantity):
        super().__init__(ticker, product, direction, quantity)

        self.name = STRATEGIES[2]

        # Default to a week from Friday as expiry
        d = dt.datetime.today()
        while d.weekday() != 4:
            d += dt.timedelta(1)
        expiry = d + dt.timedelta(days=6)

        # Add legs (Important: long leg is always first)
        if product == 'call':
            if direction == 'long':
                self.add_leg(self.quantity, product, 'long', self.initial_spot, expiry)
                self.add_leg(self.quantity, product, 'short', self.initial_spot + 2.0, expiry)
            else:
                self.add_leg(self.quantity, product, 'long', self.initial_spot + 2.0, expiry)
                self.add_leg(self.quantity, product, 'short', self.initial_spot, expiry)
        else:
            if direction == 'long':
                self.add_leg(self.quantity, product, 'long', self.initial_spot + 2.0, expiry)
                self.add_leg(self.quantity, product, 'short', self.initial_spot, expiry)
            else:
                self.add_leg(self.quantity, product, 'long', self.initial_spot, expiry)
                self.add_leg(self.quantity, product, 'short', self.initial_spot + 2.0, expiry)

    def __str__(self):
        return f'{self.name} {self.product} {self.analysis.credit_debit} spread'

    def analyze(self) -> None:
        ''' Analyze the strategy (Important: Assumes the long leg is the index-0 leg)'''

        if self._validate():
            self.legs[0].calculate()
            self.legs[1].calculate()

            price_long = self.legs[0].option.last_price if self.legs[0].option.last_price > 0.0 else self.legs[0].option.calc_price
            price_short = self.legs[1].option.last_price if self.legs[1].option.last_price > 0.0 else self.legs[1].option.calc_price

            dlong = (price_long > price_short)
            if dlong:
                self.analysis.credit_debit = 'debit'
            else:
                self.analysis.credit_debit = 'credit'

            # Calculate net debit or credit
            self.analysis.amount = abs(price_long - price_short) * self.quantity

            # Generate profit table
            self.analysis.table = self.generate_profit_table()

            # Calculate min max
            self.analysis.max_gain, self.analysis.max_loss = self.calc_max_gain_loss()

            # Calculate breakeven
            self.analysis.breakeven = self.calc_breakeven()

    def generate_profit_table(self) -> pd.DataFrame:
        profit = ((self.legs[0].table - self.legs[1].table) * self.quantity) + self.analysis.amount

        return profit

    def calc_max_gain_loss(self) -> tuple[float, float]:
        gain = loss = 0.0

        dlong = (self.legs[0].option.calc_price > self.legs[1].option.calc_price)
        if dlong:
            loss = self.analysis.amount
            gain = (self.quantity * (self.legs[0].option.strike - self.legs[1].option.strike)) - loss

            if self.product == 'call':
                self.analysis.sentiment = 'bullish'
            else:
                self.analysis.sentiment = 'bearish'
        else:
            gain = self.analysis.amount
            loss = (self.quantity * (self.legs[1].option.strike - self.legs[0].option.strike)) - gain

            if self.product == 'call':
                self.analysis.sentiment = 'bearish'
            else:
                self.analysis.sentiment = 'bullish'

        return gain, loss

    def calc_breakeven(self) -> float:
        if self.analysis.credit_debit == 'debit':
            if self.product == 'call':
                breakeven = self.legs[1].option.strike + self.analysis.amount
            else:
                breakeven = self.legs[1].option.strike + self.analysis.amount
        else:
            if self.product == 'call':
                breakeven = self.legs[1].option.strike - self.analysis.amount
            else:
                breakeven = self.legs[1].option.strike - self.analysis.amount

        return breakeven

    def get_errors(self) -> str:
        error = ''
        if self.analysis.credit_debit:
            if self.product == 'call':
                if self.analysis.credit_debit == 'debit':
                    if self.legs[0].option.strike >= self.legs[1].option.strike:
                        error = 'Bad option configuration'
                elif self.legs[1].option.strike >= self.legs[0].option.strike:
                    error = 'Bad option configuration'
            else:
                if self.analysis.credit_debit == 'debit':
                    if self.legs[1].option.strike >= self.legs[0].option.strike:
                        error = 'Bad option configuration'
                elif self.legs[0].option.strike >= self.legs[1].option.strike:
                    error = 'Bad option configuration'

        return error

    def _validate(self) -> bool:
        return len(self.legs) > 1

if __name__ == '__main__':
    import logging
    utils.get_logger(logging.INFO)

    call = Vertical('MSFT', 'call', 'long', 1)
    call.legs[0].calculate(table=False, greeks=False)
    output = f'${call.legs[0].option.calc_price:.2f}, ({call.legs[0].option.strike:.2f})'
    print(output)
    output = f'${call.legs[1].option.calc_price:.2f}, ({call.legs[1].option.strike:.2f})'
    print(output)
