import datetime as dt

import pandas as pd

import strategies as s
from strategies.strategy import Strategy
from utils import ui


_logger = ui.get_logger()


class Put(Strategy):
    def __init__(self, ticker:str, product:str, direction:str, width:int, quantity:int, load_default:bool=False):
        product = 'put'
        super().__init__(ticker, product, direction, width, quantity, load_default)

        self.name = s.STRATEGIES_BROAD[1]

        # Default to a week from Friday as expiry
        d = dt.datetime.today()
        while d.weekday() != 4:
            d += dt.timedelta(1)
        expiry = d + dt.timedelta(days=6)

        self.add_leg(self.quantity, product, direction, self.initial_spot, expiry)

        if load_default:
            _, contract = self.fetch_default_contracts(s.DEFAULT_OPTION_ITM_DISTANCE, s.DEFAULT_OPTION_WEEKS)
            if contract:
                self.legs[0].option.load_contract(contract[0])

    def __str__(self):
        return f'{self.legs[0].direction} {self.name}'

    def analyze(self) -> None:
        if self._validate():
            self.legs[0].calculate(self.legs[0].option.strike)

            price = self.legs[0].option.last_price if self.legs[0].option.last_price > 0.0 else self.legs[0].option.calc_price

            self.analysis.credit_debit = 'debit' if self.legs[0].direction == 'long' else 'credit'

            # Calculate net debit or credit
            self.analysis.amount = price * self.quantity

            # Generate profit table
            self.analysis.table = self.generate_profit_table()

            # Calculate min max
            self.analysis.max_gain, self.analysis.max_loss = self.calculate_max_gain_loss()

            # Calculate breakeven
            self.analysis.breakeven = self.calculate_breakeven()

    def generate_profit_table(self) -> pd.DataFrame:
        profit = pd.DataFrame()
        price = self.legs[0].option.last_price if self.legs[0].option.last_price > 0.0 else self.legs[0].option.calc_price

        if self.legs[0].direction == 'long':
            profit = self.legs[0].value - price
            profit = profit.applymap(lambda x: x if x > -price else -price)
        else:
            profit = self.legs[0].value
            profit = profit.applymap(lambda x: (price - x) if x < price else -(x - price))

        return profit

    def calculate_max_gain_loss(self) -> tuple[float, float]:
        price = self.legs[0].option.last_price if self.legs[0].option.last_price > 0.0 else self.legs[0].option.calc_price
        if self.legs[0].direction == 'long':
            self.analysis.sentiment = 'bearish'
            max_gain = (self.legs[0].option.strike - price) * self.quantity
            max_loss = price * self.quantity
        else:
            self.analysis.sentiment = 'bullish'
            max_gain = price * self.quantity
            max_loss = (self.legs[0].option.strike - price) * self.quantity

        return max_gain, max_loss

    def calculate_breakeven(self) -> float:
        if self.legs[0].direction == 'long':
            breakeven = self.legs[0].option.strike - self.analysis.amount
        else:
            breakeven = self.legs[0].option.strike + self.analysis.amount

        return breakeven

if __name__ == '__main__':
    import logging
    ui.get_logger(logging.INFO)

    put = Put('MSFT', 'call', 'long', 1)
    put.legs[0].calculate(put.legs[0].option.strike, value_table=False, greeks=False)
    output = f'${put.legs[0].option.calc_price:.2f}, ({put.legs[0].option.strike:.2f})'
    print(output)
