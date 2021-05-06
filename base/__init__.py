import time

class Threaded:
    def __init__(self):
        self.items_total = 0
        self.items_completed = 0
        self.items_success = 0
        self.items_symbol = ''
        self.items_error = ''
        self.items_results = []
        self.items_time = 0
        self.items_futures = []

    def threaded(func):
        def wrapper(self, *args, **kwargs):
            self.items_total = 0
            self.items_completed = 0
            self.items_success = 0
            self.items_symbol = ''
            self.items_error = ''
            self.items_results = []
            self.items_time = 0.0
            self.items_futures = []

            tic = time.perf_counter()
            func(self, *args, **kwargs)
            toc = time.perf_counter()

            self.items_time = toc - tic

        return wrapper
