from threading import Timer
from typing import Callable


class RestartableTimer:
    """A wrapper around ``threading.Timer`` that provides a restart mechanism.

    Args:
        interval: The interval (in seconds) 
        function: The callable that will be invoked
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.
        
    Attributes:
        interval: The interval (in seconds) that the timer will wait before calling `function`.
        function: A function to be called.
        args: Variable length argument list for `function`.
        kwargs: Arbitrary keyword arguments for `function`.
        timer: The underlying `threading.Timer`
    """

    def __init__(self, interval: int, function: Callable[..., None], *args, **kwargs):
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.timer = Timer(self.interval, self.function, self.args, self.kwargs)

    def restart(self):
        """Restarts the timer"""
        self.timer.cancel()
        self.timer = Timer(self.interval, self.function, self.args, self.kwargs)
        self.timer.start()

    def start(self):
        """Starts the timer

        Note:
            Starting a previously stopped timer will reset it.
        """
        self.restart()

    def stop(self):
        """Attempt to stop the timer"""
        self.timer.cancel()
