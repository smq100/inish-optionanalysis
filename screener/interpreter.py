import datetime

from utils import utils as u


logger = u.get_logger()

VALID_TECHNICALS = ('price', 'sma', 'none')
VALID_CONDITIONALS = ('lt', 'eq', 'gt')

class SyntaxError(Exception):
    def __init__(self, message):
        super().__init__(message)


class Interpreter:
    def __init__(self, symbol, filter):
        self.symbol = symbol
        self.filter = filter
        self.start_technical = ''
        self.start_level = 0.0
        self.criteria_conditional = ''
        self.criteria_value = 0.0
        self.criteria_technical = ''
        self.criteria_level = 0.0
        self.result = False

    def run(self):
        result = False
        if self.filter['start']['technical'] not in VALID_TECHNICALS:
            raise SyntaxError('Invalid "technical" specified in script')
        if self.filter['criteria']['technical'] not in VALID_TECHNICALS:
            raise SyntaxError('Invalid "technical" specified in script')
        if self.filter['criteria']['conditional'] not in VALID_CONDITIONALS:
            raise SyntaxError('Invalid "test" specified in script')

        self.start_technical = self.filter['start']['technical']
        self.start_level = self.filter['start']['level']
        self.criteria_conditional = self.filter['criteria']['conditional']
        self.criteria_value = self.filter['criteria']['value']
        self.criteria_technical = self.filter['criteria']['technical']
        self.criteria_level = self.filter['criteria']['level']

        result = self._calculate()

        return result

    def _calculate(self):
        result = False

        ### Price
        if self.start_technical == VALID_TECHNICALS[0]: # price
            price = self.symbol.ta.get_current_price()
            if self.criteria_technical == VALID_TECHNICALS[-1]: # none
                value = self.criteria_value
            elif self.criteria_technical == VALID_TECHNICALS[1]: #sma
                value = self.symbol.ta.calc_sma(self.criteria_level)[-1]

            if self.criteria_conditional == VALID_CONDITIONALS[0]: # lt
                if price < value:
                    result = True
            elif self.criteria_conditional == VALID_CONDITIONALS[1]: # eq
                if price == value:
                    result = True
            elif self.criteria_conditional == VALID_CONDITIONALS[2]: # eq
                if price > value:
                    result = True

        logger.debug(f'{__name__}: {str(self.symbol):4s}:{str(result):5s} start/{self.start_technical}/{price:6.2f} {self.criteria_conditional} criteria/{self.criteria_technical}/{value:6.2f}')

        return result
