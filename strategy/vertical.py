import datetime

from strategy.strategy import Strategy, STRATEGIES
from utils import utils as u

logger = u.get_logger()

class Vertical(Strategy):
    def __init__(self, ticker, product, direction):
        super().__init__(ticker, product, direction)

        self.name = STRATEGIES[2]

        # Default to a week from Friday as expiry
        d = datetime.datetime.today()
        while d.weekday() != 4:
            d += datetime.timedelta(1)
        expiry = d + datetime.timedelta(days=6)

        # Add legs (long leg is always first)
        if product == 'call':
            if direction == 'long':
                self.add_leg(1, product, 'long', self.initial_spot, expiry)
                self.add_leg(1, product, 'short', self.initial_spot + 2.0, expiry)
            else:
                self.add_leg(1, product, 'long', self.initial_spot + 2.0, expiry)
                self.add_leg(1, product, 'short', self.initial_spot, expiry)
        else:
            if direction == 'long':
                self.add_leg(1, product, 'long', self.initial_spot + 2.0, expiry)
                self.add_leg(1, product, 'short', self.initial_spot, expiry)
            else:
                self.add_leg(1, product, 'long', self.initial_spot, expiry)
                self.add_leg(1, product, 'short', self.initial_spot + 2.0, expiry)

    def __str__(self):
        return f'{self.name} {self.product} {self.analysis.credit_debit} spread'

    def analyze(self):
        ''' Analyze the stratwgy (Important: Assumes the long leg is the index-0 leg)'''

        if self._validate():
            self.legs[0].calculate()
            self.legs[1].calculate()

            dlong = (self.legs[0].option.calc_price > self.legs[1].option.calc_price)
            if dlong:
                self.analysis.credit_debit = 'debit'
            else:
                self.analysis.credit_debit = 'credit'

            # Calculate net debit or credit
            self.analysis.amount = self.legs[1].option.calc_price * self.legs[1].quantity
            self.analysis.amount -= (self.legs[0].option.calc_price * self.legs[0].quantity)

            # Generate profit table
            self.analysis.table = self.generate_profit_table()

            # Calculate min max
            self.analysis.max_gain, self.analysis.max_loss = self.calc_max_gain_loss()

            # Calculate breakeven
            self.analysis.breakeven = self.calc_breakeven()

    def generate_profit_table(self):
        # Create net-value table

        dframe = self.legs[0].table - self.legs[1].table + self.analysis.amount

        return dframe

    def calc_max_gain_loss(self):
        gain = loss = 0.0

        dlong = (self.legs[0].option.calc_price > self.legs[1].option.calc_price)
        if dlong:
            gain = abs(self.legs[0].option.strike - self.legs[1].option.strike)
            loss = abs(self.analysis.amount)

            if self.product == 'call':
                self.analysis.sentiment = 'bullish'
            else:
                self.analysis.sentiment = 'bearish'
        else:
            gain = abs(self.analysis.amount)
            loss = abs(self.legs[0].option.strike - self.legs[1].option.strike)

            if self.product == 'call':
                self.analysis.sentiment = 'bearish'
            else:
                self.analysis.sentiment = 'bullish'

        return gain, loss

    def calc_breakeven(self):
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

    def get_errors(self):
        error = ''
        if self.analysis.credit_debit:
            if self.product == 'call':
                if self.analysis.credit_debit == 'debit':
                    if self.legs[0].option.strike >= self.legs[1].option.strike:
                        error = 'Bad option configuration'
                elif self.legs[1].option.strike >= self.legs[0].option.strike:
                    error = 'Bad option configuration'
            else:
                if self.analysis.credit_debit == 'credit':
                    if self.legs[0].option.strike >= self.legs[1].option.strike:
                        error = 'Bad option configuration'
                elif self.legs[1].option.strike >= self.legs[0].option.strike:
                    error = 'Bad option configuration'

        return error

    def _validate(self):
        return len(self.legs) > 1

if __name__ == '__main__':
    import logging
    u.get_logger(logging.INFO)

    call = Vertical('MSFT', 'call', 'long')
    call.legs[0].calculate(table=False, greeks=False)
    output = f'${call.legs[0].option.calc_price:.2f}, ({call.legs[0].option.strike:.2f})'
    print(output)
    output = f'${call.legs[1].option.calc_price:.2f}, ({call.legs[1].option.strike:.2f})'
    print(output)
