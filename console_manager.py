import time
import threading
import logging
import datetime as dt

import argparse

import data as d
from data import store as store
from data import manager as manager
from utils import ui, logger


CSV_BASEPATH = './output'


logger.get_logger(logging.ERROR)  # , logfile='output')


class Interface:
    def __init__(self, ticker: str = '', update: str = '', quick: bool = False):
        exit = False
        self.ticker = ''
        self.quick = quick
        self.stop = False
        self.commands: list[dict] = []

        if store.is_database_connected():
            if ticker:
                if store.is_ticker(ticker.upper()):
                    self.ticker = ticker.upper()
                    self.stop = True
                else:
                    exit = True
                    ui.print_error(f'Invalid ticker specifed: {ticker}')
            elif update:
                if store.is_list(update):
                    self.ticker = update.upper()
                    self.stop = True
                elif store.is_ticker(update):
                    self.ticker = update.upper()
                    self.stop = True
                else:
                    update = ''
                    exit = True
                    ui.print_error(f'Invalid ticker specifed: {update}')

            self.exchanges: list[str] = store.get_exchanges()
            self.indexes: list[str] = store.get_indexes()
            self.manager: manager.Manager = manager.Manager()
            self.task: threading.Thread

            if not store.is_live_connection():
                ui.print_error('No Internet connection')

            if exit:
                pass
            elif ticker:
                self.main_menu(selection=2)
            elif update:
                self.main_menu(selection=5)
            else:
                self.main_menu()
        else:
            ui.print_error('No databases available')

    def main_menu(self, selection: int = 0) -> None:
        self.commands = [
            {'menu': 'Database Information', 'function': self.m_show_database_information, 'params': '', 'condition': '', 'value': ''},
            {'menu': 'Ticker Information', 'function': self.m_show_ticker_information, 'params': 'self.ticker', 'condition': 'True', 'value': 'd.ACTIVE_DB.lower()'},
            {'menu': 'Ticker Information', 'function': self.m_show_ticker_information, 'params': 'self.ticker, live=True', 'condition': 'True', 'value': 'd.ACTIVE_HISTORYDATASOURCE.lower()'},
            {'menu': 'Ticker Information (previous)', 'function': self.m_show_ticker_information, 'params': 'self.ticker, prompt=True', 'condition': 'True', 'value': ''},
            {'menu': 'Update History', 'function': self.m_update_history, 'params': '', 'condition': '', 'value': ''},
            {'menu': 'Update Company', 'function': self.m_update_company, 'params': '', 'condition': '', 'value': ''},
            {'menu': 'List Update Errors', 'function': self.m_list_errors, 'params': '', 'condition': '', 'value': ''},
            {'menu': 'Re-Check Inactive', 'function': self.m_recheck_inactive, 'params': '', 'condition': '', 'value': ''},
            {'menu': 'List Inactive', 'function': self.m_list_inactive, 'params': '', 'condition': '', 'value': ''},
            {'menu': 'Mark Active/Inactive', 'function': self.m_change_active, 'params': '', 'condition': '', 'value': ''},
            {'menu': 'Create CSV', 'function': self.m_create_csv, 'params': '', 'condition': '', 'value': ''},
            {'menu': 'Check Integrity', 'function': self.m_check_integrity, 'params': '', 'condition': '', 'value': ''},
            {'menu': 'Check Incomplete Pricing', 'function': self.m_check_incomplete_pricing, 'params': '', 'condition': '', 'value': ''},
            {'menu': 'Populate Exchange', 'function': self.m_populate_exchange, 'params': '', 'condition': '', 'value': ''},
            {'menu': 'Populate Index', 'function': self.m_populate_index, 'params': '', 'condition': '', 'value': ''},
            {'menu': 'Reset Database', 'function': self.m_reset_database, 'params': '', 'condition': '', 'value': ''},
        ]

        loop = bool(self.manager.get_database_info())

        if not loop:
            ui.print_error(f'Database {d.ACTIVE_DB} is not intialized')
            self.m_reset_database()
        elif not self.stop and not self.quick:
            self.m_show_database_information()

        # Create the menu
        menu_items = {str(i+1): f'{self.commands[i]["menu"]}' for i in range(len(self.commands))}

        # Update menu items with dynamic info
        def update(menu: dict) -> None:
            for i, item in enumerate(self.commands):
                if item['condition'] and item['value']:
                    menu[str(i+1)] = f'{self.commands[i]["menu"]}'
                    if eval(item['condition']):
                        menu[str(i+1)] += f' ({eval(item["value"])})'

        while loop:
            update(menu_items)

            selection = ui.menu(menu_items, 'Available Operations', 0, len(menu_items))
            if selection > 0:
                if self.commands[selection-1]['params']:
                    func = f'self.{self.commands[selection-1]["function"].__name__}({self.commands[selection-1]["params"]})'
                    eval(func)
                else:
                    self.commands[selection-1]['function']()
            else:
                loop = False

    def m_show_database_information(self) -> None:
        info = self.manager.get_database_info()

        if info:
            ui.print_message(f'Database Information ({d.ACTIVE_DB})')
            for i in info:
                print(f'{i["table"]:>16}:\t{i["count"]} records')

            inactive = self.manager.identify_inactive_tickers('every')
            print(f'        inactive:\t{len(inactive)} tickers')
        else:
            ui.print_error(f'Database {d.ACTIVE_DB} is empty')

    def m_show_ticker_information(self, ticker: str = '', prompt: bool = False, live: bool = False) -> None:
        if not ticker:
            ticker = ui.input_text('Enter ticker').upper()

        if ticker:
            if store.is_ticker(ticker, inactive=True):
                if prompt:
                    end = ui.input_integer('Enter number of days', 0, 100)
                else:
                    end = 0

                company = store.get_company(ticker, live=live, extra=True)
                if company:
                    if live:
                        ui.print_message(f'{ticker} Company Information (live)')
                    else:
                        ui.print_message(f'{ticker} Company Information')

                    print(f'Name:\t\t{company["name"]}')

                    if not live:
                        print(f'Exchange:\t{company["exchange"]}')
                    else:
                        print(f'Exchange:\t{store.get_ticker_exchange(ticker)}')

                    if not live:
                        print(f'Indexes:\t{company["indexes"]}')
                    else:
                        print(f'Indexes:\t{store.get_ticker_index(ticker)}')

                    print(f'Market Cap:\t{company["marketcap"]:,}')
                    print(f'Beta:\t\t{company["beta"]:.2f}')
                    print(f'Rating:\t\t{company["rating"]:.2f}')

                    print(f'Sector:\t\t{company["sector"]}')
                    print(f'Industry:\t{company["industry"]}')
                    print(f'URL:\t\t{company["url"]}')

                    if not live:
                        print(f'Price Records:\t{company["precords"]}')
                        print(f'Active:\t\t{company["active"]}')
                else:
                    ui.print_warning(f'{ticker} has no company information')

                history = store.get_history(ticker, days=100, end=end, live=live)
                if history is None or history.empty:
                    ui.print_error(f'{ticker} has no price history')
                else:
                    history = history.round(2)
                    if not live:
                        latest = history.iloc[-1]
                        print(f'Latest Record:\t{latest["date"]:%Y-%m-%d}, closed at ${latest["close"]:.2f}')

                    ui.print_message(f'{ticker} Recent Price History')
                    history = history.tail(10)
                    if not history.empty:
                        history = history.set_index('date')
                        print(history.round(2))

            else:
                ui.print_error(f'{ticker} not found')

    def list_table(self) -> None:
        found = []
        table = ui.input_table(exchange=True)
        if table:
            if store.is_exchange(table):
                found = self.manager.list_exchange(table)
            elif store.is_list(table):
                found = self.manager.list_index(table)
            else:
                ui.print_error(f'List {table} is not valid')

            if found:
                ui.print_tickers(found)

    def m_populate_exchange(self) -> None:
        table = ui.input_table(exchange=True)
        if table:
            self.task = threading.Thread(target=self.manager.populate_exchange, args=[table])
            self.task.start()

            # Show thread progress. Blocking while thread is active
            self.show_progress()

            if self.manager.task_state == 'Done':
                ui.print_message(f'{self.manager.task_success} {table} '
                                 f'Symbols populated in {self.manager.task_time/60.0:.1f} minutes with {len(self.manager.invalid_tickers)} invalid symbols')

    def m_populate_index(self) -> None:
        table = ui.input_table(index=True)
        if table:
            self.task = threading.Thread(target=self.manager.populate_index, args=[table])
            self.task.start()

            # Show thread progress. Blocking while thread is active
            self.show_progress()

            if self.manager.task_state == 'Done':
                ui.print_message(f'{self.manager.task_success} {table} Symbols populated in {self.manager.task_time:.0f} seconds')
            else:
                ui.print_error(self.manager.task_state)

    def m_update_history(self, ticker: str = '') -> None:
        if not ticker:
            table = ui.input_table(exchange=True, ticker=True, all=True)
        elif store.is_list(ticker):
            table = ticker
        elif store.is_ticker(ticker):
            table = ticker
        else:
            table = ''

        if not table:
            ui.print_message('Invalid table')
        elif store.is_ticker(ticker):
            days = self.manager.update_history_ticker(ticker)
            ui.print_message(f'Added {days} days pricing for {ticker.upper()}')
            self.m_show_ticker_information(ticker=ticker)
        else:
            self.task = threading.Thread(target=self.manager.update_history_exchange, args=[table])
            self.task.start()

            # Show thread progress. Blocking while thread is active
            self.show_progress()

            if self.manager.task_state == 'Done':
                ui.print_message(f'{self.manager.task_total} tickers refreshed in {self.manager.task_time:.0f} seconds.')
                ui.print_message(f'{self.manager.task_counter} pricing records added.')

                if not self.stop and len(self.manager.invalid_tickers) > 0:
                    if ui.input_yesno('Show unsuccessful tickers?'):
                        ui.print_message(f'{len(self.manager.invalid_tickers)} unsuccessful tickers')
                        ui.print_tickers(self.manager.invalid_tickers)

    def m_update_company(self, ticker: str = '') -> None:
        table = ui.input_table(exchange=True, ticker=True, all=True)

        if not table:
            ui.print_message('Cancelled')
        elif store.is_ticker(ticker):
            if self.manager.update_company_ticker(ticker):
                ui.print_message('Success')
                self.m_show_ticker_information(ticker)
            else:
                ui.print_error('Error')
        else:
            self.task = threading.Thread(target=self.manager.update_companies_exchange, args=[table])
            self.task.start()

            # Show thread progress. Blocking while thread is active
            self.show_progress()

            if self.manager.task_state == 'Done':
                ui.print_message(f'{self.manager.task_total} {table} Company infomation refreshed in {self.manager.task_time:.0f} seconds')

    def delete_exchange(self) -> None:
        table = ui.input_table(exchange=True)
        if table:
            self.task = threading.Thread(target=self.manager.delete_exchange, args=[table])
            self.task.start()

            # Show thread progress. Blocking while thread is active
            self.show_progress()

            self.create_missing_tables()

            if self.manager.task_state == 'Done':
                ui.print_message(f'Deleted exchange {table} in {self.manager.task_time:.0f} seconds')

    def delete_index(self) -> None:
        table = ui.input_table(index=True)
        if table:
            self.manager.delete_index(table)
            self.create_missing_tables()

            ui.print_message(f'Deleted exchange {table}')

    def delete_ticker(self) -> None:
        ticker = ui.input_table(ticker=True)
        if ticker:
            self.manager.delete_ticker(ticker)
            ui.print_message(f'Deleted ticker {ticker}')

    def m_reset_database(self) -> None:
        select = ui.input_yesno('Reset the database')
        if select == 1:
            self.manager.delete_database()
            self.manager.create_database()
            self.manager.create_exchanges()
            self.manager.create_indexes()
            ui.print_message(f'Database is reset')
        else:
            ui.print_message('Database not reset')

    def m_check_integrity(self) -> None:
        ui.print_message('Missing Tickers')
        missing_tickers = {e: self.manager.identify_missing_ticker(e) for e in self.exchanges}
        for e in self.exchanges:
            print(f'{e:>16}:\t{len(missing_tickers[e])}')

        ui.print_message('Incomplete Companies')
        incomplete_companies = {e: self.manager.identify_incomplete_companies(e) for e in self.exchanges}
        for e in self.exchanges:
            print(f'{e:>16}:\t{len(incomplete_companies[e])}')

        loop = True
        while loop:
            menu_items = {
                '1': 'List Missing Companies',
                '2': 'List Incomplete Companies',
            }

            select = ui.menu(menu_items, 'Available Operations', 0, len(menu_items), prompt='Select operation, or 0 when done')
            if select > 0:
                table = ui.input_table(exchange=True)
                if table:
                    if select == 1:
                        ui.print_tickers(missing_tickers[table])
                    elif select == 2:
                        ui.print_tickers(incomplete_companies[table])
                else:
                    loop = False
                    ui.print_message('Cancelled')
            else:
                loop = False

    def m_check_incomplete_pricing(self) -> None:
        table = ui.input_table(exchange=True, index=True, ticker=True)
        if table:
            self.task = threading.Thread(target=self.manager.identify_incomplete_pricing, args=[table])
            self.task.start()

            # Show thread progress. Blocking while thread is active
            self.show_progress()

            if self.manager.task_state == 'Done':
                ui.print_message(f'{self.manager.task_total} {table} Ticker pricing checked in {self.manager.task_time:.0f} seconds')

            if len(self.manager.task_results) > 0:
                total = []
                ui.print_message('Results')
                for item in self.manager.task_results:
                    total += item[1]
                    print(f'{item[0]}:')
                    ui.print_tickers(item[1])

                if ui.input_yesno('Mark tickers as inactive?'):
                    self.manager.change_active(total, False)
            else:
                ui.print_message('No results found')

    def m_list_errors(self) -> None:
        tickers = self.manager.get_latest_errors()
        if tickers:
            ui.print_message('Tickers with errors')
            ui.print_tickers(tickers)

            if ui.input_yesno('Mark tickers as inactive?'):
                self.manager.change_active(tickers, False)
        else:
            ui.print_message('No ticker errors')

    def m_recheck_inactive(self) -> None:
        ticker = ui.input_text('Enter ticker or \'every\' for all').upper()
        if ticker == 'EVERY':
            tickers = self.manager.identify_inactive_tickers('every')
        else:
            tickers = [ticker]

        if tickers:
            self.task = threading.Thread(target=self.manager.recheck_inactive, args=[tickers])
            self.task.start()

            # Show thread progress. Blocking while thread is active
            self.show_progress()

            if self.manager.task_state == 'Done':
                ui.print_message(f'{self.manager.task_success} Inactive tickers updated in {self.manager.task_time:.0f} seconds')
                if self.manager.task_results:
                    self.manager.change_active(self.manager.task_results, True)
                    ui.print_tickers(self.manager.task_results)
        else:
            ui.print_message('No tickers to update')

    def m_list_inactive(self) -> None:
        tickers = self.manager.identify_inactive_tickers('every')
        if tickers:
            ui.print_message(f'{len(tickers)} inactive tickers')
            ui.print_tickers(tickers)
        else:
            ui.print_message('No inactive tickers')

    def m_change_active(self) -> None:
        menu_items = {
            '1': 'Change Individual Ticker',
            '2': 'Mark Errors as Inactive',
            '3': 'Mark all as Active',
        }

        while True:
            select = ui.menu(menu_items, 'Available Operations', 0, len(menu_items), prompt='Select operation, or 0 when done')
            if select == 1:
                input = ui.input_list('Please enter symbols separated with commas').upper()
                if input:
                    tickers = input.split(',')
                    select = ui.input_integer('(1) Active, (2) Inactive', min_=1, max_=2)
                    if select > 0:
                        active = (select == 1)
                        self.manager.change_active(tickers, active)
            elif select == 2:
                tickers = self.manager.get_latest_errors()
                self.manager.change_active(tickers, False)
            elif select == 3:
                tickers = self.manager.identify_inactive_tickers('every')
                self.manager.change_active(tickers, True)
            else:
                break

    def m_create_csv(self) -> None:
        self.ticker = ui.input_alphanum('Enter exchange or index')
        if store.is_ticker(self.ticker):
            days = ui.input_integer('Enter number of days (0 for all)', 0, 9999)
            if days == 0: days = -1
            table = store.get_history(self.ticker, days)
            date = dt.datetime.now().strftime(ui.DATE_FORMAT)
            filename = f'{CSV_BASEPATH}/{date}_{self.ticker.lower()}.csv'
            table.to_csv(filename, index=False, float_format='%.4f')
        else:
            ui.print_error(f'Ticker {self.ticker} is not valid')

    def create_missing_tables(self) -> None:
        self.manager.create_exchanges()
        self.manager.create_indexes()

    def show_progress(self) -> None:
        while not self.manager.task_state:
            pass

        if self.manager.task_state == 'None':
            ui.progress_bar(self.manager.task_completed, self.manager.task_total, reset=True)

            while self.task.is_alive() and self.manager.task_state == 'None':
                time.sleep(0.5)
                total = self.manager.task_total
                completed = self.manager.task_completed
                success = self.manager.task_success
                symbol = self.manager.task_ticker
                tasks = len([True for future in self.manager.task_futures if future.running()])

                if total > 0:
                    ui.progress_bar(completed, total, ticker=symbol, success=success, tasks=tasks)
                else:
                    ui.progress_bar(completed, total)

            results = [future.result() for future in self.manager.task_futures if future.result() is not None]
            if len(results) > 0:
                ui.print_message('Processed Messages')
                for result in results:
                    print(result)
        else:
            ui.print_message(f'{self.manager.task_state}')


def main():
    parser = argparse.ArgumentParser(description='Database Management')
    parser.add_argument('-t', '--ticker', help='Get ticker information', metavar='ticker', required=False)
    parser.add_argument('-u', '--update', help='Update ticker', metavar='ticker', required=False)
    parser.add_argument('-q', '--quick', help='Start without checking database information', action='store_true')

    command = vars(parser.parse_args())

    if command['ticker']:
        Interface(ticker=command['ticker'], quick=command['quick'])
    elif command['update']:
        Interface(update=command['update'], quick=command['quick'])
    else:
        Interface(quick=command['quick'])


if __name__ == '__main__':
    main()
