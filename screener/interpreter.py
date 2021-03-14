import datetime

from analysis.technical import TechnicalAnalysis
from utils import utils as u


logger = u.get_logger()

VALID_TECHNICALS = ('price',)
VALID_TESTS = ('gt', 'lt', 'eq')
VALID_NEXT = ('end',)

class Interpreter:
    def __init__(self, symbol, condition):
        self.symbol = symbol
        self.condition = condition
        self.start_technical = ''
        self.start_level = 0.0
        self.criteria_test = ''
        self.criteria_value = 0.0
        self.result = False
        self.next = ''

    def __str__(self):
        output = f'{self.start_technical}, {self.start_level}, {self.criteria_test}, {self.criteria_value}, {self.next}'

        return output

    def run(self):
        result = False
        if self.condition['start']['technical'] not in VALID_TECHNICALS:
            raise ValueError ('Invalid technical specified in script')
        elif self.condition['criteria']['test'] not in VALID_TESTS:
            raise ValueError ('Invalid test specified in script')
        elif self.condition['next'] not in VALID_NEXT:
            raise ValueError ('Invalid next specified in script')
        else:
            self.start_technical = self.condition['start']['technical']
            self.start_level = self.condition['start']['level']
            self.criteria_test = self.condition['criteria']['test']
            self.criteria_value = self.condition['criteria']['value']
            self.next = self.condition['next']

            result = self._calculate()

        logger.debug(f'{__name__}: Calculated {self.symbol.ticker}: {result}')
        return result


    def _calculate(self):
        result = False
        if self.start_technical == VALID_TECHNICALS[0]: # price
            start = datetime.datetime.today() - datetime.timedelta(days=30)
            try:
                ta = TechnicalAnalysis(self.symbol.ticker, start)
                price = ta.get_current_price()
                if price > self.criteria_value:
                    result = True
            except ValueError:
                logger.error(f'{__name__}: Invalid symbol {self.symbol.ticker}')

        return result
