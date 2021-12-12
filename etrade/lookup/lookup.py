import json

from utils import ui

_logger = ui.get_logger()


class Lookup:
    def __init__(self, session, base_url):
        self.session = session
        self.base_url = base_url

    def lookup(self, symbols):
        # Make API call for GET request
        url = f'{self.base_url}/v1/market/lookup/{symbols}.json'
        response = self.session.get(url)

        if response is not None and response.status_code == 200:
            data = json.loads(response.text)
            parsed = json.dumps(data, indent=2, sort_keys=True)
            _logger.debug(parsed)

            if data is not None and 'LookupResponse' in data and 'Data' in data['LookupResponse']:
                ui.print_message('Lookup')
                out = ''
                for item in data['LookupResponse']['Data']:
                    if item is not None and 'symbol' in item:
                        out += f'Symbol: {item["symbol"]}'
                    if item is not None and 'type' in item:
                        out += f', Type: {item["type"]}'
                    if item is not None and 'description' in item:
                        out += f', Desc: {item["description"]}'

                    print(out)
                print()
            else:
                print('None')

        else:
            _logger.debug(f'Response Body: {response}')
            print('\nError: E*TRADE API service error')
