# Abstract
# - Creation of a podcast (wav only) via TTS API
# - Based on a YAML structure
# - Minimization of API calls
#
# Environment Variables
# - API Key
#
# Arguments
# - source file
# - directory output/working (optional)
#
# How it works
# - Parse YAML file into structure object
#   - Validation + error output (YAML schema)
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
# - Audio settings in YAML
# - API settings (except key in YAML)
# - YAML support for environment variables
#   then the API key can be used indirectly in the configuration
