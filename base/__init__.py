import time
from collections.abc import Callable


class Threaded:
    def __init__(self):
        self.task_total = 0
        self.task_completed = 0
        self.task_success = 0
        self.task_ticker = ''
        self.task_state = ''
        self.task_message = ''
        self.task_results = []
        self.task_object: any = None
        self.task_time = 0
        self.task_futures = []

    def threaded(func: Callable):
        def wrapper(self, *args, **kwargs):
            self.task_total = 0
            self.task_completed = 0
            self.task_success = 0
            self.task_ticker = ''
            self.task_state = ''
            self.task_message = ''
            self.task_results = []
            self.task_object = None
            self.task_time = 0.0
            self.task_futures = []

            tic = time.perf_counter()
            func(self, *args, **kwargs)
            toc = time.perf_counter()

            self.task_time = toc - tic

        return wrapper
