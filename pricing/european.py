'''European Pricing Class'''
import datetime
import logging

import numpy as np
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

    def calculate_prices(self, time_to_maturity=0):
        ''' Calculate Call and Put option prices based on the below equations from Black-Scholes.
        If dividend is not zero, then it is subtracted from the risk free rate in the below calculations.

            CallOptionPrice =SpotPrice*N(d1) − Strike*exp(−r(T−t))*N(d2))
            PutOptionPrice  = Strike*exp(−r(T−t)) *N(−d2) − SpotPrice*N(−d1)
        :return: <float>, <float> Calculated price of Call & Put options
        '''
        if time_to_maturity <= 0.0:
            time_to_maturity = self.time_to_maturity

        d_1 = self._calculate_d1()
        d_2 = self._calculate_d2()

        self.cost_call = ((self.spot_price * np.exp(-1 * self.dividend * time_to_maturity)) *
                stats.norm.cdf(d_1, 0.0, 1.0) -
                (self.strike_price * np.exp(-1 * self.risk_free_rate * time_to_maturity) *
                 stats.norm.cdf(d_2, 0.0, 1.0)))

        self.cost_put = (self.strike_price * np.exp(-1 * self.risk_free_rate * time_to_maturity) *
               stats.norm.cdf(-1 * d_2, 0.0, 1.0) -
               (self.spot_price * np.exp(-1 * self.dividend * time_to_maturity)) *
               stats.norm.cdf(-1 * d_1, 0.0, 1.0))

        logging.info('Calculated value for European Call Option is $%.2f ', self.cost_call)
        logging.info('Calculated value for European Put Option is $%.2f ', self.cost_put)

        return self.cost_call, self.cost_put

    def generate_profit_table(self, call_put, price):
        ''' TODO '''

        # Ensure prices have been calculated prior
        valid = False
        table = []
        type_call = True
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
                today = datetime.datetime.today()
                today = today.replace(hour=0, minute=0, second=0, microsecond=0)
                table = [{str(today) : 0.0}]

                # Create list of date dicts of weekdays until expiration that we will fill with prices
                while today < self.expiry:
                    today += datetime.timedelta(days=1)
                    if today.isoweekday() <= 5:
                        table.append({str(today): 0.0})

                for item in table:
                    key, value = list(item.items())[0]
                    maturity_date = datetime.datetime.strptime(key, '%Y-%m-%d %H:%M:%S')
                    time_to_maturity = (self.expiry - maturity_date)
                    days_to_maturity = time_to_maturity.days / 365
                    self.calculate_prices(days_to_maturity)

                    if type_call:
                        item[key] = self.cost_call
                    else:
                        item[key] = self.cost_put

                    # print(item)
                    print(key, days_to_maturity, self.cost_call, self.cost_put)

        return table


    def _calculate_d1(self):
        ''' Famous d1 variable from Black-Scholes model calculated as shown in:

                https://en.wikipedia.org/wiki/Black%E2%80%93Scholes_model
        :return: <float>
        '''
        d_1 = (np.log(self.spot_price / self.strike_price) +
            (self.risk_free_rate - self.dividend + 0.5 * self.volatility ** 2) * self.time_to_maturity) / \
            (self.volatility * np.sqrt(self.time_to_maturity))

        logging.debug('Calculated value for d1 = %f', d_1)

        return d_1

    def _calculate_d2(self):
        ''' Famous d2 variable from Black-Scholes model calculated as shown in:

                https://en.wikipedia.org/wiki/Black%E2%80%93Scholes_model
        :return: <float>
        '''
        d_2 = (np.log(self.spot_price / self.strike_price) +
            (self.risk_free_rate - self.dividend - 0.5 * self.volatility ** 2) * self.time_to_maturity) / \
            (self.volatility * np.sqrt(self.time_to_maturity))

        logging.debug('Calculated value for d2 = %f', d_2)

        return d_2


if __name__ == '__main__':
    pricer = EuropeanPricing('AAPL', datetime.datetime(2021, 2, 12), 145)
    call_price, put_price = pricer.calculate_prices()

    parity = pricer.is_call_put_parity_maintained(call_price, put_price)
    logging.info('Parity = %s', parity)

    t = pricer.generate_profit_table('call', call_price)
    # print(t)
