import os
from typing import TypeVar, Callable, Optional

T = TypeVar("T")


def env(key, cast: Callable[[str], T], default: Optional[T]) -> T:
    return cast(os.environ.get(key, default))


BUSROUTER_HOST = env("BUSROITER_HOST", str, "0.0.0.0")
BUSROUTER_PORT = env("BUSROUTER_PORT", int, 42069)
