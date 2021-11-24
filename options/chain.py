import pandas as pd

import pandas as pd

from data import store as store
from data import store as store
from utils import utils

_logger = utils.get_logger()

class Chain:
    def __init__(self, ticker:str):
        if not store.is_ticker(ticker):
            raise ValueError('Not a valid ticker')

        self.ticker:str = ticker.upper()
        self.expire:str = ''
        self.product:str = ''
        self.chain:pd.DataFrame = None

    def get_expiry(self) -> tuple[str]:
        return store.get_option_expiry(self.ticker)

    def get_chain(self, product) -> pd.DataFrame:
        self.product = product
        value = store.get_option_chain(self.ticker)(date=self.expire)

        if product == 'call':
            self.chain = value.calls
        elif product == 'put':
            self.chain = value.puts
        else:
            self.chain = None

        return self.chain

    def get_itm(self) -> int:
        index = -1

        if isinstance(self.chain, pd.DataFrame):
            itm = self.chain.iloc[0]['inTheMoney']
            for index, option in enumerate(self.chain.itertuples()):
                if option.inTheMoney != itm:
                    if itm:
                        index = index - 1 if index > 0 else 0
                    break

        return index
