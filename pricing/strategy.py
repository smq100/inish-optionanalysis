'''TODO'''
import datetime

import pandas as pd

from blackscholes import BlackScholes
from montecarlo import MonteCarlo

class Leg:
    '''TODO'''

    def __init__(self, quantity=1, call_put='call', long_short='long', strike=100.0, expiry=None):
        self.quantity = quantity
        self.call_put = call_put
        self.long_short = long_short
        self.strike = strike
        self.price = 0.0

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

    def calculate_leg(self, pricing_method=None):
        '''TODO'''

        if pricing_method is not None:
            self.pricing_method = pricing_method

        if self._validate():
            if self.pricing_method == 'monte-carlo':
                self.pricer = MonteCarlo(self.symbol['ticker'], self.legs[0].expiry, self.legs[0].strike)
            else:
                self.pricer = BlackScholes(self.symbol['ticker'], self.legs[0].expiry, self.legs[0].strike)

            price_call, price_put = self.pricer.calculate_prices()

            if self.legs[0].call_put == 'call':
                price = self.legs[0].price = price_call
            else:
                price = self.legs[0].price = price_put

            self.table_value = self.generate_value_table(self.legs[0].call_put)
            self.table_profit = self.generate_profit_table(self.table_value, price)

        return price


    def recalculate_leg(self, spot_price, time_to_maturity):
        '''TODO'''
        if self.pricer is None:
            call = put = 0.0
        else:
            call, put = self.pricer.calculate_prices(spot_price, time_to_maturity)

        # print(f'${spot_price:.2f}, {time_to_maturity*365:.1f}, ${call:.2f}')

        return call, put

    def generate_value_table(self, call_put):
        ''' TODO '''

        valid = False
        type_call = True
        dframe = pd.DataFrame()

        # Ensure prices have been calculated prior
        if self.legs[0].price <= 0.0:
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


    def _validate(self):
        '''TODO'''
        if self.pricing_method == 'black-scholes':
            valid = True
        elif self.pricing_method == 'monte-carlo':
            valid = True
        else:
            valid = False

        return valid
