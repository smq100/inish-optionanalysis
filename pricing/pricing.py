''' Abstract Option Pricing Base Class

Pricing calculation based on https://github.com/shashank-khanna/Option-Pricing
Greeks calculation based on https://aaronschlegel.me/measure-sensitivity-derivatives-greeks-python.html
'''

import abc
from abc import ABC
import datetime as dt

import numpy as np
import pandas as pd

from data import store as store
from utils import utils


_logger = utils.get_logger()


class Pricing(ABC):
    LOOK_BACK_WINDOW = 365

    def __init__(self, ticker, expiry, strike, dividend=0.0):
        '''
        :param ticker: Ticker of the Underlying Stock asset, ex. 'AAPL', 'TSLA', 'GOOGL', etc.
        :param expiry_date: <datetime.date> ExpiryDate for the option -must be in the future
        :param strike: <float> Strike price of the option. This is the price option holder plans to
        buy underlying asset (for call option) or sell underlying asset (for put option).
        :param dividend: <float> If the underlying asset is paying dividend to stock-holders.
        '''
        self.name = ''
        self.ticker = ticker
        self.expiry = expiry
        self.strike_price = strike
        self.volatility = None  # We will calculate this based on historical asset prices
        self.time_to_maturity = None  # Calculated from expiry date of the option
        self.risk_free_rate = None  # We will fetch current 3-month Treasury rate from the web
        self.spot_price = 0.0
        self.dividend = dividend or 0.0
        self.price_call = 0.0
        self.price_put = 0.0

        self.delta_call = 0.0
        self.delta_put = 0.0
        self.gamma_call = 0.0
        self.gamma_put = 0.0
        self.theta_call = 0.0
        self.theta_put = 0.0
        self.vega_call = 0.0
        self.vega_put = 0.0
        self.rho_call = 0.0
        self.rho_put = 0.0

        self._underlying_asset_data = pd.DataFrame()

        # Convert time to midnight
        self.expiry = self.expiry.replace(hour=0, minute=0, second=0, microsecond=0)

        # Initialize
        if store.is_ticker(ticker):
            self.initialize_variables()
        else:
            raise IOError('Problem fetching ticker information')

    @abc.abstractmethod
    def calculate_price(self, spot_price:float=-1.0, time_to_maturity:float=-1.0, volatility:float=-1.0) -> tuple[float, float]:
        pass

    def calculate_greeks(self, spot_price=-1.0, time_to_maturity=-1.0, volatility=-1.0) -> None:
        self.calculate_delta(spot_price=spot_price, time_to_maturity=time_to_maturity, volatility=volatility)
        self.calculate_gamma(spot_price=spot_price, time_to_maturity=time_to_maturity, volatility=volatility)
        self.calculate_theta(spot_price=spot_price, time_to_maturity=time_to_maturity, volatility=volatility)
        self.calculate_vega(spot_price=spot_price, time_to_maturity=time_to_maturity, volatility=volatility)
        self.calculate_rho(spot_price=spot_price, time_to_maturity=time_to_maturity, volatility=volatility)

    @abc.abstractmethod
    def calculate_delta(self, spot_price:float=-1.0, time_to_maturity:float=-1.0, volatility:float=-1.0) -> tuple[float, float]:
        return 0.0, 0.0

    @abc.abstractmethod
    def calculate_gamma(self, spot_price:float=-1.0, time_to_maturity:float=-1.0, volatility:float=-1.0) -> tuple[float, float]:
        return 0.0, 0.0

    @abc.abstractmethod
    def calculate_theta(self, spot_price:float=-1.0, time_to_maturity:float=-1.0, volatility:float=-1.0) -> tuple[float, float]:
        return 0.0, 0.0

    @abc.abstractmethod
    def calculate_vega(self, spot_price:float=-1.0, time_to_maturity:float=-1.0, volatility:float=-1.0) -> tuple[float, float]:
        return 0.0, 0.0

    def initialize_variables(self) -> None:
        self._calc_risk_free_rate()
        self._calc_time_to_maturity()
        self._calc_volatility()
        self._calc_spot_price()

    def is_call_put_parity_maintained(self, call_price:float, put_price:float) -> bool:
        ''' Verify is the Put-Call Pairty is maintained by the two option prices calculated by us.

        :param call_price: <float>
        :param put_price: <float>
        :return: True, if Put-Call parity is maintained else False
        '''
        lhs = call_price - put_price
        rhs = self.spot_price - np.exp(-1 * self.risk_free_rate * self.time_to_maturity) * self.strike_price

        _logger.info(f'{__name__}: Put-Call Parity LHS = %f', lhs)
        _logger.info(f'{__name__}: Put-Call Parity RHS = %f', rhs)

        return bool(round(lhs) == round(rhs))

    def _calc_underlying_asset_data(self) -> None:
        '''
        Scan through the web to get historical prices of the underlying asset.
        Please check module stock_analyzer.data_fetcher for details
        :return:
        '''
        if self._underlying_asset_data.empty:
            history = store.get_history(self.ticker, days=self.LOOK_BACK_WINDOW)
            self._underlying_asset_data = pd.DataFrame(history)

            if self._underlying_asset_data.empty:
                _logger.error(f'{__name__}: Unable to get historical stock data')
                raise IOError(f'Unable to get historical stock data for {self.ticker}!')

    def _calc_risk_free_rate(self) -> None:
        '''
        Fetch 3-month Treasury Bill Rate from the web. Please check module stock_analyzer.data_fetcher for details

        :return: <void>
        '''
        self.risk_free_rate = store.get_treasury_rate()
        _logger.info(f'{__name__}: Risk-free rate = {self.risk_free_rate:.4f}')

    def _calc_time_to_maturity(self) -> None:
        '''
        Calculate TimeToMaturity in Years. It is calculated in terms of years using below formula,

            (ExpiryDate - CurrentDate).days / 365
        :return: <void>
        '''
        if self.expiry < dt.datetime.today():
            _logger.error(f'{__name__}: Expiry/Maturity Date is in the past. Please check')
            raise ValueError('Expiry/Maturity Date is in the past. Please check')

        self.time_to_maturity = (self.expiry - dt.datetime.today()).days / 365.0
        _logger.info(f'{__name__}: Time to maturity = {self.time_to_maturity:.5f}')

    def _calc_volatility(self) -> None:
        '''
        Using historical prices of the underlying asset, calculate volatility.
        :return:
        '''
        self._calc_underlying_asset_data()
        self._underlying_asset_data.reset_index(inplace=True)
        self._underlying_asset_data.set_index('date', inplace=True)
        self._underlying_asset_data['log_returns'] = np.log(self._underlying_asset_data['close'] / self._underlying_asset_data['close'].shift(1))

        d_std = np.std(self._underlying_asset_data.log_returns)
        std = d_std * 252 ** 0.5

        self.volatility = std
        _logger.info(f'{__name__}: Calculated volatility = {self.volatility:.4f}')

    def _calc_spot_price(self) -> None:
        '''
        Get latest price of the underlying asset.
        :return:
        '''
        self._calc_underlying_asset_data()
        self.spot_price = self._underlying_asset_data['close'][-1]
        _logger.info(f'{__name__}: Spot price = {self.spot_price:.2f}')
