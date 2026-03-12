# seanox_ai_podcast/structure.py

import hashlib
import os
import re

from dataclasses import dataclass, field, fields
from itertools import chain
from urllib.parse import urlparse

from jinja2 import Template
from pathlib import Path
from typing import Any

import yaml

PATTERN_NORMALIZE_SYMBOLS = re.compile(r"[\x00-\x1F\s]+")
PATTERN_VARIABLE_EXPRESSION = re.compile(r"\$\{([^}]+)\}")


class HashableStruct:

    @staticmethod
    def _normalize(value: Any) -> str:
        value = str(value or "").strip().lower()
        value = PATTERN_NORMALIZE_SYMBOLS.sub(" ", value)
        return value

    def _flatten(self, value):
        if value is None:
            yield ""
        elif isinstance(value, HashableStruct):
            yield value.hash()
        elif isinstance(value, dict):
            for value in value.values():
                yield from self._flatten(value)
        elif isinstance(value, (list, tuple, set)):
            for entry in value:
                yield from self._flatten(entry)
        else:
            yield self._normalize(value)

    def hash(self) -> str:
        values = []
        for field in fields(self):
            if field.hash is False:
                continue
            value = getattr(self, field.name)
            values.append(self._flatten(value))
        data = "\0".join(chain.from_iterable(values))
        return hashlib.sha512(data.encode("utf-8")).hexdigest().upper()


@dataclass
class Service(HashableStruct):

    timeout: int = field(hash=False)
    url: str
    body: str
    headers: dict[str, str] | None = None

    _proxy: str = field(default="", hash=False, repr=False)

    def __post_init__(self):
        if not self.url or not self.url.strip():
            raise ValueError("YAML [structure]: audio.service.url is required")
        if not self.headers:
            raise ValueError("YAML [structure]: audio.service.headers is required")
        if not self.body or not self.body.strip():
            raise ValueError("YAML [structure]: audio.service.body is required")
        if self.timeout and not isinstance(self.timeout, int):
            raise ValueError("YAML [structure]: audio.service.timeout must be an integer")
        if self._proxy and self._proxy.strip():
            try:
                proxy = urlparse(self._proxy)
                if proxy.scheme.lower() not in ("http", "https", "socks5", "socks4"):
                    raise ValueError
                if not proxy.hostname:
                    raise ValueError
            except Exception:
                raise ValueError("YAML [structure]: audio.service.proxy valid URL required")#
        self.timeout = None if not self.timeout or self.timeout <= 0 else self.timeout / 1000
        self.headers = {key: str(value) for key, value in self.headers.items()}

    @property
    def proxy(self) -> dict | None:
        if not self._proxy:
            return None
        proxy = urlparse(self._proxy)
        return {proxy.scheme.lower(): self._proxy}

    @proxy.setter
    def proxy(self, value: str):
        self._proxy = value


@dataclass
class Audio(HashableStruct):
    service: Service | None = None

    def __post_init__(self):
        if not self.service:
            raise ValueError("YAML [structure]: audio.service is required")


@dataclass
class Speaker(HashableStruct):
    name: str
    language: str
    voice: str
    gender: str
    age: str
    characters: list[str] | None = None
    education: list[str] | None = None
    personality: list[str] | None = None

    def __post_init__(self):
        if not self.name or not self.name.strip():
            raise ValueError("YAML [structure]: speaker.name is required")
        if not self.language or not self.language.strip():
            raise ValueError("YAML [structure]: speaker.language is required")
        if not self.voice or not self.voice.strip():
            raise ValueError("YAML [structure]: speaker.voice is required")


@dataclass
class Segment(HashableStruct):
    meta: str
    speaker: Speaker
    offset: int = field(hash=False)
    text: str = ""
    prompt: str = ""

    def __post_init__(self):
        if not self.meta or not self.meta.strip():
            raise ValueError("YAML [structure]: segment.meta is required")
        if not self.speaker:
            raise ValueError("YAML [structure]: segment.speaker is required")
        if not self.text or not self.text.strip():
            raise ValueError("YAML [structure]: segment.text is required")
        if self.offset and not isinstance(self.offset, int):
            raise ValueError("YAML [structure]: segment.offset must be an integer")


