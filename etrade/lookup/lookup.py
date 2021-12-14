import json

from utils import ui

_logger = ui.get_logger()


class Lookup:
    def __init__(self, session, base_url):
        self.session = session
        self.base_url = base_url

    def lookup(self, symbol:str) -> tuple[str, dict]:
        message = 'success'
        url = f'{self.base_url}/v1/market/lookup/{symbol}.json'
        lookup_data = None

        response = self.session.get(url)
        if response is not None and response.status_code == 200:
            lookup_data = json.loads(response.text)
            parsed = json.dumps(lookup_data, indent=2, sort_keys=True)
            _logger.debug(parsed)

            if lookup_data is not None and 'LookupResponse' in lookup_data and 'Data' in lookup_data['LookupResponse']:
                pass
            else:
                lookup_data = []
                message = 'None'
        elif response is not None and response.status_code == 204:
            lookup_data = []
            message = 'None'
        else:
            _logger.debug(f'Response Body: {response}')
            message = 'E*TRADE API service error'

        return message, lookup_data
