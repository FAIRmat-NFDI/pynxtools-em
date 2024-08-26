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
"""NXem spectrum set (element of a labelled property graph) to store instance data."""

from typing import Dict, List

from pynxtools_em.concepts.nxs_object import NxObject

NX_SPECTRUM_SET_HDF_PATH: List = [
    "PROCESS-group",
    "PROCESS/PROGRAM-group",
    "PROCESS/detector_identifier-field",
    "PROCESS/mode-field",
    "PROCESS/source-group",
    "spectrum_0d/axis_energy-field",
    "spectrum_0d/axis_energy@long_name-attribute",
    "spectrum_0d/real-field",
    "spectrum_0d/real@long_name-attribute",
    "spectrum_1d/axis_energy-field",
    "spectrum_1d/axis_energy@long_name-attribute",
    "spectrum_1d/axis_i-field",
    "spectrum_1d/axis_i@long_name-attribute",
    "spectrum_1d/real-field",
    "spectrum_1d/real@long_name-attribute",
    "spectrum_2d/axis_energy-field",
    "spectrum_2d/axis_energy@long_name-attribute",
    "spectrum_2d/axis_i-field",
    "spectrum_2d/axis_i@long_name-attribute",
    "spectrum_2d/axis_j-field",
    "spectrum_2d/axis_j@long_name-attribute",
    "spectrum_2d/real-field",
    "spectrum_2d/real@long_name-attribute",
    "spectrum_3d/axis_energy-field",
    "spectrum_3d/axis_energy@long_name-attribute",
    "spectrum_3d/axis_i-field",
    "spectrum_3d/axis_i@long_name-attribute",
    "spectrum_3d/axis_j-field",
    "spectrum_3d/axis_j@long_name-attribute",
    "spectrum_3d/axis_k-field",
    "spectrum_3d/axis_k@long_name-attribute",
    "spectrum_3d/real-field",
    "spectrum_3d/real@long_name-attribute",
    "stack_0d-group",
    "stack_0d/axis_energy-field",
    "stack_0d/axis_energy@long_name-attribute",
    "stack_0d/real-field",
    "stack_0d/real@long_name-attribute",
    "stack_0d/spectrum_identifier-field",
    "stack_0d/spectrum_identifier@long_name-attribute",
]


class NxSpectrumSet:
    def __init__(self):
        self.tmp: Dict = {}
        self.tmp["source"] = None
        for entry in NX_SPECTRUM_SET_HDF_PATH:
            if entry.endswith("-field") is True:
                self.tmp[entry[0 : len(entry) - len("-field")]] = NxObject(
                    eqv_hdf="dataset"
                )
            elif entry.endswith("-attribute") is True:
                self.tmp[entry[0 : len(entry) - len("-attribute")]] = NxObject(
                    eqv_hdf="attribute"
                )
            else:
                self.tmp[entry[0 : len(entry) - len("-group")]] = NxObject(
                    eqv_hdf="group"
                )
