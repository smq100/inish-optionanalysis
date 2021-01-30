'''European Pricing Class'''
import logging

import numpy as np
import scipy.stats as stats

from methodbase import BasePricing, LOG_LEVEL


class BlackScholes(BasePricing):
    '''
    This class uses the classic Black-Scholes method to calculate prices for European Call and Put options

    I have made an attempt to include dividends in the calcultion of these options. However, still need to perform
    some testing.
    '''

    def __init__(self, ticker, expiry_date, strike, dividend=0.0):
        super().__init__(ticker, expiry_date, strike, dividend=dividend)

        logging.basicConfig(format='%(level_name)s: %(message)s', level=LOG_LEVEL)
        logging.info('Black-Scholes Option Pricing: Initializing...')

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

        logging.info('Calculated value for Black-Scholes Call Option is $%.2f ', self.cost_call)
        logging.info('Calculated value for Black-Scholes Put Option is $%.2f ', self.cost_put)

        return self.cost_call, self.cost_put

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
