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
"""Implement NeXus-specific groups and fields to document software and versions used."""

from pynxtools_em.concepts.concept_mapper import variadic_path_to_specific_path


PYNXTOOLS_EM_VERSION = "Redundant, see metadata in NXroot header"
PYNXTOOLS_EM_URL = "Redundant, see metadata in NXroot header"

NXEM_NAME = "NXem"
NXEM_VERSION = "Redundant, see metadata in NXroot header"
NXEM_URL = "Redundant, see metadata in NXroot header"

EM_APPDEF = {
    "prefix": "/ENTRY[entry*]",
    "use": [
        ("PROGRAM[program1]/program", "pynxtools/dataconverter/readers/em"),
        ("PROGRAM[program1]/program/@version", PYNXTOOLS_EM_VERSION),
        ("PROGRAM[program1]/program/@url", PYNXTOOLS_EM_URL),
        ("definition", NXEM_NAME),
        ("definition/@version", NXEM_VERSION),
        ("definition/@url", NXEM_URL),
    ],
}


class NxEmAppDef:
    """Add NeXus NXem appdef specific contextualization."""

    def __init__(self):
        pass

    def parse(
        self, template: dict, entry_id: int = 1, cmd_line_args: tuple = ()
    ) -> dict:
        """Parse application definition."""
        variadic_prefix = EM_APPDEF["prefix"]
        for entry in EM_APPDEF["use"]:
            if isinstance(entry, tuple) and len(entry) == 2:
                trg = variadic_path_to_specific_path(
                    f"{variadic_prefix}/{entry[0]}", [entry_id]
                )
                template[trg] = entry[1]

        if cmd_line_args != [] and all(isinstance(item, str) for item in cmd_line_args):
            template[f"/ENTRY[entry{entry_id}]/profiling/command_line_call"] = (
                cmd_line_args
            )
        return template
