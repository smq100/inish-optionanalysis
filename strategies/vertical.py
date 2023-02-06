import datetime as dt

import pandas as pd

from base import Threaded
import strategies as s
from strategies.strategy import Strategy
from utils import math as m
from utils import ui, logger


_logger = logger.get_logger()


class Vertical(Strategy):
    def __init__(self,
                 ticker: str,
                 product: s.ProductType,
                 direction: s.DirectionType,
                 strike: float,
                 *,
                 width: int,
                 quantity: int = 1,
                 expiry: dt.datetime = dt.datetime.now(),
                 volatility: tuple[float, float] = (-1.0, 0.0),
                 load_contracts: bool = False):

        if width < 1:
            raise ValueError('Invalid width')

        # Initialize the base strategy
        super().__init__(
            ticker,
            product,
            direction,
            strike,
            width1=width,
            width2=0,
            quantity=quantity,
            expiry=expiry,
            volatility=volatility,
            load_contracts=load_contracts)

        self.type = s.StrategyType.Vertical

        # Add legs. Long leg is always first
        # Width1 is dollar amounts when not loading contracts
        # Width1 is indexes into the chain when loading contracts
        # Strike price will be overriden when loading contracts
        if product == s.ProductType.Call:
            if direction == s.DirectionType.Long:
                self.add_leg(self.quantity, self.product, s.DirectionType.Long, self.strike, self.expiry, self.volatility)
                self.add_leg(self.quantity, self.product, s.DirectionType.Short, self.strike + self.width1, self.expiry, self.volatility)
            else:
                self.add_leg(self.quantity, self.product, s.DirectionType.Long, self.strike + self.width1, self.expiry, self.volatility)
                self.add_leg(self.quantity, self.product, s.DirectionType.Short, self.strike, self.expiry, self.volatility)
        else:
            if direction == s.DirectionType.Long:
                self.add_leg(self.quantity, self.product, s.DirectionType.Long, self.strike + self.width1, self.expiry, self.volatility)
                self.add_leg(self.quantity, self.product, s.DirectionType.Short, self.strike, self.expiry, self.volatility)
            else:
                self.add_leg(self.quantity, self.product, s.DirectionType.Long, self.strike, self.expiry, self.volatility)
                self.add_leg(self.quantity, self.product, s.DirectionType.Short, self.strike + self.width1, self.expiry, self.volatility)

        if load_contracts:
            items = self.fetch_contracts(self.expiry, strike=self.strike)
            if len(items) == 2:
                if not self.legs[0].option.load_contract(items[0][0], items[0][1]):
                    self.error = f'Unable to load leg 0 {product} contract for {self.legs[0].company.ticker}'
                elif not self.legs[1].option.load_contract(items[1][0], items[1][1]):
                    self.error = f'Unable to load leg 1 {product} contract for {self.legs[1].company.ticker}'

                if self.error:
                    _logger.warning(f'Error fetching contracts for {self.ticker}: {self.error}')
            else:
                # Not a fatal error
                _logger.warning(f'Error fetching contracts for {self.ticker}. Using calculated values')

    def __str__(self):
        return f'{self.type.value} {self.product.value} {self.analysis.credit_debit.value} spread'.lower()

    def fetch_contracts(self, expiry: dt.datetime, strike: float = -1.0) -> list[tuple[str, pd.DataFrame]]:
        expiry_tuple = self.chain.get_expiry()

        # Calculate expiry
        if not expiry_tuple:
            raise ValueError('No option expiry dates')

        # Get the closest date to expiry
        expiry_list = [dt.datetime.strptime(item, ui.DATE_FORMAT_YMD) for item in expiry_tuple]
        self.expiry = min(expiry_list, key=lambda d: abs(d - expiry))
        self.chain.expire = self.expiry

        # Get the option chain
        items = []
        chain_index = -1
        product = self.legs[0].option.product
        options = self.chain.get_chain(product)

        # Calculate the index into the option chain
        if options.empty:
            _logger.warning(f'Error fetching option chain for {self.ticker}')
        elif strike <= 0.0:
            chain_index = self.chain.get_index_itm()
        else:
            chain_index = self.chain.get_index_strike(strike)

        # Add the long option contract
        if chain_index < 0:
            _logger.warning(f'No option index found for {self.ticker} leg 1')
        elif chain_index >= len(options):
            _logger.warning(f'Insufficient options for {self.ticker} leg 1')
        else:
            contract = options.iloc[chain_index]['contractSymbol']
            items.append((contract, options))

        # Calculate the index to the short option
        if not items:
            pass
        elif self.product == s.ProductType.Call:
            if self.direction == s.DirectionType.Long:
                chain_index += self.width1
            else:
                chain_index -= self.width1
        elif self.direction == s.DirectionType.Long:
            chain_index -= self.width1
        else:
            chain_index += self.width1

        # Add the short option contract
        if not items:
            pass
        elif chain_index < 0:
            items = []
            _logger.warning(f'No option index found for {self.ticker} leg 2')
        elif chain_index >= len(options):
            items = []
            _logger.warning(f'Insufficient options for {self.ticker} leg 2')
        else:
            contract = options.iloc[chain_index]['contractSymbol']
            items.append((contract, options))

        return items

    @Threaded.threaded
    def analyze(self) -> None:
        if self.validate():
            self.task_state = 'None'
            self.task_message = self.legs[0].option.ticker

            # Ensure all legs use the same min, max, step centered around the strike
            range = m.calculate_min_max_step(self.strike)
            self.legs[0].range = self.legs[1].range = range

            self.legs[0].calculate()
            self.legs[1].calculate()

            # Important: Assumes the long leg is the index-0 leg

            self.analysis.total = abs(self.legs[0].option.price_eff - self.legs[1].option.price_eff) * self.quantity

            self.generate_profit_table()
            self.calculate_metrics()
            self.calculate_breakeven()
            self.calculate_pop()
            self.calculate_score()
            self.analysis.summarize()

            _logger.info(f'{self.ticker}: g={self.analysis.max_gain:.2f}, l={self.analysis.max_loss:.2f} b={self.analysis.breakeven[0]:.2f}')
        else:
            _logger.warning(f'Unable to analyze strategy for {self.ticker}: {self.error}')

        self.task_state = 'Done'

    def generate_profit_table(self) -> bool:
        profit = self.legs[0].value_table - self.legs[1].value_table
        profit *= self.quantity

        if self.analysis.credit_debit == s.OutlayType.Credit:
            profit += self.analysis.total
        else:
            profit -= self.analysis.total

        self.analysis.profit_table = profit

        return True

    def calculate_metrics(self) -> bool:
        max_gain = max_loss = 0.0

        debit = (self.analysis.credit_debit == s.OutlayType.Debit)
        if self.product == s.ProductType.Call:
            if debit:
                max_loss = self.analysis.total
                max_gain = (self.quantity * (self.legs[1].option.strike - self.legs[0].option.strike)) - max_loss
                if max_gain < 0.0:
                    max_gain = 0.0  # Debit is more than possible gain!
                self.analysis.sentiment = s.SentimentType.Bullish
            else:
                max_gain = self.analysis.total
                max_loss = (self.quantity * (self.legs[0].option.strike - self.legs[1].option.strike)) - max_gain
                if max_loss < 0.0:
                    max_loss = 0.0  # Credit is more than possible loss!
                self.analysis.sentiment = s.SentimentType.Bearish
        else:
            if debit:
                max_loss = self.analysis.total
                max_gain = (self.quantity * (self.legs[0].option.strike - self.legs[1].option.strike)) - max_loss
                if max_gain < 0.0:
                    max_gain = 0.0  # Debit is more than possible gain!
                self.analysis.sentiment = s.SentimentType.Bearish
            else:
                max_gain = self.analysis.total
                max_loss = (self.quantity * (self.legs[1].option.strike - self.legs[0].option.strike)) - max_gain
                if max_loss < 0.0:
                    max_loss = 0.0  # Credit is more than possible loss!
                self.analysis.sentiment = s.SentimentType.Bullish

        self.analysis.max_gain = max_gain
        self.analysis.max_loss = max_loss
        self.analysis.upside = max_gain / max_loss if max_loss > 0.0 else 0.0
        self.analysis.score_options = 0.0

        return True

    def calculate_breakeven(self) -> bool:
        if self.analysis.credit_debit == s.OutlayType.Debit:
            breakeven = self.legs[1].option.strike + self.analysis.total
        else:
            breakeven = self.legs[1].option.strike - self.analysis.total

        self.analysis.breakeven = [breakeven]

        return True

    def calculate_pop(self) -> bool:
        self.analysis.pop = 1.0 - (self.analysis.max_gain / abs((self.legs[1].option.strike - self.legs[0].option.strike)))

        return True

    def calculate_score(self) -> bool:
        score = self.analysis.pop + self.analysis.upside
        self.analysis.score_options = score if score >= 0.0 else 0.0

        return True

    def validate(self) -> bool:
        if self.error:
            pass  # Return existing error
        elif len(self.legs) != 2:
            self.error = 'Incorrect number of legs'
        elif self.analysis.credit_debit:
            if self.product == s.ProductType.Call:
                if self.analysis.credit_debit == s.OutlayType.Debit:
                    if self.legs[0].option.strike >= self.legs[1].option.strike:
                        self.error = f'Incorrect option legs configuration (1) ({self.legs[0].option.strike:.2f} >= {self.legs[1].option.strike:.2f})'
                elif self.legs[1].option.strike >= self.legs[0].option.strike:
                    self.error = f'Incorrect option legs configuration (2) ({self.legs[1].option.strike:.2f} >= {self.legs[0].option.strike:.2f})'
            else:
                if self.analysis.credit_debit == s.OutlayType.Debit:
                    if self.legs[1].option.strike >= self.legs[0].option.strike:
                        self.error = f'Incorrect option legs configuration (3) ({self.legs[1].option.strike:.2f} >= {self.legs[0].option.strike:.2f})'
                elif self.legs[0].option.strike >= self.legs[1].option.strike:
                    self.error = f'Incorrect option legs configuration (4) ({self.legs[0].option.strike:.2f} >= {self.legs[1].option.strike:.2f})'

        return not bool(self.error)


if __name__ == '__main__':
    # import logging
    # logger.get_logger(logging.INFO)
    import math
    from data import store

    pd.options.display.float_format = '{:,.2f}'.format

    ticker = 'AAPL'
    strike = float(math.ceil(store.get_last_price(ticker)))
    vert = Vertical(ticker, s.ProductType.Call, s.DirectionType.Long, strike, width=1)
    vert.analyze()

    print(vert.legs[0])
    print(vert.legs[0].value_table)
