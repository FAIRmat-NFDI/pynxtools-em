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

from typing import Dict

from pynxtools_em.concepts.nxs_object import NxObject

NX_IMAGE_REAL_SPACE_SET_HDF_PATH = [
    "image_1d/axis_i-field",
    "image_1d/axis_i@long_name-attribute",
    "image_1d/real-field",
    "image_2d/axis_i-field",
    "image_2d/axis_i@long_name-attribute",
    "image_2d/axis_j-field",
    "image_2d/axis_j@long_name-attribute",
    "image_2d/real-field",
    "image_3d/axis_i-field",
    "image_3d/axis_i@long_name-attribute",
    "image_3d/axis_j-field",
    "image_3d/axis_j@long_name-attribute",
    "image_3d/axis_k-field",
    "image_3d/axis_k@long_name-attribute",
    "image_3d/real-field",
    "stack_1d/axis_i-field",
    "stack_1d/axis_i@long_name-attribute",
    "stack_1d/axis_image_identifier-field",
    "stack_1d/axis_image_identifier@long_name-attribute",
    "stack_1d/real-field",
    "stack_2d/axis_i-field",
    "stack_2d/axis_i@long_name-attribute",
    "stack_2d/axis_image_identifier-field",
    "stack_2d/axis_image_identifier@long_name-attribute",
    "stack_2d/axis_j-field",
    "stack_2d/axis_j@long_name-attribute",
    "stack_2d/real-field",
    "stack_3d/axis_i-field",
    "stack_3d/axis_i@long_name-attribute",
    "stack_3d/axis_image_identifier-field",
    "stack_3d/axis_image_identifier@long_name-attribute",
    "stack_3d/axis_j-field",
    "stack_3d/axis_j@long_name-attribute",
    "stack_3d/axis_k-field",
    "stack_3d/axis_k@long_name-attribute",
    "stack_3d/real-field",
]


class NxImageRealSpaceSet:
    def __init__(self):
        self.tmp: Dict = {}
        self.tmp["source"] = None
        for entry in NX_IMAGE_REAL_SPACE_SET_HDF_PATH:
            if entry.endswith("-field"):
                self.tmp[entry[0 : len(entry) - len("-field")]] = NxObject(
                    eqv_hdf="dataset"
                )
            elif entry.endswith("-attribute"):
                self.tmp[entry[0 : len(entry) - len("-attribute")]] = NxObject(
                    eqv_hdf="attribute"
                )
            else:
                self.tmp[entry[0 : len(entry) - len("-group")]] = NxObject(
                    eqv_hdf="group"
                )
