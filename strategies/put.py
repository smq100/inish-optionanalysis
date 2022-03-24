import pandas as pd

from base import Threaded
import strategies as s
from strategies.strategy import Strategy
from utils import math as m
from utils import ui, logger


_logger = logger.get_logger()


class Put(Strategy):
    def __init__(self, ticker: str, product: str, direction: str, strike: float, width1: int, width2: int, quantity: int = 1, load_contracts: bool = False):
        product = s.PRODUCTS[1]

        # Initialize the base strategy
        super().__init__(ticker, product, direction, strike, width1, 0, quantity, load_contracts)

        self.name = s.STRATEGIES_BROAD[1]

        # Default expiry to third Friday of next month
        expiry = m.third_friday()

        self.add_leg(self.quantity, product, direction, self.strike, expiry)

        if load_contracts:
            _, _, contract = self.fetch_contracts(strike)
            if contract:
                self.legs[0].option.load_contract(contract[0])
            else:
                _logger.warning(f'{__name__}: Error fetching contracts for {self.ticker}. Using calculated values')

    def __str__(self):
        return f'{self.legs[0].direction} {self.name}'

    def fetch_contracts(self, strike: float = -1.0, distance: int = 1, weeks: int = -1) -> tuple[str, int, list[str]]:
        if distance < 0:
            raise ValueError('Invalid distance')

        contract = ''
        expiry = self.chain.get_expiry()

        if not expiry:
            raise ValueError('No option expiry dates')
        elif weeks < 0:
            # Default to next month's option date
            third = f'{m.third_friday():%Y-%m-%d}'
            self.chain.expire = third if third in expiry else expiry[0]
        elif len(expiry) > weeks:
            self.chain.expire = expiry[weeks]
        else:
            self.chain.expire = expiry[0]

        product = self.legs[0].option.product
        options = self.chain.get_chain(product)

        if strike <= 0.0:
            chain_index = self.chain.get_index_itm()
        else:
            chain_index = self.chain.get_index_strike(strike)

        if chain_index >= 0:
            contract = options.iloc[chain_index]['contractSymbol']
        else:
            _logger.error(f'{__name__}: Error fetching default contract for {self.ticker}')

        return product, chain_index, [contract]

    @Threaded.threaded
    def analyze(self) -> None:
        if self.validate():
            self.task_error = 'None'
            self.task_message = self.legs[0].option.ticker

            self.legs[0].calculate()
            self.legs[0].option.eff_price = self.legs[0].option.last_price if self.legs[0].option.last_price > 0.0 else self.legs[0].option.calc_price

            self.analysis.credit_debit = 'debit' if self.direction == 'long' else 'credit'
            self.analysis.total = self.legs[0].option.eff_price * self.quantity

            self.analysis.max_gain, self.analysis.max_loss, self.analysis.upside, self.analysis.sentiment = self.calculate_gain_loss()
            self.analysis.table = self.generate_profit_table()
            self.analysis.breakeven = self.calculate_breakeven()
            self.analysis.summarize()

            _logger.info(f'{__name__}: {self.ticker}: p={self.legs[0].option.eff_price:.2f}, g={self.analysis.max_gain:.2f}, \
                l={self.analysis.max_loss:.2f} b={self.analysis.breakeven[0]:.2f}')

        self.task_error = 'Done'

    def calculate_gain_loss(self) -> tuple[float, float, float, str]:
        upside = -1.0

        if self.legs[0].direction == 'long':
            max_gain = (self.legs[0].option.strike - self.legs[0].option.eff_price) * self.quantity
            max_loss = self.legs[0].option.eff_price * self.quantity
            sentiment = 'bearish'
        else:
            max_gain = self.legs[0].option.eff_price * self.quantity
            max_loss = (self.legs[0].option.strike - self.legs[0].option.eff_price) * self.quantity
            sentiment = 'bullish'

        return max_gain, max_loss, upside, sentiment

    def generate_profit_table(self) -> pd.DataFrame:
        profit = pd.DataFrame()

        if self.legs[0].direction == 'long':
            profit = self.legs[0].value_table - self.legs[0].option.eff_price
            profit = profit.applymap(lambda x: x if x > -self.legs[0].option.eff_price else -self.legs[0].option.eff_price)
        else:
            profit = self.legs[0].value_table
            profit = profit.applymap(lambda x: (self.legs[0].option.eff_price - x) if x < self.legs[0].option.eff_price else -(x - self.legs[0].option.eff_price))

        return profit

    def calculate_breakeven(self) -> list[float]:
        if self.legs[0].direction == 'long':
            breakeven = self.legs[0].option.strike - self.analysis.total
        else:
            breakeven = self.legs[0].option.strike + self.analysis.total

        return [breakeven]


if __name__ == '__main__':
    # import logging
    # logger.get_logger(logging.INFO)
    import math
    from data import store

    pd.options.display.float_format = '{:,.2f}'.format

    ticker = 'AAPL'
    strike = float(math.floor(store.get_last_price(ticker)))
    put = Put(ticker, 'put', 'long', strike, 1, 0, load_contracts=True)
    put.analyze()

    print(put.legs[0])
    # print(put.legs[0].value_table)
