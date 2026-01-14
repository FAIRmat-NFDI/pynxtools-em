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
"""Dict mapping values for conventions and reference frames."""

from typing import Any

CONV_ROTATIONS_TO_NEXUS: dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/consistent_rotations",
    "prefix_src": "consistent_rotations/",
    "map_to_str": [
        "rotation_handedness",
        "rotation_convention",
        "euler_angle_convention",
        "axis_angle_convention",
        "sign_convention",
    ],
}


CONV_PROCESSING_CSYS_TO_NEXUS: dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/processing_reference_frame",
    "prefix_src": "processing_reference_frame/",
    "map_to_str": [
        "alias",
        "type",
        "handedness",
        "origin",
        "x_alias",
        "x_direction",
        "y_alias",
        "y_direction",
        "z_alias",
        "z_direction",
    ],
}


CONV_SAMPLE_CSYS_TO_NEXUS: dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/sample_reference_frame",
    "prefix_src": "sample_reference_frame/",
    "map_to_str": [
        "alias",
        "type",
        "handedness",
        "origin",
        "x_alias",
        "x_direction",
        "y_alias",
        "y_direction",
        "z_alias",
        "z_direction",
    ],
}


CONV_DETECTOR_CSYS_TO_NEXUS: dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/NAMED_reference_frameID[detector_reference_frame1]",
    "prefix_src": "detector_reference_frame/",
    "map_to_str": [
        "alias",
        "type",
        "handedness",
        "origin",
        "x_alias",
        "x_direction",
        "y_alias",
        "y_direction",
        "z_alias",
        "z_direction",
    ],
}


CONV_GNOMONIC_CSYS_TO_NEXUS: dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/roiID[roi*]/ebsd/gnomonic_reference_frame",
    "prefix_src": "gnomonic_reference_frame/",
    "map_to_str": [
        "alias",
        "type",
        "handedness",
        "origin",
        "x_direction",
        "y_direction",
        "z_direction",
    ],
}


CONV_PATTERN_CSYS_TO_NEXUS: dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/roiID[roi*]/ebsd/pattern_center",
    "prefix_src": "pattern_center/",
    "map_to_str": [
        "x_boundary_convention",
        "x_normalization_direction",
        "y_boundary_convention",
        "y_normalization_direction",
    ],
}
