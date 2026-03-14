# seanox_ai_podcast/modules/abstract.py

from dataclasses import dataclass
from typing import Callable, Any


@dataclass
class AudioService():
    url: str
    body: str
    headers: dict[str, str] | None = None
    decode: Callable[[Any], bytes] | None = None

    def __init__(self, data: dict):
        pass
