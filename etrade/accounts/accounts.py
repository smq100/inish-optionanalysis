import json
import configparser

from utils import ui, logger

_logger = logger.get_logger()


class Accounts:
    def __init__(self, session, base_url):
        self.config = configparser.ConfigParser()
        self.config.read('etrade/config.ini')
        self.session = session
        self.base_url = base_url
        self.accounts = []

    def list(self) -> tuple[str, list[str]]:
        url = self.base_url + '/v1/accounts/list.json'
        response = self.session.get(url)
        message = 'success'
        listing = []

        self.accounts = []

        if response is not None and response.status_code == 200:
            data = response.json()
            parsed = json.dumps(data, indent=2, sort_keys=True)
            _logger.info(parsed)

            if data is not None and 'AccountListResponse' in data \
                    and 'Accounts' in data['AccountListResponse'] \
                    and 'Account' in data['AccountListResponse']['Accounts']:
                accounts = data['AccountListResponse']['Accounts']['Account']

                self.accounts[:] = [d for d in accounts if d.get('accountStatus') != 'CLOSED']
                for account in self.accounts:
                    print_str = ''
                    if account is not None and 'accountId' in account:
                        print_str += account['accountId']
                    if account is not None and 'accountDesc' in account and account['accountDesc'].strip() is not None:
                        print_str += f', {account["accountDesc"].strip()}'
                    if account is not None and 'institutionType' in account:
                        print_str += f', {account["institutionType"]}'

                    listing += [print_str]

            else:
                _logger.error(f'Response Body: {response.text}')
                self.accounts = []
                listing = []
                if response is not None and response.headers['Content-Type'] == 'application/json' \
                        and 'Error' in response.json() and 'message' in response.json()['Error'] \
                        and response.json()['Error']['message'] is not None:
                    message = data['Error']['message']
                else:
                    message = 'E*TRADE API service error'
        else:
            _logger.error(f'Response Body: {response.text}')
            self.accounts = []
            listing = []
            if response is not None and response.headers['Content-Type'] == 'application/json' \
                    and 'Error' in response.json() and 'message' in response.json()['Error'] \
                    and response.json()['Error']['message'] is not None:
                message = 'Error: ' + response.json()['Error']['message']
            else:
                message = '\nError: E*TRADE API service error'

        return message, listing

    def balance(self, account_index: int) -> tuple[str, dict]:
        message = 'success'
        url = self.base_url + '/v1/accounts/' + self.accounts[account_index]['accountIdKey'] + '/balance.json'
        params = {'instType': self.accounts[account_index]['institutionType'], 'realTimeNAV': 'true'}
        headers = {'consumerkey': self.config['DEFAULT']['CONSUMER_KEY']}

        response = self.session.get(url, params=params, headers=headers)
        if response is not None and response.status_code == 200:
            data = json.loads(response.text)
            parsed = json.dumps(data, indent=2, sort_keys=True)
            _logger.debug(parsed)

            if data is not None and 'BalanceResponse' in data:
                balance_data = data['BalanceResponse']
            else:
                _logger.error(f'Response Body: {response.text}')
                balance_data = []
                if response is not None and response.headers['Content-Type'] == 'application/json' \
                        and 'Error' in response.json() and 'message' in response.json()['Error'] \
                        and response.json()['Error']['message'] is not None:
                    message = data['Error']['message']
                else:
                    message = 'E*TRADE API service error'
        else:
            _logger.error(f'Response Body: {response.text}')
            balance_data = []
            if response is not None and response.headers['Content-Type'] == 'application/json' \
                    and 'Error' in response.json() and 'message' in response.json()['Error'] \
                    and response.json()['Error']['message'] is not None:
                message = 'Error: ' + response.json()['Error']['message']
            else:
                message = '\nError: E*TRADE API service error'

        return message, balance_data

    def portfolio(self, account_index: int) -> tuple[str, dict]:
        message = 'success'
        url = self.base_url + '/v1/accounts/' + self.accounts[account_index]['accountIdKey'] + '/portfolio.json'

        response = self.session.get(url)
        if response is not None and response.status_code == 200:
            portfolio = json.loads(response.text)
            parsed = json.dumps(portfolio, indent=2, sort_keys=True)
            _logger.debug(parsed)

            if portfolio is not None and 'PortfolioResponse' in portfolio and 'AccountPortfolio' in portfolio['PortfolioResponse']:
                pass
            else:
                _logger.error(f'Response Body: {response.text}')
                portfolio = []
                if response is not None and response.headers['Content-Type'] == 'application/json' \
                        and 'Error' in response.json() and 'message' in response.json()['Error'] \
                        and response.json()['Error']['message'] is not None:
                    message = portfolio['Error']['message']
                else:
                    message = 'E*TRADE API service error'

        elif response is not None and response.status_code == 204:
            portfolio = []
            message = 'None'
        else:
            _logger.error(f'Response Body: {response.text}')
            portfolio = []
            message = 'E*TRADE API service error'

        return message, portfolio
