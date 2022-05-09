import abc
from abc import ABC


class Sheet(ABC):
    def __init__(self, sheet_name):
        self.sheet_name = sheet_name
        self.tab_name = ''
        self.sheet = None
        self.col = None
        self.opened = False

    def __str__(self):
        return self.sheet_name

    @abc.abstractmethod
    def open(self, tab: str) -> bool:
        return False

    @abc.abstractmethod
    def get_column(self, column: int) -> list[str]:
        return []
