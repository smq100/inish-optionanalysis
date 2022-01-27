import datetime as dt
import math

import pandas as pd

import strategies as s
from company.company import Company
from options.option import Option
from pricing.pricing import Pricing
from pricing.blackscholes import BlackScholes
from pricing.montecarlo import MonteCarlo
from utils import ui, logger
from utils import math as m


_IV_CUTOFF = 0.020

_logger = logger.get_logger()


class Leg:
    def __init__(self, ticker: str, quantity: int, product: str, direction: str, strike: float, expiry: dt.datetime):
        if product not in s.PRODUCTS:
            raise ValueError('Invalid product')
        if direction not in s.DIRECTIONS:
            raise ValueError('Invalid direction')
        if quantity < 1:
            raise ValueError('Invalid quantity')

        self.company: Company = Company(ticker, days=1)
        self.option: Option = Option(ticker, product, strike, expiry)
        self.quantity: int = quantity
        self.product: str = product
        self.direction: str = direction
        self.pricing_method: str = 'black-scholes'
        self.pricer: Pricing = None
        self.value: pd.DataFrame = None

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
            output = f'{self.quantity:2d} '\
                f'{self.company.ticker}@${self.company.price:.2f} '\
                f'{self.direction} '\
                f'{self.product} '\
                f'${self.option.strike:.2f} for '\
                f'{str(self.option.expiry)[:10]}'

        return output

    def calculate(self, value_table: bool = True, greeks: bool = True) -> float:
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
            if value_table:
                self.value = self.generate_value_table()

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

    def recalculate(self, spot_price: float, time_to_maturity: int) -> tuple[float, float]:
        if self.pricer is not None:
            if self.option.implied_volatility < _IV_CUTOFF:
                call, put = self.pricer.calculate_price(spot_price, time_to_maturity)
            else:
                call, put = self.pricer.calculate_price(spot_price, time_to_maturity, volatility=self.option.implied_volatility)
        else:
            raise AssertionError('Must call calculate() prior to recalculate()')

        return call, put

    def reset(self) -> None:
        self.value = None
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
                min_, max_, step_ = m.calculate_min_max_step(self.option.strike)
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
                        spot = m.mround(spot, 10.0)
                    elif spot > 100.0:
                        spot = m.mround(spot, 1.00)
                    elif spot > 50.0:
                        spot = m.mround(spot, 0.50)
                    elif spot > 20.0:
                        spot = m.mround(spot, 0.10)
                    else:
                        spot = m.mround(spot, 0.01)

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
