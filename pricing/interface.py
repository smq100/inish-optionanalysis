''' TODO '''
import datetime
import pandas as pd
from european import EuropeanPricing


class Interface():
    '''TODO'''
    def __init__(self):
        self.symbol = []
        self.legs = []
        self.strategy = 'long_call'
        self.method = 'black-scholes'
        self.pricer = None
        self.table_value = pd.DataFrame()
        self.table_profit = pd.DataFrame()

        pd.options.display.float_format = '{:,.2f}'.format

    def calculate(self):
        '''TODO'''
        if self._validate():
            if self.method == 'black-scholes':
                self.pricer = EuropeanPricing(self.symbol['ticker'], self.legs[0]['expiry'], self.legs[0]['strike'])
                call_price, put_price = self.pricer.calculate_prices()
                self.table_value = self.pricer.generate_value_table(self.legs[0]['call_put'])
                self.table_profit = self.pricer.generate_profit_table(call_price, self.table_value)
                self.plot_profit()

    def main_menu(self):
        '''Displays opening menu'''

        menu_items = {
            '1': 'Specify Symbol',
            '2': 'Specify Strategy',
            '3': 'Specify Expiry',
            '4': 'Specify Strike',
            '5': 'Calculate',
            '6': 'Plot Value',
            '7': 'Plot Profit',
            '8': 'Exit'
        }

        while True:
            print('\nSelect Option')
            print('---------------------')

            option = menu_items.keys()
            for entry in option:
                print(f'{entry})\t{menu_items[entry]}')

            selection = input('Please select: ')

            if selection == '1':
                self.enter_symbol()
            elif selection == '2':
                self.enter_strategy()
            elif selection == '3':
                self.enter_expiry()
            elif selection == '4':
                self.enter_strike()
            elif selection == '5':
                self.calculate()
            elif selection == '6':
                self.plot_value()
            elif selection == '7':
                self.plot_profit()
            elif selection == '8':
                break
            else:
                print('Unknown operation selected')

    def reset(self):
        '''TODO'''
        self.symbol = []
        self.legs = []

    def set_symbol(self, ticker, volatility=-1, dividend=0.0):
        '''TODO'''
        self.symbol = {'ticker':ticker, 'volitility':volatility, 'dividend':dividend}

    def add_leg(self, quantity, call_put, long_short, strike, expiry_date):
        '''TODO'''
        self.legs.append({'quantity':quantity, 'call_put':call_put, 'long_short':long_short, 'strike': strike, 'expiry': expiry_date})

    def enter_symbol(self):
        '''TODO'''
        selection = input('Please enter symbol: ').upper()
        self.set_symbol(selection)
        self.write_all()

    def enter_strategy(self):
        '''TODO'''
        self.write_all()

    def enter_expiry(self):
        '''TODO'''
        self.write_all()

    def enter_strike(self):
        '''TODO'''
        selection = input('Please enter a strike price: ')
        self.legs[0]['strike'] = float(selection)
        self.write_all()

    def write_all(self):
        '''TODO'''
        print(_delimeter('Configuration', True))
        output = \
            f'Strategy:{self.strategy}, '\
            f'Method:{self.method}'
        print(output)
        output = \
            f'Symbol:{self.symbol["ticker"]}, '\
            f'Volitility:{self.symbol["volitility"]}, '\
            f'Dividend:{self.symbol["dividend"]}'
        print(output)
        output = \
            f'Quantity:{self.legs[0]["quantity"]}, '\
            f'C-P:{self.legs[0]["call_put"]}, '\
            f'L-S:{self.legs[0]["long_short"]}, '\
            f'Strike:${self.legs[0]["strike"]:.2f}, '\
            f'Expiry:{str(self.legs[0]["expiry"])[:10]}'
        print(output)
        print(_delimeter(''))

    def plot_value(self):
        '''TODO'''
        self.write_all()
        print(self.table_value)

    def plot_profit(self):
        '''TODO'''
        self.write_all()
        print(self.table_profit)

    def _validate(self):
        '''TODO'''
        return True

def _delimeter(message, creturn=False):
    '''Common delimeter to bracket output'''
    if creturn:
        output = '\n'
    else:
        output = ''

    if len(message) > 0:
        output += f'***** {message} *****'
    else:
        output += '*****'

    return output

if __name__ == '__main__':
    ui = Interface()
    ui.reset()
    ui.set_symbol('AAPL')
    ui.add_leg(1, 'call', 'long', 130.0, datetime.datetime(2021, 2, 12))

    ui.main_menu()
