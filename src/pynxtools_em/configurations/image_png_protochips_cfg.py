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
"""Configuration of the image_png_protochips parser."""

import re
from typing import Any, Dict

from pynxtools_em.utils.pint_custom_unit_registry import ureg


def specific_to_variadic(token):
    # "MicroscopeControlImageMetadata.AuxiliaryData.AuxiliaryDataCategory.[0].DataValues.AuxiliaryDataValue.[20].HeatingPower"
    # to "MicroscopeControlImageMetadata.AuxiliaryData.AuxiliaryDataCategory.[*].DataValues.AuxiliaryDataValue.[*].HeatingPower"
    if isinstance(token, str) and token != "":
        concept = token.strip()
        idxs = re.finditer(r".\[[0-9]+\].", concept)
        if sum(1 for _ in idxs) > 0:
            variadic = concept
            for idx in re.finditer(r".\[[0-9]+\].", concept):
                variadic = variadic.replace(concept[idx.start(0) : idx.end(0)], ".[*].")
            return variadic
        else:
            return concept
    return None


AXON_STATIC_STAGE_NX: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/instrument/stage",
    "prefix_src": "MicroscopeControlImageMetadata.ActivePositionerSettings.PositionerSettings.[*].Stage.",
    "use": [("design", "heating_chip")],
    "map_to_str": [("alias", "Name")],
}


AXON_STATIC_DETECTOR_NX: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/instrument/DETECTOR[detector*]",
    "prefix_src": "",
    "use": [
        (
            "local_name",
            "As tested with AXON 10.4.4.21, 2021-04-26T22:51:28.4539893-05:00 not included in Protochips PNG metadata",
        )
    ],
}


AXON_DYNAMIC_STAGE_NX: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/events/EVENT_DATA_EM[event_data_em*]/instrument/stage",
    "prefix_src": "MicroscopeControlImageMetadata.ActivePositionerSettings.PositionerSettings.[*].Stage.",
    "map_to_f8": [
        ("position", ureg.meter, ["X", "Y", "Z"], ureg.meter)
    ],  # values are much to large to be in m!
}


AXON_DYNAMIC_CHIP_NX: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/events/EVENT_DATA_EM[event_data_em*]/instrument/stage/sample_heater",
    "prefix_src": "MicroscopeControlImageMetadata.AuxiliaryData.AuxiliaryDataCategory.[*].DataValues.AuxiliaryDataValue.[*].",
    "use": [("physical_quantity", "temperature")],
    "map_to_f8": [
        ("heater_current", ureg.ampere, "HeatingCurrent", ureg.ampere),
        ("heater_power", ureg.watt, "HeatingPower", ureg.watt),
        ("heater_voltage", ureg.volt, "HeatingVoltage", ureg.volt),
    ],
}


AXON_DYNAMIC_AUX_NX: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/events/EVENT_DATA_EM[event_data_em*]/instrument/ebeam_column",
    "prefix_src": "MicroscopeControlImageMetadata.AuxiliaryData.AuxiliaryDataCategory.[*].DataValues.AuxiliaryDataValue.[*].",
    "use": [
        ("SENSOR[sensor1]/measurement", "temperature"),
        ("SENSOR[sensor2]/measurement", "pressure"),
    ],
    "map_to_f8": [
        ("SENSOR[sensor1]/value", ureg.degC, "HolderTemperature", ureg.degC),
        ("SENSOR[sensor2]/value", ureg.bar, "HolderPressure", ureg.torr),
    ],
}


AXON_DYNAMIC_VARIOUS_NX: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/events/EVENT_DATA_EM[event_data_em*]",
    "prefix_src": "MicroscopeControlImageMetadata.MicroscopeSettings.",
    "map_to_str": [
        (
            "instrument/ebeam_column/DEFLECTOR[beam_blanker1]/state",
            "BeamBlankerState",
        ),
    ],
    "map_to_f8": [
        (
            "instrument/ebeam_column/electron_source/voltage",
            ureg.volt,
            "AcceleratingVoltage",
            ureg.volt,
        ),
        (
            "instrument/optics/camera_length",
            ureg.meter,
            "CameraLengthValue",
            ureg.meter,
        ),
        (
            "instrument/optics/magnification",
            "MagnificationValue",
        ),
    ],
}
