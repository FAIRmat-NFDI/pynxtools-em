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
"""Parser NOMAD-Oasis-specific configuration serialized as oasis.yaml to NeXus NXem."""

# mapping instructions as a dictionary
#   prefix is the (variadic prefix to be add to every path on the target side)
#   different modifiers are used
#       "use": list of pair of trg, src endpoint, take the value in src copy into trg
#       "load": list of single value or pair (trg, src)
#           if single value this means that the endpoint of trg and src is the same
#           e.g. in the example below "name" means
#           ("/ENTRY[entry*]/USER[user*]/name, "load", "name")
#           if pair load the value pointed to by src and copy into trg

import pathlib

import flatdict as fd
import yaml

from pynxtools_em.concepts.mapping_functors import add_specific_metadata
from pynxtools_em.config.oasis_cfg import EM_CSYS_TO_NEXUS, EM_CITATION_TO_NEXUS


class NxEmNomadOasisConfigurationParser:
    """Parse deployment specific configuration."""

    def __init__(self, file_path: str, entry_id: int, verbose: bool = False):
        print(
            f"Extracting data from deployment-specific configuration file {file_path} ..."
        )
        if (
            pathlib.Path(file_path).name.endswith(".oasis.specific.yaml")
            or pathlib.Path(file_path).name.endswith(".oasis.specific.yml")
        ) and entry_id > 0:
            self.entry_id = entry_id
            self.file_path = file_path
            with open(self.file_path, "r", encoding="utf-8") as stream:
                self.yml = fd.FlatDict(yaml.safe_load(stream), delimiter="/")
                if verbose:
                    for key, val in self.yml.items():
                        print(f"key: {key}, val: {val}")
        else:
            self.entry_id = 1
            self.file_path = ""
            self.yml = {}

    def parse_reference_frames(self, template: dict) -> dict:
        """Copy details about frames of reference into template."""
        src = "coordinate_system_set"
        if src in self.yml:
            if isinstance(self.yml[src], list):
                if all(isinstance(entry, dict) for entry in self.yml[src]):
                    csys_id = 1
                    # custom schema delivers a list of dictionaries...
                    for csys_dict in self.yml[src]:
                        if csys_dict == {}:
                            continue
                        identifier = [self.entry_id, csys_id]
                        add_specific_metadata(
                            EM_CSYS_TO_NEXUS,
                            fd.FlatDict(csys_dict),
                            identifier,
                            template,
                        )
                        csys_id += 1
        return template

    def parse_example(self, template: dict) -> dict:
        """Copy data from example-specific section into template."""
        src = "citation"
        if src in self.yml:
            if isinstance(self.yml[src], list):
                if all(isinstance(entry, dict) for entry in self.yml[src]) is True:
                    cite_id = 1
                    # custom schema delivers a list of dictionaries...
                    for cite_dict in self.yml[src]:
                        if cite_dict == {}:
                            continue
                        identifier = [self.entry_id, cite_id]
                        add_specific_metadata(
                            EM_CITATION_TO_NEXUS,
                            fd.FlatDict(cite_dict),
                            identifier,
                            template,
                        )
                        cite_id += 1
        return template

    def report(self, template: dict) -> dict:
        """Copy data from configuration applying mapping functors."""
        self.parse_reference_frames(template)
        self.parse_example(template)
        return template
