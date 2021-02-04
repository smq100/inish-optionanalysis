'''TODO'''
import abc
from abc import ABC
import datetime
import math
import logging

import pandas as pd

from pricing.blackscholes import BlackScholes
from pricing.montecarlo import MonteCarlo
from utils import utils as u

class Strategy(ABC):
    '''TODO'''

    def __init__(self, ticker=''):
        self.name = ''
        self.ticker = ticker
        self.analysis = Analysis()
        self.legs = []

        logging.basicConfig(format='%(level_name)s: %(message)s', level=u.LOG_LEVEL)
        logging.info('Initializing Strategy ...')

    def __str__(self):
        return 'Strategy base class'


    def set_symbol(self, ticker, volatility=-1.0, dividend=0.0):
        '''TODO'''

        self.ticker = ticker
        self.reset()

        for leg in self.legs:
            leg.modify_symbol(ticker, volatility, dividend)


    def calculate(self):
        '''TODO'''

        for leg in self.legs:
            leg.calculate()


    def reset(self):
        '''TODO'''

        # Clear the analysis
        self.analysis = Analysis()


    @abc.abstractmethod
    def analyze(self):
        ''' TODO '''


    def add_leg(self, quantity, call_put, long_short, strike, expiry=None):
        '''TODO'''

        # Add the leg if a symbol is specified
        if expiry is None:
            expiry = datetime.datetime.today() + datetime.timedelta(days=10)

        # Add one day to act as expiry value
        expiry += datetime.timedelta(days=1)

        leg = Leg(self, self.ticker, quantity, call_put, long_short, strike, expiry)
        self.legs.append(leg)

        return len(self.legs)


    @abc.abstractmethod
    def _calc_price_min_max_step(self):
        ''' TODO '''


