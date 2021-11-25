import sys
import abc
from abc import ABC
import datetime as dt
import math

import pandas as pd

import strategies as s
import pricing
from data import store as store
from company.company import Company
from options.option import Option
from options.chain import Chain
from analysis.strategy import StrategyAnalysis
from pricing.pricing import Pricing
from pricing.blackscholes import BlackScholes
from pricing.montecarlo import MonteCarlo
from utils import utils


_IV_CUTOFF = 0.020
_MIN_MAX_PERCENT = 0.20

_logger = utils.get_logger()


class Strategy(ABC):
    def __init__(self, ticker:str, product:str, direction:str, width:int, quantity:int, load_default:bool=False):
        if not store.is_ticker(ticker):
            raise ValueError('Invalid ticker')
        if product not in s.PRODUCTS:
            raise ValueError('Invalid product')
        if direction not in s.DIRECTIONS:
            raise ValueError('Invalid direction')
        if width < 0:
            raise ValueError('Invalid width')
        if quantity < 1:
            raise ValueError('Invalid quantity')

        self.name = ''
        self.ticker = ticker.upper()
        self.product = product
        self.direction = direction
        self.quantity = quantity
        self.width = width
        self.pricing_method = 'black-scholes'
        self.chain:Chain = Chain(self.ticker)
        self.analysis = StrategyAnalysis()
        self.legs:list[Leg] = []
        self.initial_spot = 0.0
        self.initial_spot = self.get_current_spot(ticker, roundup=True)

        self.analysis.credit_debit = 'debit' if direction == 'long' else 'credit'

    def __str__(self):
        return 'Strategy abstract base class'

    def calculate(self) -> None:
        for leg in self.legs:
            leg.calculate()

    @abc.abstractmethod
    def analyze(self) -> None:
        pass

    def reset(self) -> None:
        self.analysis = StrategyAnalysis()

    def update_expiry(self, date:dt.datetime) -> None:
        for leg in self.legs:
            leg.option.expiry = date

    def add_leg(self, quantity:int, product:str, direction:str, strike:float, expiry:dt.datetime) -> int:
        expiry += dt.timedelta(days=1)

        leg = Leg(self, self.ticker, quantity, product, direction, strike, expiry)
        self.legs += [leg]

        return len(self.legs)

    def get_current_spot(self, ticker:str, roundup:bool=False) -> float:
        expiry = dt.datetime.today() + dt.timedelta(days=10)

        if self.pricing_method == 'black-scholes':
            pricer = BlackScholes(ticker, expiry, self.initial_spot)
        elif self.pricing_method == 'monte-carlo':
            pricer = MonteCarlo(ticker, expiry, self.initial_spot)
        else:
            raise ValueError('Unknown pricing model')

        if roundup:
            spot = math.ceil(pricer.spot_price)
        else:
            spot = pricer.spot_price

        return spot

    def set_pricing_method(self, method:str):
        if method in pricing.PRICING_METHODS:
            self.pricing_method = method
            for leg in self.legs:
                leg.pricing_method = method
        else:
            raise ValueError('Invalid pricing method')

    def fetch_default_contracts(self, distance:int, weeks:int) -> tuple[int, list[str]]:
        # Works for strategies with one leg. Multiple-leg strategies should be overridden
        if distance < 0:
            raise ValueError('Invalid distance')
        if weeks < 0:
            raise ValueError('Invalid weeks')

        contract = ''
        expiry = self.chain.get_expiry()
        self.chain.expire = expiry[weeks]

        options = self.chain.get_chain(self.legs[0].option.product)

        index = self.chain.get_itm()
        if index >= 0:
            contract = options.iloc[index]['contractSymbol']
        else:
            _logger.error(f'{__name__}: Error fetching default contract')

        _logger.debug(f'{__name__}: {options}')
        _logger.debug(f'{__name__}: {index=}')

        return index, [contract]

    @abc.abstractmethod
    def generate_profit_table(self) -> pd.DataFrame:
        return pd.DataFrame()

    @abc.abstractmethod
    def calculate_max_gain_loss(self) -> tuple[float, float]:
        return (0.0, 0.0)

    @abc.abstractmethod
    def calculate_breakeven(self) -> float:
        return 0.0

    def get_errors(self) -> str:
        return ''

    @staticmethod
    def compress_table(table:pd.DataFrame, rows:int, cols:int) -> pd.DataFrame:
        if not isinstance(table, pd.DataFrame):
            raise ValueError("'table' must be a Pandas DataFrame")
        else:
            srows, scols = table.shape
            if cols > 0 and cols < scols:
                # thin out cols
                step = int(math.ceil(scols/cols))
                end = table[table.columns[-2::]]        # Save the last two cols
                table = table[table.columns[:-2:step]]  # Thin the table (less the last two cols)
                table = pd.concat([table, end], axis=1) # Add back the last two cols

            if rows > 0 and rows < srows:
                # Thin out rows
                step = int(math.ceil(srows/rows))
                table = table.iloc[::step]

        return table

    def _calc_price_min_max_step(self) -> tuple[float, float, float]:
        min_ = 0.0
        max_ = 0.0
        step = 0.0

        if len(self.legs) > 0:
            min_ = self.legs[0].option.strike * (1.0 - _MIN_MAX_PERCENT)
            max_ = self.legs[0].option.strike * (1.0 + _MIN_MAX_PERCENT)

            step = (max_ - min_) / 40.0
            step = utils.mround(step, step / 10.0)

            if min_ < step:
                min_ = step

        return min_, max_, step

    def _validate(self):
        return len(self.legs) > 0

