# seanox_ai_podcast/structure.py

import hashlib
import os
import re
import yaml

from itertools import chain
from pathlib import Path
from typing import Any

ENVIRONMENT = {key.lower(): value for key, value in os.environ.items()}

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
        data = "\0".join(
            chain.from_iterable(
                self._flatten(value) for value in vars(self).values()))
        return hashlib.sha256(data.encode("utf-8")).hexdigest().upper()


class Audio(HashableStruct):
    pass


class Speaker(HashableStruct):
    def __init__(self, name: str, language: str, voice: str, gender: str, age: str,
                 characters: [str], education: [str], personality: [str]):
        self.name = name
        self.language = language
        self.voice = voice
        self.gender = gender
        self.age = age
        self.characters = characters
        self.education = education
        self.personality = personality


class Segment(HashableStruct):
    def __init__(self, meta: str, speaker: str, offset: int, text: str, prompt: str):
        self.meta = meta
        self.speaker = speaker
        self.offset = offset
        self.text = text
        self.prompt = prompt


class Podcast(HashableStruct):
    def __init__(self, audio: Audio, speakers: dict, segments: [Segment]):
        self.audio = audio
        self.speakers = speakers
        self.segments = segments


def _substitute_expression_match(match: re.Match) -> str:

    expression = match.group(1)

    # syntax: ${VAR:-default} (fallback value)
    if ":-" in expression:
        key, default = expression.split(":-", 1)
        return ENVIRONMENT.get(key.lower(), default)

    # syntax: ${VAR:?error} (error if variable is missing)
    if ":?" in expression:
        key, message = expression.split(":?", 1)
        if key.lower() not in ENVIRONMENT:
            raise ValueError(f"Error: {message}")
        return ENVIRONMENT[key.lower()]

    # syntax: ${VAR} (standard case)
    return ENVIRONMENT.get(expression.lower(), "")


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
        speakers[name] = speaker

    meta = " ".join(
        [audio.hash().lower()] +
        [speakers[name].hash().lower() for name in sorted(speakers)]
    )

    segments = []
    for segment in structure.get("segments", []):
        speaker = speakers[segment["speaker"]]
        segments.append(Segment(
            meta=meta,
            speaker=speaker,
            offset=segment["offset"],
            text=segment["text"],
            prompt=segment["prompt"]
        ))

    return Podcast(
        audio=audio,
        speakers=speakers,
        segments=segments)
