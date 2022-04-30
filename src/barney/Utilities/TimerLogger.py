from __future__ import annotations

import functools
import logging
from time import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import TracebackType
    from typing import Any, Type


logger = logging.getLogger(__name__)


def timed_version_of(func: Any) -> Any:
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        t = time()
        val = func(*args, **kwargs)
        t = time() - t
        return t, val

    return wrapper


class TimerLoggerContatainer:
    def __init__(self) -> None:
        self.first: float = -1.0
        self.current: float = 0.0
        self.total: float = 0.0
        self.count: int = 0


def timerlogger(
    func: Any = None,
    provided_logger: logging.Logger = None,
    decimals: int = 1,
    use_ms: bool = True,
) -> Any:
    def _timerlogger(func: Any) -> Any:
        times = TimerLoggerContatainer()
        conversion_factor = 1000 if use_ms else 1
        time_unit = "ms" if use_ms else "s"
        if provided_logger:
            log = provided_logger
        else:
            log = logger  # logger for TimerLogger module

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if timerlogger.disableAll:  # type: ignore
                return func(*args, **kwargs)

            t = time()
            retval = func(*args, **kwargs)
            t = (time() - t) * conversion_factor

            times.total += t
            times.count += 1
            t = round(t, decimals)
            times.current = t
            if times.first < 0:
                times.first = t

            avg = round(times.total / times.count, decimals)
            log.debug(
                "Time Logger Information: \n"
                + f"\t{func.__name__}({*args, *kwargs.values()}) \n"
                + f"\tThis time: {times.current} {time_unit}\n"
                + f"\tFirst time: {times.first} {time_unit}\n"
                + f"\tAverage time: {avg} {time_unit}\n"
                + f"\tTotal time: {round(times.total, decimals)} {time_unit}"
            )

            return retval

        wrapper.times = times  # type: ignore

        return wrapper

    if func is None:  # called without args, about to be applied to function
        return _timerlogger
    else:  # called with args, apply to function now
        return _timerlogger(func)


timerlogger.disableAll = False  # type: ignore


def disableAllTimerLoggers(disable: bool = True) -> None:
    timerlogger.disableAll = disable  # type: ignore


class ElapsedTimeLogger:
    def __init__(
        self,
        tag: str = "Timed Context Manager",
        provided_logger: logging.Logger = None,
        use_ms: bool = True,
        decimals: int = 1,
        log: bool = True,
    ) -> None:
        if provided_logger is not None:
            self.logger = provided_logger
        else:  # global logger for module
            self.logger = logger
        self.log = log

        self.t_init = -1.0
        self.tag = tag
        self.decimals = decimals
        self.conversion_factor = 1000 if use_ms else 1
        self.time_unit = "ms" if use_ms else "s"

    def __enter__(self) -> ElapsedTimeLogger:
        self.t_init = time()
        return self

    def current_time(self) -> float:
        return (time() - self.t_init) * self.conversion_factor

    def __exit__(
        self, type_: Type, value: BaseException, traceback: TracebackType
    ) -> None:
        t = round(self.current_time(), self.decimals)
        if self.log:
            self.logger.info(f"{self.tag}: {t} {self.time_unit}")

    def lognow(self) -> None:
        t = round(self.current_time(), self.decimals)
        self.logger.info(f"{self.tag}: Current time: {t} {self.time_unit}")
