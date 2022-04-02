'''American Pricing Class'''

import datetime as dt
from random import gauss

import numpy as np

import pricing
from .pricing import Pricing
from utils import logger

_logger = logger.get_logger()


class MonteCarlo(Pricing):
    '''
    This class uses Monte-Carlo simulation to calculate prices for American Call and Put Options.

    :param ticker: Ticker of the Underlying Stock asset, ex. 'AAPL', 'TSLA', 'GOOGL', etc.
    :param expiry_date: <datetime.date> ExpiryDate for the option -must be in the future
    :param strike: <float> Strike price of the option. This is the price option holder plans to
    buy underlying asset (for call option) or sell underlying asset (for put option).
    :param dividend: <float> If the underlying asset is paying dividend to stock-holders.

    TODO: Create a separate class to calculate prices using Binomial Trees
    '''

    SIMULATION_COUNT = 100000  # Number of Simulations to be performed for Brownian motion

    def __init__(self, ticker: str, expiry: dt.datetime, strike: float, dividend: float=0.0):
        super().__init__(ticker, expiry, strike, dividend=dividend)

        self.name = pricing.PRICING_METHODS[1]

    def calculate_price(self, spot_price=-1.0, time_to_maturity=-1.0):
        ''' Calculate present-value of of expected payoffs and their average becomes the price of the respective option.
        Calculations are performed based on below equations:

            Ct=PV(E[max(0,PriceAtExpiry−Strike)])

            Pt=PV(E[max(0,Strike−PriceAtExpiry)])

        :return: <float>, <float> Calculated price of Call & Put options
        '''

        if spot_price <= 0.0:
            spot_price = self.spot_price

        call_payoffs, put_payoffs = self._generate_simulations(spot_price)
        discount_factor = np.exp(-1 * self.risk_free_rate * self.time_to_maturity)

        self.price_call = discount_factor * (sum(call_payoffs) / len(call_payoffs))
        self.price_put = discount_factor * (sum(put_payoffs) / len(put_payoffs))

        return self.price_call, self.price_put

    def calculate_delta(self, spot_price=-1.0, time_to_maturity=-1.0):
        '''TODO'''
        return 0.0, 0.0

    def calculate_gamma(self, spot_price=-1.0, time_to_maturity=-1.0):
        '''TODO'''
        return 0.0, 0.0

    def calculate_theta(self, spot_price=-1.0, time_to_maturity=-1.0):
        '''TODO'''
        return 0.0, 0.0

    def calculate_vega(self, spot_price=-1.0, time_to_maturity=-1.0):
        '''TODO'''
        return 0.0, 0.0

    def _generate_asset_price(self, spot_price):
        ''' Calculate predicted Asset Price at the time of Option Expiry date.
        It used a random variable based on Gaus model and then calculate price using the below equation.

            St = S * exp((r− 0.5*σ^2)(T−t)+σT−t√ϵ)

        :return: <float> Expected Asset Price
        '''
        expected_price = spot_price * np.exp(
            (self.risk_free_rate - 0.5 * self.volatility ** 2) * self.time_to_maturity +
            self.volatility * np.sqrt(self.time_to_maturity) * gauss(0.0, 1.0))

        return expected_price

    def _call_payoff(self, expected_price):
        ''' Calculate payoff of the call option at Option Expiry Date assuming the asset price
        is equal to expected price. This calculation is based on below equation:

            Payoff at T = max(0,ExpectedPrice−Strike)

        :param expected_price: <float> Expected price of the underlying asset on Expiry Date
        :return: <float> payoff
        '''
        return max(0, expected_price - self.strike_price)

    def _put_payoff(self, expected_price):
        ''' Calculate payoff of the put option at Option Expiry Date assuming the asset price
        is equal to expected price. This calculation is based on below equation:

            Payoff at T = max(0,Strike-ExpectedPrice)

        :param expected_price: <float> Expected price of the underlying asset on Expiry Date
        :return: <float> payoff
        '''
        return max(0, self.strike_price - expected_price)

    def _generate_simulations(self, spot_price):
        ''' Perform Brownian motion simulation to get the Call & Put option payouts on Expiry Date

        :return: <list of call-option payoffs>, <list of put-option payoffs>
        '''
        call_payoffs, put_payoffs = [], []
        for _ in range(self.SIMULATION_COUNT):
            expected_asset_price = self._generate_asset_price(spot_price)
            call_payoffs.append(self._call_payoff(expected_asset_price))
            put_payoffs.append(self._put_payoff(expected_asset_price))

        return call_payoffs, put_payoffs


if __name__ == '__main__':
    import datetime as dt

    pricer_ = MonteCarlo('TSLA', dt.datetime(2021, 8, 31), 1000)
    call_price, put_price = pricer_.calculate_price()