class Leg:
    '''TODO'''

    def __init__(self, strategy, ticker, quantity=1, call_put='call', long_short='long', strike=130.0, expiry=None):
        self.strategy = strategy
        self.quantity = quantity
        self.call_put = call_put
        self.long_short = long_short

        self.symbol = Symbol(ticker)
        self.strike = strike
        self.price = 0.0
        self.time_to_maturity = 0
        self.pricing_method = 'black-scholes'
        self.pricer = None
        self.table = None

        if expiry is None:
            self.expiry = datetime.datetime.today() + datetime.timedelta(days=10)
        else:
            self.expiry = expiry

    def __str__(self):
        if self.price > 0.0:
            output = f'{self.quantity} '\
            f'{self.symbol.ticker}@${self.symbol.spot:.2f} '\
            f'{self.long_short:5s} '\
            f'{self.call_put:5s} '\
            f'${self.strike:.2f} for '\
            f'{str(self.expiry)[:10]}'\
            f' = ${self.price*self.quantity:.2f}'

            if self.quantity > 1:
                output += f' (${self.price:.2f} each)'
        else:
            output = f'{self.symbol.ticker} leg not yet calculated'

        return output

    def modify_symbol(self, ticker, volatility=-1.0, dividend=0.0):
        self.symbol = Symbol(ticker, volatility, dividend)
        self.reset()

    def modify_values(self, quantity, call_put, long_short, strike, expiry=None):
        self.quantity = quantity
        self.call_put = call_put
        self.long_short = long_short
        self.strike = strike

        if expiry is None:
            self.expiry = datetime.datetime.today() + datetime.timedelta(days=10)
        else:
            self.expiry = expiry

        # Clear any calculated data and reacalculate
        self.strategy.reset()
        self.reset()

        return True

    def reset(self):
        self.table = None
        self.pricer = None
        self.calculate()

    def calculate(self, pricing_method='black-scholes'):
        '''TODO'''

        if pricing_method is not None:
            self.pricing_method = pricing_method

        price = 0.0

        if self._validate():
            if self.pricing_method == 'monte-carlo':
                self.pricer = MonteCarlo(self.symbol.ticker, self.expiry, self.strike)
            else:
                self.pricer = BlackScholes(self.symbol.ticker, self.expiry, self.strike)

            price_call, price_put = self.pricer.calculate_prices()
            self.symbol.spot = self.pricer.spot_price
            self.symbol.volatility = self.pricer.volatility
            self.time_to_maturity = self.pricer.time_to_maturity

            if self.call_put == 'call':
                price = self.price = price_call
            else:
                price = self.price = price_put

            logging.info('Option price = ${:.2f} '.format(price))

            self.table = self.generate_value_table()

        return price


    def recalculate(self, spot_price, time_to_maturity):
        '''TODO'''
        call = put = 0.0

        if self.pricer is not None:
            call, put = self.pricer.calculate_prices(spot_price, time_to_maturity)

        return call, put


    def generate_value_table(self):
        ''' TODO '''

        dframe = pd.DataFrame()

        if self.price > 0.0:
            cols, step = self._calc_date_cols_step()
            if cols > 1:
                row = []
                table = []
                col_index = []
                row_index = []

                # Create list of dates to be used as the df columns
                today = datetime.datetime.today()
                today = today.replace(hour=0, minute=0, second=0, microsecond=0)

                col_index.append(str(today))
                while today < self.expiry:
                    today += datetime.timedelta(days=step)
                    col_index.append(str(today))

                # Calculate cost of option every day till expiry
                min_, max_, step_ = self.strategy._calc_price_min_max_step()
                for spot in range(min_, max_, step_):
                    row = []
                    for item in col_index:
                        maturity_date = datetime.datetime.strptime(item, '%Y-%m-%d %H:%M:%S')
                        time_to_maturity = self.expiry - maturity_date
                        decimaldays_to_maturity = time_to_maturity.days / 365.0

                        # Compensate for zero delta days to provide small fraction of day
                        if decimaldays_to_maturity < 0.0003:
                            decimaldays_to_maturity = 0.00001

                        price_call, price_put = self.recalculate(spot_price=spot, time_to_maturity=decimaldays_to_maturity)

                        if self.call_put == 'call':
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


    def compress_table(self, rows, cols):
        ''' TODO '''

        table = self.table
        srows, scols = table.shape

        if cols > 0 and cols < scols:
            # thin out cols
            step = int(math.ceil(scols/cols))
            end = table[table.columns[-2::]]        # Save the last two rows
            table = table[table.columns[:-2:step]]  # Thin the table (less the last two rows: Last day and exp)
            table = pd.concat([table, end], axis=1) # Add back the last two rows

        if rows > 0 and rows < srows:
            # Thin out rows
            step = int(math.ceil(srows/rows))
            print(rows, srows, step)
            table = table.iloc[::step]

        return table


    def _calc_date_cols_step(self):
        ''' TODO '''

        cols = int(math.ceil(self.time_to_maturity * 365))
        step = 1

        return cols, step


    def _validate(self):
        '''TODO'''

        valid = False

        if (len(self.symbol.ticker) > 0):
            valid = True

        # Check for valid method
        if not valid:
            pass
        elif self.pricing_method == 'black-scholes':
            valid = True
        elif self.pricing_method == 'monte-carlo':
            valid = True

        return valid


class Analysis:
    '''TODO'''

    def __init__(self):
        self.table = None
        self.credit_debit = ''
        self.sentiment = ''
        self.amount = 0.0
        self.max_gain = 0.0
        self.max_loss = 0.0
        self.breakeven = 0.0


    def __str__(self):
        if self.table is not None:
            if self.max_gain >= 0.0:
                gain = f'${self.max_gain:.2f}'
            else:
                gain = 'Unlimited'

            if self.max_loss >= 0.0:
                loss = f'${self.max_loss:.2f}'
            else:
                loss = 'Unlimited'

            output = '\n'\
                f'Type:      {self.credit_debit.title()}\n'\
                f'Sentiment: {self.sentiment.title()}\n'\
                f'Amount:    ${self.amount:.2f} {self.credit_debit}\n'\
                f'Max Gain:  {gain}\n'\
                f'Max Loss:  {loss}\n'\
                f'Breakeven: ${self.breakeven:.2f} at expiry\n'
        else:
            output = 'Not yet analyzed'

        return output


    def compress_table(self, rows, cols):
        ''' TODO '''

        if self.table is not None:
            table = self.table
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


if __name__ == '__main__':
    pd.options.display.float_format = '{:,.2f}'.format

    strategy_ = Strategy()
    leg_ = Leg()

    strategy_.add_leg(leg_.quantity, leg_.call_put, leg_.long_short, leg_.strike, leg_.expiry)
    strategy_.legs[0].calculate()
    print(strategy_.legs[0].table)
