'''European Pricing Class'''
import logging
import datetime

import numpy as np
import scipy.stats as stats

from .pricing import Pricing
from utils import utils as u


class BlackScholes(Pricing):
    '''
    This class uses the classic Black-Scholes method to calculate prices for European Call and Put options

    '''

    def __init__(self, ticker, expiry, strike, dividend=0.0):
        super().__init__(ticker, expiry, strike, dividend=dividend)

        logging.basicConfig(format='%(level_name)s: %(message)s', level=u.LOG_LEVEL)
        logging.info('Initializing Black-Scholes pricing...')

        # Get/Calculate all the required underlying parameters, ex. Volatility, Risk-free rate, etc.
        self.log_parameters()

    def calculate_price(self, spot_price=-1.0, time_to_maturity=-1.0):
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

        d1 = self._calculate_d1(spot_price, time_to_maturity)
        d2 = self._calculate_d2(spot_price, time_to_maturity)

        self.price_call = ((spot_price * np.exp(-1 * self.dividend * time_to_maturity)) *
            stats.norm.cdf(d1, 0.0, 1.0) -
            (self.strike_price * np.exp(-1 * self.risk_free_rate * time_to_maturity) *
            stats.norm.cdf(d2, 0.0, 1.0)))

        self.price_put = (self.strike_price * np.exp(-1 * self.risk_free_rate * time_to_maturity) *
            stats.norm.cdf(-1 * d2, 0.0, 1.0) -
            (spot_price * np.exp(-1 * self.dividend * time_to_maturity)) *
            stats.norm.cdf(-1 * d1, 0.0, 1.0))

        logging.info('Calculated value for Black-Scholes Call Option is $%.2f ', self.price_call)
        logging.info('Calculated value for Black-Scholes Put Option is $%.2f ', self.price_put)

        return self.price_call, self.price_put


    def calculate_delta(self, spot_price=-1.0, time_to_maturity=-1.0):
        ''' Calculate Call and Put option delta based on the below equations from Black-Scholes.
        If dividend is not zero, then it is subtracted from the risk free rate in the below calculations.

        delta call =  np.exp(-q * T) * si.norm.cdf(d1, 0.0, 1.0)
        delta put  = -np.exp(-q * T) * si.norm.cdf(-d1, 0.0, 1.0)

        :return: <float>, <float> Calculated delta of Call & Put options
        '''

        if spot_price <= 0.0:
            spot_price = self.spot_price

        if time_to_maturity <= 0.0:
            time_to_maturity = self.time_to_maturity

        d1 = self._calculate_d1(spot_price, time_to_maturity)

        self.delta_call = np.exp(-self.dividend * time_to_maturity) * stats.norm.cdf(d1, 0.0, 1.0)
        self.delta_put = -np.exp(-self.dividend * time_to_maturity) * stats.norm.cdf(-d1, 0.0, 1.0)

        logging.info('Calculated delta for Black-Scholes Call Option is $%.2f ', self.delta_call)
        logging.info('Calculated delta for Black-Scholes Put Option is $%.2f ', self.delta_put)

        return self.delta_call, self.delta_put


    def calculate_gamma(self, spot_price=-1.0, time_to_maturity=-1.0):
        ''' Calculate Call and Put option gamma based on the below equations from Black-Scholes.
        If dividend is not zero, then it is subtracted from the risk free rate in the below calculations.

        gamma call & put = np.exp(-q * T) * si.norm.cdf(d1, 0.0, 1.0) / S * sigma * np.sqrt(T)

        :return: <float>, <float> Calculated delta of Call & Put options
        '''

        if spot_price <= 0.0:
            spot_price = self.spot_price

        if time_to_maturity <= 0.0:
            time_to_maturity = self.time_to_maturity

        d1 = self._calculate_d1(spot_price, time_to_maturity)

        gamma = np.exp(-self.dividend * time_to_maturity) * stats.norm.cdf(d1, 0.0, 1.0) / spot_price * self.volatility * np.sqrt(time_to_maturity)

        self.gamma_call = self.gamma_put = gamma

        logging.info('Calculated gamma for Black-Scholes Call Option is $%.2f ', self.gamma_call)
        logging.info('Calculated gamma for Black-Scholes Put Option is $%.2f ', self.gamma_put)

        return self.gamma_call, self.gamma_put


    def calculate_theta(self, spot_price=-1.0, time_to_maturity=-1.0):
        ''' Calculate Call and Put option theta based on the below equations from Black-Scholes.
        If dividend is not zero, then it is subtracted from the risk free rate in the below calculations.

        theta call = -np.exp(-q * T) *
                     (S * si.norm.cdf(d1, 0.0, 1.0) * sigma) /
                     (2 * np.sqrt(T)) - r * K * np.exp(-r * T) *
                     si.norm.cdf(d2, 0.0, 1.0) + q * S *
                     np.exp(-q * T) * si.norm.cdf(d1, 0.0, 1.0)

        theta put = -np.exp(-q * T) *
                     (S * si.norm.cdf(d1, 0.0, 1.0) * sigma) /
                     (2 * np.sqrt(T)) + r * K * np.exp(-r * T) *
                     si.norm.cdf(-d2, 0.0, 1.0) - q * S *
                     np.exp(-q * T) * si.norm.cdf(-d1, 0.0, 1.0)


        :return: <float>, <float> Calculated delta of Call & Put options
        '''

        if spot_price <= 0.0:
            spot_price = self.spot_price

        if time_to_maturity <= 0.0:
            time_to_maturity = self.time_to_maturity

        d1 = self._calculate_d1(spot_price, time_to_maturity)
        d2 = self._calculate_d2(spot_price, time_to_maturity)

        theta_call = -np.exp(-self.dividend * time_to_maturity) * \
                     (spot_price * stats.norm.cdf(d1, 0.0, 1.0) * self.volatility) / \
                     (2 * np.sqrt(time_to_maturity)) - self.risk_free_rate * self.strike_price * np.exp(-self.risk_free_rate * time_to_maturity) * \
                     stats.norm.cdf(d2, 0.0, 1.0) + self.dividend * spot_price * \
                     np.exp(-self.dividend * time_to_maturity) * stats.norm.cdf(d1, 0.0, 1.0)

        theta_put = -np.exp(-self.dividend * time_to_maturity) * \
                    (spot_price * stats.norm.cdf(d1, 0.0, 1.0) * self.volatility) / \
                    (2 * np.sqrt(time_to_maturity)) + self.risk_free_rate * self.strike_price * np.exp(-self.risk_free_rate * time_to_maturity) * \
                    stats.norm.cdf(-d2, 0.0, 1.0) - self.dividend * spot_price * \
                    np.exp(-self.dividend * time_to_maturity) * stats.norm.cdf(-d1, 0.0, 1.0)

        self.theta_call = theta_call / 365.0
        self.theta_put = theta_put / 365.0

        logging.info('Calculated theta for Black-Scholes Call Option is $%.2f ', self.theta_call)
        logging.info('Calculated theta for Black-Scholes Put Option is $%.2f ', self.theta_put)

        return self.theta_call, self.theta_put


    def calculate_vega(self, spot_price=-1.0, time_to_maturity=-1.0):
        ''' Calculate Call and Put option vega based on the below equations from Black-Scholes.
        If dividend is not zero, then it is subtracted from the risk free rate in the below calculations.

        vega call & put = 1 / np.sqrt(2 * np.pi) * S * np.exp(-q * T) * np.exp(-d1 ** 2 * 0.5) * np.sqrt(T)

        :return: <float>, <float> Calculated delta of Call & Put options
        '''
        if spot_price <= 0.0:
            spot_price = self.spot_price

        if time_to_maturity <= 0.0:
            time_to_maturity = self.time_to_maturity

        d1 = self._calculate_d1(spot_price, time_to_maturity)

        vega = 1 / np.sqrt(2 * np.pi) * spot_price * np.exp(-self.dividend * time_to_maturity) * np.exp(-d1 ** 2 * 0.5) * np.sqrt(time_to_maturity)

        self.vega_call = self.vega_put = vega / 100.0

        logging.info('Calculated vega for Black-Scholes Call Option is $%.2f ', self.vega_call)
        logging.info('Calculated vega for Black-Scholes Put Option is $%.2f ', self.vega_put)

        return self.vega_call, self.vega_put


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
    pricer_ = BlackScholes('TSLA', datetime.datetime(2021, 8, 31), 1000)
    call_price, put_price = pricer_.calculate_prices()
