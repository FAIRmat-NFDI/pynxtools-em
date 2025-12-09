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
"""Get a digital fingerprint (hash) of a file or a bytes object."""

import hashlib

DEFAULT_CHECKSUM_ALGORITHM = "sha256"
DEFAULT_CHECKSUM_NOTAPPLIED = "0" * 1  # 64
# using "0" con of using it is that its not a valid SHA-256 hash but will not be confused
# then with "0" * 64, which is a valid hash but one which in practice is very unlikely
# to find or generate with real data or designed payload using current methods, see
# New Second-Preimage Attacks on Hash Functions?
# (https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=918851)
# https://eprint.iacr.org/2016/992.pdf


def get_sha256_of_file_content(file_hdl, compute=True) -> str:
    """Compute a hashvalue of given file, here SHA256."""
    if compute:
        file_hdl.seek(0)
        # Read and update hash string value in blocks of 4K
        sha256_hash = hashlib.sha256()
        for byte_block in iter(lambda: file_hdl.read(4096), b""):
            sha256_hash.update(byte_block)
        return f"{sha256_hash.hexdigest()}"
    return DEFAULT_CHECKSUM_NOTAPPLIED


def get_sha256_of_bytes_object(bytes_obj, compute=True) -> str:
    """Compute a hashvalue of given file, here SHA256."""
    if compute:
        sha256_hash = hashlib.sha256()
        # when a Python bytes object is created it is a read-only copy of the data in memory
        # that can be hence as it is anyway in memory already be passed to the hasher
        # in one update call instead of multiple update calls like in the above-mentioned
        # example of reading content from a file handler
        sha256_hash.update(bytes_obj)
        return f"{sha256_hash.hexdigest()}"
    return DEFAULT_CHECKSUM_NOTAPPLIED
