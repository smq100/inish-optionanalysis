import pandas as pd

from base import Threaded
import strategies as s
from strategies.strategy import Strategy
from utils import math as m
from utils import ui, logger


_logger = logger.get_logger()
DEFAULT_WIDTH = 2.0


class Vertical(Strategy):
    def __init__(self, ticker: str, product: str, direction: str, width: int, quantity: int, load_default: bool = False):
        if width < 1:
            raise ValueError('Invalid width')

        super().__init__(ticker, product, direction, width, quantity, load_default)

        self.name = s.STRATEGIES_BROAD[2]

        # Default expiry to tird Friday of next month
        expiry = m.third_friday()

        # Add legs. Long leg is always first!
        if product == 'call':
            if direction == 'long':
                self.add_leg(self.quantity, product, 'long', self.initial_spot, expiry)
                self.add_leg(self.quantity, product, 'short', self.initial_spot + DEFAULT_WIDTH, expiry)
            else:
                self.add_leg(self.quantity, product, 'long', self.initial_spot + DEFAULT_WIDTH, expiry)
                self.add_leg(self.quantity, product, 'short', self.initial_spot, expiry)
        else:
            if direction == 'long':
                self.add_leg(self.quantity, product, 'long', self.initial_spot + DEFAULT_WIDTH, expiry)
                self.add_leg(self.quantity, product, 'short', self.initial_spot, expiry)
            else:
                self.add_leg(self.quantity, product, 'long', self.initial_spot, expiry)
                self.add_leg(self.quantity, product, 'short', self.initial_spot + DEFAULT_WIDTH, expiry)

        if load_default:
            _, _, contracts = self.fetch_default_contracts()
            if len(contracts) == 2:
                self.legs[0].option.load_contract(contracts[0])
                self.legs[1].option.load_contract(contracts[1])
            else:
                _logger.warning(f'{__name__}: Error fetching contracts for {self.ticker}. Using calculated values')

    def __str__(self):
        return f'{self.name} {self.product} {self.analysis.credit_debit} spread'

    def fetch_default_contracts(self, distance: int = 1, weeks: int = -1) -> tuple[str, int, list[str]]:
        # super() fetches the long option & itm index
        product, index, contracts = super().fetch_default_contracts(distance, weeks)

        if index >= 0:
            if self.product == 'call':
                if self.direction == 'long':
                    index += self.width
                else:
                    index -= self.width
            elif self.direction == 'long':
                index -= self.width
            else:
                index += self.width

        # Add the short option
        if index >= 0:
            options = self.chain.get_chain(product)
            if index < len(options):
                contracts += [options.iloc[index]['contractSymbol']]
        else:
            _logger.error(f'{__name__}: Bad index value for {self.ticker}: {index=}')
            product = ''
            index = 0
            contracts = []

        return product, index, contracts

    @Threaded.threaded
    def analyze(self) -> None:

        if self._validate():
            self.task_error = 'None'
            self.task_message = self.legs[0].option.ticker

            self.legs[0].calculate()
            self.legs[1].calculate()

            # Important: Assumes the long leg is the index-0 leg)
            self.legs[0].option.eff_price = self.legs[0].option.last_price if self.legs[0].option.last_price > 0.0 else self.legs[0].option.calc_price
            self.legs[1].option.eff_price = self.legs[1].option.last_price if self.legs[1].option.last_price > 0.0 else self.legs[1].option.calc_price

            self.analysis.credit_debit = 'debit' if self.legs[0].option.eff_price > self.legs[1].option.eff_price else 'credit'
            self.analysis.total = abs(self.legs[0].option.eff_price - self.legs[1].option.eff_price) * self.quantity
            self.analysis.max_gain, self.analysis.max_loss, self.analysis.upside, self.analysis.sentiment = self.calculate_gain_loss()
            self.analysis.breakeven = self.calculate_breakeven()
            self.analysis.table = self.generate_profit_table()
            self.analysis.summarize()

            _logger.info(f'{__name__}: {self.ticker}: g={self.analysis.max_gain:.2f}, l={self.analysis.max_loss:.2f} b={self.analysis.breakeven :.2f}')
        self.task_error = 'Done'

    def generate_profit_table(self) -> pd.DataFrame:
        if self.analysis.credit_debit == 'credit':
            profit = ((self.legs[0].value - self.legs[1].value) * self.quantity) + self.analysis.total
        else:
            profit = ((self.legs[0].value - self.legs[1].value) * self.quantity) - self.analysis.total

        return profit

    def calculate_gain_loss(self) -> tuple[float, float, float, str]:
        max_gain = max_loss = 0.0

        self.legs[0].option.eff_price = self.legs[0].option.last_price if self.legs[0].option.last_price > 0.0 else self.legs[0].option.calc_price
        self.legs[1].option.eff_price = self.legs[1].option.last_price if self.legs[1].option.last_price > 0.0 else self.legs[1].option.calc_price

        debit = self.legs[0].option.eff_price > self.legs[1].option.eff_price
        if self.product == 'call':
            if debit:
                max_loss = self.analysis.total
                max_gain = (self.quantity * (self.legs[1].option.strike - self.legs[0].option.strike)) - max_loss
                if max_gain < 0.0:
                    max_gain = 0.0 # Debit is more than possible gain!
                sentiment = 'bullish'
            else:
                max_gain = self.analysis.total
                max_loss = (self.quantity * (self.legs[0].option.strike - self.legs[1].option.strike)) - max_gain
                if max_loss < 0.0:
                    max_loss = 0.0 # Credit is more than possible loss!
                sentiment = 'bearish'
        else:
            if debit:
                max_loss = self.analysis.total
                max_gain = (self.quantity * (self.legs[0].option.strike - self.legs[1].option.strike)) - max_loss
                if max_gain < 0.0:
                    max_gain = 0.0 # Debit is more than possible gain!
                sentiment = 'bearish'
            else:
                max_gain = self.analysis.total
                max_loss = (self.quantity * (self.legs[1].option.strike - self.legs[0].option.strike)) - max_gain
                if max_loss < 0.0:
                    max_loss = 0.0 # Credit is more than possible loss!
                sentiment = 'bullish'

        upside = max_gain - max_loss
        return max_gain, max_loss, upside, sentiment

    def calculate_breakeven(self) -> float:
        if self.analysis.credit_debit == 'debit':
            breakeven = self.legs[1].option.strike + self.analysis.total
        else:
            breakeven = self.legs[1].option.strike - self.analysis.total

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
        return len(self.legs) == 2


if __name__ == '__main__':
    import logging
    ui.get_logger(logging.INFO)

    call = Vertical('MSFT', 'call', 'long', 1)
    call.legs[0].calculate(call.legs[0].option.strike, value_table=False, greeks=False)
    output = f'${call.legs[0].option.calc_price:.2f}, ({call.legs[0].option.strike:.2f})'
    print(output)
    output = f'${call.legs[1].option.calc_price:.2f}, ({call.legs[1].option.strike:.2f})'
    print(output)
