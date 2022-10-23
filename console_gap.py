import time
import threading
import logging

import argparse
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from tabulate import tabulate

from analysis.gap import Gap
from data import store as store
from utils import ui, logger


logger.get_logger(logging.WARNING, logfile='')


class Interface:
    def __init__(self, list: str = '', days: int = 100, disp_calc: bool = False, disp_plot: bool = False, disp_anly: bool = False):
        self.list = list.upper()
        self.days: int = days
        self.disp_calc: bool = disp_calc
        self.disp_plot: bool = disp_plot
        self.disp_anly: bool = disp_anly
        self.tickers: list[str] = []
        self.results: list[pd.DataFrame] = []
        self.analysis: pd.DataFrame = pd.DataFrame()
        self.commands: list[dict] = []
        self.gap: Gap | None = None
        self.task: threading.Thread
        self.use_cache: bool = False

        if list:
            self.m_select_tickers(list)

        if self.tickers:
            self.m_calculate_gap()
            self.main_menu()
        else:
            self.main_menu()

    def main_menu(self) -> None:
        self.commands = [
            {'menu': 'Select Tickers', 'function': self.m_select_tickers, 'condition': 'self.tickers', 'value': 'self.list'},
            {'menu': 'Days', 'function': self.m_select_days, 'condition': 'True', 'value': 'self.days'},
            {'menu': 'Calculate', 'function': self.m_calculate_gap, 'condition': 'not self.analysis.empty', 'value': 'len(self.analysis)'},
            {'menu': 'Show Analysis', 'function': self.m_show_analysis, 'condition': '', 'value': ''},
            {'menu': 'Show Results', 'function': self.m_show_results, 'condition': '', 'value': ''},
            {'menu': 'Show Plot', 'function': self.m_show_plot, 'condition': '', 'value': ''}
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

        loop = True
        while loop:
            update(menu_items)

            selection = ui.menu(menu_items, 'Available Operations', 0, len(menu_items))
            if selection > 0:
                self.commands[selection-1]['function']()
            else:
                loop = False

    def m_select_tickers(self, list='') -> None:
        if not list:
            list = ui.input_text('Enter exchange, index, ticker, or \'every\'')

        self.list = list.upper()

        if self.list == 'EVERY':
            self.tickers = store.get_tickers('every')
            self.list = list.lower()
        elif store.is_exchange(list):
            self.tickers = store.get_exchange_tickers(self.list)
            self.use_cache = True
        elif store.is_index(list):
            self.tickers = store.get_index_tickers(self.list)
            self.use_cache = True
        elif store.is_ticker(list):
            self.tickers = [self.list]
        else:
            self.tickers = []
            self.list = ''
            ui.print_error(f'List \'{list}\' is not valid')

    def m_select_days(self):
        self.days = 0
        while self.days < 30:
            self.days = ui.input_integer('Enter number of days', 30, 9999)

    def m_calculate_gap(self) -> None:
        self.results = []

        if self.tickers:
            self.gap = Gap(self.tickers, self.list, days=self.days)
            if len(self.tickers) > 1:
                self.task = threading.Thread(target=self.gap.calculate, kwargs={'use_cache': self.use_cache})
                self.task.start()

                # Show thread progress. Blocking while thread is active
                self.show_progress()

                if self.gap.task_state == 'Done':
                    if self.gap.cache_used:
                        ui.print_message(f'{len(self.gap.results)} symbols identified. Cached results from {self.gap.cache_date} used')
                    else:
                        ui.print_message(f'{len(self.gap.results)} symbols identified in {self.gap.task_time:.1f} seconds', pre_creturn=1)
            else:
                self.gap.calculate(use_cache=self.use_cache)

                if self.disp_calc:
                    self.m_show_results()

                if self.disp_plot:
                    self.m_show_plot()

            self.calculate_analysis()

            if self.disp_anly:
                self.m_show_analysis()
        else:
            ui.print_error('Enter a ticker before calculating')

    def calculate_analysis(self) -> None:
        self.analysis = pd.DataFrame()
        if len(self.gap.results) > 0:
            self.gap.analyze()
            self.analysis = self.gap.analysis

    def m_show_results(self) -> None:
        if self.gap:
            if len(self.tickers) > 1:
                ticker = ui.input_text('Enter ticker')
            else:
                ticker = self.tickers[0]

            index = self._get_index(ticker)
            if index < 0:
                ui.print_error('Ticker not found in results')
            else:
                pass
        else:
            ui.print_error(f'Must first run calculation', post_creturn=1)

    def m_show_analysis(self) -> None:
        if self.gap:
            if len(self.analysis) > 0:
                pass
            else:
                ui.print_message(f'No gaps found', post_creturn=1)
        else:
            ui.print_error(f'Must first run calculation', post_creturn=1)

    def m_show_plot(self, show: bool = True, cursor: bool = True) -> None:
        if len(self.tickers) > 0:
            pass
        else:
            ui.print_error(f'No ticker(s) specified', post_creturn=1)

    def show_progress(self) -> None:
        while not self.gap.task_state:
            pass

        if self.gap.task_state == 'None':
            print()
            prefix = 'Fetching Data'
            ui.progress_bar(0, 0, prefix=prefix, suffix=self.gap.task_message, reset=True)

            while self.gap.task_state == 'None':
                time.sleep(ui.PROGRESS_SLEEP)
                total = self.gap.task_total
                completed = self.gap.task_completed
                ticker = self.gap.task_ticker
                ui.progress_bar(completed, total, prefix=prefix, ticker=ticker, success=-1)

            print()
        elif self.gap.task_state == 'Done':
            pass  # Nothing processed. Cached results used
        else:
            ui.print_message(f'{self.gap.task_state}')

    def _get_index(self, ticker: str):
        index = -1
        if self.gap:
            for i, item in enumerate(self.gap.results):
                if ticker.upper() == item.index.name:
                    index = i

        return index


def main():
    parser = argparse.ArgumentParser(description='Gap Analysis')
    parser.add_argument('-t', '--tickers', metavar='tickers', help='Specify a ticker or list')
    parser.add_argument('-d', '--days', metavar='days', help='Days to run analysis', default=100)
    parser.add_argument('-s', '--show_calc', help='Show calculation results', action='store_true')
    parser.add_argument('-S', '--show_plot', help='Show results plot', action='store_true')

    command = vars(parser.parse_args())
    if command['tickers']:
        Interface(list=command['tickers'], days=int(command['days']), disp_calc=command['show_calc'], disp_plot=command['show_plot'])
    else:
        Interface()


if __name__ == '__main__':
    main()
