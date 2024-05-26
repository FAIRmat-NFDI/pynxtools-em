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
"""Try to recover atom_types."""

import re
from pynxtools_em.examples.ebsd_database import (
    PHASE_NAME_TO_CONCEPT,
    CONCEPT_TO_ATOM_TYPES,
)
from ase.data import chemical_symbols


class NxEmAtomTypesResolver:
    """Find elements to store in sample/atom_types for NXem."""

    def __init__(self, entry_id: int = 1):
        if entry_id >= 1:
            self.entry_id = entry_id

    def identify_atomtypes(self, template: dict) -> dict:
        """Inspect template and find elements to eventually overwrite sample/atom_types."""
        atom_types = set()
        for key in template:
            if (
                re.match(
                    f"^/ENTRY\[entry{self.entry_id}\]/ROI\[roi1\]/ebsd/indexing/phaseID\[phase[0-9]+\]/phase_name",
                    key,
                )
                is None
            ):
                continue
            print(f">>>>>>> {key} contributes to atom_types {type(template[key])}, {template[key]}")
            free_text = str(template[key])  # .strip()
            print(f"{type(free_text)}, ___{free_text}__")
            if free_text in PHASE_NAME_TO_CONCEPT:
                concept = PHASE_NAME_TO_CONCEPT[free_text]
                if concept in CONCEPT_TO_ATOM_TYPES:
                    symbols = CONCEPT_TO_ATOM_TYPES[concept].split(";")
                    for symbol in symbols:
                        if symbol in chemical_symbols[1::]:
                            atom_types.add(symbol)
            print(atom_types)
        if len(atom_types) > 0:
            trg = f"/ENTRY[entry{self.entry_id}]/sample/atom_types"
            template[trg] = ", ".join(list(atom_types))
        return template
