# seanox_ai_podcast/pipeline.py

import base64
import logging
import numpy as np
import re
import requests
import wave

from jinja2 import Template
from pathlib import Path
from typing import Any

from seanox_ai_podcast import structure
from seanox_ai_podcast.structure import Service

LOGGING = logging.getLogger(__name__)
LOGGING.addHandler(logging.NullHandler())

PATTERN_SEGMENT_WAV_FILE = re.compile(r"^0x((?:[0-9a-fA-F]{32})+)\.wav$")
PATTERN_BASE64_ENCODING = re.compile(r"^[A-Za-z0-9+/=]+$")


def _fetch_json_audio(data: Any, signature: bytes = None) -> bytes | None:
    if isinstance(data, dict):
        for value in data.values():
            result = _fetch_json_audio(value, signature)
            if result:
                return result
    elif isinstance(data, list):
        for item in data:
            result = _fetch_json_audio(item, signature)
            if result:
                return result
    elif isinstance(data, str):
        if PATTERN_BASE64_ENCODING.fullmatch(data):
            decoded = base64.b64decode(data, validate=True)
            if signature and not decoded.startswith(signature):
                return None
            return decoded
    return None


def _create_segment_wav(service: Service, segment: structure.Segment, workspace: Path) -> None:

    output = Path(workspace, f"0x{segment.hash()}.wav")

    response = requests.post(
        service.url,
        headers=service.headers,
        data=Template(service.body).render(speaker=segment.speaker, segment=segment),
        proxies=service.proxy,
        timeout=service.timeout
    )

    data = service.decode(response)
    if not data or data[:4] != b"RIFF":
        raise PipelineError("Invalid WAV response from TTS service")
    with open(output, "wb") as file:
        file.write(data)


def read_wav(path: Path):
    with wave.open(str(path), "rb") as w:
        params = w.getparams()
        frames = w.readframes(w.getnframes())
        data = np.frombuffer(frames, dtype=np.int16)
    return data, params


def _mix_podcast_wav(podcast, workspace: Path, target: Path):

    # Create an empty audio mix buffer with an extended range (safe headroom)
    # to prevent overflow during mixing. Standard WAV audio data is usually
    # 16-bit, but for mixing the bit depth is temporarily increased to 32-bit.
    # At the end, the signal is clipped and converted back to the 16-bit range
    # required for WAV output.
    mixed = np.zeros(0, dtype=np.int32)

    for segment in podcast.segments:
        file = workspace / f"0x{segment.hash()}.wav"

        with wave.open(str(file), "rb") as input:
            params = input.getparams()
            frames = input.readframes(input.getnframes())
            data = np.frombuffer(frames, dtype=np.int16)

        sample_rate = params.framerate
        samples_per_ms = sample_rate / 1000
        overlap_samples = int(round(segment.offset * samples_per_ms))

        if mixed.size == 0:
            mixed = data.astype(np.int32)
            continue

        # For mixing (overlap), the audio blocks are simply joined.
        # The audio buffer must be increased accordingly.
        start = max(0, mixed.size - overlap_samples)
        end = start + data.size
        if end > mixed.size:
            mixed = np.pad(mixed, (0, end - mixed.size))
        mixed[start:end] += data.astype(np.int32)

    # For a soft fade-out, 250 ms of silence is added.
    silence_duration = 0.250
    silence_samples = int(silence_duration * sample_rate)
    silence = np.zeros(silence_samples, dtype=mixed.dtype)
    mixed = np.concatenate([mixed, silence])

    # Limit the mixed signal to the valid 16-bit range to prevent overflow when
    # reducing the bit depth. During mixing, values may exceed the 16-bit limits
    # due to summation. Therefore, the signal is first clipped to [-32768, 32767]
    # and then converted from 32-bit back to 16-bit, which is required for
    # standard WAV output.
    mixed = np.clip(mixed, -32768, 32767).astype(np.int16)

    with wave.open(str(target), "wb") as output:
        output.setparams(params)
        output.writeframes(mixed.astype(np.int16).tobytes())


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
    def __init__(self, message: str, details: str = None):
        super().__init__(message)


class PipelineError(Exception):

    def __init__(self, message: str, details: str = None):
        super().__init__(message.strip() if message and message.strip() else None)
        self.details = details.strip() if details and details.strip() else None

    def __str__(self):
        if self.details:
            return f"{super().__str__()} -- {self.details}"
        return super().__str__()
