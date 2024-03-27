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
"""Wrapping multiple parsers for vendor files with NOMAD Oasis/ELN/YAML metadata."""

# pylint: disable=no-member,duplicate-code,too-many-nested-blocks

import flatdict as fd
import yaml


from pynxtools_em.config.em_example_eln_to_nx_map import (
    EM_EXAMPLE_OTHER_TO_NEXUS,
    EM_EXAMPLE_USER_TO_NEXUS,
)
from pynxtools_em.shared.shared_utils import rchop
from pynxtools_apm.shared.mapping_functors import (
    variadic_path_to_specific_path,
)
from pynxtools_apm.utils.apm_parse_composition_table import (
    parse_composition_table,
)
from pynxtools_em.shared.shared_utils import (
    get_sha256_of_file_content,
)


class NxApmNomadOasisElnSchemaParser:  # pylint: disable=too-few-public-methods
    """Parse eln_data.yaml dump file content generated from a NOMAD Oasis YAML.

    This parser implements a design where an instance of a specific NOMAD
    custom schema ELN template is used to fill pieces of information which
    are typically not contained in files from technology partners
    (e.g. pos, epos, apt, rng, rrng, ...). Until now, this custom schema and
    the NXapm application definition do not use a fully harmonized vocabulary.
    Therefore, the here hardcoded implementation is needed which maps specifically
    named pieces of information from the custom schema instance on named fields
    in an instance of NXapm

    The functionalities in this ELN YAML parser do not check if the
    instantiated template yields an instance which is compliant with NXapm.
    Instead, this task is handled by the generic part of the dataconverter
    during the verification of the template dictionary.
    """

    def __init__(self, file_path: str, entry_id: int, verbose: bool = False):
        print(f"Extracting data from ELN file: {file_path}")
        if (
            file_path.rsplit("/", 1)[-1].startswith("eln_data")
            or file_path.startswith("eln_data")
        ) and entry_id > 0:
            self.entry_id = entry_id
            self.file_path = file_path
            with open(self.file_path, "r", encoding="utf-8") as stream:
                self.yml = fd.FlatDict(yaml.safe_load(stream), delimiter="/")
                if verbose is True:
                    for key, val in self.yml.items():
                        print(f"key: {key}, value: {val}")
        else:
            self.entry_id = 1
            self.file_path = ""
            self.yml = {}

    def parse_user(self, template: dict) -> dict:
        """Copy data from user section into template."""
        src = "user"
        if src in self.yml:
            if isinstance(self.yml[src], list):
                if all(isinstance(entry, dict) for entry in self.yml[src]) is True:
                    user_id = 1
                    # custom schema delivers a list of dictionaries...
                    for user_dict in self.yml[src]:
                        if user_dict == {}:
                            continue
                        identifier = [self.entry_id, user_id]
                        for key in user_dict:
                            for tpl in EM_EXAMPLE_USER_TO_NEXUS:
                                if isinstance(tpl, tuple) and (len(tpl) == 3):
                                    if (tpl[1] == "load_from") and (key == tpl[2]):
                                        trg = variadic_path_to_specific_path(
                                            tpl[0], identifier
                                        )
                                        # res = apply_modifier(modifier, user_dict)
                                        # res is not None
                                        template[trg] = user_dict[tpl[2]]
                        user_id += 1
        return template

    def report(self, template: dict) -> dict:
        """Copy data from self into template the appdef instance."""
        self.parse_user(template)
        return template
