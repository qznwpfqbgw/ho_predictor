from threading import Timer, Thread, Event

class LoopTimer(Thread):
    def __init__(self, interval, function, *args, **kwargs):
        Thread.__init__(self)
        self.daemon = True
        self.stopped = Event()
        self.interval = interval
        self.function = function
        self.args = args if args is not None else []
        self.kwargs = kwargs if kwargs is not None else {}

    def stop(self):
        self.stopped.set()
        self.join()

    def run(self):
        while not self.stopped.wait(self.interval):
            if not self.stopped.is_set():
                self.function(*self.args, **self.kwargs)
            else:
                break