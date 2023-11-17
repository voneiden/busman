import os
from typing import Callable, TypeVar

T = TypeVar("T")


def env(key, cast: Callable[[str], T], default: str) -> T:
    return cast(os.environ.get(key, default))


BUSROUTER_HOST = env("BUSROUTER_HOST", str, "0.0.0.0")
BUSROUTER_PORT = env("BUSROUTER_PORT", int, "42069")
MAPPER_SETUP_URL = env("MAPPER_SETUP_URL", str, "http://localhost:8000/v1/mapping")
