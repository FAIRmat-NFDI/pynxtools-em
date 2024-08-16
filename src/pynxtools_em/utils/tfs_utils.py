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
"""Utility functions for working with ThermoFisher content and concepts."""

from typing import List

from pynxtools_em.configurations.image_tiff_tfs_cfg import (
    TIFF_TFS_ALL_CONCEPTS,
    TIFF_TFS_PARENT_CONCEPTS,
)


def get_fei_parent_concepts() -> List:
    """Get list of unique FEI parent concepts."""
    return TIFF_TFS_PARENT_CONCEPTS


def get_fei_childs(parent_concept: str) -> List:
    """Get all children of FEI parent concept."""
    child_concepts = set()
    for entry in TIFF_TFS_ALL_CONCEPTS:
        if isinstance(entry, str) and entry.count("/") == 1:
            if entry.startswith(f"{parent_concept}/") is True:
                child_concepts.add(entry.split("/")[1])
    return list(child_concepts)
