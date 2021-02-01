'''TODO'''
import datetime
import logging

import pandas as pd

from .blackscholes import BlackScholes
from .montecarlo import MonteCarlo
from . import utils as u


class Leg:
    '''TODO'''

    def __init__(self, quantity=1, call_put='call', long_short='long', strike=130.0, expiry=None):
        self.quantity = quantity
        self.call_put = call_put
        self.long_short = long_short
        self.strike = strike
        self.price = 0.0
        self.table_value = None
        self.table_profit = None

        if expiry is None:
            self.expiry = datetime.datetime.today() + datetime.timedelta(days=10)
        else:
            self.expiry = expiry

class Strategy:
    '''TODO'''

    def __init__(self, strategy='long_call', pricing_method='black-scholes'):
        self.symbol = {'ticker': 'AAPL', 'volitility': -1.0, 'dividend': 0.0}
        self.legs = []
        self.pricer = None
        self.strategy = strategy
        self.pricing_method = pricing_method
        self.table_value = None
        self.table_profit = None

        logging.basicConfig(format='%(level_name)s: %(message)s', level=u.LOG_LEVEL)
        logging.info('Initializing Strategy ...')

    def reset(self):
        '''TODO'''
        self.symbol = []
        self.legs = []

    def set_symbol(self, ticker, volatility=-1.0, dividend=0.0):
        '''TODO'''
        self.symbol = {'ticker': ticker, 'volitility': volatility, 'dividend': dividend}

    def add_leg(self, quantity, call_put, long_short, strike, expiry):
        '''TODO'''
        # Add one day to act as expiry value
        expiry += datetime.timedelta(days=1)

        leg = Leg(quantity, call_put, long_short, strike, expiry)
        self.legs.append(leg)

        return len(self.legs)

    def calculate_leg(self, leg, pricing_method=None):
        '''TODO'''

        if pricing_method is not None:
            self.pricing_method = pricing_method
        price = 0.0

        if self._validate(leg):
            if self.pricing_method == 'monte-carlo':
                self.pricer = MonteCarlo(self.symbol['ticker'], self.legs[leg].expiry, self.legs[leg].strike)
            else:
                self.pricer = BlackScholes(self.symbol['ticker'], self.legs[leg].expiry, self.legs[leg].strike)

            price_call, price_put = self.pricer.calculate_prices()

            if self.legs[leg].call_put == 'call':
                price = self.legs[leg].price = price_call
            else:
                price = self.legs[leg].price = price_put

            logging.info('Option price = ${:.2f} '.format(price))

            self.legs[leg].table_value = self.generate_value_table(self.legs[leg].call_put, leg)
            self.legs[leg].table_profit = self.generate_profit_table(self.legs[leg].table_value, price)

        return price


    def recalculate_leg(self, spot_price, time_to_maturity):
        '''TODO'''
        if self.pricer is None:
            call = put = 0.0
        else:
            call, put = self.pricer.calculate_prices(spot_price, time_to_maturity)

        # print(f'${spot_price:.2f}, {time_to_maturity*365:.1f}, ${call:.2f}')

        return call, put

    def generate_value_table(self, call_put, leg):
        ''' TODO '''

        valid = False
        type_call = True
        dframe = pd.DataFrame()

        # Ensure prices have been calculated prior
        if self.legs[leg].price <= 0.0:
            pass
        elif call_put.upper() == 'CALL':
            valid = True
        elif call_put.upper() == 'PUT':
            type_call = False
            valid = True

        if valid:
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
                for spot in range(int(self.pricer.strike_price) - 10, int(self.pricer.strike_price) + 11, 1):
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

                        if type_call:
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

    def generate_profit_table(self, table, price):
        ''' TODO '''
        dframe = table - price
        dframe = dframe.applymap(lambda x: x if x > -price else -price)

        return dframe


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
