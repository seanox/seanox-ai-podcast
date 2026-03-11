# seanox_ai_podcast/structure.py

import hashlib
import os
import re

from dataclasses import dataclass, field, fields
from itertools import chain
from pathlib import Path
from typing import Any

import yaml

PATTERN_NORMALIZE_BOUNDARY_WHITESPACE = re.compile(r"(?<=\W)\s+|\s+(?=\W)")
PATTERN_NORMALIZE_SYMBOLS = re.compile(r"[\x00-\x1F\s]+")
PATTERN_VARIABLE_EXPRESSION = re.compile(r"\$\{([^}]+)\}")


class HashableStruct:

    @staticmethod
    def _normalize(value: Any) -> str:
        value = str(value or "").strip().lower()
        value = PATTERN_NORMALIZE_BOUNDARY_WHITESPACE.sub("", value)
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
            values.append(list(self._flatten(value)))
        data = "\0".join(chain.from_iterable(values))
        return hashlib.sha512(data.encode("utf-8")).hexdigest().upper()


@dataclass
class Audio(HashableStruct):
    pass


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
        if not self.name.strip():
            raise ValueError("speaker.name is required")
        if not self.language.strip():
            raise ValueError("speaker.language is required")
        if not self.voice.strip():
            raise ValueError("speaker.voice is required")


@dataclass
class Segment(HashableStruct):
    meta: str
    speaker: Speaker
    offset: int = field(hash=False)
    text: str = ""
    prompt: str = ""

    def __post_init__(self):
        if not self.meta.strip():
            raise ValueError("segment.meta is required")
        if not self.speaker:
            raise ValueError("segment.speaker is required")
        if not self.text.strip():
            raise ValueError("segment.text is required")
        if not isinstance(self.offset, int):
            raise ValueError("segment.offset must be an integer")


@dataclass
class Podcast(HashableStruct):
    audio: Audio
    speakers: dict[str, Speaker]
    segments: list[Segment]

    def __post_init__(self):
        if not self.audio:
            raise ValueError("audio is required")
        if not self.speakers:
            raise ValueError("speakers is required")
        if not self.segments:
            raise ValueError("segments are required")


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
            raise ValueError(message)
        return value

    # Required value (empty allowed): ${KEY?error}
    if "?" in expression:
        key, message = expression.split("?", 1)
        if key not in os.environ:
            raise ValueError(message)
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


def parser(source: str | Path) -> Podcast:

    if isinstance(source, Path):
        with open(source, 'r', encoding='utf-8') as file:
            source = file.read()
    source = PATTERN_VARIABLE_EXPRESSION.sub(_substitute_expression_match, source)

    structure = yaml.safe_load(source)

    audio = Audio()

    speakers = {}
    for name, meta in structure.get("speakers", {}).items():
        speaker = Speaker(
            name=name,
            language=meta["language"],
            voice=meta["voice"],
            gender=meta["gender"],
            age=meta["age"],
            characters=meta["characters"],
            education=meta["education"],
            personality=meta["personality"]
        )
        speakers[name.lower()] = speaker

    meta = " ".join(
        [audio.hash().lower()] +
        [speakers[name].hash().lower() for name in sorted(speakers)]
    )

    segments = []
    for segment in structure.get("segments", []):
        speaker = str(segment.get("speaker") or "").lower()
        segments.append(Segment(
            meta=meta,
            speaker=speakers[speaker],
            offset=segment["offset"],
            text=segment["text"],
            prompt=segment["prompt"]
        ))

    return Podcast(
        audio=audio,
        speakers=speakers,
        segments=segments)
