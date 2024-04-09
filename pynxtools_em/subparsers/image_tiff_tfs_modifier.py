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
"""Utilities for working with TFS/FEI-specific concepts."""

from numpy import pi


def get_nexus_value(modifier, qnt_name, metadata: dict):
    """Interpret a functional mapping and modifier on qnt_name loaded from metadata."""
    if qnt_name in metadata.keys():
        if modifier == "load_from":
            return metadata[qnt_name]
        elif modifier == "load_from_rad_to_deg":
            if qnt_name in metadata.keys():
                return metadata[qnt_name] / pi * 180.0
        elif modifier == "load_from_lower_case":
            if isinstance(metadata[qnt_name], str):
                return metadata[qnt_name].lower()
            return None
    else:
        return None
