class Threaded:
    def __init__(self):
        self.items_total = 0
        self.items_completed = 0
        self.items_success = 0
        self.items_symbol = ''
        self.items_error = ''

    def threaded(func):
        def wrapper(self, *args, **kwargs):
            # self.items_total = 0
            self.items_completed = 0
            self.items_success = 0
            self.items_symbol = ''
            self.items_error = ''
            func(self, *args, **kwargs)

        return wrapper
