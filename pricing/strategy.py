'''TODO'''
import datetime

import pandas as pd

from blackscholes import BlackScholes

class Strategy:
    '''TODO'''
    def __init__(self):
        self.symbol = {'ticker':'AAPL', 'volitility':-1, 'dividend':0.0}
        self.legs = []
        self.pricer = None
        self.strategy = 'long_call'
        self.method = 'black-scholes'
        self.price_call = 0.0
        self.price_put = 0.0
        self.table_value = None
        self.table_profit = None


    def reset(self):
        '''TODO'''
        self.symbol = []
        self.legs = []

    def set_symbol(self, ticker, volatility=-1, dividend=0.0):
        '''TODO'''
        self.symbol = {'ticker':ticker, 'volitility':volatility, 'dividend':dividend}


    def add_leg(self, quantity, call_put, long_short, strike, expiry):
        '''TODO'''
        self.legs.append({'quantity':quantity, 'call_put':call_put, 'long_short':long_short, 'strike': strike, 'expiry': expiry})

    def calculate(self):
        '''TODO'''
        if self._validate():
            self.pricer = BlackScholes(self.symbol['ticker'], self.legs[0]['expiry'], self.legs[0]['strike'])
            self.price_call, self.price_put = self.pricer.calculate_prices()

            price = self.price_call if self.legs[0]['call_put'] == 'call' else self.price_call
            self.table_value = self.generate_value_table(self.legs[0]['call_put'])
            self.table_profit = self.generate_profit_table(self.table_value, price)


    def calculate_prices(self, spot_price=-1.0, time_to_maturity=-1.0):
        '''TODO'''
        self.pricer.calculate_prices(spot_price, time_to_maturity)


    def generate_value_table(self, call_put):
        ''' TODO '''

        valid = False
        type_call = True
        dframe = pd.DataFrame()

        # Ensure prices have been calculated prior
        if call_put.upper() == 'CALL':
            if self.price_call > 0.0:
                valid = True
        elif call_put.upper() == 'PUT':
            if self.price_put > 0.0:
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
                    if today.isoweekday() <= 5:
                        col_index.append(str(today))

                # Calculate cost of option every day till expiry
                for spot in range(int(self.pricer.strike_price) - 10, int(self.pricer.strike_price) + 11, 1):
                    row = []
                    for item in col_index:
                        maturity_date = datetime.datetime.strptime(item, '%Y-%m-%d %H:%M:%S')
                        time_to_maturity = self.pricer.expiry - maturity_date
                        decimaldays_to_maturity = time_to_maturity.days / 365
                        self.calculate_prices(spot_price=spot, time_to_maturity=decimaldays_to_maturity)

                        if type_call:
                            value = self.pricer.cost_call
                        else:
                            value = self.pricer.cost_put
                        row.append(value)

                    row_index.append(spot)
                    table.append(row)

                # Strip the time from the datetime string
                for index, item in enumerate(col_index):
                    day = datetime.datetime.strptime(item, '%Y-%m-%d %H:%M:%S').date()
                    col_index[index] = f'{str(day.strftime("%b"))}-{str(day.day)}'

                # Finally, create the Pandas dataframe and reverse the row order
                dframe = pd.DataFrame(table, index=row_index, columns=col_index)
                dframe = dframe.iloc[::-1]

        return dframe

    def generate_profit_table(self, table, price):
        ''' TODO '''
        dframe = table - price
        dframe = dframe.applymap(lambda x: x if x >= -price else 0.0)

        return dframe

    def _validate(self):
        '''TODO'''
        return True
