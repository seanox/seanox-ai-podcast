# seanox_ai_podcast/pipeline.py


from pathlib import Path

from seanox_ai_podcast import structure


def pipeline(source: str | Path, output: str | Path = None) -> None:

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
        output = None

    podcast = structure.parse(source)


# Abstract
# - Creation of a podcast (wav only) via TTS API
# - Based on a YAML structure
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
# - Create the output directory if it does not exist
#   - If not specified, output = input directory
# - Create map with hashes for all segments (all fields)
#   - The hashing concept is intended to simplify moving without having to
#     recreate segments or juggle IDs.
#   - Protection against hash collisions by combining the checksum.
#   - TODO: Permanent validation due to hash collision?
#     Error message/warning/do nothing?
# - Clean up sound fragments if there is no matching hash in YAML
# - Generate sound fragments (wav format only)
#   - Create a system prompt from speaker info + segment prompt
#   - For all segments for which no sound fragment exists for their hash
#   - Use the hash from the YAML segment as the name
# - Mix the sound fragments according to their position in YAML into an output wav
#   - take into account the "offset" which can be positive or negative
#
# TODO:
# - Audio parser.py in YAML
# x API parser.py (except key in YAML)
# x YAML support for environment variables
#   then the API key can be used indirectly in the configuration
