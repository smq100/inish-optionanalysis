'''TODO'''
import abc
from abc import ABC
import datetime
import logging

import pandas as pd

from pricing.blackscholes import BlackScholes
from pricing.montecarlo import MonteCarlo
from utils import utils as u

class Symbol:
    '''TODO'''

    def __init__(self, ticker, dividend=0.0, volatility=-1.0):
        self.ticker = ticker
        self.dividend = dividend
        self.volatility = volatility
        self.spot = 0.0


    def __str__(self):
        output = f'{self.ticker}@${self.spot:.2f}/{self.volatility*100:.1f}%'

        return output


class Analysis:
    '''TODO'''

    def __init__(self):
        self.table_value = None


class Leg:
    '''TODO'''

    def __init__(self, quantity=1, call_put='call', long_short='long', strike=130.0, expiry=None):
        self.symbol = Symbol('AAPL')
        self.quantity = quantity
        self.call_put = call_put
        self.long_short = long_short
        self.strike = strike
        self.price = 0.0
        self.table_value = None

        if expiry is None:
            self.expiry = datetime.datetime.today() + datetime.timedelta(days=10)
        else:
            self.expiry = expiry

    def __str__(self):
        output = \
            f'{self.quantity} '\
            f'{self.symbol.ticker}@${self.symbol.spot:.2f} '\
            f'{self.long_short:5s} '\
            f'{self.call_put:5s} '\
            f'${self.strike:.2f} for '\
            f'{str(self.expiry)[:10]}'

        if self.price > 0.0:
            output += f' = ${self.price:.2f}'

        return output


class Strategy(ABC):
    '''TODO'''

    def __init__(self, name, pricing_method):
        self.analysis = Analysis()
        self.symbol = {'ticker': 'AAPL', 'volatility': -1.0, 'dividend': 0.0}
        self.legs = []
        self.pricer = None
        self.name = name
        self.pricing_method = pricing_method

        logging.basicConfig(format='%(level_name)s: %(message)s', level=u.LOG_LEVEL)
        logging.info('Initializing Strategy ...')

    def __str__(self):
        output = \
            f'{self.name} '\
            f'({self.pricing_method})'

        return output


    def reset(self):
        '''TODO'''
        self.symbol = []
        self.legs = []

    def set_symbol(self, ticker, volatility=0.3, dividend=0.0):
        '''TODO'''
        self.reset()
        self.symbol = {'ticker': ticker, 'volatility': volatility, 'dividend': dividend}

    def add_leg(self, quantity, call_put, long_short, strike, expiry):
        '''TODO'''

        # Add the leg if a symbol is specified
        if len(self.symbol['ticker']) > 0:
            # Add one day to act as expiry value
            expiry += datetime.timedelta(days=1)

            leg = Leg(quantity, call_put, long_short, strike, expiry)
            leg.symbol.ticker = self.symbol['ticker']
            leg.symbol.volatility = self.symbol['volatility']
            leg.symbol.dividend = self.symbol['dividend']

            self.legs.append(leg)

        return len(self.legs)

    def calculate_leg(self, leg, pricing_method=None):
        '''TODO'''

        if pricing_method is not None:
            self.pricing_method = pricing_method
        price = 0.0

        if self._validate(leg):
            if self.pricing_method == 'monte-carlo':
                self.pricer = MonteCarlo(self.legs[leg].symbol.ticker, self.legs[leg].expiry, self.legs[leg].strike)
            else:
                self.pricer = BlackScholes(self.legs[leg].symbol.ticker, self.legs[leg].expiry, self.legs[leg].strike)

            price_call, price_put = self.pricer.calculate_prices()
            self.legs[leg].symbol.spot = self.pricer.spot_price
            self.legs[leg].symbol.volatility = self.pricer.volatility

            if self.legs[leg].call_put == 'call':
                price = self.legs[leg].price = price_call
            else:
                price = self.legs[leg].price = price_put

            logging.info('Option price = ${:.2f} '.format(price))

            self.legs[leg].table_value = self.generate_value_table(leg)

        return price


    def recalculate_leg(self, spot_price, time_to_maturity):
        '''TODO'''
        if self.pricer is None:
            call = put = 0.0
        else:
            call, put = self.pricer.calculate_prices(spot_price, time_to_maturity)

        # print(f'${spot_price:.2f}, {time_to_maturity*365:.1f}, ${call:.2f}')

        return call, put

    @abc.abstractmethod
    def analyze(self):
        ''' TODO '''


    def generate_value_table(self, leg):
        ''' TODO '''

        dframe = pd.DataFrame()

        if self.legs[leg].price > 0.0:
            cols = int(self.pricer.time_to_maturity * 365)
            if cols > 1:
                row = []
                table = []
                col_index = []
                row_index = []

                # Create list of dates to be used as the df columns
                today = datetime.datetime.today()
                today = today.replace(hour=0, minute=0, second=0, microsecond=0)
                col_index.append(str(today))
                while today < self.pricer.expiry:
                    today += datetime.timedelta(days=1)
                    col_index.append(str(today))

                # Calculate cost of option every day till expiry
                min_, max_, step_ = self._calc_price_min_max_step()
                for spot in range(min_, max_, step_):
                    row = []
                    for item in col_index:
                        maturity_date = datetime.datetime.strptime(
                            item, '%Y-%m-%d %H:%M:%S')
                        time_to_maturity = self.pricer.expiry - maturity_date
                        decimaldays_to_maturity = time_to_maturity.days / 365.0

                        # Compensate for zero delta days to provide small fraction of day
                        if decimaldays_to_maturity < 0.0003:
                            decimaldays_to_maturity = 0.0001

                        price_call, price_put = self.recalculate_leg(spot_price=spot, time_to_maturity=decimaldays_to_maturity)

                        if self.legs[leg].call_put == 'call':
                            row.append(price_call)
                        else:
                            row.append(price_put)

                    row_index.append(spot)
                    table.append(row)

                # Strip the time from the datetime string
                for index, item in enumerate(col_index):
                    day = datetime.datetime.strptime(
                        item, '%Y-%m-%d %H:%M:%S').date()
                    col_index[index] = f'{str(day.strftime("%b"))}-{str(day.day)}'

                # Finally, create the Pandas dataframe then reverse the row order
                col_index[-1] = 'Exp'
                dframe = pd.DataFrame(
                    table, index=row_index, columns=col_index)
                dframe = dframe.iloc[::-1]

        return dframe

    @abc.abstractmethod
    def _calc_price_min_max_step(self):
        ''' TODO '''

    def _validate(self, leg):
        '''TODO'''
        # Check for valid method
        if self.pricing_method == 'black-scholes':
            valid = True
        elif self.pricing_method == 'monte-carlo':
            valid = True
        else:
            valid = False

        # Check for correct leg index
        if not valid:
            pass
        elif leg < len(self.legs):
            valid = True
        else:
            valid = False

        return valid

if __name__ == '__main__':
    pd.options.display.float_format = '{:,.2f}'.format

    strategy_ = Strategy()
    leg_ = Leg()
    strategy_.add_leg(leg_.quantity, leg_.call_put, leg_.long_short, leg_.strike, leg_.expiry)
    strategy_.calculate_leg(0)
    print(strategy_.legs[0].table_value)
