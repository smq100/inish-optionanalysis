import logging

import matplotlib.pyplot as plt

from analysis.technical import Technical
from analysis.trend import METHOD, SupportResistance
from data import store as store
from utils import utils as utils


_logger = utils.get_logger(logging.WARNING)

class Interface:
    def __init__(self, ticker:str, days:int=365, run:bool=False, exit:bool=False):
        self.ticker = ticker.upper()
        self.days = days
        self.run = run
        self.technical:Technical = None
        self.tickers:list[str] = []

        if store.is_ticker(ticker.upper()):
            if self.run:
                self.show_trend()
            else:
                self.technical = Technical(self.ticker, None, 365)
                self.main_menu()
        else:
            utils.print_error(f'Invalid ticker: {self.ticker}')
            self.ticker = ''
            self.run = False
            self.main_menu()

    def main_menu(self):
        while True:
            menu_items = {
                '1': 'Change Ticker',
                '2': 'Support & Resistance Chart',
                '3': 'Technical Analysis',
                '0': 'Exit'
            }

            if self.technical is not None:
                menu_items['1'] = f'Change Ticker ({self.ticker})'

            selection = utils.menu(menu_items, 'Select Operation', 0, 3)

            if selection == 1:
                self.select_ticker()
            elif selection == 2:
                self.get_trend_parameters()
            elif selection == 3:
                self.select_technical()
            elif selection == 0:
                break

    def select_ticker(self):
        valid = False

        while not valid:
            self.ticker = input('Please enter symbol, or 0 to cancel: ').upper()
            if self.ticker != '0':
                valid = store.is_ticker(self.ticker)
                if valid:
                    self.technical = Technical(self.ticker, None, 365)
                else:
                    utils.print_error('Invalid ticker symbol. Try again or select "0" to cancel')
            else:
                break

    def select_technical(self):
        if self.technical is not None:
            while True:
                menu_items = {
                    '1': 'EMA',
                    '2': 'RSI',
                    '3': 'VWAP',
                    '4': 'MACD',
                    '5': 'Bollinger Bands',
                    '0': 'Done',
                }

                selection = utils.menu(menu_items, 'Select Indicator', 0, 5)

                if selection == 1:
                    interval = utils.input_integer('Enter interval: ', 5, 200)
                    df = self.technical.calc_ema(interval)
                    utils.print_message(f'EMA {interval}')
                    print(f'Yesterday: {df.iloc[-1]:.2f}')
                    self.plot(df, f'EMA {interval}')
                elif selection == 2:
                    df = self.technical.calc_rsi()
                    utils.print_message('RSI')
                    print(f'Yesterday: {df.iloc[-1]:.2f}')
                elif selection == 3:
                    df = self.technical.calc_vwap()
                    utils.print_message('VWAP')
                    print(f'Yesterday: {df.iloc[-1]:.2f}')
                elif selection == 4:
                    df = self.technical.calc_macd()
                    utils.print_message('MACD')
                    print(f'Diff: {df.iloc[-1]["Diff"]:.2f}')
                    print(f'MACD: {df.iloc[-1]["MACD"]:.2f}')
                    print(f'Sig:  {df.iloc[-1]["Signal"]:.2f}')
                elif selection == 5:
                    df = self.technical.calc_bb()
                    utils.print_message('Bollinger Band')
                    print(f'High: {df.iloc[-1]["High"]:.2f}')
                    print(f'Mid:  {df.iloc[-1]["Mid"]:.2f}')
                    print(f'Low:  {df.iloc[-1]["Low"]:.2f}')
                elif selection == 0:
                    break
        else:
            utils.print_error('Please first select a ticker')

    def get_trend_parameters(self):
        if self.technical is not None:
            filename = ''
            method = 'NSQUREDLOGN'

            while True:
                name = filename if filename else 'none'
                menu_items = {
                    '1': f'Number of Days ({self.days})',
                    '2': f'Plot File Name ({name})',
                    '3': 'Analyze',
                    '0': 'Cancel'
                }

                selection = utils.menu(menu_items, 'Select option', 0, 3)

                if selection == 1:
                    self.days = utils.input_integer('Enter number of days: ', 30, 9999)

                if selection == 2:
                    filename = input('Enter filename: ')

                if selection == 3:
                    self.show_trend()
                    break

                if selection == 0:
                    break
        else:
            utils.print_error('Please forst select symbol')

    def show_trend(self):
        sr = SupportResistance(self.ticker, method='NSQUREDLOGN', days=self.days)
        sr.calculate()
        sr.plot(show=False)

        sr = SupportResistance(self.ticker, method='NCUBED', days=self.days)
        sr.calculate()
        sr.plot(show=False)

        sr = SupportResistance(self.ticker, method='HOUGHLINES', days=self.days)
        sr.calculate()
        sr.plot(show=False)

        sr = SupportResistance(self.ticker, method='PROBHOUGH', days=self.days)
        sr.calculate()
        sr.plot(show=False)

        plt.show()

    def plot_all(self):
        if self.technical is not None:
            df1 = self.technical.calc_ema(21)
            df1.plot(label='EMA')
            df2 = self.technical.calc_rsi()
            df2.plot(label='RSI')
            df3 = self.technical.calc_vwap()
            df3.plot(label='VWAP')
            df4 = self.technical.calc_macd()
            df4.plot(label='MACD')
            df5 = self.technical.calc_bb()
            df5.plot(label='BB')

            plt.legend()
            plt.show()
        else:
            utils.print_error('Please select symbol')

    def plot(self, df, title=''):
        if df is not None:
            plt.style.use('seaborn-whitegrid')
            plt.grid()
            plt.margins(x=0.1)
            plt.legend()
            if title:
                plt.title(title)
            df.plot()
            plt.show()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Technical Analysis')
    parser.add_argument('-t', '--ticker', help='Run using ticker')
    parser.add_argument('-d', '--days', help='Days to run analysis', default=1000)
    parser.add_argument('-r', help='Run trend analysis (only valid with -t)', action='store_true')

    command = vars(parser.parse_args())
    if command['ticker']:
        Interface(ticker=command['ticker'], days=int(command['days']), run=command['r'])
    else:
        Interface('AAPL')
