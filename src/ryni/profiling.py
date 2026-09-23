"""Opt-in, per-run timings for the engine and arbitrary rule-pack helpers."""

from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from contextvars import ContextVar
from dataclasses import asdict, dataclass
from time import perf_counter


@dataclass
class Timing:
    kind: str
    name: str
    calls: int = 0
    seconds: float = 0.0
    failures: int = 0
    cache_hits: int = 0
    cache_misses: int = 0


class CheckProfile:
    """Collect inclusive wall times. Create a fresh instance for each measured run.

    Nested timings overlap: helper time is also part of the requesting rule's
    time. Rule times aggregate all targets, including evaluations after fixes.
    No paths, file contents, or helper arguments are retained.
    """

    def __init__(self) -> None:
        self._timings: dict[tuple[str, str], Timing] = {}

    @contextmanager
    def measure(
        self, kind: str, name: str, *, cache_hit: bool | None = None
    ) -> Iterator[None]:
        timing = self._timings.setdefault((kind, name), Timing(kind, name))
        timing.calls += 1
        if cache_hit is not None:
            if cache_hit:
                timing.cache_hits += 1
            else:
                timing.cache_misses += 1
        start = perf_counter()
        try:
            yield
        except BaseException:
            timing.failures += 1
            raise
        finally:
            timing.seconds += perf_counter() - start

    def to_dict(self) -> dict:
        return {"timings": [asdict(timing) for timing in self._timings.values()]}


_active: ContextVar[CheckProfile | None] = ContextVar("ryni_profile", default=None)


def current_profile() -> CheckProfile | None:
    return _active.get()


@contextmanager
def profile_run(profile: CheckProfile | None) -> Iterator[None]:
    token = _active.set(profile)
    try:
        yield
    finally:
        _active.reset(token)


def measure(kind: str, name: str):
    """Internal instrumentation; no clock reads when profiling is disabled."""
    profile = current_profile()
    return nullcontext() if profile is None else profile.measure(kind, name)
