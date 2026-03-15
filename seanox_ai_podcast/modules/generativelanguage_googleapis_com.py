# seanox_ai_podcast/modules/generativelanguage_googleapis_com.py

import json
import re

from dataclasses import dataclass
from requests import Response


@dataclass(frozsen=True)
class GoogleGenerativeLanguageService:
    url: str
    body: str
    headers: dict[str, str] | None = None

    def __init__(self, data: dict):

        from seanox_ai_podcast.modules.abstract import AbstractAudioService
        data = AbstractAudioService.create_dataclass(data, [
            "model", "version", "api-key", "text", "prompt"
        ])

        object.__setattr__(self, "url", f"https://generativelanguage.googleapis.com/v1beta/models/{data.model}:generateContent")
        object.__setattr__(self, "headers", {
            "x-goog-api-key": data.api_key,
            "Content-Type": "application/json; charset=utf-8",
        })
        object.__setattr__(self, "body", json.dumps({
            "model": data.model,
            "contents": [{
                "parts": [{
                    "text": "{{ segment.prompt }}: {{ segment.text }}"
                }]
            }],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {
                            "voiceName": "{{ speaker.voice }}"
                        }
                    }
                }
            }
        }))

    def decode(self, response: Response) -> bytes:

        from seanox_ai_podcast.modules.abstract import AudioServiceError
        if response.status_code != 200:
            raise AudioServiceError(f"Unexpected HTTP response: {response.status_code} {response.reason}")

        content_type = response.headers.get("Content-Type", "")
        if not re.search(r"\bapplication/json\b", content_type, re.IGNORECASE):
            raise AudioServiceError(f"Unexpected Content-Type: {content_type}")
        # TODO:
