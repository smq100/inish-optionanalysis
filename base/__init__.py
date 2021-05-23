import time

class Threaded:
    def __init__(self):
        self.task_total = 0
        self.task_completed = 0
        self.task_success = 0
        self.task_symbol = ''
        self.task_error = ''
        self.task_results = []
        self.task_object = None
        self.task_time = 0
        self.task_futures = []

    def threaded(func):
        def wrapper(self, *args, **kwargs):
            self.task_total = 0
            self.task_completed = 0
            self.task_success = 0
            self.task_symbol = ''
            self.task_error = ''
            self.task_results = []
            self.task_object = None
            self.task_time = 0.0
            self.task_futures = []

            tic = time.perf_counter()
            func(self, *args, **kwargs)
            toc = time.perf_counter()

            self.task_time = toc - tic

        return wrapper
