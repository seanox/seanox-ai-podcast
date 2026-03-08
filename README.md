<p>
  <a href="https://github.com/seanox/seanox-ai-podcast/pulls"
      title="Development"
    ><img src="https://img.shields.io/badge/development-active-green?style=for-the-badge"
  ></a>  
  <a href="https://github.com/seanox/seanox-ai-podcast/issues"
    ><img src="https://img.shields.io/badge/maintenance-active-green?style=for-the-badge"
  ></a>
  <a href="https://seanox.com/contact"
    ><img src="https://img.shields.io/badge/support-active-green?style=for-the-badge"
  ></a>
</p>

# Description
Python pipeline for automated podcast creation based on an external
Text-To-Speech (TTS) API. The structure of the podcast is defined using YAML and
describes segments, speakers, and text content. Multiple voices or characters
are supported, allowing different roles within a podcast to be represented.

The podcast sections are defined in individual segments. Each segment refers to
a speaker and contains the text as well as an optional prompt and offset that
influences the temporal position within the podcast. Offsets can be positive or
negative, allowing the segments to be arranged flexibly without having to
regenerate the audio fragments. The YAML files also support environment
variables, which enables the outsourcing of secrets for the TTS API, for
example.

Each segment is generated as a WAV file. To minimize TTS API calls, a hash is
generated for each segment from the relevant fields. Existing audio fragments
are reused if the hash is unchanged, and fragments that are no longer needed are
automatically removed. The hashes also function as automatic IDs, allowing
segments to be moved or rearranged as desired. Finally, the generated segments
are assembled into a complete podcast file according to the YAML definition.

# Features

# License Terms
Seanox Software Solutions is an open-source project, hereinafter referred to as
__Seanox__.

This software is licensed under the __Apache License, Version 2.0__.

__Copyright (C) 2026 Seanox Software Solutions__

Licensed under the Apache License, Version 2.0 (the "License"); you may not use
this file except in compliance with the License. You may obtain a copy of the
License at

https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed
under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

# System Requirement
- Python 3.11 or higher

# Installation & Setup

# Quickstart

# Changes

# Contact
[Issues](https://github.com/seanox/seanox-ai-podcast/issues)  
[Requests](https://github.com/seanox/seanox-ai-podcast/pulls)  
[Mail](https://seanox.com/contact)
