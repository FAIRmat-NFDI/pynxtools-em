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
"""Parse conventions from an ELN schema instance."""

import pathlib

import flatdict as fd
import yaml
from pynxtools_em.concepts.mapping_functors import (
    add_specific_metadata,
    variadic_path_to_specific_path,
)
from pynxtools_em.configurations.conventions_cfg import (
    DETECTOR_CSYS_TO_NEXUS,
    GNOMONIC_CSYS_TO_NEXUS,
    PATTERN_CSYS_TO_NEXUS,
    PROCESSING_CSYS_TO_NEXUS,
    ROTATIONS_TO_NEXUS,
    SAMPLE_CSYS_TO_NEXUS,
)
from pynxtools_em.geometries.euler_angle_convention import euler_convention
from pynxtools_em.geometries.handed_cartesian import (
    AXIS_DIRECTIONS,
    REFERENCE_FRAMES,
    is_cartesian_cs_well_defined,
)
from pynxtools_em.geometries.msmse_convention import is_consistent_with_msmse_convention


class NxEmConventionParser:
    """Document rotation and reference frame conventions and choices used."""

    def __init__(self, file_path: str, entry_id: int = 1, verbose: bool = False):
        """Fill template with ELN pieces of information."""
        print(f"Extracting conventions from {file_path} ...")
        if (
            pathlib.Path(file_path).name.endswith("conventions.yaml")
            or pathlib.Path(file_path).name.endswith("conventions.yml")
        ) and entry_id > 0:
            self.entry_id = entry_id
            self.file_path = file_path
            with open(self.file_path, "r", encoding="utf-8") as stream:
                self.yml = fd.FlatDict(yaml.safe_load(stream), delimiter="/")
                if verbose:
                    for key, val in self.yml.items():
                        print(f"key: {key}, value: {val}")
        else:
            self.entry_id = 1
            self.file_path = ""
            self.yml = {}

    def parse(self, template) -> dict:
        """Extract metadata from generic ELN text file to respective NeXus objects."""
        print("Parsing conventions...")
        identifier = [self.entry_id, 1]
        add_specific_metadata(ROTATIONS_TO_NEXUS, self.yml, identifier, template)
        add_specific_metadata(PROCESSING_CSYS_TO_NEXUS, self.yml, identifier, template)
        add_specific_metadata(SAMPLE_CSYS_TO_NEXUS, self.yml, identifier, template)
        add_specific_metadata(DETECTOR_CSYS_TO_NEXUS, self.yml, identifier, template)
        add_specific_metadata(GNOMONIC_CSYS_TO_NEXUS, self.yml, identifier, template)
        add_specific_metadata(PATTERN_CSYS_TO_NEXUS, self.yml, identifier, template)

        # check is used convention follows EBSD community suggestions by Rowenhorst et al.
        prfx = f"/ENTRY[entry{self.entry_id}]/ROI[roi1]/ebsd/conventions/rotation_conventions"
        cvn_used = {}
        for key in [
            "rotation_handedness",
            "rotation_convention",
            "euler_angle_convention",
            "axis_angle_convention",
        ]:
            cvn_used[key] = template.undocumented[f"{prfx}/{key}"]
        if is_consistent_with_msmse_convention(cvn_used) == "inconsistent":
            print("WARNING::Convention set is different from community suggestion!")

        # assess if made conventions are consistent
        for csys_name in ["processing", "sample"]:
            trg = f"/ENTRY[entry{self.entry_id}]/ROI[roi1]/ebsd/conventions"
            handedness = template.undocumented[
                f"{trg}/{csys_name}_reference_frame/handedness"
            ]
            directions = []
            for dir_name in ["x", "y", "z"]:
                directions.append(
                    template.undocumented[
                        f"{trg}/{csys_name}_reference_frame/{dir_name}_direction"
                    ]
                )
            if not is_cartesian_cs_well_defined(handedness, directions):
                raise ValueError(f"{csys_name}_reference_frame is not well defined!")

        # could add tests for gnomonic and pattern_centre as well
        return template
