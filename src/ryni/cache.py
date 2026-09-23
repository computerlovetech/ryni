"""Share expensive reads during one engine check, without retaining stale data."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from typing import cast

from ryni.profiling import current_profile

_cache: ContextVar[dict | None] = ContextVar("ryni_check_cache", default=None)


def cached_per_check[**P, T](function: Callable[P, T]) -> Callable[P, T]:
    """Cache successful calls during check(); call normally outside the engine.

    Arguments must be hashable and callers must treat returned values as read-only.
    Each check has its own cache, which is cleared after every attempted fix.
    Use this for discovery, reads and parsing, not rule evaluation or mutations.
    Profiled checks report this helper's time, cache hits and cache misses.
    """

    module = getattr(function, "__module__", type(function).__module__)
    qualified_name = getattr(function, "__qualname__", type(function).__qualname__)
    name = f"{module}.{qualified_name}"

    @wraps(function)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
        cache = _cache.get()
        if cache is None:
            return function(*args, **kwargs)
        key = (function, args, tuple(sorted(kwargs.items())))
        hit = key in cache
        profile = current_profile()
        if profile is not None:
            with profile.measure("helper", name, cache_hit=hit):
                if not hit:
                    cache[key] = function(*args, **kwargs)
                return cast(T, cache[key])
        if not hit:
            cache[key] = function(*args, **kwargs)
        return cast(T, cache[key])

    return wrapped


@contextmanager
def check_cache() -> Iterator[None]:
    token = _cache.set({})
    try:
        yield
    finally:
        _cache.reset(token)


def clear_check_cache() -> None:
    cache = _cache.get()
    if cache is not None:
        cache.clear()
