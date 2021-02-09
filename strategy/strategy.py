'''TODO'''

import sys
import abc
from abc import ABC
import datetime
import math
import logging

import pandas as pd

from .symbol import Symbol
from options.option import Option
from pricing.blackscholes import BlackScholes
from pricing.montecarlo import MonteCarlo
from utils import utils as u

class Strategy(ABC):
    '''TODO'''

    def __init__(self, ticker, product, direction):
        self.name = ''
        self.ticker = ticker
        self.product = product
        self.width = 1
        self.analysis = Analysis()
        self.legs = []
        self.initial_spot = 0.0

        logging.basicConfig(format='%(level_name)s: %(message)s', level=u.LOG_LEVEL)
        logging.info('Initializing Strategy ...')

        self.initial_spot = self.get_current_spot(ticker, True)


    def __str__(self):
        return 'Strategy abstract base class'


    def calculate(self):
        '''TODO'''

        # Calculate all legs
        for leg in self.legs:
            leg.calculate()


    @abc.abstractmethod
    def analyze(self):
        ''' TODO '''


    def reset(self):
        '''TODO'''

        # Clear the analysis
        self.analysis = Analysis()


    def update_expiry(self, date):
        for leg in self.legs:
            leg.option.expiry = date


    def add_leg(self, quantity, product, direction, strike, expiry):
        '''TODO'''

        # Add one day to act as expiry value
        expiry += datetime.timedelta(days=1)

        leg = Leg(self, self.ticker, quantity, product, direction, strike, expiry)
        self.legs.append(leg)

        return len(self.legs)


    def get_current_spot(self, ticker, roundup=False):
        '''TODO'''

        expiry = datetime.datetime.today() + datetime.timedelta(days=10)
        pricer = MonteCarlo(ticker, expiry, self.initial_spot)

        if roundup:
            spot = math.ceil(pricer.spot_price)
        else:
            spot = pricer.spot_price

        return spot


    @abc.abstractmethod
    def generate_profit_table(self):
        '''TODO'''


    @abc.abstractmethod
    def calc_max_gain_loss(self):
        '''TODO'''


    @abc.abstractmethod
    def calc_breakeven(self):
        '''TODO'''

    def get_errors(self):
        '''TODO'''
        return ''


    def _calc_price_min_max_step(self):
        '''TODO'''

        min_ = max_ = step_ = 0

        if len(self.legs) > 0:
            percent = 0.20
            min_ = self.legs[0].symbol.spot * (1 - percent)
            max_ = self.legs[0].symbol.spot * (1 + percent)

            step_ = (max_ - min_) / 40.0
            step_ = u.mround(step_, step_ / 10.0)

            if min_ < step_:
                min_ = step_

        return min_, max_, step_


    def _validate(self):
        '''TODO'''

        return len(self.legs) > 0


class Leg:
    '''TODO'''

    def __init__(self, strategy, ticker, quantity, product, direction, strike, expiry):
        self.symbol = Symbol(ticker)
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
            output = f'{self.quantity} '\
            f'{self.symbol.ticker}@${self.symbol.spot:.2f} '\
            f'{self.direction:5s} '\
            f'{self.product:5s} '\
            f'${self.option.strike:.2f} for '\
            f'{str(self.option.expiry)[:10]}'\
            f' = ${self.option.calc_price * self.quantity:.2f}'

            if self.quantity > 1:
                output += f' (${self.option.calc_price:.2f} each)'

            if not self.option.contract_symbol:
                output += ' (specific option not selected)'

        else:
            output = f'{self.symbol.ticker} leg not yet calculated'

        return output


    def calculate(self, pricing_method='black-scholes'):
        '''TODO'''

        if pricing_method is not None:
            self.pricing_method = pricing_method

        price = 0.0

        if self._validate():
            # Build the pricer
            if self.pricing_method == 'monte-carlo':
                self.pricer = MonteCarlo(self.symbol.ticker, self.option.expiry, self.option.strike)
            else:
                self.pricer = BlackScholes(self.symbol.ticker, self.option.expiry, self.option.strike)

            # Calculate prices
            price_call, price_put = self.pricer.calculate_prices()
            self.symbol.spot = self.pricer.spot_price
            self.symbol.volatility = self.pricer.volatility
            self.option.time_to_maturity = self.pricer.time_to_maturity

            if self.product == 'call':
                price = self.option.calc_price = price_call
            else:
                price = self.option.calc_price = price_put

            # Generate the values table
            self.table = self.generate_value_table()

            logging.info('Option price = ${:.2f} '.format(price))

        return price


    def modify_symbol(self, ticker, volatility=-1.0, dividend=0.0):
        '''TODO'''

        symbol = self.symbol
        strike = self.option.strike

        self.symbol = Symbol(ticker, volatility, dividend)

        try:
            # Reset strike to spot value
            self.option.strike = self.strategy.get_current_spot(ticker, True)
            self.reset()
            return True
        except:
            self.symbol = symbol
            self.option.strike = strike
            u.print_error(sys.exc_info()[1])
            return False


    def modify_values(self, quantity, product, direction, strike):
        '''TODO'''

        self.quantity = quantity
        self.product = product
        self.direction = direction
        self.option.strike = strike

        # Clear any calculated data and reacalculate
        self.strategy.reset()
        self.reset()

        return True

    def reset(self):
        '''TODO'''

        self.table = None
        self.pricer = None
        self.calculate()


    def recalculate(self, spot_price, time_to_maturity):
        '''TODO'''

        call = put = 0.0

        if self.pricer is not None:
            call, put = self.pricer.calculate_prices(spot_price, time_to_maturity)

        return call, put


    def generate_value_table(self):
        ''' TODO '''

        dframe = pd.DataFrame()

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

                col_index.append(str(today))
                while today < self.option.expiry:
                    today += datetime.timedelta(days=step)
                    col_index.append(str(today))

                # Calculate cost of option every day till expiry
                min_, max_, step_ = self.strategy._calc_price_min_max_step()
                for spot in range(int(math.ceil(min_*40)), int(math.ceil(max_*40)), int(math.ceil(step_*40))):
                    spot /= 40.0
                    row = []
                    for item in col_index:
                        maturity_date = datetime.datetime.strptime(item, '%Y-%m-%d %H:%M:%S')
                        time_to_maturity = self.option.expiry - maturity_date
                        decimaldays_to_maturity = time_to_maturity.days / 365.0

                        # Compensate for zero delta days to provide small fraction of day
                        if decimaldays_to_maturity < 0.0003:
                            decimaldays_to_maturity = 0.00001

                        price_call, price_put = self.recalculate(spot_price=spot, time_to_maturity=decimaldays_to_maturity)

                        if self.product == 'call':
                            row.append(price_call)
                        else:
                            row.append(price_put)

                    table.append(row)

                    # Create row index
                    if spot > 500.0:
                        spot = u.mround(spot, 10.0)
                    elif spot > 100.0:
                        spot = u.mround(spot, 1.00)
                    elif spot > 50.0:
                        spot = u.mround(spot, 0.50)
                    elif spot > 20.0:
                        spot = u.mround(spot, 0.10)
                    else:
                        spot = u.mround(spot, 0.01)


                    row_index.append(spot)

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
            table = table.iloc[::step]

        return table


    def _calc_date_step(self):
        ''' TODO '''

        cols = int(math.ceil(self.option.time_to_maturity * 365))
        step = 1

        return cols, step


    def _validate(self):
        '''TODO'''

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
                f'Amount:    ${abs(self.amount):.2f} {self.credit_debit}\n'\
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
