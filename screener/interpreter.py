import datetime

from utils import utils as u


logger = u.get_logger()

VALID_TECHNICALS = ('price',)
VALID_TESTS = ('lt', 'eq', 'gt')
VALID_CONDITIONALS = ('and', 'or')

class SyntaxError(Exception):
    def __init__(self, message):
        super().__init__(message)


class Interpreter:
    def __init__(self, symbol, condition):
        self.symbol = symbol
        self.condition = condition
        self.start_technical = ''
        self.start_level = 0.0
        self.criteria_test = ''
        self.criteria_value = 0.0
        self.result = False
        self.conditional = ''

    def __str__(self):
        output = f'{self.start_technical}, {self.start_level}, {self.criteria_test}, {self.criteria_value}, {self.condition}'

        return output

    def run(self):
        result = False
        if self.condition['start']['technical'] not in VALID_TECHNICALS:
            raise SyntaxError('Invalid "technical" specified in script')
        if self.condition['criteria']['test'] not in VALID_TESTS:
            raise SyntaxError('Invalid "test" specified in script')
        if self.condition['conditional'] not in VALID_CONDITIONALS:
            raise SyntaxError('Invalid "conditional" specified in script')

        self.start_technical = self.condition['start']['technical']
        self.start_level = self.condition['start']['level']
        self.criteria_test = self.condition['criteria']['test']
        self.criteria_value = self.condition['criteria']['value']
        self.conditional = self.condition['conditional']

        result = self._calculate()

        logger.debug(f'{__name__}: Calculated {self.symbol.ticker}: {result}')
        return result


    def _calculate(self):
        result = False

        ### Price
        if self.start_technical == VALID_TECHNICALS[0]:
            price = self.symbol.ta.get_current_price()
            if self.criteria_test == VALID_TESTS[0]: # lt
                if price < self.criteria_value:
                    result = True
            elif self.criteria_test == VALID_TESTS[1]: # eq
                if price == self.criteria_value:
                    result = True
            elif self.criteria_test == VALID_TESTS[2]: # eq
                if price > self.criteria_value:
                    result = True

        return result