@dataclass
class Podcast(HashableStruct):
    audio: Audio
    speakers: dict[str, Speaker]
    segments: list[Segment]

    def __post_init__(self):
        if not self.audio:
            raise ValueError("YAML [structure]: audio is required")
        if not self.speakers:
            raise ValueError("YAML [structure]: speakers is required")
        if not self.segments:
            raise ValueError("YAML [structure]: segments are required")


def _substitute_expression_match(match: re.Match) -> str:
    """
    Inspired by the interpolation syntax in Docker (Compose).
    BUT WITHOUT NESTING!

    Direct substitution
    - ${VAR} -> value of VAR

    Default value
    - ${VAR:-default} -> value of VAR if set and non-empty, otherwise default
    - ${VAR-default} -> value of VAR if set, otherwise default

    Required value
    - ${VAR:?error} -> value of VAR if set and non-empty, otherwise raise an error
    - ${VAR?error} -> value of VAR if set, otherwise raise an error

    Alternative value
    - ${VAR:+replacement} -> replacement if VAR is set and non-empty, otherwise empty
    - ${VAR+replacement} -> replacement if VAR is set, otherwise empty

    Notes
    - No nesting inside the expression is supported.
    - "set" means the key exists as environment variable (value is not None).
    - "non-empty" means the value of the environment variable is not an empty string.
    - For error forms the provided message is used as the ValueError message.
    """

    expression = match.group(1)

    # Default if unset or empty: ${KEY:-default}
    if ":-" in expression:
        key, default = expression.split(":-", 1)
        value = os.environ.get(key)
        return value if value not in (None, "") else default

    # Default if unset: ${KEY-default}
    if "-" in expression:
        key, default = expression.split("-", 1)
        if key in os.environ:
            return os.environ[key]
        return default

    # Required value: ${KEY:?error}
    if ":?" in expression:
        key, message = expression.split(":?", 1)
        value = os.environ.get(key)
        if value is None or value == "":
            raise ValueError(f"YAML [structure]: {message}")
        return value

    # Required value (empty allowed): ${KEY?error}
    if "?" in expression:
        key, message = expression.split("?", 1)
        if key not in os.environ:
            raise ValueError(f"YAML [structure]: {message}")
        return os.environ[key]

    # Alternative if set and non-empty: ${KEY:+replacement}
    if ":+" in expression:
        key, replacement = expression.split(":+", 1)
        value = os.environ.get(key)
        return replacement if value not in (None, "") else ""

    # Alternative if set (empty allowed): ${KEY+replacement}
    if "+" in expression:
        key, replacement = expression.split("+", 1)
        return replacement if key in os.environ else ""

    # Simple substitution: ${KEY}
    return os.environ.get(expression, "")


def parse(source: str | Path) -> Podcast:

    if isinstance(source, Path):
        with open(source, 'r', encoding='utf-8') as file:
            source = file.read()
    source = PATTERN_VARIABLE_EXPRESSION.sub(_substitute_expression_match, source)

    structure = yaml.safe_load(source)

    service = structure.get("audio", {}).get("service", {})
    audio = Audio(
        service=Service(
            url=service.get("url"),
            proxy=service.get("proxy"),
            headers=service.get("headers"),
            body=service.get("body"),
            timeout=service.get("timeout", -1)
        )
    )

    speakers = {}
    for name, speaker in structure.get("speakers", {}).items():
        if name.lower() in speakers:
            raise ValueError(f"YAML [structure]: speakers ambiguous speaker found")
        speaker = Speaker(
            name=speaker.get("name"),
            language=speaker.get("language"),
            voice=speaker.get("voice"),
            gender=speaker.get("gender"),
            age=speaker.get("age"),
            characters=speaker.get("characters"),
            education=speaker.get("education"),
            personality=speaker.get("personality")
        )
        speakers[name.lower()] = speaker

    meta = " ".join(
        [audio.hash()] +
        [speakers[name.lower()].hash() for name in sorted(speakers)]
    )

    segments = []
    for segment in structure.get("segments", []):
        speaker = segment.get("speaker", "").lower()
        speaker = speakers.get(speaker)
        if not speaker:
            raise ValueError("YAML [structure]: segment.speaker is required")
        segments.append(Segment(
            meta=meta,
            speaker=speaker,
            offset=segment.get("offset") or 0,
            text=Template(segment.get("text")).render(speaker=speaker).strip(),
            prompt=Template(segment.get("prompt") or "").render(speaker=speaker).strip()
        ))

    return Podcast(
        audio=audio,
        speakers=speakers,
        segments=segments
    )
