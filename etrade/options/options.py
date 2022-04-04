import json

from requests_oauthlib import OAuth1Session

from utils import logger

_logger = logger.get_logger()


class Options:
    def __init__(self, session, base_url):
        self.session: OAuth1Session = session
        self.base_url: str = base_url

    def chain(self,
              symbol: str,
              expiry_month: int,
              expiry_year: int,
              strikes: int = 10,
              weekly: bool = False,
              otype: str = 'CALLPUT') -> tuple[str, dict]:

        message = 'success'
        url = self.base_url + '/v1/market/optionchains.json'
        params = {
            'chainType': f'{otype}',
            'noOfStrikes': f'{strikes}',
            'includeWeekly': f'{str(weekly)}',
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
