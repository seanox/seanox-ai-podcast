# seanox_ai_podcast/modules/abstract.py

import logging
import re

from dataclasses import dataclass
from requests import Response
from typing import Callable

from seanox_ai_podcast.modules import (
    GoogleGenerativeLanguageService, GoogleCloudService
)

LOGGING = logging.getLogger(__name__)
LOGGING.addHandler(logging.NullHandler())


def check_inconsistent_service_configuration(data: dict):
    if not data:
        return
    if any(key in data for key in ("url", "body", "headers")):
        LOGGING.warning("YAML [structure]: audio.service.provider is used; url, body, headers are ignored.")


@dataclass(frozen=True)
class AudioService():
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
        provider = data.get("provider", {})
        if provider:
            name = provider.get("name", "")
            if not name:
                LOGGING.warning("YAML [structure]: audio.service.provider.name is required")
            match name.lower():
                case "generativelanguage.googleapis.com":
                    check_inconsistent_service_configuration(data)
                    service = GoogleGenerativeLanguageService(data)
                case "texttospeech.googleapis.com":
                    check_inconsistent_service_configuration(data)
                    service = GoogleCloudService(data)
                case _:
                    raise AudioServiceError(f"YAML [structure]: audio.service.provider {provider or 'None'} is not supported")
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
        object.__setattr__(self, "url", data.get("url", ""))
        object.__setattr__(self, "headers", data.get("headers", {}))
        object.__setattr__(self, "body", data.get("body", ""))

    def decode(self, response: Response) -> bytes:

        if response.status_code != 200:
            raise AudioServiceError(f"Unexpected HTTP response: {response.status_code} {response.reason}".strip())

        content_type = response.headers.get("Content-Type", "")
        if not re.search(r"\baudio/wav\b", content_type, re.IGNORECASE):
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
        super().__init__(message)
        self.details = details

    def __str__(self):
        if self.details:
            return f"{super().__str__()} -- {self.details}"
        return super().__str__()
