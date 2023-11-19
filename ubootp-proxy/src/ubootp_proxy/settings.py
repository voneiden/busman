import os
from typing import TypeVar, Callable

T = TypeVar("T")


def env(key, cast: Callable[[str], T], default: str) -> T:
    return cast(os.environ.get(key, default))


BROADCAST_ADDRESS = env("BROADCAST_ADDRESS", str, "255.255.255.255")
BROADCAST_PORT = env("BROADCAST_PORT", int, "42069")
MULTICAST_ADDRESS = env("MULTICAST_ADDRESS", str, "239.0.1.64")
MULTICAST_PORT = env("MULTICAST_PORT", int, "42069")
MULTICAST_BIND = env("MULTICAST_BIND", str, default="0.0.0.0")
