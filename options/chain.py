import pandas as pd

import pandas as pd

from data import store as store
from data import store as store
from utils import ui

_logger = ui.get_logger()

class Chain:
    def __init__(self, ticker:str):
        if not store.is_ticker(ticker):
            raise ValueError('Not a valid ticker')

        self.ticker:str = ticker.upper()
        self.expire:str = ''
        self.product:str = ''
        self.chain:pd.DataFrame = None

        # Fetch the company info so we can used a cached version on subsequent calls (uselast=True)
        store.get_company(ticker, live=True, test=True)

    def get_expiry(self) -> tuple[str]:
        return store.get_option_expiry(self.ticker, uselast=True)

    def get_chain(self, product:str) -> pd.DataFrame:
        self.product = product
        value = store.get_option_chain(self.ticker, uselast=True)(date=self.expire)

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
