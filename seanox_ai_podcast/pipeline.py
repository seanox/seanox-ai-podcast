# seanox_ai_podcast/pipeline.py
import logging
import re

from pathlib import Path

from seanox_ai_podcast import structure

LOGGING = logging.getLogger(__name__)
LOGGING.addHandler(logging.NullHandler())

PATTERN_SEGMENT_WAV_FILE = re.compile(r"^0x((?:[0-9a-fA-F]{32})+)\.wav$")


def _create_segment_wav(segment: structure.Segment, workspace: Path):
    output = Path(workspace, f"0x{segment.hash()}.wav")
    output.touch(exist_ok=True)
    print(output)


def _mix_podcast_wav(podcast: structure.Podcast, workspace: Path, target: Path):
    pass


def pipeline(source: str | Path, workspace: str | Path = None) -> None:

    LOGGING.info(f"Podcast as Code [Version 0.0.0 00000000]")
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

    LOGGING.info(f"Parsing {source}")
    podcast = structure.parse(source)

    if not workspace.exists():
        LOGGING.info(f"Creating workspace directory {workspace}")
        workspace.mkdir(exist_ok=True)

    # Irrelevant segments are cleaned up.
    # Irrelevant means all existing segments that do not match any of the
    # current segments based on their hash values.
    LOGGING.info("Cleaning up obsolete segments")
    segments = [segment.hash() for segment in podcast.segments]
    for file in workspace.glob("*.wav"):
        match = PATTERN_SEGMENT_WAV_FILE.match(file.name)
        if match and match.group(1) not in segments:
            file.unlink()

    LOGGING.info("Creating new segments")
    for segment in podcast.segments:
        file = workspace / f"0x{segment.hash()}.wav"
        if file.exists():
            continue
        _create_segment_wav(segment, workspace)

    target = source.with_suffix(".wav")
    LOGGING.info(f"Mixing and cutting {target}")
    _mix_podcast_wav(podcast, workspace, target)

    LOGGING.info("Done")

# --- --- ---

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

pipeline("../examples/Minimalismus als Design- und Architektur-Entscheidung/podcast.yaml")

# Abstract
# - Creation of a podcast (wav only) via TTS API
# x Based on a YAML structure
# - Minimization of API calls
#
# Environment Variables
# x API Key
#
# Arguments
# x source file
# x directory output/working (optional)
#
# How it works
# x Parse YAML file into structure object
#   x Validation + error output (YAML schema)
# x Create the output directory if it does not exist
#   x If not specified, output = input directory
# x Create map with hashes for all segments (all fields)
#   x The hashing concept is intended to simplify moving without having to
#     recreate segments or juggle IDs.
#   x Protection against hash collisions by combining the checksum.
#   x TODO: Permanent validation due to hash collision?
#     Error message/warning/do nothing?
# x Clean up sound fragments if there is no matching hash in YAML
# - Generate sound fragments (wav format only)
#   - Create a system prompt from speaker info + segment prompt
#   x For all segments for which no sound fragment exists for their hash
#   x Use the hash from the YAML segment as the name
# - Mix the sound fragments according to their position in YAML into an output wav
#   - take into account the "offset" which can be positive or negative
#
# TODO:
# - Audio parser.py in YAML
# x API parser.py (except key in YAML)
# x YAML support for environment variables
#   then the API key can be used indirectly in the configuration
