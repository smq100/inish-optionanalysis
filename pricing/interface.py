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
                pass
            elif selection == '2':
                pass
            elif selection == '3':
                pass
            elif selection == '4':
                pass
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

    def set_symbol(self, ticker, volatility=-1, dividend=0.0):
        '''TODO'''
        self.symbol = {'ticker':ticker, 'volitility':volatility, 'dividend':dividend}

    def clear_legs(self):
        '''TODO'''
        self.legs = []

    def add_leg(self, quantity, call_put, long_short, strike, expiry_date):
        '''TODO'''
        self.legs.append({'quantity':quantity, 'call_put':call_put, 'long_short':long_short, 'strike': strike, 'expiry': expiry_date})

    def plot_value(self):
        '''TODO'''
        print('\n***** Value Table *****')
        print(self.table_value)

    def plot_profit(self):
        '''TODO'''
        print('\n***** Profit Table *****')
        print(self.table_profit)

    def _validate(self):
        '''TODO'''
        return True

if __name__ == '__main__':
    ui = Interface()
    ui.clear_legs()
    ui.set_symbol('AAPL')
    ui.add_leg(1, 'call', 'long', 145.0, datetime.datetime(2021, 2, 12))

    ui.main_menu()
