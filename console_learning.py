import logging

from learning.predict import Prediction
from data import store as store
from utils import utils as utils


_logger = utils.get_logger(logging.WARNING)

class Interface:
    def __init__(self, ticker='', days=0, exit=False):
        self.ticker = ticker.upper()
        self.days = days
        self.exit = exit

        if not ticker:
            self.main_menu()
        elif store.is_symbol_valid(self.ticker):
            self.main_menu(selection=2)
        else:
            utils.print_error('Invalid ticker specified')

    def main_menu(self, selection=0):
        while True:
            menu_items = {
                '1': 'Specify ticker',
                '2': 'Run Pricing Prediction',
                '0': 'Exit'
            }

            if selection == 0:
                selection = utils.menu(menu_items, 'Select Operation', 0, 2)

            if selection == 1:
                self.select_symbol()
            elif selection == 2:
                self.run_model()
            elif selection == 0:
                break

            if self.exit:
                break

            selection = 0

    def run_model(self):
        if self.ticker:
            predict = Prediction(self.ticker, future=self.days)
            predict.prepare()
            predict.create_model()

            utils.print_message(f'Metrics for {self.ticker}')
            print(f'Accuracy: {predict.accuracy:.3e}')
            print(f'Loss: {predict.loss:.3e}')

            predict.test()
            predict.plot()
        else:
            utils.print_error('Please first specify ticker')

    def select_symbol(self):
        valid = False

        while not valid:
            ticker = input('Please enter ticker, or 0 to cancel: ').upper()
            if ticker != '0':
                valid = store.is_symbol_valid(ticker)
                if not valid:
                    utils.print_error('Invalid ticker. Try again or select "0" to cancel')
            else:
                break

        if valid:
            self.ticker = ticker


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Learning')
    parser.add_argument('-t', '--ticker', help='Run using ticker')
    parser.add_argument('-f', '--future', help='Future days', default=0)
    parser.add_argument('-x', help='Exit after running (only valid with -t)', action='store_true')

    command = vars(parser.parse_args())
    if command['ticker']:
        if command['x']:
            Interface(ticker=command['ticker'], days=int(command['future']), exit=True)
        else:
            Interface(ticker=command['ticker'], days=int(command['future']))
    else:
        Interface()
