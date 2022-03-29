import pandas as pd

from base import Threaded
import strategies as s
from strategies.strategy import Strategy
from utils import math as m
from utils import logger


_logger = logger.get_logger()


class Vertical(Strategy):
    def __init__(self, ticker: str, product: str, direction: str, strike: float, width1: int, width2: int, quantity: int = 1, load_contracts: bool = False):
        if width1 < 1:
            raise ValueError('Invalid width')

        # Initialize the base strategy
        super().__init__(ticker, product, direction, strike, width1, 0, quantity, load_contracts)

        self.name = s.STRATEGIES_BROAD[2]

        # Default expiry to tird Friday of next month
        expiry = m.third_friday()

        # Add legs. Long leg is always first
        # Width1 is dollar amounts when not loading contracts
        # Width1 is indexes into the chain when loading contracts
        # Strike price will be overriden when loading contracts
        if product == 'call':
            if direction == 'long':
                self.add_leg(self.quantity, product, 'long', self.strike, expiry)
                self.add_leg(self.quantity, product, 'short', self.strike + self.width1, expiry)
            else:
                self.add_leg(self.quantity, product, 'long', self.strike + self.width1, expiry)
                self.add_leg(self.quantity, product, 'short', self.strike, expiry)
        else:
            if direction == 'long':
                self.add_leg(self.quantity, product, 'long', self.strike + self.width1, expiry)
                self.add_leg(self.quantity, product, 'short', self.strike, expiry)
            else:
                self.add_leg(self.quantity, product, 'long', self.strike, expiry)
                self.add_leg(self.quantity, product, 'short', self.strike + self.width1, expiry)

        if load_contracts:
            contracts = self.fetch_contracts(self.strike)
            if len(contracts) == 2:
                if not self.legs[0].option.load_contract(contracts[0]):
                    self.error = f'Unable to load leg 0 {product} contract for {self.legs[0].company.ticker}'
                elif not self.legs[1].option.load_contract(contracts[1]):
                    self.error = f'Unable to load leg 1 {product} contract for {self.legs[1].company.ticker}'

                if not self.error:
                    self.analysis.volatility = 'implied'
                else:
                    _logger.warning(f'{__name__}: Error fetching contracts for {self.ticker}: {self.error}')
            else:
                # Not a fatal error
                _logger.warning(f'{__name__}: Error fetching contracts for {self.ticker}. Using calculated values')

    def __str__(self):
        return f'{self.name} {self.product} {self.analysis.credit_debit} spread'

    def fetch_contracts(self, strike: float = -1.0, distance: int = 0, weeks: int = -1) -> list[str]:
        if distance < 0:
            raise ValueError('Invalid distance')

        expiry = self.chain.get_expiry()

        # Calculate expiry
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

        # Get the option chain
        contracts = []
        chain_index = -1
        product = self.legs[0].option.product
        options = self.chain.get_chain(product)

        # Calculate the index into the option chain
        if options.empty:
            _logger.warning(f'{__name__}: Error fetching option chain for {self.ticker}')
        elif strike <= 0.0:
            chain_index = self.chain.get_index_itm()
        else:
            chain_index = self.chain.get_index_strike(strike)

        # Add the long option contract
        if chain_index < 0:
            _logger.warning(f'{__name__}: No option index found for {self.ticker} leg 1')
        elif chain_index >= len(options):
            _logger.warning(f'{__name__}: Insufficient options for {self.ticker} leg 1')
        else:
            contracts = [options.iloc[chain_index]['contractSymbol']]

        # Calculate the index to the short option
        if not contracts:
            pass
        elif self.product == 'call':
            if self.direction == 'long':
                chain_index += self.width1
            else:
                chain_index -= self.width1
        elif self.direction == 'long':
            chain_index -= self.width1
        else:
            chain_index += self.width1

        # Add the short option contract
        if not contracts:
            pass
        elif chain_index < 0:
            contracts = []
            _logger.warning(f'{__name__}: No option index found for {self.ticker} leg 2')
        elif chain_index >= len(options):
            contracts = []
            _logger.warning(f'{__name__}: Insufficient options for {self.ticker} leg 2')
        else:
            contracts += [options.iloc[chain_index]['contractSymbol']]

        return contracts

    @Threaded.threaded
    def analyze(self) -> None:
        if not self.get_errors():
            self.task_state = 'None'
            self.task_message = self.legs[0].option.ticker

            self.legs[0].calculate()

            # Ensure both legs use the same min, max, step
            self.legs[1].range =  self.legs[0].range

            self.legs[1].calculate()

            # Important: Assumes the long leg is the index-0 leg
            self.legs[0].option.eff_price = self.legs[0].option.last_price if self.legs[0].option.last_price > 0.0 else self.legs[0].option.calc_price
            self.legs[1].option.eff_price = self.legs[1].option.last_price if self.legs[1].option.last_price > 0.0 else self.legs[1].option.calc_price

            self.analysis.credit_debit = 'debit' if self.direction == 'long' else 'credit'
            self.analysis.total = abs(self.legs[0].option.eff_price - self.legs[1].option.eff_price) * self.quantity

            self.analysis.max_gain, self.analysis.max_loss, self.analysis.upside, self.analysis.sentiment = self.calculate_gain_loss()
            self.analysis.table = self.generate_profit_table()
            self.analysis.breakeven = self.calculate_breakeven()
            self.analysis.pop = self.calculate_pop()
            self.analysis.summarize()

            _logger.info(f'{__name__}: {self.ticker}: g={self.analysis.max_gain:.2f}, l={self.analysis.max_loss:.2f} b={self.analysis.breakeven[0]:.2f}')
        else:
            _logger.warning(f'{__name__}: Unable to analyze strategy for {self.ticker}: {self.error}')

        self.task_state = 'Done'

    def calculate_gain_loss(self) -> tuple[float, float, float, str]:
        max_gain = max_loss = 0.0

        self.legs[0].option.eff_price = self.legs[0].option.last_price if self.legs[0].option.last_price > 0.0 else self.legs[0].option.calc_price
        self.legs[1].option.eff_price = self.legs[1].option.last_price if self.legs[1].option.last_price > 0.0 else self.legs[1].option.calc_price

        debit = self.analysis.credit_debit == 'debit'
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

        upside = max_gain / max_loss if max_loss > 0.0 else 0.0
        return max_gain, max_loss, upside, sentiment

    def generate_profit_table(self) -> pd.DataFrame:
        profit = self.legs[0].value_table - self.legs[1].value_table
        profit *= self.quantity

        if self.analysis.credit_debit == 'credit':
            profit += self.analysis.total
        else:
            profit -= self.analysis.total

        return profit

    def calculate_breakeven(self) -> list[float]:
        if self.analysis.credit_debit == 'debit':
            breakeven = self.legs[1].option.strike + self.analysis.total
        else:
            breakeven = self.legs[1].option.strike - self.analysis.total

        return [breakeven]

    def calculate_pop(self) -> float:
        pop = 1.0 - (self.analysis.max_gain / abs((self.legs[1].option.strike - self.legs[0].option.strike)))
        return pop if pop > 0.0 else 0.0

    def get_errors(self) -> str:
        if self.error:
            pass # Return existing error
        elif len(self.legs) != 2:
            self.error = 'Insufficient number of legs'
        elif self.analysis.credit_debit:
            if self.product == 'call':
                if self.analysis.credit_debit == 'debit':
                    if self.legs[0].option.strike >= self.legs[1].option.strike:
                        self.error = 'Bad option leg configuration'
                elif self.legs[1].option.strike >= self.legs[0].option.strike:
                    self.error = 'Bad option leg configuration'
            else:
                if self.analysis.credit_debit == 'debit':
                    if self.legs[1].option.strike >= self.legs[0].option.strike:
                        self.error = 'Bad option leg configuration'
                elif self.legs[0].option.strike >= self.legs[1].option.strike:
                    self.error = 'Bad option leg configuration'

        return self.error


if __name__ == '__main__':
    # import logging
    # logger.get_logger(logging.INFO)
    import math
    from data import store

    pd.options.display.float_format = '{:,.2f}'.format

    ticker = 'AAPL'
    strike = float(math.ceil(store.get_last_price(ticker)))
    vert = Vertical(ticker, 'call', 'long', strike, 1, 1, load_contracts=True)
    vert.analyze()

    print(vert.legs[0])
    print(vert.legs[0].value_table)
