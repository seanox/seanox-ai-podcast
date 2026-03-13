# seanox_ai_podcast/pipeline.py

import base64
import json
import logging
import re
import requests

from jinja2 import Template
from pathlib import Path

from seanox_ai_podcast import structure
from seanox_ai_podcast.structure import Service

LOGGING = logging.getLogger(__name__)
LOGGING.addHandler(logging.NullHandler())

PATTERN_SEGMENT_WAV_FILE = re.compile(r"^0x((?:[0-9a-fA-F]{32})+)\.wav$")


def _create_segment_wav(service: Service, segment: structure.Segment, workspace: Path) -> None:

    output = Path(workspace, f"0x{segment.hash()}.wav")

    response = requests.post(
        service.url,
        headers=service.headers,
        data=Template(service.body).render(speaker=segment.speaker, segment=segment),
        proxies=service.proxy,
        timeout=service.timeout
    )
    if response.status_code != 200:
        raise PipelineError(f"Unexpected HTTP response: {response.status_code}")

    if re.search(r"\baudio/wav\b", response.headers.get("Content-Type", ""), re.IGNORECASE):
        with open(output, "wb") as file:
            for index, chunk in enumerate(response.iter_content(chunk_size=8192)):
                if index <= 0:
                    if chunk[:4] != b'RIFF':
                        raise PipelineError("Invalid WAV response from TTS service")
                file.write(chunk)
        return

    if re.search(r"\bapplication/json\b", response.headers.get("Content-Type", ""), re.IGNORECASE):
        try:
            data = response.json()
        except json.JSONDecodeError:
            raise PipelineError("Invalid JSON response from TTS service")
        data = data.get("audioContent")
        if not data:
            raise PipelineError("Invalid JSON response from TTS service")
        with open(output, "wb") as file:
            file.write(base64.b64decode(data))
        return

    raise PipelineError(f"Unsupported Content-Type: {response.headers.get('Content-Type')}")


def _mix_podcast_wav(podcast: structure.Podcast, workspace: Path, target: Path) -> None:
    pass


def pipeline(source: str | Path, workspace: str | Path = None) -> None:

    LOGGING.info(f"Seanox Podcast as Code [Version 0.0.0 00000000]")
    LOGGING.info(f"Copyright (C) 0000 Seanox Software Solutions")

    if not source or not str(source).strip():
        raise ValueError("Source is required")
    source = Path(source)
    if not source.exists() or not source.is_file():
        raise ValueError(f"Source {source} must be a file")

    if not workspace or not str(workspace).strip():
        workspace = source.parent
    workspace = Path(workspace)
    if workspace.exists() and not workspace.is_dir():
        raise ValueError(f"Workspace {workspace} must be a directory")

    LOGGING.info(f"Workspace {workspace}")
    if not workspace.exists():
        workspace.mkdir(exist_ok=True)

    LOGGING.info(f"Parsing {source}")
    podcast = structure.parse(source)

    # Irrelevant segments are cleaned up.
    # Irrelevant means all existing segments that do not match any of the
    # current segments based on their hash values.
    LOGGING.info("Cleaning up obsolete segments")
    segments = [segment.hash() for segment in podcast.segments]
    for file in workspace.glob("*.wav"):
        match = PATTERN_SEGMENT_WAV_FILE.match(file.name)
        if match and match.group(1) not in segments:
            LOGGING.info(f"- {file}")
            file.unlink()

    LOGGING.info("Creating new segments")
    for segment in podcast.segments:
        file = workspace / f"0x{segment.hash()}.wav"
        if file.exists():
            continue
        LOGGING.info(f"- {file}")
        _create_segment_wav(podcast.audio.service, segment, workspace)

    target = source.with_suffix(".wav")
    LOGGING.info(f"Mixing and cutting {target}")
    _mix_podcast_wav(podcast, workspace, target)

    LOGGING.info("Done")


class PipelineError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
