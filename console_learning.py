import logging

import argparse
import matplotlib.pyplot as plt

from learning.learning import Learning
from data import store as store
from utils import ui, logger


logger.get_logger(logging.WARNING, logfile='')

class Interface:
    def __init__(self, ticker: str, days: int = 1000, exit: bool = False):
        if not store.is_ticker(ticker):
            raise ValueError('Invalid ticker')

        self.ticker = ticker.upper()
        self.days = days
        self.exit = exit

        self.learning = Learning(ticker=self.ticker, days=self.days)

        self.main_menu()

    def main_menu(self) -> None:
        self.commands = [
            {'menu': 'Change Ticker', 'function': self.select_ticker, 'condition': 'self.ticker', 'value': 'self.ticker'},
            {'menu': 'Days', 'function': self.select_days, 'condition': 'True', 'value': 'self.days'},
            {'menu': 'Run Model', 'function': self.run_model, 'condition': '', 'value': ''},
        ]

        # Create the menu
        menu_items = {str(i+1): f'{self.commands[i]["menu"]}' for i in range(len(self.commands))}

        # Update menu items with dynamic info
        def update(menu: dict) -> None:
            for i, item in enumerate(self.commands):
                if item['condition'] and item['value']:
                    menu[str(i+1)] = f'{self.commands[i]["menu"]}'
                    if eval(item['condition']):
                        menu[str(i+1)] += f' ({eval(item["value"])})'

        while not self.exit:
            update(menu_items)

            selection = ui.menu(menu_items, 'Available Operations', 0, len(menu_items))
            if selection > 0:
                self.commands[selection-1]['function']()
            else:
                self.exit = True

    def select_ticker(self):
        valid = False

        while not valid:
            ticker = input('Please enter symbol, or 0 to cancel: ').upper()
            if ticker != '0':
                valid = store.is_ticker(ticker)
                if valid:
                    self.ticker = ticker
                    self.learning = Learning(ticker=self.ticker, days=self.days)
                else:
                    ui.print_error('Invalid ticker symbol. Try again or select "0" to cancel')
            else:
                break

    def select_days(self):
        self.days = 0
        while self.days < 30:
            self.days = ui.input_integer('Enter number of days', 30, 9999)

        self.learning = Learning(ticker=self.ticker, days=self.days)

    def run_model(self):
        self.learning.run()
        self.plot()

    def plot(self):
        real_data = self.learning.history[-self.learning.test_size:].reset_index()
        plots = [row for row in self.learning.prediction.itertuples(index=False)]

        plt.figure(figsize=(18, 8))
        for item in plots:
            plt.plot(item, color= 'green')

        plt.plot(real_data['close'], color='grey')
        plt.title('Close')
        plt.show()


def main():
    parser = argparse.ArgumentParser(description='Learning model')
    parser.add_argument('-t', '--ticker', metavar='ticker', help='Run using ticker')
    parser.add_argument('-d', '--days', metavar='days', help='Days to run analysis', default=1000)
    parser.add_argument('-x', '--exit', help='Run trend analysis then exit (only valid with -t)', action='store_true')

    command = vars(parser.parse_args())
    if command['ticker']:
        Interface(tickers=command['ticker'], days=int(command['days']), exit=command['exit'])
    else:
        Interface(ticker='AAPL', days=int(command['days']))


if __name__ == '__main__':
    main()
