import pandas as pd

from base import Threaded
import strategies as s
from strategies.strategy import Strategy
from utils import math as m
from utils import logger


_logger = logger.get_logger()

class IronCondor(Strategy):
    def __init__(self, ticker: str, product: str, direction: str, strike: float, width: int, quantity: int = 1, load_contracts: bool = False):
        if width < 1:
            raise ValueError('Invalid width')

        # Initialize the base strategy
        product = s.PRODUCTS[2]
        super().__init__(ticker, product, direction, strike, width, quantity, load_contracts)

        self.name = s.STRATEGIES_BROAD[3]

        # Default expiry to third Friday of next month
        expiry = m.third_friday()

        # Add legs in decending order of strike price
        if direction == 'long':
            self.add_leg(self.quantity, 'call', 'short', self.strike + (2 * self.width), expiry)
            self.add_leg(self.quantity, 'call', 'long', self.strike + self.width, expiry)
            self.add_leg(self.quantity, 'put', 'long', self.strike - self.width, expiry)
            self.add_leg(self.quantity, 'put', 'short', self.strike - (2 * self.width), expiry)
        else:
            self.add_leg(self.quantity, 'call', 'long', self.strike + (2 * self.width), expiry)
            self.add_leg(self.quantity, 'call', 'short', self.strike + self.width, expiry)
            self.add_leg(self.quantity, 'put', 'short', self.strike - self.width, expiry)
            self.add_leg(self.quantity, 'put', 'long', self.strike - (2 * self.width), expiry)

        if load_contracts:
            _, _, contracts = self.fetch_contracts(strike)
            if len(contracts) == 4:
                self.legs[0].option.load_contract(contracts[0])
                self.legs[1].option.load_contract(contracts[1])
                self.legs[2].option.load_contract(contracts[2])
                self.legs[3].option.load_contract(contracts[3])
            else:
                _logger.warning(f'{__name__}: Error fetching contracts for {self.ticker}. Using calculated values')

    def __str__(self):
        return f'{self.analysis.credit_debit} {self.name}'

    def fetch_contracts(self, strike: float = -1.0, distance: int = 1, weeks: int = -1) -> tuple[str, int, list[str]]:
        if distance < 0:
            raise ValueError('Invalid distance')

        # Calculate expiry
        expiry = self.chain.get_expiry()
        if not expiry:
            raise ValueError('No option expiry dates')
        elif weeks < 0:
            # Default to next month's option expiration date
            third = f'{m.third_friday():%Y-%m-%d}'
            self.chain.expire = third if third in expiry else expiry[0]
        elif len(expiry) > weeks:
            self.chain.expire = expiry[weeks]
        else:
            self.chain.expire = expiry[0]

        # Get baseline chain index
        contracts = []
        options_c = self.chain.get_chain('call')
        options_p = self.chain.get_chain('put')

        if strike <= 0.0:
            chain_index = self.chain.get_index_itm()
        else:
            chain_index = self.chain.get_index_strike(strike)

        # Make sure the chain is large enough to work with
        if chain_index < (2 * self.width):
            chain_index = -1
        elif len(options_c) < (5 * self.width):
            chain_index = -1
        elif len(options_p) < (5 * self.width):
            chain_index = -1
        elif len(options_c) - chain_index < (2 * self.width):
            chain_index = -1
        elif len(options_p) - chain_index < (2 * self.width):
            chain_index = -1

        # Get the option contracts
        if chain_index < 0:
            _logger.error(f'{__name__}: Option chain not large enough for {self.ticker}')
        else:
            contracts  = [options_c.iloc[chain_index + (2 * self.width)]['contractSymbol']]
            contracts += [options_c.iloc[chain_index + (1 * self.width)]['contractSymbol']]
            contracts += [options_p.iloc[chain_index - (1 * self.width)]['contractSymbol']]
            contracts += [options_p.iloc[chain_index - (2 * self.width)]['contractSymbol']]

        return s.PRODUCTS[2], chain_index, contracts

    @Threaded.threaded
    def analyze(self) -> None:
        if self._validate():
            self.task_error = 'None'
            self.task_message = self.legs[0].option.ticker

            self.legs[0].calculate()
            self.legs[0].option.eff_price = self.legs[0].option.last_price if self.legs[0].option.last_price > 0.0 else self.legs[0].option.calc_price

            # Ensure all legs use the same min, max, step calculated in leg[0]
            self.legs[3].range = self.legs[2].range = self.legs[1].range = self.legs[0].range

            self.legs[1].calculate()
            self.legs[1].option.eff_price = self.legs[1].option.last_price if self.legs[1].option.last_price > 0.0 else self.legs[1].option.calc_price

            self.legs[2].calculate()
            self.legs[2].option.eff_price = self.legs[2].option.last_price if self.legs[2].option.last_price > 0.0 else self.legs[2].option.calc_price

            self.legs[3].calculate()
            self.legs[3].option.eff_price = self.legs[3].option.last_price if self.legs[3].option.last_price > 0.0 else self.legs[3].option.calc_price

            if self.direction == 'long':
                self.analysis.credit_debit = 'debit'
            else:
                self.analysis.credit_debit = 'credit'

            total_c = abs(self.legs[0].option.eff_price - self.legs[1].option.eff_price) * self.quantity
            total_p = abs(self.legs[3].option.eff_price - self.legs[2].option.eff_price) * self.quantity
            self.analysis.total = total_c + total_p

            self.analysis.table = self.generate_profit_table()
            self.analysis.max_gain, self.analysis.max_loss, self.analysis.upside, self.analysis.sentiment = self.calculate_gain_loss()
            self.analysis.breakeven = self.calculate_breakeven()
            self.analysis.summarize()

            _logger.info(f'{__name__}: {self.ticker}: g={self.analysis.max_gain:.2f}, l={self.analysis.max_loss:.2f} b1={self.analysis.breakeven[0] :.2f} b2={self.analysis.breakeven[1] :.2f}')
        self.task_error = 'Done'

    def generate_profit_table(self) -> pd.DataFrame:
        if self.direction == 'long':
            profit_c = self.legs[0].value_table.sub(self.legs[1].value_table)
            profit_p = self.legs[3].value_table.sub(self.legs[2].value_table)
        else:
            profit_c = self.legs[1].value_table.sub(self.legs[0].value_table)
            profit_p = self.legs[2].value_table.sub(self.legs[3].value_table)

        profit = profit_c.add(profit_p)
        profit *= self.quantity

        if self.analysis.credit_debit == 'credit':
            profit += self.analysis.total
        else:
            profit -= self.analysis.total

        return profit

    def calculate_gain_loss(self) -> tuple[float, float, float, str]:
        max_gain = max_loss = 0.0

        if self.analysis.credit_debit == 'credit':
            max_gain = self.analysis.total
            max_loss = (self.quantity * (self.legs[0].option.strike - self.legs[3].option.strike)) - max_gain
            if max_loss < 0.0:
                max_loss = 0.0 # Credit is more than possible loss!
            sentiment = 'bullish'
        else:
            max_loss = self.analysis.total
            max_gain = (self.quantity * (self.legs[0].option.strike - self.legs[3].option.strike)) - max_loss
            if max_gain < 0.0:
                max_gain = 0.0 # Debit is more than possible gain!
            sentiment = 'bearish'

        upside = max_gain - max_loss
        return max_gain, max_loss, upside, sentiment

    def calculate_breakeven(self) -> list[float]:
        breakeven  = [self.legs[1].option.strike - self.analysis.total]
        breakeven += [self.legs[2].option.strike + self.analysis.total]

        return breakeven

    def get_errors(self) -> str:
        error = ''

        if self.legs[0].option.strike <= self.legs[1].option.strike:
            error = 'Bad option configuration'
        elif self.legs[1].option.strike <= self.legs[2].option.strike:
            error = 'Bad option configuration'
        elif self.legs[2].option.strike <= self.legs[3].option.strike:
            error = 'Bad option configuration'

        return error

    def _validate(self) -> bool:
        return len(self.legs) == 4


if __name__ == '__main__':
    # import logging
    # logger.get_logger(logging.INFO)
    import math
    from data import store

    pd.options.display.float_format = '{:,.2f}'.format

    ticker = 'AAPL'
    strike = float(math.ceil(store.get_last_price(ticker)))
    ic = IronCondor(ticker, 'hybrid', 'long', strike, 1, load_contracts=True)
    ic.analyze()

    print(ic.legs[0])
    print(ic.legs[0].option.eff_price)
    # print(ic.legs[0].value_table)

    print(ic.legs[1])
    print(ic.legs[1].option.eff_price)
    # print(ic.legs[1].value_table)

    print(ic.legs[2])
    print(ic.legs[2].option.eff_price)
    # print(ic.legs[2].value_table)

    print(ic.legs[3])
    print(ic.legs[3].option.eff_price)
    # print(ic.legs[3].value_table)

    print(ic.analysis.table)
