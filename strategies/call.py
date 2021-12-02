import pandas as pd

from base import Threaded
import strategies as s
from strategies.strategy import Strategy
from utils import ui
from utils import math as m


_logger = ui.get_logger()


class Call(Strategy):
    def __init__(self, ticker:str, product:str, direction:str, width:int, quantity:int, load_default:bool=False):
        product = 'call'
        super().__init__(ticker, product, direction, width, quantity, load_default)

        self.name = s.STRATEGIES_BROAD[0]


        # Default expiry to tird Friday of next month
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

            self.legs[0].calculate(self.legs[0].option.strike)

            price = self.legs[0].option.last_price if self.legs[0].option.last_price > 0.0 else self.legs[0].option.calc_price

            self.analysis.credit_debit = 'debit' if self.legs[0].direction == 'long' else 'credit'

            # Calculate net debit or credit
            self.analysis.amount = price * self.quantity

            # Generate profit table
            self.analysis.table = self.generate_profit_table()

            # Calculate min max
            self.analysis.max_gain, self.analysis.max_loss, self.analysis.upside, self.analysis.sentiment = self.calculate_gain_loss()

            # Calculate breakeven
            self.analysis.breakeven = self.calculate_breakeven()

        self.task_error = 'Done'

    def generate_profit_table(self) -> pd.DataFrame:
        profit = pd.DataFrame()
        price = self.legs[0].option.last_price if self.legs[0].option.last_price > 0.0 else self.legs[0].option.calc_price

        if self.legs[0].direction == 'long':
            profit = self.legs[0].value - price
        else:
            profit = self.legs[0].value
            profit = profit.applymap(lambda x: (price - x) if x < price else -(x - price))

        return profit

    def calculate_gain_loss(self) -> tuple[float, float, float, str]:
        price = self.legs[0].option.last_price if self.legs[0].option.last_price > 0.0 else self.legs[0].option.calc_price
        if self.legs[0].direction == 'long':
            max_gain = -1.0
            max_loss = price * self.quantity
            upside = 0.0
            sentiment = 'bullish'
        else:
            max_gain = price * self.quantity
            max_loss = -1.0
            upside = 0.0
            sentiment = 'bearish'

        return max_gain, max_loss, upside, sentiment

    def calculate_breakeven(self) -> float:
        if self.legs[0].direction == 'long':
            breakeven = self.legs[0].option.strike + self.analysis.amount
        else:
            breakeven = self.legs[0].option.strike - self.analysis.amount

        return breakeven


if __name__ == '__main__':
    import logging
    ui.get_logger(logging.INFO)

    call = Call('AAPL', 'call', 'long', 1, 1)
    call.legs[0].calculate(call.legs[0].option.strike, value_table=False, greeks=False)
    output = f'${call.legs[0].option.calc_price:.2f}, ({call.legs[0].option.strike:.2f})'
    print(output)
