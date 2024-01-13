# Author: obnoxious, fuck mongodb for not implementing AnyIO and making me do this
# I fucking hate you.

# Seriously, like a lot.

"""trio compatbility layer for Motor, an asynchronous MongoDB driver.

See "Frameworks" in the Developer Guide.
"""

import functools
import multiprocessing
import os

import trio

CLASS_PREFIX = "Trio"
_EXECUTOR = None  # ThreadPoolExecutor for AsyncIO


if "MOTOR_MAX_WORKERS" in os.environ:
    max_workers = int(os.environ["MOTOR_MAX_WORKERS"])
else:
    max_workers = multiprocessing.cpu_count() * 5

trio.to_thread.current_default_thread_limiter.total_tokens = max_workers

def run_on_executor(loop, function, *args, **kwargs):
    return trio.to_thread.run_sync(function, *args, **kwargs)

def pymongo_class_wrapper(f, pymongo_class):
    """Executes the coroutine f and wraps its result in a Motor class.

    See WrapAsync.
    """

    @functools.wraps(f)
    async def _wrapper(self, *args, **kwargs):
        result = await f(self, *args, **kwargs)

        # Don't call isinstance(), not checking subclasses.
        if result.__class__ == pymongo_class:
            # Delegate to the current object to wrap the result.
            return self.wrap(result)
        else:
            return result

    return _wrapper


def platform_info():
    return "trio"
