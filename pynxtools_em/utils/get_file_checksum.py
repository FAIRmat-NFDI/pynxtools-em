#
# Copyright The NOMAD Authors.
#
# This file is part of NOMAD. See https://nomad-lab.eu for further info.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Get a digital fingerprint (hash) of a file."""

import hashlib


DEFAULT_CHECKSUM_ALGORITHM = "sha256"


def get_sha256_of_file_content(file_hdl) -> str:
    """Compute a hashvalue of given file, here SHA256."""
    file_hdl.seek(0)
    # Read and update hash string value in blocks of 4K
    sha256_hash = hashlib.sha256()
    for byte_block in iter(lambda: file_hdl.read(4096), b""):
        sha256_hash.update(byte_block)
    return str(sha256_hash.hexdigest())
