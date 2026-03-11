# seanox_ai_podcast/pipeline.py

import re

from pathlib import Path
from seanox_ai_podcast import structure

PATTERN_SEGMENT_WAV_FILE = re.compile(r"^0x([0-9a-fA-F]{32})+\.wav$")


def pipeline(source: str | Path, output: str | Path = None, verbose: bool = True) -> None:

    if not source or not str(source).strip():
        raise ValueError("source is required")
    source = Path(source) if not isinstance(source, Path) else source
    if not source.exists() or not source.is_file():
        raise ValueError(f"{source} must be a file")

    if output is not None and not str(output).strip():
        if not isinstance(output, Path):
            output = Path(output)
    if output.exists() and not output.is_dir():
        raise ValueError(f"{output} must be a directory")
    else:
        output = source.parent.resolve()

    if verbose:
        print(f"Parsing {source}")
    podcast = structure.parse(source)

    if not output.exists():
        if verbose:
            print(f"Creating output directory {output}")
        output.mkdir(exist_ok=True)

    # Irrelevant segments are cleaned up.
    # Irrelevant means all existing segments that do not match any of the
    # current segments based on their hash values.
    if verbose:
        print("Cleaning up obsolete segments")
    segments = [segment.hash() for segment in podcast.segments]
    for file in output.glob("*.wav"):
        if not PATTERN_SEGMENT_WAV_FILE.match(file.stem):
            continue
        if file.stem not in segments:
            file.unlink()

    if verbose:
        print("Creating new segments")
    for segment in podcast.segments:
        file = output / f"0x{segment.hash()}.wav"
        if file.is_file():
            continue
        _create_segment_wav(file, segment)

    target = source.with_suffix(".wav")
    if verbose:
        print(f"Mixing and cutting {target}")
    _mix_podcast_wav(output, target, podcast)

    if verbose:
        print("Done")

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
