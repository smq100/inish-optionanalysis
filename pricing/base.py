''' Option Pricing Base Class

Based on https://github.com/shashank-khanna/Option-Pricing
'''

import datetime
import logging

import numpy as np
import pandas as pd
from pandas.tseries.offsets import BDay

from fetcher import get_ranged_data, get_treasury_rate

LOG_LEVEL = logging.WARNING


class BasePricing():
    ''' TODO '''

    LOOK_BACK_WINDOW = 252

    def __init__(self, ticker, expiry_date, strike, dividend=0.0):
        '''

        :param ticker: Ticker of the Underlying Stock asset, ex. 'AAPL', 'TSLA', 'GOOGL', etc.
        :param expiry_date: <datetime.date> ExpiryDate for the option -must be in the future
        :param strike: <float> Strike price of the option. This is the price option holder plans to
        buy underlying asset (for call option) or sell underlying asset (for put option).
        :param dividend: <float> If the underlying asset is paying dividend to stock-holders.
        '''
        self.ticker = ticker
        self.expiry = expiry_date
        self.strike_price = strike
        self.volatility = None  # We will calculate this based on historical asset prices
        self.time_to_maturity = None  # Calculated from expiry date of the option
        self.risk_free_rate = None  # We will fetch current 3-month Treasury rate from the web
        self.spot_price = None
        self.dividend = dividend or 0.0
        self.cost_call = 0.0
        self.cost_put = 0.0
        self.__underlying_asset_data = pd.DataFrame()
        self.__start_date = datetime.datetime.today() - BDay(self.LOOK_BACK_WINDOW)  # How far we need to go to get historical prices

        # Convert expiry time to midnight
        self.expiry = self.expiry.replace(hour=0, minute=0, second=0, microsecond=0)

        # Initialize
        self.initialize_variables()

        logging.basicConfig(format='%(level_name)s: %(message)s', level=LOG_LEVEL)

    def initialize_variables(self):
        '''
        Initialize all the required parameters for Option pricing
        :return:
        '''
        self._set_risk_free_rate()
        self._set_time_to_maturity()
        self._set_volatility()
        self._set_spot_price()

        logging.debug('Initializing variables completed')

    def override_historical_start_date(self, hist_start_date):
        '''
        If we want to change the look_back window for historical prices (used for volatility calculations),
        we can override the look_back window here. Farther back the start date is bigger our window.

        :param hist_start_date:
        :return: <void>
        '''
        self.__start_date = hist_start_date

    def log_parameters(self):
        '''
        Useful method for logging purpose. Prints all the parameter values required for Option pricing.

        :return: <void>
        '''
        logging.info('TICKER = %s', self.ticker)
        logging.info('STRIKE = %.2f', self.strike_price)
        logging.info('DIVIDEND = %.2f', self.dividend)
        logging.info('VOLATILITY = %.2f', self.volatility)
        logging.info('EXPIRY = %s', self.expiry)
        logging.info('TIME TO MATURITY = %.1f', self.time_to_maturity*365)
        logging.info('RISK FREE RATE = %f', self.risk_free_rate)
        logging.info('SPOT PRICE = %.2f', self.spot_price)

    def is_call_put_parity_maintained(self, call_price, put_price):
        ''' Verify is the Put-Call Pairty is maintained by the two option prices calculated by us.

        :param call_price: <float>
        :param put_price: <float>
        :return: True, if Put-Call parity is maintained else False
        '''
        lhs = call_price - put_price
        rhs = self.spot_price - np.exp(-1 * self.risk_free_rate * self.time_to_maturity) * self.strike_price

        logging.info('Put-Call Parity LHS = %f', lhs)
        logging.info('Put-Call Parity RHS = %f', rhs)

        return bool(round(lhs) == round(rhs))

    def _set_risk_free_rate(self):
        '''
        Fetch 3-month Treasury Bill Rate from the web. Please check module stock_analyzer.data_fetcher for details

        :return: <void>
        '''
        self.risk_free_rate = get_treasury_rate()  # / 100?
        logging.info('Risk Free Rate = %d', self.risk_free_rate)


    def _set_time_to_maturity(self):
        '''
        Calculate TimeToMaturity in Years. It is calculated in terms of years using below formula,

            (ExpiryDate - CurrentDate).days / 365
        :return: <void>
        '''
        if self.expiry < datetime.datetime.today():
            logging.error('Expiry/Maturity Date is in the past. Please check')
            raise ValueError('Expiry/Maturity Date is in the past. Please check')

        self.time_to_maturity = (self.expiry - datetime.datetime.today()).days / 365.0

        logging.info('Setting Time To Maturity to %d days as Expiry/Maturity Date provided is %s ', self.time_to_maturity, self.expiry)


    def _get_underlying_asset_data(self):
        '''
        Scan through the web to get historical prices of the underlying asset.
        Please check module stock_analyzer.data_fetcher for details
        :return:
        '''
        if self.__underlying_asset_data.empty:
            logging.debug('Getting historical stock data for %s; used to calculate volatility in this asset', self.ticker)

            self.__underlying_asset_data = get_ranged_data(self.ticker, self.__start_date, None, use_quandl=False)

            if self.__underlying_asset_data.empty:
                logging.error('Unable to get historical stock data')
                raise IOError(f'Unable to get historical stock data for {self.ticker}!')


    def _set_volatility(self):
        '''
        Using historical prices of the underlying asset, calculate volatility.
        :return:
        '''
        self._get_underlying_asset_data()
        self.__underlying_asset_data.reset_index(inplace=True)
        self.__underlying_asset_data.set_index('Date', inplace=True)
        self.__underlying_asset_data['log_returns'] = np.log(self.__underlying_asset_data['Close'] / self.__underlying_asset_data['Close'].shift(1))
        d_std = np.std(self.__underlying_asset_data.log_returns)
        std = d_std * 252 ** 0.5

        logging.info('Annualized Volatility calculated is {:f} '.format(std))

        self.volatility = std


    def _set_spot_price(self):
        '''
        Get latest price of the underlying asset.
        :return:
        '''
        self._get_underlying_asset_data()
        self.spot_price = self.__underlying_asset_data['Close'][-1]
