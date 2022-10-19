import logging
from dataclasses import asdict

import argparse
import matplotlib.pyplot as plt

import pandas as pd
from learning.lstm_base import LSTM_Base, Parameters
from learning.lstm_predict import LSTM_Predict
from learning.lstm_test import LSTM_Test

from data import store as store
from analysis.technical import Technical
from utils import ui, logger
from utils.math import RangeValue


logger.get_logger(logging.WARNING, logfile='')


class Interface:
    def __init__(self, ticker: str, days: int = 1000, exit: bool = False):
        if not store.is_ticker(ticker):
            raise ValueError('Invalid ticker')

        self.ticker: str = ticker.upper()
        self.days: int = days
        self.exit: bool = exit
        self.parameters: Parameters = Parameters()
        self.lstm: LSTM_Base

        self.main_menu()

    def main_menu(self) -> None:
        self.commands = [
            {'menu': 'Change Ticker', 'function': self.select_ticker, 'condition': 'self.ticker', 'value': 'self.ticker'},
            {'menu': 'Run Test (price)', 'function': self.run_test_history, 'condition': '', 'value': ''},
            {'menu': 'Run Test (averages)', 'function': self.run_test_averages, 'condition': '', 'value': ''},
            {'menu': 'Run Prediction (history)', 'function': self.run_prediction_history, 'condition': '', 'value': ''},
            {'menu': 'Days', 'function': self.select_days, 'condition': 'True', 'value': 'self.days'},
            {'menu': 'Parameters', 'function': self.change_parameters, 'condition': '', 'value': ''},
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
                else:
                    ui.print_error('Invalid ticker symbol. Try again or select "0" to cancel')
            else:
                break

    def select_days(self):
        self.days = 0
        while self.days < 30:
            self.days = ui.input_integer('Enter number of days', 30, 9999)

    def change_parameters(self):
        item = ui.menu_from_dataclass(self.parameters, 'Available Parameters')
        if item[0]:
            if type(item[2].value) == int:
                value = ui.input_integer(f"Enter new value for '{item[1]}'", item[2].minimum, item[2].maximum)
            elif type(item[2].value) == float:
                value = ui.input_float(f"Enter new value for '{item[1]}'", item[2].minimum, item[2].maximum)
            else:
                raise ValueError('Unknown type')

            v:RangeValue = getattr(self.parameters, item[0])
            v.value = value

    def run_test_history(self):
        history = store.get_history(self.ticker, days=self.days)
        inputs = ['open', 'high', 'low', 'volume', 'close']
        self.lstm = LSTM_Test(self.ticker, history, inputs, self.days, self.parameters)
        self.lstm.run()
        self.plot_test([], 'History')

    def run_test_averages(self):
        history = store.get_history(self.ticker, days=self.days)
        ta = Technical(self.ticker, history, self.days)
        sma15 = ta.calc_sma(15)
        sma50 = ta.calc_sma(50)
        sma200 = ta.calc_sma(200)
        history = pd.concat([history, sma15, sma50, sma200], axis=1)
        inputs = ['sma_15', 'sma_50', 'sma_200']
        self.lstm = LSTM_Test(self.ticker, history, inputs, self.days, self.parameters)
        self.lstm.run()
        self.plot_test(inputs, 'Averages')

    def run_prediction_history(self):
        history = store.get_history(self.ticker, days=self.days)
        inputs = ['open', 'high', 'low', 'volume', 'close']
        self.lstm = LSTM_Predict(self.ticker, history, inputs, self.days, self.parameters)
        self.lstm.run()
        self.plot_prediction()

    def plot_test(self, items:list[str], title: str = 'Plot'):
        history = self.lstm.history[-self.lstm.test_size:].reset_index()

        plt.figure(figsize=(18, 8))
        plt.title(title)
        plt.plot(self.lstm.prediction, label='prediction', color= 'black')
        plt.plot(history['close'], linestyle='--', label='close', color='grey')

        color_index = 0
        colors = 'bgrcmk'
        for item in items:
            plt.plot(history[item], label=item, color=colors[color_index])
            color_index += 1

        plt.legend(loc='best')
        plt.show()

    def plot_prediction(self, title: str = 'Close'):
        history = self.lstm.history[-self.lstm.test_size:].reset_index()
        plots = [row for row in self.lstm.prediction.itertuples(index=False)]

        plt.figure(figsize=(18, 8))

        plt.plot(history['close'], linestyle='--', label='close', color='grey')
        for item in plots:
            plt.plot(item, color= 'green')

        plt.title(title)
        plt.show()


def main():
    parser = argparse.ArgumentParser(description='Learning model')
    parser.add_argument('-t', '--ticker', metavar='ticker', help='Run using ticker')
    parser.add_argument('-d', '--days', metavar='days', help='Days to run analysis', default=1000)
    parser.add_argument('-x', '--exit', help='Run trend analysis then exit (only valid with -t)', action='store_true')

    command = vars(parser.parse_args())
    if command['ticker']:
        Interface(ticker=command['ticker'], days=int(command['days']), exit=command['exit'])
    else:
        Interface(ticker='AAPL', days=int(command['days']))


if __name__ == '__main__':
    main()
