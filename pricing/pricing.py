'''
Pricing calculation based on https://github.com/shashank-khanna/Option-Pricing
Greeks calculation based on https://aaronschlegel.me/measure-sensitivity-derivatives-greeks-python.html
'''

import abc
from abc import ABC
import datetime as dt

import numpy as np
import pandas as pd

from data import store as store
from utils import logger


_logger = logger.get_logger()


class Pricing(ABC):
    def __init__(self, ticker: str, expiry: dt.datetime, strike: float, dividend: float):
        if not store.is_ticker(ticker):
            raise ValueError(f'Invalid ticker {ticker.upper()}')

        if strike <= 0.0:
            raise ValueError(f'Invalid strike price for {ticker.upper()}')

        self.name = ''
        self.ticker = ticker.upper()
        self.expiry = expiry
        self.strike_price = strike
        self.volatility = 0.0
        self.time_to_maturity = -1.0
        self.risk_free_rate = 0.0
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

        self.underlying_asset_data = pd.DataFrame()

        self.expiry = self.expiry.replace(hour=0, minute=0, second=0, microsecond=0) # Convert time to midnight

        self.calculate_risk_free_rate()
        self.calculate_time_to_maturity()
        self.calculate_volatility()
        self.calculate_spot_price()

    @abc.abstractmethod
    def calculate_price(self, spot_price: float = -1.0, time_to_maturity: float = -1.0, volatility: float = -1.0) -> tuple[float, float]:
        pass

    def is_call_put_parity_maintained(self, call_price: float, put_price: float) -> bool:
        ''' Verify is the Put-Call Pairty is maintained by the two option prices calculated

        :param call_price: <float>
        :param put_price: <float>
        '''
        lhs = call_price - put_price
        rhs = self.spot_price - np.exp(-1 * self.risk_free_rate * self.time_to_maturity) * self.strike_price

        _logger.info(f'{__name__}: Put-Call Parity LHS = {lhs}')
        _logger.info(f'{__name__}: Put-Call Parity RHS = {rhs}',)

        return bool(round(lhs) == round(rhs))

    def calculate_underlying_asset_data(self) -> None:
        '''
        Scan through the web to get historical prices of the underlying asset.
        '''
        if self.underlying_asset_data.empty:
            self.underlying_asset_data = store.get_history(self.ticker, days=365)

            if self.underlying_asset_data.empty:
                s = f'{__name__}: Unable to get historical stock data for {self.ticker}'
                _logger.error(s)
                raise IOError(s)

    def calculate_risk_free_rate(self) -> None:
        '''
        Fetch 3-month Treasury Bill Rate
        '''
        self.risk_free_rate = store.get_treasury_rate()

        _logger.info(f'{__name__}: Risk-free rate = {self.risk_free_rate:.4f}')

    def calculate_time_to_maturity(self) -> None:
        '''
        Calculate TimeToMaturity in decimal Years.
        '''
        if self.expiry < dt.datetime.today():
            s = f'{__name__}: Expiry/Maturity Date is in the past. Please check'
            _logger.error(s)
            raise ValueError(s)

        self.time_to_maturity = (self.expiry - dt.datetime.today()).days / 365.0

        _logger.info(f'{__name__}: Time to maturity = {self.time_to_maturity:.5f}')

    def calculate_volatility(self) -> None:
        '''
        Using historical prices of the underlying asset, calculate volatility.
        '''
        self.calculate_underlying_asset_data()
        self.underlying_asset_data = self.underlying_asset_data.reset_index()
        self.underlying_asset_data = self.underlying_asset_data.set_index('date')
        self.underlying_asset_data['log_returns'] = np.log(self.underlying_asset_data['close'] / self.underlying_asset_data['close'].shift(1))

        daily_std = np.std(self.underlying_asset_data['log_returns'])
        self.volatility = daily_std * np.sqrt(252.0)

        _logger.info(f'{__name__}: Calculated volatility = {self.volatility:.4f}')

    def calculate_spot_price(self) -> None:
        '''
        Get latest price of the underlying asset.
        '''
        self.calculate_underlying_asset_data()
        self.spot_price = self.underlying_asset_data['close'][-1]

        _logger.info(f'{__name__}: Spot price = {self.spot_price:.2f}')

    def calculate_greeks(self, spot_price=-1.0, time_to_maturity=-1.0, volatility=-1.0) -> None:
        self.calculate_delta(spot_price=spot_price, time_to_maturity=time_to_maturity, volatility=volatility)
        self.calculate_gamma(spot_price=spot_price, time_to_maturity=time_to_maturity, volatility=volatility)
        self.calculate_theta(spot_price=spot_price, time_to_maturity=time_to_maturity, volatility=volatility)
        self.calculate_vega(spot_price=spot_price, time_to_maturity=time_to_maturity, volatility=volatility)
        self.calculate_rho(spot_price=spot_price, time_to_maturity=time_to_maturity, volatility=volatility)

    @abc.abstractmethod
    def calculate_delta(self, spot_price: float = -1.0, time_to_maturity: float = -1.0, volatility: float = -1.0) -> tuple[float, float]:
        return 0.0, 0.0

    @abc.abstractmethod
    def calculate_gamma(self, spot_price: float = -1.0, time_to_maturity: float = -1.0, volatility: float = -1.0) -> tuple[float, float]:
        return 0.0, 0.0

    @abc.abstractmethod
    def calculate_theta(self, spot_price: float = -1.0, time_to_maturity: float = -1.0, volatility: float = -1.0) -> tuple[float, float]:
        return 0.0, 0.0

    @abc.abstractmethod
    def calculate_vega(self, spot_price: float = -1.0, time_to_maturity: float = -1.0, volatility: float = -1.0) -> tuple[float, float]:
        return 0.0, 0.0

    @abc.abstractmethod
    def calculate_rho(self, spot_price: float = -1.0, time_to_maturity: float = -1.0, volatility: float = -1.0) -> tuple[float, float]:
        return 0.0, 0.0