class Leg:
    def __init__(self, strategy:Strategy, ticker:str, quantity:int, product:str, direction:str, strike:float, expiry:dt.datetime):
        if product not in s.PRODUCTS:
            raise ValueError('Invalid product')
        if direction not in s.DIRECTIONS:
            raise ValueError('Invalid direction')
        if quantity < 1:
            raise ValueError('Invalid quantity')

        self.company:Company = Company(ticker, days=1)
        self.option:Option = Option(ticker, product, strike, expiry)
        self.strategy:Strategy = strategy
        self.quantity:int = quantity
        self.product:str = product
        self.direction:str = direction
        self.pricing_method:str = 'black-scholes'
        self.pricer:Pricing = None
        self.table:pd.DataFrame = None

    def __str__(self):
        if self.option.calc_price > 0.0:
            d1 = 'bs' if self.pricing_method == 'black-scholes' else 'mc'
            d2 = 'cv' if self.option.implied_volatility < _IV_CUTOFF else 'iv'
            d3 = '*' if self.option.implied_volatility < _IV_CUTOFF else ''
            output = f'{self.quantity:2d} '\
            f'{self.company.ticker}@${self.company.price:.2f} '\
            f'{self.direction} '\
            f'{self.product} '\
            f'${self.option.strike:.2f} for '\
            f'{str(self.option.expiry)[:10]}'\
            f'=${self.option.last_price:.2f}{d3} each (${self.option.calc_price:.2f} {d1}/{d2})'

            if not self.option.contract:
                output += ' *option not selected'

            if self.option.last_price > 0.0:
                if self.option.implied_volatility < _IV_CUTOFF and self.option.implied_volatility > 0.0:
                    output += '\n    *** Warning: The iv is unsually low, perhaps due to after-hours. Using cv.'

                diff = self.option.calc_price / self.option.last_price
                if diff > 1.50 or diff < 0.50:
                    output += '\n    *** Warning: The calculated price is significantly different than the last traded price.'
        else:
            output = 'Leg not yet calculated'

        return output

    def calculate(self, table:bool=True, greeks:bool=True) -> float:
        price = 0.0

        if self._validate():
            # Build the pricer
            if self.pricing_method == 'black-scholes':
                self.pricer = BlackScholes(self.company.ticker, self.option.expiry, self.option.strike)
            elif self.pricing_method == 'monte-carlo':
                self.pricer = MonteCarlo(self.company.ticker, self.option.expiry, self.option.strike)
            else:
                raise ValueError('Unknown pricing model')

            _logger.info(f'{__name__}: Calculating price using {self.pricing_method}')

            # Calculate prices
            if self.option.implied_volatility < _IV_CUTOFF:
                self.pricer.calculate_price()
                _logger.info(f'{__name__}: Using calculated volatility')
            else:
                self.pricer.calculate_price(volatility=self.option.implied_volatility)
                _logger.info(f'{__name__}: Using implied volatility = {self.option.implied_volatility:.4f}')

            if self.product == 'call':
                self.option.calc_price = price = self.pricer.price_call
            else:
                self.option.calc_price = price = self.pricer.price_put

            self.option.spot = self.pricer.spot_price
            self.company.price = self.pricer.spot_price
            self.option.rate = self.pricer.risk_free_rate
            self.option.calc_volatility = self.pricer.volatility
            self.company.volatility = self.pricer.volatility
            self.option.time_to_maturity = self.pricer.time_to_maturity

            # Generate the values table
            if table:
                self.table = self.generate_value_table()

            _logger.info(f'{__name__}: Strike {self.option.strike:.2f}')
            _logger.info(f'{__name__}: Expiry {self.option.expiry}')
            _logger.info(f'{__name__}: Price {price:.4f}')
            _logger.info(f'{__name__}: Spot {self.option.spot:.2f}')
            _logger.info(f'{__name__}: Rate {self.option.rate:.4f}')
            _logger.info(f'{__name__}: Cvol {self.option.calc_volatility:.4f}')
            _logger.info(f'{__name__}: Ivol {self.option.implied_volatility:.4f}')
            _logger.info(f'{__name__}: TTM {self.option.time_to_maturity:.4f}')

            # Calculate Greeks
            if greeks:
                if self.option.implied_volatility < _IV_CUTOFF:
                    self.pricer.calculate_greeks()
                else:
                    self.pricer.calculate_greeks(volatility=self.option.implied_volatility)

                if self.product == 'call':
                    self.option.delta = self.pricer.delta_call
                    self.option.gamma = self.pricer.gamma_call
                    self.option.theta = self.pricer.theta_call
                    self.option.vega = self.pricer.vega_call
                    self.option.rho = self.pricer.rho_call
                else:
                    self.option.delta = self.pricer.delta_put
                    self.option.gamma = self.pricer.gamma_put
                    self.option.theta = self.pricer.theta_put
                    self.option.vega = self.pricer.vega_put
                    self.option.rho = self.pricer.rho_put

                _logger.info(f'{__name__}: Delta {self.option.delta:.4f}')
                _logger.info(f'{__name__}: Gamma {self.option.gamma:.4f}')
                _logger.info(f'{__name__}: Theta {self.option.theta:.4f}')
                _logger.info(f'{__name__}: Vega {self.option.vega:.4f}')
                _logger.info(f'{__name__}: Rho {self.option.rho:.4f}')
        else:
            _logger.error(f'{__name__}: Validation error')

        return price

    def recalculate(self, spot_price:float, time_to_maturity:int) -> tuple[float, float]:
        if self.pricer is not None:
            if self.option.implied_volatility < _IV_CUTOFF:
                call, put = self.pricer.calculate_price(spot_price, time_to_maturity)
            else:
                call, put = self.pricer.calculate_price(spot_price, time_to_maturity, volatility=self.option.implied_volatility)
        else:
            raise AssertionError('Must call calculate() prior to recalculate()')

        return call, put

    def modify_company(self, ticker:str) -> bool:
        self.company = Company(ticker, days=1)

        try:
            # Reset strike to spot value
            self.option.strike = self.strategy.get_current_spot(ticker, True)
            self.reset()
            return True
        except Exception as e:
            utils.print_error(str(sys.exc_info()[1]))
            return False

    def modify_values(self, quantity:int, product:str, direction:str, strike:float) -> bool:
        self.quantity = quantity
        self.product = product
        self.direction = direction
        self.option.strike = strike

        # Clear any calculated data and reacalculate
        self.strategy.reset()
        self.reset()

        return True

    def reset(self) -> None:
        self.table = None
        self.pricer = None
        self.calculate()

    def generate_value_table(self) -> pd.DataFrame:
        value = pd.DataFrame()

        if self.option.calc_price > 0.0:
            cols, step = self._calculate_date_step()
            if cols > 1:
                row = []
                table = []
                col_index = []
                row_index = []

                # Create list of dates to be used as the df columns
                today = dt.datetime.today()
                today = today.replace(hour=0, minute=0, second=0, microsecond=0)

                col_index += [str(today)]
                while today < self.option.expiry:
                    today += dt.timedelta(days=step)
                    col_index += [str(today)]

                # Calculate cost of option every day till expiry
                min_, max_, step_ = self.strategy._calc_price_min_max_step()
                for s in range(int(math.ceil(min_*40)), int(math.ceil(max_*40)), int(math.ceil(step_*40))):
                    spot = s / 40.0
                    row = []
                    for item in col_index:
                        maturity_date = dt.datetime.strptime(item, '%Y-%m-%d %H:%M:%S')
                        time_to_maturity = self.option.expiry - maturity_date
                        decimaldays_to_maturity = time_to_maturity.days / 365.0

                        # Compensate for zero delta days to provide small fraction of day (ex: expiration day)
                        if decimaldays_to_maturity < 0.0003:
                            decimaldays_to_maturity = 0.00001

                        price_call, price_put = self.recalculate(spot_price=spot, time_to_maturity=decimaldays_to_maturity)

                        if self.product == 'call':
                            row += [price_call]
                        else:
                            row += [price_put]

                    table += [row]

                    # Create row index
                    if spot > 500.0:
                        spot = utils.mround(spot, 10.0)
                    elif spot > 100.0:
                        spot = utils.mround(spot, 1.00)
                    elif spot > 50.0:
                        spot = utils.mround(spot, 0.50)
                    elif spot > 20.0:
                        spot = utils.mround(spot, 0.10)
                    else:
                        spot = utils.mround(spot, 0.01)

                    row_index += [spot]

                # Strip the time from the datetime string
                for index, item in enumerate(col_index):
                    day = dt.datetime.strptime(item, '%Y-%m-%d %H:%M:%S').date()
                    col_index[index] = f'{str(day.strftime("%b"))}-{str(day.day)}'

                # Finally, create the dataframe then reverse the row order
                col_index[-1] = 'Exp'
                value = pd.DataFrame(table, index=row_index, columns=col_index)
                value = value.iloc[::-1]

        return value

    def _calculate_date_step(self) -> tuple[int, int]:
        cols = int(math.ceil(self.option.time_to_maturity * 365))
        step = 1

        return cols, step

    def _validate(self) -> bool:

        valid = bool(self.company.ticker)

        # Check for valid pricing method
        if not valid:
            pass
        elif self.pricing_method == 'black-scholes':
            valid = True
        elif self.pricing_method == 'monte-carlo':
            valid = True

        return valid

if __name__ == '__main__':
    import logging
    from strategies.call import Call
    from strategies.put import Put
    from strategies.vertical import Vertical
    from utils import utils

    utils.get_logger(logging.DEBUG)

    # strategy = Vertical('AAPL', 'call', 'long', 1, 1, True)
    strategy = Call('AAPL', 'call', 'long', 1, 1, True)
    # strategy = Put('AAPL', 'call', 'long', 1, 1, True)
    strategy.analyze()
    print(strategy.analysis.table)
