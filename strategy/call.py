import datetime as dt

from strategy.strategy import Strategy, STRATEGIES
from utils import utils as utils

_logger = utils.get_logger()

class Call(Strategy):
    def __init__(self, ticker, product, direction, quantity):
        product = 'call'
        super().__init__(ticker, product, direction, quantity)

        self.name = STRATEGIES[0]

        # Default to a week from Friday as expiry
        d = dt.datetime.today()
        while d.weekday() != 4:
            d += dt.timedelta(1)
        expiry = d + dt.timedelta(days=6)

        self.add_leg(self.quantity, product, direction, self.initial_spot, expiry)

    def __str__(self):
        return f'{self.legs[0].direction} {self.name}'

    def analyze(self):
        if self._validate():
            self.legs[0].calculate()

            price = self.legs[0].option.last_price if self.legs[0].option.last_price > 0.0 else self.legs[0].option.calc_price

            if self.legs[0].direction == 'long':
                self.analysis.credit_debit = 'debit'
            else:
                self.analysis.credit_debit = 'credit'

            # Calculate net debit or credit
            self.analysis.amount = price * self.quantity

            # Generate profit table
            self.analysis.table = self.generate_profit_table()

            # Calculate min max
            self.analysis.max_gain, self.analysis.max_loss = self.calc_max_gain_loss()

            # Calculate breakeven
            self.analysis.breakeven = self.calc_breakeven()

    def generate_profit_table(self):
        profit = None
        price = self.legs[0].option.calc_price

        if self.legs[0].direction == 'long':
            profit = self.legs[0].table - price
        else:
            profit = self.legs[0].table
            profit = profit.applymap(lambda x: (price - x) if x < price else -(x - price))

        return profit

    def calc_max_gain_loss(self):
        if self.legs[0].direction == 'long':
            self.analysis.sentiment = 'bullish'
            max_gain = -1.0
            max_loss = self.legs[0].option.calc_price * self.quantity
        else:
            self.analysis.sentiment = 'bearish'
            max_gain = self.legs[0].option.calc_price * self.quantity
            max_loss = -1.0

        return max_gain, max_loss

    def calc_breakeven(self):
        if self.legs[0].direction == 'long':
            breakeven = self.legs[0].option.strike + self.analysis.amount
        else:
            breakeven = self.legs[0].option.strike - self.analysis.amount

        return breakeven


if __name__ == '__main__':
    import logging
    utils.get_logger(logging.INFO)

    call = Call('MSFT', 'call', 'long')
    call.legs[0].calculate(table=False, greeks=False)
    output = f'${call.legs[0].option.calc_price:.2f}, ({call.legs[0].option.strike:.2f})'
    print(output)
