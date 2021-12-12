import json
import datetime

from utils import ui

_logger = ui.get_logger()


class Alerts:
    def __init__(self, session, base_url):

        self.session = session
        self.base_url = base_url

    def alerts(self):
        # Make API call for GET request
        params = {'status': ['READ', 'UNREAD']}
        url = f'{self.base_url}/v1/user/alerts.json'

        response = self.session.get(url, params=params)
        if response is not None and response.status_code == 200:
            data = json.loads(response.text)
            parsed = json.dumps(data, indent=2, sort_keys=True)
            _logger.debug(parsed)

            if data is not None and 'AlertsResponse' in data and 'Alert' in data['AlertsResponse']:
                ui.print_message('Alerts')
                out = ''

                for item in data['AlertsResponse']['Alert']:
                    if item is not None and 'id' in item:
                        out = f'ID: {item["id"]}'

                    if item is not None and 'createTime' in item:
                        timestamp = datetime.datetime.fromtimestamp(
                            item["createTime"]).strftime('%Y-%m-%d %H:%M:%S')
                        out += f', Time: {timestamp}'

                    if item is not None and 'subject' in item:
                        out += f', Subject: {item["subject"]}'

                    if item is not None and 'status' in item:
                        out += f', Status: {item["status"]}'

                    print(out)
            else:
                print('None')

        else:
            _logger.debug(f'Response Body: {response}')
            print(f'\nError: E*TRADE API service error: {response}')
