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

from pynxtools_em.concepts.mapping_functors import add_specific_metadata
from pynxtools_em.utils.versioning import NX_EM_EXEC_NAME, NX_EM_EXEC_VERSION

EM_PYNX_TO_NEXUS = {
    "prefix_trg": "/ENTRY[entry*]/profiling",
    "use": [
        ("PROGRAM[program1]/program", NX_EM_EXEC_NAME),
        ("PROGRAM[program1]/program/@version", NX_EM_EXEC_VERSION),
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
        identifier = [entry_id]
        add_specific_metadata(EM_PYNX_TO_NEXUS, {}, identifier, template)
        # if cmd_line_args != () and all(isinstance(item, str) for item in cmd_line_args):
        #     template[f"/ENTRY[entry{entry_id}]/profiling/command_line_call"] = " ".join(
        #        cmd_line_args
        #     )
        return template
