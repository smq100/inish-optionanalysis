import pandas as pd

from base import Threaded
import strategies as s
from strategies.strategy import Strategy
from utils import math as m
from utils import ui, logger


_logger = logger.get_logger()


class Call(Strategy):
    def __init__(self, ticker: str, product: str, direction: str, width: int, quantity: int, load_default: bool = False):
        product = 'call'
        super().__init__(ticker, product, direction, width, quantity, load_default)

        self.name = s.STRATEGIES_BROAD[0]

        # Default expiry to third Friday of next month
        expiry = m.third_friday()

        self.add_leg(self.quantity, product, direction, self.initial_spot, expiry)

        if load_default:
            _, _, contract = self.fetch_default_contracts()
            if contract:
                self.legs[0].option.load_contract(contract[0])

    def __str__(self):
        return f'{self.legs[0].direction} {self.name}'

    @Threaded.threaded
    def analyze(self) -> None:
        if self.validate():
            self.task_error = 'None'
            self.task_message = self.legs[0].option.ticker

            self.legs[0].calculate()
            self.legs[0].option.eff_price = self.legs[0].option.last_price if self.legs[0].option.last_price > 0.0 else self.legs[0].option.calc_price

            self.analysis.credit_debit = 'debit' if self.legs[0].direction == 'long' else 'credit'
            self.analysis.total = self.legs[0].option.eff_price * self.quantity
            self.analysis.table = self.generate_profit_table()
            self.analysis.max_gain, self.analysis.max_loss, self.analysis.upside, self.analysis.sentiment = self.calculate_gain_loss()
            self.analysis.breakeven = self.calculate_breakeven()
            self.analysis.summarize()

            _logger.info(f'{__name__}: {self.ticker}: p={self.legs[0].option.eff_price:.2f}, g={self.analysis.max_gain:.2f}, l={self.analysis.max_loss:.2f} b={self.analysis.breakeven :.2f}')

        self.task_error = 'Done'

    def generate_profit_table(self) -> pd.DataFrame:
        profit = pd.DataFrame()

        if self.legs[0].direction == 'long':
            profit = self.legs[0].value - self.legs[0].option.eff_price
        else:
            profit = self.legs[0].value
            profit = profit.applymap(lambda x: (self.legs[0].option.eff_price - x) if x < self.legs[0].option.eff_price else -(x - self.legs[0].option.eff_price))

        return profit

    def calculate_gain_loss(self) -> tuple[float, float, float, str]:
        upside = -1.0

        if self.legs[0].direction == 'long':
            max_gain = -1.0
            max_loss = self.legs[0].option.eff_price * self.quantity
            sentiment = 'bullish'
        else:
            max_gain = self.legs[0].option.eff_price * self.quantity
            max_loss = -1.0
            sentiment = 'bearish'

        return max_gain, max_loss, upside, sentiment

    def calculate_breakeven(self) -> float:
        if self.legs[0].direction == 'long':
            breakeven = self.legs[0].option.strike + self.analysis.total
        else:
            breakeven = self.legs[0].option.strike - self.analysis.total

        return breakeven


if __name__ == '__main__':
    import logging
    ui.get_logger(logging.INFO)

    call = Call('AAPL', 'call', 'long', 1, 1)
    call.legs[0].calculate(call.legs[0].option.strike, value_table=False, greeks=False)
    output = f'${call.legs[0].option.calc_price:.2f}, ({call.legs[0].option.strike:.2f})'
    print(output)
