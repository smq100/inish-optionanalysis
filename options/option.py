'''TODO'''

''' yfinance fields
contractSymbol
lastTradeDate
strike
lastPrice
bid
ask
change
percentChange
volume
openInterest
impliedVolatility
inTheMoney
contractSize
currency
'''


from .chain import get_contract
from utils import utils as u


class Option():
    def __init__(self, strike):
        self.ticker = ''
        self.product = ''
        self.strike = strike
        self.expiry = ''
        self.time_to_maturity = 0.0
        self.price = 0.0

        self.contract_symbol = ''
        self.last_trade_date = ''
        self.last_price = 0.0
        self.bid = 0.0
        self.ask = 0.0
        self.change = 0.0
        self.percent_change = 0.0
        self.volume = 0.0
        self.open_interest = 0.0
        self.implied_volatility = 0.0
        self.itm = False
        self.contract_size = ''
        self.currency = ''


    def __str__(self):
        return f'{self.contract_symbol} '\
            f'{self.ticker} '\
            f'{self.product} '\
            f'{self.expiry} '\
            f'${self.strike:.2f}'\
            f'{self.last_trade_date} '\
            f'{self.price} '\
            f'{self.last_price:7.2f} '\
            f'{self.bid} '\
            f'{self.ask} '\
            f'{self.change} '\
            f'{self.percent_change} '\
            f'{self.volume} '\
            f'{self.open_interest} '\
            f'{self.implied_volatility} '\
            f'{self.itm} '\
            f'{self.contract_size} '\
            f'{ self.currency} '\


    def load_option(self, contract_name):
        self.contract_symbol = contract_name
        parsed = u.parse_contract_name(contract_name)

        self.ticker = parsed['ticker']
        self.product = parsed['product']
        self.expiry = parsed['expiry']
        self.strike = parsed['strike']

        contract = get_contract(contract_name)

        self.contract_symbol = str(contract['contractSymbol'])
        self.last_trade_date = str(contract['lastTradeDate'])
        self.strike = float(contract['strike'])
        self.last_price = contract['lastPrice']
        self.bid = contract['bid']
        self.ask = contract['ask']
        self.change = contract['change']
        self.percent_change = contract['percentChange']
        self.volume = contract['volume']
        self.open_interest = contract['openInterest']
        self.implied_volatility = contract['impliedVolatility']
        self.itm = contract['inTheMoney']
        self.contract_size = contract['contractSize']
        self.currency = contract['currency']
