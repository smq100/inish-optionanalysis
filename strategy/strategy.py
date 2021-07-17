import sys
import abc
from abc import ABC
import datetime
import math

import pandas as pd

from company.company import Company
from options.option import PRODUCTS, DIRECTIONS, Option
from pricing.pricing import METHODS
from pricing.blackscholes import BlackScholes
from pricing.montecarlo import MonteCarlo
from analysis.strategy import StrategyAnalysis
from utils import utils as utils


IV_CUTOFF = 0.020
STRATEGIES = ['call', 'put', 'vertical']

_logger = utils.get_logger()


class Strategy(ABC):
    def __init__(self, ticker, product, direction, quantity):
        if product not in PRODUCTS:
            raise ValueError('Invalid product')
        if direction not in DIRECTIONS:
            raise ValueError('Invalid direction')

        self.name = ''
        self.ticker = ticker
        self.product = product
        self.direction = direction
        self.quantity = quantity
        self.width = 1
        self.analysis = StrategyAnalysis()
        self.legs = []
        self.initial_spot = 0.0
        self.initial_spot = self.get_current_spot(ticker, True)

    def __str__(self):
        return 'Strategy abstract base class'

    def calculate(self):
        for leg in self.legs:
            leg.calculate()

    @abc.abstractmethod
    def analyze(self):
        pass

    def reset(self):
        self.analysis = StrategyAnalysis()

    def update_expiry(self, date):
        for leg in self.legs:
            leg.option.expiry = date

    def add_leg(self, quantity, product, direction, strike, expiry):
        # Add one day to act as expiry value
        expiry += datetime.timedelta(days=1)

        leg = Leg(self, self.ticker, quantity, product, direction, strike, expiry)
        self.legs += [leg]

        return len(self.legs)

    def get_current_spot(self, ticker, roundup=False):
        expiry = datetime.datetime.today() + datetime.timedelta(days=10)
        pricer = MonteCarlo(ticker, expiry, self.initial_spot)

        if roundup:
            spot = math.ceil(pricer.spot_price)
        else:
            spot = pricer.spot_price

        return spot

    def set_pricing_method(self, method):
        if method in METHODS:
            for leg in self.legs:
                leg.pricing_method = method
        else:
            raise ValueError('Invalid pricing method')

    @abc.abstractmethod
    def generate_profit_table(self):
        pass

    @abc.abstractmethod
    def calc_max_gain_loss(self):
        pass

    @abc.abstractmethod
    def calc_breakeven(self):
        pass

    def get_errors(self):
        return ''

    def _calc_price_min_max_step(self):
        min_ = max_ = step_ = 0

        if len(self.legs) > 0:
            percent = 0.20
            min_ = self.legs[0].symbol.spot * (1 - percent)
            max_ = self.legs[0].symbol.spot * (1 + percent)

            step_ = (max_ - min_) / 40.0
            step_ = utils.mround(step_, step_ / 10.0)

            if min_ < step_:
                min_ = step_

        return min_, max_, step_

    def _validate(self):
        return len(self.legs) > 0

class Leg:
    def __init__(self, strategy, ticker, quantity, product, direction, strike, expiry):
        if product not in PRODUCTS:
            raise ValueError('Invalid product')
        if direction not in DIRECTIONS:
            raise ValueError('Invalid direction')
        if quantity < 1:
            raise ValueError('Invalid quantity')

        self.symbol = Company(ticker, days=1)
        self.option = Option(ticker, product, strike, expiry)
        self.strategy = strategy
        self.quantity = quantity
        self.product = product
        self.direction = direction
        self.pricing_method = 'black-scholes'
        self.pricer = None
        self.table = None

    def __str__(self):
        if self.option.calc_price > 0.0:
            d1 = 'bs' if self.pricing_method == 'black-scholes' else 'mc'
            d2 = 'cv' if self.option.implied_volatility < IV_CUTOFF else 'iv'
            d3 = '*' if self.option.implied_volatility < IV_CUTOFF else ''
            output = f'{self.quantity:2d} '\
            f'{self.symbol.ticker}@${self.symbol.spot:.2f} '\
            f'{self.direction} '\
            f'{self.product} '\
            f'${self.option.strike:.2f} for '\
            f'{str(self.option.expiry)[:10]}'\
            f'=${self.option.last_price:.2f}{d3} each (${self.option.calc_price:.2f}{d1}/{d2})'

            if not self.option.contract_symbol:
                output += ' *option not selected'

            if self.option.last_price > 0.0:
                if self.option.implied_volatility < IV_CUTOFF and self.option.implied_volatility > 0.0:
                    output += '\n    *** Warning: The implied volatility is unsually low, perhaps due to after-hours. Using calculated volatility.'
                diff = self.option.calc_price / self.option.last_price
                if diff > 1.50 or diff < 0.50:
                    output += '\n    *** Warning: The calculated price is significantly different than the last traded price.'
        else:
            output = 'Leg not yet calculated'

        return output

    def calculate(self, table=True, greeks=True):
        price = 0.0

        if self._validate():
            # Build the pricer
            if self.pricing_method == 'black-scholes':
                self.pricer = BlackScholes(self.symbol.ticker, self.option.expiry, self.option.strike)
            elif self.pricing_method == 'monte-carlo':
                self.pricer = MonteCarlo(self.symbol.ticker, self.option.expiry, self.option.strike)
            else:
                raise ValueError('Unknown pricing model')

            _logger.debug(f'{__name__}: Calculating price using {self.pricing_method}')

            # Calculate prices
            if self.option.implied_volatility < IV_CUTOFF:
                self.pricer.calculate_price()
                _logger.debug(f'{__name__}: Using calculated volatility')
            else:
                self.pricer.calculate_price(volatility=self.option.implied_volatility)
                _logger.debug(f'{__name__}: Using implied volatility = {self.option.implied_volatility:.4f}')

            if self.product == 'call':
                self.option.calc_price = price = self.pricer.price_call
            else:
                self.option.calc_price = price = self.pricer.price_put

            self.option.spot = self.symbol.spot = self.pricer.spot_price
            self.option.rate = self.pricer.risk_free_rate
            self.option.calc_volatility = self.symbol.volatility = self.pricer.volatility
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
                if self.option.implied_volatility < IV_CUTOFF:
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

    def recalculate(self, spot_price, time_to_maturity):
        if self.pricer is not None:
            if self.option.implied_volatility < IV_CUTOFF:
                call, put = self.pricer.calculate_price(spot_price, time_to_maturity)
            else:
                call, put = self.pricer.calculate_price(spot_price, time_to_maturity, volatility=self.option.implied_volatility)
        else:
            raise AssertionError('Must call calculate() prior to recalculate()')

        return call, put

    def modify_symbol(self, ticker):
        self.symbol = Company(ticker)

        try:
            # Reset strike to spot value
            self.option.strike = self.strategy.get_current_spot(ticker, True)
            self.reset()
            return True
        except Exception as e:
            self.symbol = ticker
            utils.print_error(sys.exc_info()[1])
            return False

    def modify_values(self, quantity, product, direction, strike):
        self.quantity = quantity
        self.product = product
        self.direction = direction
        self.option.strike = strike

        # Clear any calculated data and reacalculate
        self.strategy.reset()
        self.reset()

        return True

    def reset(self):
        self.table = None
        self.pricer = None
        self.calculate()

    def generate_value_table(self):
        df = pd.DataFrame()

        if self.option.calc_price > 0.0:
            cols, step = self._calc_date_step()
            if cols > 1:
                row = []
                table = []
                col_index = []
                row_index = []

                # Create list of dates to be used as the df columns
                today = datetime.datetime.today()
                today = today.replace(hour=0, minute=0, second=0, microsecond=0)

                col_index += [str(today)]
                while today < self.option.expiry:
                    today += datetime.timedelta(days=step)
                    col_index += [str(today)]

                # Calculate cost of option every day till expiry
                min_, max_, step_ = self.strategy._calc_price_min_max_step()
                for spot in range(int(math.ceil(min_*40)), int(math.ceil(max_*40)), int(math.ceil(step_*40))):
                    spot /= 40.0
                    row = []
                    for item in col_index:
                        maturity_date = datetime.datetime.strptime(item, '%Y-%m-%d %H:%M:%S')
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
                    day = datetime.datetime.strptime(item, '%Y-%m-%d %H:%M:%S').date()
                    col_index[index] = f'{str(day.strftime("%b"))}-{str(day.day)}'

                # Finally, create the dataframe then reverse the row order
                col_index[-1] = 'Exp'
                df = pd.DataFrame(table, index=row_index, columns=col_index)
                df = df.iloc[::-1]

        return df

    def _calc_date_step(self):
        cols = int(math.ceil(self.option.time_to_maturity * 365))
        step = 1

        return cols, step

    def _validate(self):
        valid = False

        if self.symbol.ticker:
            valid = True

        # Check for valid method
        if not valid:
            pass
        elif self.pricing_method == 'black-scholes':
            valid = True
        elif self.pricing_method == 'monte-carlo':
            valid = True

        return valid
