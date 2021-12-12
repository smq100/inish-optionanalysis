import json
import configparser

from etrade.orders.orders import Orders
from utils import ui

_logger = ui.get_logger()


class Accounts:
    def __init__(self, session, base_url):
        self.config = configparser.ConfigParser()
        self.config.read('etrade/config.ini')
        self.session = session
        self.account = {}
        self.base_url = base_url

    def list(self):
        # Make API call for GET request
        url = self.base_url + '/v1/accounts/list.json'
        response = self.session.get(url)

        if response is not None and response.status_code == 200:
            data = response.json()
            parsed = json.dumps(data, indent=2, sort_keys=True)
            _logger.info(parsed)

            if data is not None and 'AccountListResponse' in data and 'Accounts' in data['AccountListResponse'] \
                    and 'Account' in data['AccountListResponse']['Accounts']:
                accounts = data['AccountListResponse']['Accounts']['Account']
                while True:
                    # Display account list
                    count = 1
                    print('')

                    accounts[:] = [d for d in accounts if d.get(
                        'accountStatus') != 'CLOSED']
                    for account in accounts:
                        print_str = str(count) + ')\t'
                        if account is not None and 'accountId' in account:
                            print_str = print_str + account['accountId']
                        if account is not None and 'accountDesc' in account and account['accountDesc'].strip() is not None:
                            print_str = print_str + \
                                f', {account["accountDesc"].strip()}'
                        if account is not None and 'institutionType' in account:
                            print_str = print_str + \
                                f', {account["institutionType"]}'

                        print(print_str)
                        count = count + 1

                    print(str(count) + ')\t' 'Go Back')

                    # Select account option
                    account_index = input('Please select an account: ')
                    if account_index.isdigit() and 0 < int(account_index) < count:
                        if self.base_url == '':
                            self.account = accounts[int(account_index) - 1]
                        else:
                            self.account = accounts[int(account_index) - 1]
                        self.account_menu()
                    elif account_index == str(count):
                        break
                    else:
                        print('Unknown Account Selected')

            else:
                # Handle errors
                _logger.debug(f'Response Body: {response.text}')
                if response is not None and response.headers['Content-Type'] == 'application/json' \
                        and 'Error' in response.json() and 'message' in response.json()['Error'] \
                        and response.json()['Error']['message'] is not None:
                    print('Error: ' + data['Error']['message'])
                else:
                    print('\nError: E*TRADE API service error')
        else:
            # Handle errors
            _logger.debug(f'Response Body: {response.text}')
            if response is not None and response.headers['Content-Type'] == 'application/json' \
                    and 'Error' in response.json() and 'message' in response.json()['Error'] \
                    and response.json()['Error']['message'] is not None:
                print('Error: ' + response.json()['Error']['message'])
            else:
                print('\nError: E*TRADE API service error')

    def portfolio(self):
        # URL for the API endpoint
        url = self.base_url + '/v1/accounts/' + \
            self.account['accountIdKey'] + '/portfolio.json'

        # Make API call for GET request
        response = self.session.get(url)

        # Handle and parse response
        if response is not None and response.status_code == 200:
            data = json.loads(response.text)
            parsed = json.dumps(data, indent=2, sort_keys=True)
            _logger.debug(parsed)

            if data is not None and 'PortfolioResponse' in data and 'AccountPortfolio' in data['PortfolioResponse']:
                ui.print_message('Portfolio')
                for acct_portfolio in data['PortfolioResponse']['AccountPortfolio']:
                    if acct_portfolio is not None and 'Position' in acct_portfolio:
                        for position in acct_portfolio['Position']:
                            if position is not None:
                                print_str = ''
                                if 'symbolDescription' in position:
                                    print_str = print_str + \
                                        f'{str(position["symbolDescription"])}'
                                if 'quantity' in position:
                                    print_str = print_str + \
                                        f', Q: {position["quantity"]}'
                                if 'Quick' in position and 'lastTrade' in position['Quick']:
                                    print_str = print_str + \
                                        f', Price: {position["Quick"]["lastTrade"]:,.2f}'
                                if 'pricePaid' in position:
                                    print_str = print_str + \
                                        f', Paid: {position["pricePaid"]:,.2f}'
                                if 'totalGain' in position:
                                    print_str = print_str + \
                                        f', Gain: {position["totalGain"]:,.2f}'
                                if 'marketValue' in position:
                                    print_str = print_str + \
                                        f', Value: {position["marketValue"]:,.2f}'

                                print(print_str)
                    else:
                        print('None')
                print()
            else:
                # Handle errors
                _logger.debug(f'Response Body: {response.text}')
                if response is not None and 'headers' in response and 'Content-Type' in response.headers \
                        and response.headers['Content-Type'] == 'application/json' \
                        and 'Error' in response.json() and 'message' in response.json()['Error'] \
                        and response.json()['Error']['message'] is not None:
                    print('Error: ' + response.json()['Error']['message'])
                else:
                    print('\nError: E*TRADE API service error')

        elif response is not None and response.status_code == 204:
            print('None')
        else:
            _logger.debug(f'Response Body: {response.text}')
            print('\nError: E*TRADE API service error')

    def balance(self):
        # URL for the API endpoint
        url = self.base_url + '/v1/accounts/' + \
            self.account['accountIdKey'] + '/balance.json'

        # Add parameters and header information
        params = {'instType': self.account['institutionType'], 'realTimeNAV': 'true'}
        headers = {'consumerkey': self.config['DEFAULT']['CONSUMER_KEY']}

        # Make API call for GET request
        response = self.session.get(url, params=params, headers=headers)

        # Handle and parse response
        if response is not None and response.status_code == 200:
            data = json.loads(response.text)
            parsed = json.dumps(data, indent=2, sort_keys=True)
            _logger.debug(parsed)

            if data is not None and 'BalanceResponse' in data:
                ui.print_message('Account Balances')
                balance_data = data['BalanceResponse']
                if balance_data is not None and 'accountId' in balance_data:
                    print(f'Balance for {balance_data["accountId"]}:')
                else:
                    print('Balance:')

                # Display balance information
                if balance_data is not None:
                    if 'accountDescription' in balance_data:
                        print(f'Account Nickname: {balance_data["accountDescription"]}')
                    if 'accountType' in balance_data:
                        print(f'Account Type: {balance_data["accountType"]}')
                    if 'Computed' in balance_data \
                            and 'RealTimeValues' in balance_data['Computed'] \
                            and 'totalAccountValue' in balance_data['Computed']['RealTimeValues']:
                        print(
                            f'Net Account Value: ${balance_data["Computed"]["RealTimeValues"]["totalAccountValue"]:,.2f}')
                    if 'Computed' in balance_data \
                            and 'marginBuyingPower' in balance_data['Computed']:
                        print(
                            f'Margin Buying Power: ${balance_data["Computed"]["marginBuyingPower"]:,.2f}')
                    if 'Computed' in balance_data \
                            and 'cashBuyingPower' in balance_data['Computed']:
                        print(
                            f'Cash Buying Power: ${balance_data["Computed"]["cashBuyingPower"]:,.2f}')
                    if 'accountDescription' in balance_data:
                        print(f'Option Level: {balance_data["optionLevel"]}')
                    print()
            else:
                # Handle errors
                _logger.debug(f'Response Body: {response.text}')
                if response is not None and response.headers['Content-Type'] == 'application/json' \
                        and 'Error' in response.json() and 'message' in response.json()['Error'] \
                        and response.json()['Error']['message'] is not None:
                    print('Error: ' + response.json()['Error']['message'])
                else:
                    print('Error: Balance API service error')
        else:
            # Handle errors
            _logger.debug(f'Response Body: {response.text}')
            if response is not None and response.headers['Content-Type'] == 'application/json' \
                    and 'Error' in response.json() and 'message' in response.json()['Error'] \
                    and response.json()['Error']['message'] is not None:
                print('Error: ' + response.json()['Error']['message'])
            else:
                print('Error: Balance API service error')

    def account_menu(self):
        if self.account['institutionType'] == 'BROKERAGE':
            menu_items = {'1': 'Balance',
                          '2': 'Portfolio',
                          '3': 'Orders',
                          '4': 'Go Back'}

            while True:
                print('')
                options = menu_items.keys()
                for entry in options:
                    print(f'{entry})\t{menu_items[entry]}')

                selection = input('Please select an option: ')
                if selection == '1':
                    self.balance()
                elif selection == '2':
                    self.portfolio()
                elif selection == '3':
                    order = Orders(self.session, self.account, self.base_url)
                    order.view()
                elif selection == '4':
                    break
                else:
                    print('Unknown Option Selected')
        elif self.account['institutionType'] == 'BANK':
            menu_items = {'1': 'Balance',
                          '2': 'Go Back'}

            while True:
                print('\n')
                options = menu_items.keys()
                for entry in options:
                    print(f'{entry})\t{menu_items[entry]}')

                selection = input('Please select an option: ')
                if selection == '1':
                    self.balance()
                elif selection == '2':
                    break
                else:
                    print('Unknown Option Selected')
        else:
            menu_items = {'1': 'Go Back'}

            while True:
                print('')
                options = menu_items.keys()
                for entry in options:
                    print(entry + ')\t' + menu_items[entry])

                selection = input('Please select an option: ')
                if selection == '1':
                    break

                print('Unknown Option Selected')
