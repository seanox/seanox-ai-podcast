# seanox_ai_podcast/modules/generativelanguage_googleapis_com.py

import base64
import io
import jmespath
import json
import re
import wave

from dataclasses import dataclass
from requests import Response


def _parse_audio_meta(meta: str) -> dict:
    meta = meta.replace('/', '=', 1)
    meta = dict(part.split('=') for part in meta.split(';'))
    return {
        "sample-rate": int(meta.get("rate", 24000)),
        "sample-width": 2 if "L16" in meta.get("audio", "") else 1,
        "channels": 1
    }


@dataclass(frozen=True)
class GoogleGenerativeLanguageService:
    url: str
    body: str
    headers: dict[str, str] | None = None

    def __init__(self, data: dict):

        from seanox_ai_podcast.modules.abstract import AbstractDynamicDataclass
        data = AbstractDynamicDataclass.create(data, [
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
                    "text": "{{ segment.prompt | tojson }}: {{ segment.text | tojson }}"
                }]
            }],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {
                            "voiceName": "{{ speaker.voice | tojson }}"
                        }
                    }
                }
            }
        }))

    def decode(self, response: Response) -> bytes:

        from seanox_ai_podcast.modules.abstract import AudioServiceError
        if response.status_code != 200:
            data = response.json()
            message = jmespath.search("error.message", data)
            raise AudioServiceError(f"Unexpected HTTP response: {response.status_code} {response.reason}", message)

        content_type = response.headers.get("Content-Type", "")
        if not re.search(r"\bapplication/json\b", content_type, re.IGNORECASE):
            raise AudioServiceError(f"Unexpected Content-Type: {content_type}")

        data = response.json()
        meta = _parse_audio_meta(
            jmespath.search("candidates[0].content.parts[0].inlineData.mimeType", data)
        )
        audio = base64.b64decode(
            jmespath.search("candidates[0].content.parts[0].inlineData.data", data)
        )

        with io.BytesIO() as buffer:
            with wave.open(buffer, 'wb') as wav:
                wav.setnchannels(meta['channels'])
                wav.setsampwidth(meta['sample-width'])
                wav.setframerate(meta['sample-rate'])
                wav.writeframes(audio)
            wav_bytes = buffer.getvalue()
        return wav_bytes
