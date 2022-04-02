import datetime as dt
import math

import pandas as pd
import numpy as np

import pricing
import strategies as s
from company.company import Company
from options.option import Option
from pricing.pricing import Pricing
from pricing.blackscholes import BlackScholes
from pricing.montecarlo import MonteCarlo
from utils import logger
from utils import math as m


_IV_CUTOFF = 0.020

_logger = logger.get_logger()
class Leg:
    def __init__(self, ticker: str, quantity: int, product: str, direction: str, strike: float, expiry: dt.datetime, volatility: tuple[float, float]):
        if product not in s.PRODUCTS:
            raise ValueError('Invalid product')
        if direction not in s.DIRECTIONS:
            raise ValueError('Invalid direction')
        if quantity < 1:
            raise ValueError('Invalid quantity')

        self.option = Option(ticker, product, strike, expiry, volatility)
        self.company = Company(ticker, days=1)
        self.pricing_method = pricing.PRICING_METHODS[0]
        self.quantity = quantity
        self.direction = direction
        self.pricer: Pricing = None
        self.value_table = pd.DataFrame()
        self.range = m.range_type(0.0, 0.0, 0.0)

    def __str__(self):
        return self.description()

    def calculate(self, greeks: bool = True) -> float:
        self.option.price_calc = 0.0

        if self.validate():
            # Build the pricer
            if self.pricing_method == pricing.PRICING_METHODS[0]:
                self.pricer = BlackScholes(self.company.ticker, self.option.expiry, self.option.strike)
            elif self.pricing_method == pricing.PRICING_METHODS[1]:
                self.pricer = MonteCarlo(self.company.ticker, self.option.expiry, self.option.strike)
            else:
                raise ValueError(f'Unknown pricing model {self.pricing_method.upper()}')

            _logger.info(f'{__name__}: Calculating price using {self.pricing_method}')

            self.company.price = self.pricer.spot_price
            self.company.volatility = self.pricer.volatility
            self.option.volatility_calc = self.pricer.volatility
            self.option.rate = self.pricer.risk_free_rate
            self.option.time_to_maturity = self.pricer.time_to_maturity

            # Calculate volatility (self.pricer must be valid)
            self.calculate_volatility()

            # Calculate initial price using implied volatility if known. Any delta will be used for subsequent calculations
            volatility = self.option.volatility_implied if self.option.volatility_implied > 0.0 else self.option.volatility_calc
            self.pricer.calculate_price(volatility=volatility)

            if self.option.product == 'call':
                self.option.price_calc = self.pricer.price_call
            else:
                self.option.price_calc = self.pricer.price_put

            # Determine effective price
            if self.option.volatility_user > 0.0:
                self.option.price_eff = self.option.price_calc
            elif self.option.price_last > 0.0:
                self.option.price_eff = self.option.price_last
            else:
                self.option.price_eff = self.option.price_calc

            # Generate the value table
            self.value_table = self.generate_value_table()

            _logger.info(f'{__name__}: Strike {self.option.strike:.2f}')
            _logger.info(f'{__name__}: Expiry {self.option.expiry}')
            _logger.info(f'{__name__}: Price {self.option.price_calc:.4f}')
            _logger.info(f'{__name__}: Rate {self.option.rate:.4f}')
            _logger.info(f'{__name__}: Vol {self.option.volatility_eff:.4f}')
            _logger.info(f'{__name__}: TTM {self.option.time_to_maturity:.4f}')

            # Calculate Greeks
            if greeks:
                self.pricer.calculate_greeks(volatility=self.option.volatility_eff)

                if self.option.product == 'call':
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

        return self.option.price_calc

    def recalculate(self, spot_price: float, time_to_maturity: int) -> tuple[float, float]:
        if self.pricer is not None:
            call, put = self.pricer.calculate_price(spot_price, time_to_maturity, volatility=self.option.volatility_eff)
        else:
            raise AssertionError('Must call calculate() prior to recalculate()')

        return call, put

    def calculate_volatility(self):
        if self.option.volatility_user > 0.0:
            self.option.volatility_eff = self.option.volatility_user
            _logger.info(f'{__name__}: Using requested volatility = {self.option.volatility_user:.4f}')
        elif self.option.volatility_user == 0.0:
            self.option.volatility_eff = self.option.volatility_calc
            _logger.info(f'{__name__}: Using calculated volatility')
        elif self.option.volatility_implied < _IV_CUTOFF:
            self.option.volatility_eff = self.option.volatility_calc
            _logger.info(f'{__name__}: Using calculated volatility')
        else:
            self.option.volatility_eff = self.option.volatility_implied
            _logger.info(f'{__name__}: Using implied volatility = {self.option.volatility_implied:.4f}')

        _logger.info(f'{__name__}: User volatility = {self.option.volatility_user:.2f}')
        _logger.info(f'{__name__}: Calculated volatility = {self.option.volatility_calc:.2f}')
        _logger.info(f'{__name__}: Implied volatility = {self.option.volatility_implied:.2f}')
        _logger.info(f'{__name__}: Delta volatility = {self.option.volatility_delta:.2f}')
        _logger.info(f'{__name__}: Effective volatility = {self.option.volatility_eff:.2f}')

        # Compensate with delta if specified
        self.option.volatility_eff += (self.option.volatility_eff * self.option.volatility_delta)

    def generate_value_table(self) -> pd.DataFrame:
        value = pd.DataFrame()

        if self.option.price_calc > 0.0:
            cols, step = self.calculate_date_step()
            if cols > 1:
                row = []
                table = []
                col_index = []
                row_index = []

                # Create list of dates to be used as the df columns
                today = dt.datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)

                col_index += [str(today)]
                while today < self.option.expiry:
                    today += dt.timedelta(days=step)
                    col_index += [str(today)]

                if self.range.min <= 0.0 or self.range.max <= 0.0 or self.range.step <= 0.0:
                    self.range = m.calculate_min_max_step(self.option.strike)

                # Calculate option price every day till expiry
                for spot in np.arange(self.range.min, self.range.max, self.range.step):
                    row = []
                    for item in col_index:
                        maturity_date = dt.datetime.strptime(item, '%Y-%m-%d %H:%M:%S')
                        time_to_maturity = self.option.expiry - maturity_date
                        decimaldays_to_maturity = time_to_maturity.days / 365.0

                        # Compensate for zero delta days to provide small fraction of day (ex: expiration day)
                        if decimaldays_to_maturity < 0.0003:
                            decimaldays_to_maturity = 0.00001

                        price_call, price_put = self.recalculate(spot_price=spot, time_to_maturity=decimaldays_to_maturity)

                        if self.option.product == 'call':
                            row += [price_call]
                        else:
                            row += [price_put]

                    table += [row]

                    # Create row index
                    row_index += [spot]

                # Strip the time from the datetime string
                for index, item in enumerate(col_index):
                    day = dt.datetime.strptime(item, '%Y-%m-%d %H:%M:%S').date()
                    col_index[index] = f'{str(day.strftime("%b"))}-{str(day.day)}-{str(day.year)}'

                # Finally, create the dataframe then reverse the row order
                # col_index[-1] = 'Expiry'
                value = pd.DataFrame(table, index=row_index, columns=col_index)
                value = value.iloc[::-1]

        return value

    def calculate_date_step(self) -> tuple[int, int]:
        cols = int(math.ceil(self.option.time_to_maturity * 365))
        step = 1

        return cols, step

    def description(self, greeks: bool = False) -> str:
        if greeks:
            output = f'Delta={self.option.delta:.3f}, gamma={self.option.gamma:.3f}, theta={self.option.theta:.3f}, vega={self.option.vega:.3f}, rho={self.option.rho:.3f}'
        elif self.option.price_calc > 0.0:
            d2 = 'bs' if self.pricing_method == pricing.PRICING_METHODS[0] else pricing.PRICING_METHODS[1]
            if self.option.volatility_user > 0.0:
                d3 = 'uv'
            elif self.option.volatility_user == 0.0:
                d3 = 'cv'
            elif self.option.volatility_implied < _IV_CUTOFF:
                d3 = 'cv'
            else:
                d3 = 'iv'

            output = f'{self.quantity} '\
                f'{self.company.ticker} (${self.company.price:.2f}) '\
                f'{self.direction} '\
                f'{self.option.product} '\
                f'${self.option.strike:.2f} '\
                f'({str(self.option.expiry)[:10]}) '\
                f'${self.option.price_eff:.2f} '\
                f'(c={self.option.price_calc:.2f} l={self.option.price_last:.2f}) {d3}/{d2} '\
                f'cv={self.option.volatility_calc:.2f} iv={self.option.volatility_implied:.2f} uv={self.option.volatility_user:.2f} '\
                f'∆={self.option.volatility_delta:.2f} ev={self.option.volatility_eff:.2f}'

            if not self.option.contract:
                output += ' * option not selected'

            if self.option.price_last > 0.0:
                if self.option.volatility_implied < _IV_CUTOFF and self.option.volatility_implied > 0.0:
                    output += '\n    * The iv is unsually low, perhaps due to after-hours. Using cv.'

                diff = self.option.price_calc / self.option.price_last
                if diff > 1.50 or diff < 0.50:
                    output += '\n    * The calculated price is significantly different than the last traded price.'
        else:
            output = f'{self.quantity} '\
                f'{self.company.ticker} (${self.company.price:.2f}) '\
                f'{self.direction} '\
                f'{self.option.product} '\
                f'${self.option.strike:.2f} for '\
                f'{str(self.option.expiry)[:10]}'

        return output

    def reset(self) -> None:
        self.value_table = None
        self.pricer = None
        self.calculate()

    def validate(self) -> bool:

        valid = bool(self.company.ticker)

        # Check for valid pricing method
        if not valid:
            pass
        elif self.pricing_method == pricing.PRICING_METHODS[0]:
            valid = True
        elif self.pricing_method == pricing.PRICING_METHODS[1]:
            valid = True

        return valid
