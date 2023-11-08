import os
from typing import TypeVar, Callable, Optional

T = TypeVar('T')


def env(key, cast: Callable[[str], T], default: Optional[T]) -> T:
    return cast(os.environ.get(key, default))


UBOOTP_ADDRESS = env("MULTICAST_ADDRESS", str, "239.0.1.64")
UBOOTP_PORT = env("MULTICAST_PORT", int, 42069)
UBOOTP_BIND = env("MULTICAST_BIND", str, default="0.0.0.0")

