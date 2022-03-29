import pandas as pd

from base import Threaded
import strategies as s
from strategies.strategy import Strategy
from utils import math as m
from utils import logger


_logger = logger.get_logger()

class IronButterfly(Strategy):
    def __init__(self, ticker: str, product: str, direction: str, strike: float, width1: int, width2: int, quantity: int = 1, load_contracts: bool = False):
        if width1 < 1:
            raise ValueError('Invalid width1')

        # Initialize the base strategy
        product = s.PRODUCTS[2]
        super().__init__(ticker, product, direction, strike, width1, width2, quantity, load_contracts)

        self.name = s.STRATEGIES_BROAD[4]

        # Default expiry to third Friday of next month
        expiry = m.third_friday()

        # Add legs in decending order of strike price
        # Width1 is dollar amounts when not loading contracts
        # Width1 is an indexe into the chain when loading contracts
        # Strike price will be overriden when loading contracts
        if direction == 'short':
            self.add_leg(self.quantity, 'call', 'long', self.strike + self.width1, expiry)
            self.add_leg(self.quantity, 'call', 'short', self.strike, expiry)
            self.add_leg(self.quantity, 'put', 'short', self.strike, expiry)
            self.add_leg(self.quantity, 'put', 'long', self.strike - self.width1, expiry)
        else:
            self.add_leg(self.quantity, 'call', 'short', self.strike + self.width1, expiry)
            self.add_leg(self.quantity, 'call', 'long', self.strike, expiry)
            self.add_leg(self.quantity, 'put', 'long', self.strike, expiry)
            self.add_leg(self.quantity, 'put', 'short', self.strike - self.width1, expiry)

        if load_contracts:
            contracts = self.fetch_contracts(strike=self.strike)
            if len(contracts) == 4:
                if not self.legs[0].option.load_contract(contracts[0]):
                    self.error = f'Unable to load leg 0 contract for {self.legs[0].company.ticker}'
                elif not self.legs[1].option.load_contract(contracts[1]):
                    self.error = f'Unable to load leg 1 contract for {self.legs[1].company.ticker}'
                elif not self.legs[2].option.load_contract(contracts[2]):
                    self.error = f'Unable to load leg 2 contract for {self.legs[2].company.ticker}'
                elif not self.legs[3].option.load_contract(contracts[3]):
                    self.error = f'Unable to load leg 3 contract for {self.legs[3].company.ticker}'

                if not self.error:
                    self.analysis.volatility = 'implied'
                else:
                    _logger.warning(f'{__name__}: Error fetching contracts for {self.ticker}: {self.error}')
            else:
                _logger.warning(f'{__name__}: Error fetching contracts for {self.ticker}. Using calculated values')

    def __str__(self):
        return f'{self.analysis.credit_debit} {self.name}'

    def fetch_contracts(self, strike: float = -1.0, distance: int = 0, weeks: int = -1) -> list[str]:
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

        # Get the option chain. Need to track call and put indexes seperately because there may be differences in chain structures
        contracts = []
        chain_index_c = -1
        chain_index_p = -1

        # Calculate the index into the call option chain
        options_c = self.chain.get_chain('call')
        if options_c.empty:
            _logger.warning(f'{__name__}: Error fetching option chain for {self.ticker} calls')
        elif strike <= 0.0:
            chain_index_c = self.chain.get_index_itm()
        else:
            chain_index_c = self.chain.get_index_strike(strike)

        # Calculate the index into the put option chain
        if chain_index_c >= 0:
            options_p = self.chain.get_chain('put')
            if options_p.empty:
                _logger.warning(f'{__name__}: Error fetching option chain for {self.ticker} puts')
            elif strike <= 0.0:
                chain_index_p = self.chain.get_index_itm()
            else:
                chain_index_p = self.chain.get_index_strike(strike)

        # Add the leg 1 & 2 option contracts
        if chain_index_c < 0:
            _logger.warning(f'{__name__}: No option index found for {self.ticker} calls')
        elif chain_index_p < 0:
            _logger.warning(f'{__name__}: No option index found for {self.ticker} puts')
        elif len(options_c) < (self.width1 + 1):
            chain_index_c = -1 # Chain too small
        elif (len(options_c) - chain_index_c) <= (self.width1 + 1):
            chain_index_c = -1 # Index too close to end of chain
        else:
            contracts += [options_c.iloc[chain_index_c + self.width1]['contractSymbol']]
            contracts += [options_c.iloc[chain_index_c]['contractSymbol']]

        # Add the leg 3 & 4 option contracts
        if chain_index_c < 0:
            _logger.warning(f'{__name__}: No option index found for {self.ticker} calls')
        elif chain_index_p < 0:
            _logger.warning(f'{__name__}: No option index found for {self.ticker} puts')
        elif len(options_p) < (self.width1 + 1):
            chain_index_p = -1 # Chain too small
        elif (len(options_p) - chain_index_p) <= (self.width1 + 1):
            chain_index_p = -1 # Index too close to beginning of chain
        else:
            contracts += [options_p.iloc[chain_index_p]['contractSymbol']]
            contracts += [options_p.iloc[chain_index_p - self.width1]['contractSymbol']]

        return contracts

    @Threaded.threaded
    def analyze(self) -> None:
        if not self.get_errors():
            self.task_state = 'None'
            self.task_message = self.legs[0].option.ticker

            # Ensure all legs use the same min, max, step centered around the strike
            range = m.calculate_min_max_step(self.strike)
            self.legs[0].range = self.legs[1].range = self.legs[2].range = self.legs[3].range = range

            self.legs[0].calculate()
            self.legs[0].option.eff_price = self.legs[0].option.last_price if self.legs[0].option.last_price > 0.0 else self.legs[0].option.calc_price

            self.legs[1].calculate()
            self.legs[1].option.eff_price = self.legs[1].option.last_price if self.legs[1].option.last_price > 0.0 else self.legs[1].option.calc_price

            self.legs[2].calculate()
            self.legs[2].option.eff_price = self.legs[2].option.last_price if self.legs[2].option.last_price > 0.0 else self.legs[2].option.calc_price

            self.legs[3].calculate()
            self.legs[3].option.eff_price = self.legs[3].option.last_price if self.legs[3].option.last_price > 0.0 else self.legs[3].option.calc_price

            if self.direction == 'short':
                self.analysis.credit_debit = 'credit'
            else:
                self.analysis.credit_debit = 'debit'

            total_c = abs(self.legs[0].option.eff_price - self.legs[1].option.eff_price) * self.quantity
            total_p = abs(self.legs[3].option.eff_price - self.legs[2].option.eff_price) * self.quantity
            self.analysis.total = total_c + total_p

            self.analysis.max_gain, self.analysis.max_loss, self.analysis.upside, self.analysis.sentiment = self.calculate_gain_loss()
            self.analysis.table = self.generate_profit_table()
            self.analysis.breakeven = self.calculate_breakeven()
            self.analysis.pop = self.calculate_pop()
            self.analysis.summarize()

            _logger.info(f'{__name__}: {self.ticker}: g={self.analysis.max_gain:.2f}, l={self.analysis.max_loss:.2f} \
                b1={self.analysis.breakeven[0] :.2f} b2={self.analysis.breakeven[1] :.2f}')
        else:
            _logger.warning(f'{__name__}: Unable to analyze strategy for {self.ticker}: {self.error}')

        self.task_state = 'Done'

    def calculate_gain_loss(self) -> tuple[float, float, float, str]:
        max_gain = max_loss = 0.0

        if self.direction == 'short':
            max_gain = self.analysis.total
            max_loss = (self.quantity * (self.legs[0].option.strike - self.legs[1].option.strike)) - max_gain
            if max_loss < 0.0:
                max_loss = 0.0 # Credit is more than possible loss!
            sentiment = 'low volatility'
        else:
            max_loss = self.analysis.total
            max_gain = (self.quantity * (self.legs[0].option.strike - self.legs[1].option.strike)) - max_loss
            if max_gain < 0.0:
                max_gain = 0.0 # Debit is more than possible gain!
            sentiment = 'high volatility'

        upside = max_gain / max_loss if max_loss > 0.0 else 0.0
        return max_gain, max_loss, upside, sentiment

    def generate_profit_table(self) -> pd.DataFrame:
        if self.direction == 'short':
            profit_c = self.legs[0].value_table - self.legs[1].value_table
            profit_p = self.legs[3].value_table - self.legs[2].value_table
        else:
            profit_c = self.legs[1].value_table - self.legs[0].value_table
            profit_p = self.legs[2].value_table - self.legs[3].value_table

        profit = profit_c + profit_p
        profit *= self.quantity

        if self.direction == 'short':
            profit += self.analysis.max_gain
        else:
            profit -= self.analysis.max_loss

        return profit

    def calculate_breakeven(self) -> list[float]:
        breakeven  = [self.legs[1].option.strike + self.analysis.total]
        breakeven += [self.legs[2].option.strike - self.analysis.total]

        return breakeven

    def calculate_pop(self) -> float:
        pop = 1.0 - (self.analysis.max_gain / (self.legs[0].option.strike - self.legs[1].option.strike))
        return pop if pop > 0.0 else 0.0

    def get_errors(self) -> str:
        if self.error:
            pass # Return existing error
        elif len(self.legs) != 4:
            self.error = 'Insufficient number of legs'
        elif self.legs[0].option.strike <= self.legs[1].option.strike:
            self.error = f'Bad option leg configuration ({self.legs[0].option.strike:.2f} <= {self.legs[1].option.strike:.2f})'
        elif self.legs[2].option.strike <= self.legs[3].option.strike:
            self.error = f'Bad option leg configuration ({self.legs[2].option.strike:.2f} <= {self.legs[3].option.strike:.2f})'

        return self.error


if __name__ == '__main__':
    # import logging
    # logger.get_logger(logging.INFO)
    import math
    from data import store

    pd.options.display.float_format = '{:,.2f}'.format

    ticker = 'MSFT'
    strike = float(math.ceil(store.get_last_price(ticker)))
    ic = IronButterfly(ticker, 'hybrid', 'short', strike, 1, 0, load_contracts=True)
    ic.analyze()

    # print(ic.legs[0])
    # print(ic.legs[0].option.eff_price)
    # print(ic.legs[0].value_table)

    # print(ic.legs[1])
    # print(ic.legs[1].option.eff_price)
    # print(ic.legs[1].value_table)

    # print(ic.legs[2])
    # print(ic.legs[2].option.eff_price)
    # print(ic.legs[2].value_table)

    # print(ic.legs[3])
    # print(ic.legs[3].option.eff_price)
    # print(ic.legs[3].value_table)

    print(f'{ic.strike=:.2f}, {ic.analysis.max_gain=:.2f}, {ic.analysis.max_loss=:.2f}, {ic.analysis.total=:.2f}')
    print(ic.analysis.table)
