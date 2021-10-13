import logging

import matplotlib.pyplot as plt

from analysis.trend import SupportResistance
from data import store as store
from utils import utils


_logger = utils.get_logger(logging.WARNING, logfile='')

class Interface:
    def __init__(self, ticker:str, days:int=365, exit:bool=False):
        self.ticker = ticker.upper()
        self.days = days
        self.exit = exit
        self.tickers:list[str] = []

        if store.is_ticker(ticker.upper()):
            if self.exit:
                self.show_trend()
            else:
                self.main_menu()
        else:
            utils.print_error(f'Invalid ticker: {self.ticker}')
            self.ticker = ''
            self.exit = False
            self.main_menu()

    def main_menu(self):
        while True:
            menu_items = {
                '1': 'Change Ticker',
                '2': f'Days ({self.days})',
                '3': 'Support & Resistance Chart',
                '0': 'Exit'
            }

            if self.ticker is not None:
                menu_items['1'] = f'Change Ticker ({self.ticker})'

            selection = utils.menu(menu_items, 'Select Operation', 0, 3)

            if selection == 1:
                self.select_ticker()
            elif selection == 2:
                self.select_days()
            elif selection == 3:
                self.show_trend()
            elif selection == 0:
                self.exit = True

            if self.exit:
                break

    def select_ticker(self):
        valid = False

        while not valid:
            self.ticker = input('Please enter symbol, or 0 to cancel: ').upper()
            if self.ticker != '0':
                valid = store.is_ticker(self.ticker)
                if not valid:
                    utils.print_error('Invalid ticker symbol. Try again or select "0" to cancel')
            else:
                break

    def select_days(self):
        self.days = 0
        while self.days < 30:
            self.days = utils.input_integer('Enter number of days: ', 30, 9999)

    def show_trend(self):
        sr = SupportResistance(self.ticker, method=['NSQUREDLOGN'], days=self.days)
        sr.calculate()
        sr.plot(show=False)

        sr = SupportResistance(self.ticker, method=['NCUBED'], days=self.days)
        sr.calculate()
        sr.plot(show=False)

        sr = SupportResistance(self.ticker, method=['HOUGHLINES'], days=self.days)
        sr.calculate()
        sr.plot(show=False)

        sr = SupportResistance(self.ticker, method=['PROBHOUGH'], days=self.days)
        sr.calculate()
        sr.plot(show=False)

        plt.show()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Technical Analysis')
    parser.add_argument('-t', '--ticker', help='Run using ticker')
    parser.add_argument('-d', '--days', help='Days to run analysis', default=1000)
    parser.add_argument('-x', '--exit',  help='Run trend analysis (only valid with -t) then exit', action='store_true')

    command = vars(parser.parse_args())
    if command['ticker']:
        Interface(ticker=command['ticker'], days=int(command['days']), exit=command['exit'])
    else:
        Interface('AAPL')
