'''TODO'''

class Option():
    def __init__(self, strike):
        self.contract_symbol = ''
        self.last_trade_date = ''
        self.strike = strike
        self.price = 0.0
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
        self.time_to_maturity = 0.0
