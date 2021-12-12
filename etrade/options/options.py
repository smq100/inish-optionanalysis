import json

from utils import ui

_logger = ui.get_logger()


class Options:
    def __init__(self, session, base_url):
        self.session = session
        self.base_url = base_url

    def chain(self,
              symbols='',
              otype='CALLPUT',
              strikes=5,
              expiry_month=2,
              expiry_year=2022):

        # Make API call for GET request
        url = self.base_url + '/v1/market/optionchains.json'
        params = {
            'chainType': f'{otype}',
            'noOfStrikes': f'{strikes}',
            'includeWeekly': 'true',
            'expiryMonth': f'{expiry_month}',
            'expiryYear': f'{expiry_year}',
            'symbol': f'{symbols}'
        }
        response = self.session.get(url, params=params)

        if response is not None and response.status_code == 200:
            data = json.loads(response.text)
            parsed = json.dumps(data, indent=2, sort_keys=True)
            _logger.debug(parsed)

            if data is not None and 'OptionChainResponse' in data and 'OptionPair' in data['OptionChainResponse']:
                ui.print_message('Options Chain')
                for pair in data['OptionChainResponse']['OptionPair']:
                    if pair['Call'] is not None:
                        call = pair['Call']
                        out = ''
                        ask_bid = ''

                        if 'displaySymbol' in call:
                            out += f'{call["displaySymbol"]} '
                        if 'ask' in call:
                            ask_bid = f' ask:${call["ask"]:.2f}'
                        if 'askSize' in call:
                            ask_bid += f'x{call["askSize"]}'
                            out += f'{ask_bid:15s}'
                        if 'bid' in call:
                            ask_bid = f' bid:${call["bid"]:.2f}'
                        if 'bidSize' in call:
                            ask_bid += f'x{call["bidSize"]}'
                            out += f'{ask_bid:15s}'
                        if 'inTheMoney' in call:
                            out += f' ITM:{call["inTheMoney"]}'
                        print(out)

                    if pair['Put'] is not None:
                        put = pair['Put']
                        out = ''
                        ask_bid = ''

                        if 'displaySymbol' in put:
                            out += f'{put["displaySymbol"]}  '
                        if 'ask' in put:
                            ask_bid = f' ask:${put["ask"]:.2f}'
                        if 'askSize' in put:
                            ask_bid += f'x{put["askSize"]}'
                            out += f'{ask_bid:15s}'
                        if 'bid' in put:
                            ask_bid = f' bid:${put["bid"]:.2f}'
                        if 'bidSize' in put:
                            ask_bid += f'x{put["bidSize"]}'
                            out += f'{ask_bid:15s}'
                        if 'inTheMoney' in put:
                            out += f' ITM:{put["inTheMoney"]}'
                        print(out)
                print()

        elif response is not None and response.status_code == 400:
            _logger.debug(f'Response Body: {response}')
            data = json.loads(response.text)
            print(f'\nError ({data["Error"]["code"]}): {data["Error"]["message"]}')
        else:
            _logger.debug(f'Response Body: {response}')
            print('\nError: E*TRADE API service error')
