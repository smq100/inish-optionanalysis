import datetime as dt

import pandas as pd

import strategies as s
from data import store as store
from utils import logger

_logger = logger.get_logger()


class Chain:
    def __init__(self, ticker: str):
        if not store.is_ticker(ticker):
            raise ValueError('Not a valid ticker')

        self.ticker: str = ticker.upper()
        self.expire: dt.datetime = dt.datetime.now()
        self.chain: pd.DataFrame = pd.DataFrame()

    def get_expiry(self) -> tuple[str]:
        return store.get_option_expiry(self.ticker)

    def get_chain(self, product: s.ProductType) -> pd.DataFrame:
        if self.chain.empty:
            self.chain = store.get_option_chain(self.ticker, self.expire)

        chain = self.chain[self.chain['type'] == product.name.lower()].copy()

        return chain

    def get_index_itm(self) -> int:
        index = -1

        if not self.chain.empty:
            itm = self.chain.iloc[0]['inTheMoney']
            for index, option in enumerate(self.chain.itertuples()):
                if option.inTheMoney != itm:
                    if itm:
                        index = index - 1 if index > 0 else 0
                    break
        else:
            _logger.warning(f'{__name__}: Empty ITM option chain for {self.ticker}')

        return index

    def get_index_strike(self, strike: float) -> int:
        index = -1

        if not self.chain.empty:
            for index, option in enumerate(self.chain.itertuples()):
                if option.strike >= strike:
                    break
        else:
            _logger.warning(f'{__name__}: Empty Strike option chain for {self.ticker}')

        return index
