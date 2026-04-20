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
"""Configuration of the image_tiff_jeol parser."""

from typing import Any

from pynxtools_em.utils.pint_custom_unit_registry import ureg

JEOL_KEYWORD_TO_PINT_UNITS = {
    "CM_VERSION": "",
    "CM_IMAGE_SIZE": "dimensionless",
    "CM_COLOR_MODE": "dimensionless",
    "CM_CONTRAST": "dimensionless",
    "CM_BRIGHTNESS": "dimensionless",
    "CM_ACCEL_VOLT": ureg.kilovolt,
    "CM_MAG": "dimensionless",
    "CM_STAGE_POSITION": ureg.micrometer,
    "CM_FIELD_OF_VIEW": ureg.micrometer,
    "CM_PIXEL_SIZE": ureg.nanometer,
    "CM_SEGMENT_NUMBER": "dimensionless",
    "CM_FORMAT": "",
    "SM_VERSION": "",
    "MP_VERSION": "",
    "SM_DETECTOR": "",
    "SM_WD": ureg.millimeter,
    "MP_PROBE_NUMBER": "dimensionless",
    "MP_PROBE_CURRENT_MODE": "dimensionless",
    "SM_DETECTOR1": "",
    "MP_CONTRAST1": "dimensionless",
    "MP_BRIGHTNESS1": "dimensionless",
    "SM_VACUUM_MODE": "",
    "MP_LOW_VACUUM_MODE": "",
    "SM_SCAN_ROTATION": ureg.degree,
    "SM_PNU_TYPE": "dimensionless",
    "SM_PNU_HEIGHT": "dimensionless",
    "SM_INTEGRATION_NUMBER": "dimensionless",
    "SM_SCAN_TIME": ureg.second,  # ???
    "SM_DWELL_TIME": ureg.nanometer,
    "SM_SCAN_TYPE": "dimensionless",
    "SM_LIVE_FILTER_MODE": "dimensionless",
    "SM_OBJECT_LENS_TYPE": "",
    "MP_BEAM_SHIFT": "dimensionless",
    "MP_DYNAMIC_FOCUS": "dimensionless",
    "SM_TILT_MAG_CORRECTION": "dimensionless",
    "SM_MONITOR_MAGNIFICATION": "dimensionless",
    "MP_FIELD_IMAGE_MAGNIFICATION": "dimensionless",
    "SM_NICKNAME": "",
    "SM_STANDARD_FIELD_SIZE": "dimensionless",
    "SM_GUN_TYPE": "",
    "SM_STAGE_BIAS_VOLT": ureg.kilovolt,  # ???
    "SM_GUN_VOLT": ureg.kilovolt,  # ???
    "SM_COLUMN_MODE": "",
    "MP_STAGE_DRIVE": "dimensionless",
}


JEOL_DYNAMIC_VARIOUS_NX: dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/eventID[event*]",
    "prefix_src": "",
    "map_to_f8": [
        ("instrument/optics/magnification", ureg.nx_dimensionless, "CM_MAG"),
        (
            "instrument/optics/working_distance",
            ureg.meter,
            "SM_WD",
            ureg.millimeter,
        ),
        (
            "instrument/ebeam_column/electron_source/voltage",
            ureg.volt,
            "CM_ACCEL_VOLTAGE",
            ureg.kilovolt,
        ),
    ],
}


JEOL_STATIC_VARIOUS_NX: dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/instrument/fabrication",
    "prefix_src": "",
    "use": [("vendor", "JEOL")],
    "map": [
        ("model", "CM_INSTRUMENT"),
    ],
}
