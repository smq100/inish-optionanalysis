import abc
from abc import ABC

class Sheet(ABC):
    def __init__(self, sheet_name):
        self.spreadsheet = sheet_name
        self.opened = False
        self.tab = ''
        self.sheet = None
        self.result = ''
        self.col = None

    def __str__(self):
        return self.spreadsheet

    @abc.abstractmethod
    def open(self, tab):
        pass

    @abc.abstractmethod
    def get_column(self, column):
        pass
