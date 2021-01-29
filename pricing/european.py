'''European Pricing Class'''
import datetime
import logging

import numpy as np
import pandas as pd
import scipy.stats as stats

from base import PricingBase, LOG_LEVEL


class EuropeanPricing(PricingBase):
    '''
    This class uses the classic Black-Scholes method to calculate prices for European Call and Put options

    I have made an attempt to include dividends in the calcultion of these options. However, still need to perform
    some testing.
    '''

    def __init__(self, ticker, expiry_date, strike, dividend=0.0):
        super().__init__(ticker, expiry_date, strike, dividend=dividend)

        logging.basicConfig(format='%(level_name)s: %(message)s', level=LOG_LEVEL)
        logging.info('European Option Pricing. Initializing...')

        # Get/Calculate all the required underlying parameters, ex. Volatility, Risk-free rate, etc.
        self.initialize_variables()
        self.log_parameters()

    def calculate_prices(self, spot_price=-1.0, time_to_maturity=-1.0):
        ''' Calculate Call and Put option prices based on the below equations from Black-Scholes.
        If dividend is not zero, then it is subtracted from the risk free rate in the below calculations.

            CallOptionPrice = SpotPrice*N(d1) − Strike*exp(−r(T−t))*N(d2))
            PutOptionPrice  = Strike*exp(−r(T−t)) *N(−d2) − SpotPrice*N(−d1)
        :return: <float>, <float> Calculated price of Call & Put options
        '''

        if spot_price <= 0.0:
            spot_price = self.spot_price

        if time_to_maturity <= 0.0:
            time_to_maturity = self.time_to_maturity

        d_1 = self._calculate_d1(spot_price, time_to_maturity)
        d_2 = self._calculate_d2(spot_price, time_to_maturity)

        self.cost_call = ((spot_price * np.exp(-1 * self.dividend * time_to_maturity)) *
                stats.norm.cdf(d_1, 0.0, 1.0) -
                (self.strike_price * np.exp(-1 * self.risk_free_rate * time_to_maturity) *
                 stats.norm.cdf(d_2, 0.0, 1.0)))

        self.cost_put = (self.strike_price * np.exp(-1 * self.risk_free_rate * time_to_maturity) *
               stats.norm.cdf(-1 * d_2, 0.0, 1.0) -
               (spot_price * np.exp(-1 * self.dividend * time_to_maturity)) *
               stats.norm.cdf(-1 * d_1, 0.0, 1.0))

        # logging.info('Calculated value for European Call Option is $%.2f ', self.cost_call)
        # logging.info('Calculated value for European Put Option is $%.2f ', self.cost_put)

        return self.cost_call, self.cost_put

    def generate_value_table(self, call_put, price):
        ''' TODO '''

        valid = False
        type_call = True
        dframe = pd.DataFrame()

        # Ensure prices have been calculated prior
        if call_put.upper() == 'CALL':
            if self.cost_call > 0.0:
                valid = True
        elif call_put.upper() == 'PUT':
            if self.cost_put > 0.0:
                type_call = False
                valid = True

        if valid:
            cols = int(self.time_to_maturity * 365)
            if cols > 1:
                row = []
                table = []
                col_index = []
                row_index = []

                # Create list of dates to be used as the df columns
                today = datetime.datetime.today()
                today = today.replace(hour=0, minute=0, second=0, microsecond=0)
                while today < self.expiry:
                    today += datetime.timedelta(days=1)
                    if today.isoweekday() <= 5:
                        col_index.append(str(today))

                # Remove last item (days_to_maturity == 0)
                col_index.pop()

                # Calculate cost of option every day till expiry
                for spot in range(int(self.strike_price) - 10, int(self.strike_price) + 11, 1):
                    row = []
                    for item in col_index:
                        maturity_date = datetime.datetime.strptime(item, '%Y-%m-%d %H:%M:%S')
                        time_to_maturity = self.expiry - maturity_date
                        decimaldays_to_maturity = time_to_maturity.days / 365
                        self.calculate_prices(spot_price=spot, time_to_maturity=decimaldays_to_maturity)

                        if type_call:
                            value = self.cost_call
                        else:
                            value = self.cost_put
                        row.append(value)

                    row_index.append(spot)
                    table.append(row)

                # Create the Pandas dataframe
                for index, item in enumerate(col_index):
                    day = datetime.datetime.strptime(item, '%Y-%m-%d %H:%M:%S').date()
                    col_index[index] = str(day)

                dframe = pd.DataFrame(table, index=row_index, columns=col_index)

                # Reverse the row order
                dframe = dframe.iloc[::-1]

        return dframe


    def _calculate_d1(self, spot_price=-1.0, time_to_maturity=-1.0):
        ''' Famous d1 variable from Black-Scholes model calculated as shown in:

                https://en.wikipedia.org/wiki/Black%E2%80%93Scholes_model
        :return: <float>
        '''
        if spot_price <= 0.0:
            spot_price = self.spot_price

        if time_to_maturity <= 0.0:
            time_to_maturity = self.time_to_maturity

        d_1 = (np.log(spot_price / self.strike_price) +
            (self.risk_free_rate - self.dividend + 0.5 * self.volatility ** 2) * time_to_maturity) / \
            (self.volatility * np.sqrt(time_to_maturity))

        logging.debug('Calculated value for d1 = %f', d_1)

        return d_1

    def _calculate_d2(self, spot_price=-1.0, time_to_maturity=-1.0):
        ''' Famous d2 variable from Black-Scholes model calculated as shown in:

                https://en.wikipedia.org/wiki/Black%E2%80%93Scholes_model
        :return: <float>
        '''
        if spot_price <= 0.0:
            spot_price = self.spot_price

        if time_to_maturity <= 0.0:
            time_to_maturity = self.time_to_maturity

        d_2 = (np.log(spot_price / self.strike_price) +
            (self.risk_free_rate - self.dividend - 0.5 * self.volatility ** 2) * time_to_maturity) / \
            (self.volatility * np.sqrt(time_to_maturity))

        logging.debug('Calculated value for d2 = %f', d_2)

        return d_2


if __name__ == '__main__':
    pricer = EuropeanPricing('AAPL', datetime.datetime(2021, 2, 12), 145)
    call_price, put_price = pricer.calculate_prices()

    parity = pricer.is_call_put_parity_maintained(call_price, put_price)
    logging.info('Parity = %s', parity)

    df = pricer.generate_value_table('call', call_price)
    print(df)
