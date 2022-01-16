import json

from utils import ui, logger

_logger = logger.get_logger()


class Options:
    def __init__(self, session, base_url):
        self.session = session
        self.base_url = base_url

    def chain(self,
              symbol: str = '',
              otype: str = 'CALLPUT',
              strikes: int = 5,
              expiry_month: int = 2,
              expiry_year: int = 2022) -> tuple[str, dict]:

        message = 'success'
        url = self.base_url + '/v1/market/optionchains.json'
        params = {
            'chainType': f'{otype}',
            'noOfStrikes': f'{strikes}',
            'includeWeekly': 'true',
            'expiryMonth': f'{expiry_month}',
            'expiryYear': f'{expiry_year}',
            'symbol': f'{symbol}'
        }
        chain_data = None

        response = self.session.get(url, params=params)
        if response is not None and response.status_code == 200:
            chain_data = json.loads(response.text)
            parsed = json.dumps(chain_data, indent=2, sort_keys=True)
            _logger.debug(parsed)

            if chain_data is not None and 'OptionChainResponse' in chain_data and 'OptionPair' in chain_data['OptionChainResponse']:
                pass
            else:
                message = 'Chain error'
        elif response is not None and response.status_code == 400:
            _logger.debug(f'Response Body: {response}')
            chain_data = json.loads(response.text)
            message = f'\nError ({chain_data["Error"]["code"]}): {chain_data["Error"]["message"]}'
        else:
            _logger.debug(f'Response Body: {response}')
            message = 'E*TRADE API service error'

        return message, chain_data
