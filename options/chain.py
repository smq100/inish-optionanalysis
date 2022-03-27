import pandas as pd

import pandas as pd

from data import store as store
from data import store as store
from utils import ui, logger

_logger = logger.get_logger()


class Chain:
    def __init__(self, ticker: str):
        if not store.is_ticker(ticker):
            raise ValueError('Not a valid ticker')

        self.ticker: str = ticker.upper()
        self.expire: str = ''
        self.product: str = ''
        self.chain: pd.DataFrame = pd.DataFrame()

        # Fetch the company info so we can used a cached version on subsequent calls (uselast=True)
        store.get_company(ticker, live=True, test=True)

    def get_expiry(self) -> tuple[str]:
        return store.get_option_expiry(self.ticker, uselast=True)

    def get_chain(self, product: str) -> pd.DataFrame:
        self.product = product
        value = store.get_option_chain(self.ticker, uselast=True)(date=self.expire)

        if product == 'call':
            self.chain = value.calls
        elif product == 'put':
            self.chain = value.puts
        else:
            self.chain = pd.DataFrame()

        return self.chain

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
