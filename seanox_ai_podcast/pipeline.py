# seanox_ai_podcast/pipeline.py

import base64
import logging
import os

import numpy
import re
import requests
import wave
import yaml

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


def _create_segment_wav(service: Service, segment: structure.Segment, workspace: Path, simulate: bool = False) -> None:

    output = Path(workspace, f"0x{segment.hash()}.wav")

    if simulate:
        payload = Template(service.body).render(speaker=segment.speaker, segment=segment)
        payload = re.sub(r"\s*[\r\n]+\s*", " ", payload)
        data = {
            "url": service.url,
            "headers": service.headers,
            "payload": payload,
            "proxies": service.proxy,
            "timeout": service.timeout
        }
        data = yaml.dump(data, sort_keys=False, default_flow_style=False, allow_unicode=True)
        data = os.linesep.join("\t" + line for line in data.splitlines())
        LOGGING.info(f"- {output}{os.linesep}{data}")
        return

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
        data = numpy.frombuffer(frames, dtype=numpy.int16)
    return data, params


def _mix_podcast_wav(podcast, workspace: Path, target: Path, simulate: bool = False):

    if simulate:
        for segment in podcast.segments:
            file = workspace / f"0x{segment.hash()}.wav"
            LOGGING.info(f"- {file}")
        return

    # Create an empty audio mix buffer with an extended range (safe headroom)
    # to prevent overflow during mixing. Standard WAV audio data is usually
    # 16-bit, but for mixing the bit depth is temporarily increased to 32-bit.
    # At the end, the signal is clipped and converted back to the 16-bit range
    # required for WAV output.
    mixed = numpy.zeros(0, dtype=numpy.int32)

    for segment in podcast.segments:
        file = workspace / f"0x{segment.hash()}.wav"

        LOGGING.info(f"- {file}")
        with wave.open(str(file), "rb") as input:
            params = input.getparams()
            frames = input.readframes(input.getnframes())
            data = numpy.frombuffer(frames, dtype=numpy.int16)

        sample_rate = params.framerate
        samples_per_ms = sample_rate / 1000
        overlap_samples = int(round(segment.offset * samples_per_ms))

        if mixed.size == 0:
            mixed = data.astype(numpy.int32)
            continue

        # For mixing (overlap), the audio blocks are simply joined.
        # The audio buffer must be increased accordingly.
        start = max(0, mixed.size - overlap_samples)
        end = start + data.size
        if end > mixed.size:
            mixed = numpy.pad(mixed, (0, end - mixed.size))
        mixed[start:end] += data.astype(numpy.int32)

    # For a soft fade-out, 250 ms of silence is added.
    silence_duration = 0.250
    silence_samples = int(silence_duration * sample_rate)
    silence = numpy.zeros(silence_samples, dtype=mixed.dtype)
    mixed = numpy.concatenate([mixed, silence])

    # Limit the mixed signal to the valid 16-bit range to prevent overflow when
    # reducing the bit depth. During mixing, values may exceed the 16-bit limits
    # due to summation. Therefore, the signal is first clipped to [-32768, 32767]
    # and then converted from 32-bit back to 16-bit, which is required for
    # standard WAV output.
    mixed = numpy.clip(mixed, -32768, 32767).astype(numpy.int16)

    with wave.open(str(target), "wb") as output:
        output.setparams(params)
        output.writeframes(mixed.astype(numpy.int16).tobytes())


def pipeline(source: str | Path, workspace: str | Path = None, simulate: bool = False) -> None:

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

    simulation = "[SIMULATION] " if simulate else ""

    # Irrelevant segments are cleaned up.
    # Irrelevant means all existing segments that do not match any of the
    # current segments based on their hash values.
    LOGGING.info(f"{simulation}Cleaning up obsolete segments")
    segments = [segment.hash() for segment in podcast.segments]
    for file in workspace.glob("*.wav"):
        match = PATTERN_SEGMENT_WAV_FILE.match(file.name)
        if match and match.group(1) not in segments:
            LOGGING.info(f"- {file}")
            if not simulate:
                file.unlink()

    LOGGING.info(f"{simulation}Creating new segments")
    for segment in podcast.segments:
        file = workspace / f"0x{segment.hash()}.wav"
        if file.exists():
            continue
        if not simulate:
            LOGGING.info(f"- {file}")
        _create_segment_wav(podcast.audio.service, segment, workspace, simulate)

    target = source.with_suffix(".wav")
    LOGGING.info(f"{simulation}Mixing and cutting {target}")
    _mix_podcast_wav(podcast, workspace, target, simulate)

    LOGGING.info("Done")


class PipelineError(Exception):

    def __init__(self, message: str, details: str = None):
        super().__init__(message.strip() if message and message.strip() else None)
        self.details = details.strip() if details and details.strip() else None

    def __str__(self):
        if self.details:
            return f"{super().__str__()} -- {self.details}"
        return super().__str__()
