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
"""Configuration of the image_tiff_tescan parser."""

from typing import Any, Dict

from pynxtools_em.utils.pint_custom_unit_registry import ureg

TESCAN_DYNAMIC_VARIOUS_NX: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/EVENT_DATA_EM[event*]",
    "prefix_src": "",
    "map_to_f8": [
        ("instrument/optics/magnification", "Magnification"),
        (
            "instrument/optics/working_distance",
            ureg.meter,
            "WD",
            ureg.meter,
        ),
        (
            "instrument/optics/probe_diameter",
            ureg.meter,
            "SpotSize",  # diameter or probe at the specimen surface?
            ureg.meter,
        ),
        (
            "instrument/optics/beam_current",
            ureg.ampere,
            "PredictedBeamCurrent",
            ureg.ampere,
        ),
        (
            "instrument/optics/specimen_current",
            ureg.ampere,
            "SpecimenCurrent",
            ureg.ampere,
        ),
        (
            "instrument/ebeam_column/electron_source/voltage",
            ureg.volt,
            "HV",
            ureg.volt,
        ),
        (
            "instrument/ebeam_column/electron_source/emission_current",
            ureg.ampere,
            "EmissionCurrent",
            ureg.ampere,
        ),
    ],
}


TESCAN_DYNAMIC_STIGMATOR_NX: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/EVENT_DATA_EM[event*]/instrument/ebeam_column/corrector_ax",
    "prefix_src": "",
    "map_to_f8": [("value_x", "StigmatorX"), ("value_y", "StigmatorY")],
}


TESCAN_DYNAMIC_STAGE_NX: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/EVENT_DATA_EM[event*]/instrument/MANIPULATOR[stage]",
    "prefix_src": "",
    "map_to_f8": [
        ("rotation", ureg.radian, "StageRotation", ureg.degree),
        ("tilt1", ureg.radian, "StageTilt", ureg.degree),
        ("position", ureg.meter, ["StageX", "StageY", "StageZ"], ureg.meter),
    ],
}


TESCAN_STATIC_VARIOUS_NX: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/instrument/fabrication",
    "prefix_src": "",
    "use": [("vendor", "TESCAN")],
    "map_to_str": [
        ("model", "Device"),
        ("serial_number", "SerialNumber"),
    ],
}
