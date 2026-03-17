# seanox_ai_podcast/modules/abstract.py

import logging
import jmespath
import re

from dataclasses import dataclass, make_dataclass
from requests import Response
from typing import Callable, Any, Optional

LOGGING = logging.getLogger(__name__)
LOGGING.addHandler(logging.NullHandler())


@dataclass(frozen=True)
class AbstractDynamicDataclass:

    @staticmethod
    def create(data: dict, required: list[str], optional: list[str] = None) -> Any:

        missing = [key for key in required if not data.get(key)]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")

        PATTERN_NORMALIZE = re.compile("[^0-9a-zA-Z]+")

        fields = []
        values = {}

        for key in required + (optional or []):
            if not key or key[0].isdigit():
                continue
            value = data.get(key)
            field = PATTERN_NORMALIZE.sub("_", key.lower())
            if key in required:
                if value is None:
                    raise ValueError(f"Missing required fields: {', '.join(missing)}")
                fields.append((field, type(value), value))
            else:
                fields.append((field, Optional[type(value)], value))
            values[field] = value

        return make_dataclass("__dataclass", fields)(**values)


@dataclass(frozen=True)
class AbstractAudioService:

    @staticmethod
    def check_inconsistent_service_configuration(data: dict):
        if not data:
            return
        if any(key in data for key in ("url", "body", "headers")):
            LOGGING.warning("YAML [structure]: audio.service.provider is used, so the url, body, and headers are ignored")


@dataclass(frozen=True)
class AudioService:
    url: str
    body: str
    headers: dict[str, str] | None = None
    decode: Callable[[Response], bytes] | None = None

    def __init__(self, data: dict):
        if "provider" not in data:
            service = StandardAudioService(data)
            object.__setattr__(self, "url", service.url)
            object.__setattr__(self, "headers", service.headers)
            object.__setattr__(self, "body", service.body)
            object.__setattr__(self, "decode", service.decode)
            return
        provider = (jmespath.search("provider.name", data) or "").strip()
        match provider.lower():
            case "generativelanguage.googleapis.com":
                AbstractAudioService.check_inconsistent_service_configuration(data)
                from seanox_ai_podcast.modules import GoogleGenerativeLanguageService
                service = GoogleGenerativeLanguageService(data["provider"])
            case "texttospeech.googleapis.com":
                AbstractAudioService.check_inconsistent_service_configuration(data)
                from seanox_ai_podcast.modules import GoogleCloudService
                service = GoogleCloudService(data["provider"])
            case _:
                if not provider:
                    raise AudioServiceError(f"YAML [structure]: audio.service.provider is required")
                raise AudioServiceError(f"YAML [structure]: audio.service.provider {provider} is not supported")
        object.__setattr__(self, "url", service.url)
        object.__setattr__(self, "headers", service.headers)
        object.__setattr__(self, "body", service.body)
        object.__setattr__(self, "decode", service.decode)


@dataclass(frozen=True)
class StandardAudioService:
    url: str
    body: str
    headers: dict[str, str] | None = None

    def __init__(self, data: dict):
        data = AbstractDynamicDataclass.create(data, [
            "url", "headers", "body"
        ])
        object.__setattr__(self, "url", data.url)
        object.__setattr__(self, "headers", data.headers)
        object.__setattr__(self, "body", data.body)

    def decode(self, response: Response) -> bytes:

        if response.status_code != 200:
            raise AudioServiceError(f"Unexpected HTTP response: {response.status_code} {response.reason}")

        content_type = response.headers.get("Content-Type", "")
        if not re.search(r"\baudio/(x-)?wav\b", content_type, re.IGNORECASE):
            raise AudioServiceError(f"Unexpected Content-Type: {content_type or 'None'}")
        chunks = []
        for index, chunk in enumerate(response.iter_content(chunk_size=8192)):
            if index == 0:
                if chunk[:4] != b"RIFF":
                    raise AudioServiceError("Invalid WAV response from TTS service")
            chunks.append(chunk)
        return b"".join(chunks)


class AudioServiceError(Exception):

    def __init__(self, message: str, details: str = None):
        super().__init__(message.strip() if message and message.strip() else None)
        self.details = details.strip() if details and details.strip() else None

    def __str__(self):
        if self.details:
            return f"{super().__str__()} -- {self.details}"
        return super().__str__()
