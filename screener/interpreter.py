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

        return self._calculate()


    def _calculate(self):
        logger.debug(f'{__name__}: {self.symbol.ticker}:\t{self.condition}')
        return True
