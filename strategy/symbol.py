'''TODO'''

class Symbol:
    '''TODO'''

    def __init__(self, ticker, dividend=0.0, volatility=-1.0):
        self.ticker = ticker
        self.dividend = dividend
        self.volatility = volatility
        self.spot = 0.0
        self.short_name = 'unknown'


    def __str__(self):
        output = f'{self.ticker}@${self.spot:.2f}/{self.volatility*100:.1f}%'

        return output
