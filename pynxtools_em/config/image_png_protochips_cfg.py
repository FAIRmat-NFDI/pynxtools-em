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
"""Configuration of the image_png_protochips subparser."""

from typing import Dict


AXON_STAGE_STATIC_TO_NX_EM = {
    "prefix_trg": "/ENTRY[entry*]/measurement/em_lab/STAGE_LAB[stage_lab]",
    "prefix_src": "MicroscopeControlImageMetadata.ActivePositionerSettings.PositionerSettings.[*].Stage.",
    "use": [("design", "heating_chip")],
    "load_from": [("alias", "Name")],
}


AXON_DETECTOR_STATIC_TO_NX_EM = {
    "prefix": "/ENTRY[entry*]/measurement/em_lab/DETECTOR[detector*]",
    "use": [
        (
            "local_name",
            "As tested with AXON 10.4.4.21, 2021-04-26T22:51:28.4539893-05:00 not included in Protochips PNG metadata",
        )
    ],
}


AXON_CHIP_DYNAMIC_TO_NX_EM = {
    "prefix_trg": "/ENTRY[entry*]/measurement/EVENT_DATA_EM_SET[event_data_em_set]/EVENT_DATA_EM[event_data_em*]/em_lab/HEATER[heater]",
    "prefix_src": "MicroscopeControlImageMetadata.AuxiliaryData.AuxiliaryDataCategory.[*].DataValues.AuxiliaryDataValue.[*].",
    "use": [("current/@units", "A"), ("power/@units", "W"), ("voltage/@units", "V")],
    "load_from": [
        ("current", "HeatingCurrent"),
        ("power", "HeatingPower"),
        ("voltage", "HeatingVoltage"),
    ],
}


AXON_AUX_DYNAMIC_TO_NX_EM = {
    "prefix_trg": "/ENTRY[entry*]/measurement/EVENT_DATA_EM_SET[event_data_em_set]/EVENT_DATA_EM[event_data_em*]/em_lab/STAGE_LAB[stage_lab]",
    "prefix_src": "MicroscopeControlImageMetadata.AuxiliaryData.AuxiliaryDataCategory.[*].DataValues.AuxiliaryDataValue.[*].",
    "use": [
        ("SENSOR[sensor2]/value/@units", "torr"),
        ("SENSOR[sensor2]/measurement", "pressure"),
        ("SENSOR[sensor1]/value/@units", "°C"),
        ("SENSOR[sensor1]/measurement", "temperature"),
    ],
    "load_from": [
        ("SENSOR[sensor2]/value", "HolderPressure"),
        ("SENSOR[sensor1]/value", "HolderTemperature"),
    ],
}


AXON_VARIOUS_DYNAMIC_TO_NX_EM = {
    "prefix_trg": "/ENTRY[entry*]/measurement/EVENT_DATA_EM_SET[event_data_em_set]/EVENT_DATA_EM[event_data_em*]",
    "prefix_src": "MicroscopeControlImageMetadata.MicroscopeSettings.",
    "use": [
        ("em_lab/EBEAM_COLUMN[ebeam_column]/electron_source/voltage/@units", "V"),
        (
            "event_type",
            "As tested with AXON 10.4.4.21, 2021-04-26T22:51:28.4539893-05:00 not included in Protochips PNG metadata",
        ),
        (
            "em_lab/DETECTOR[detector*]/mode",
            "As tested with AXON 10.4.4.21, 2021-04-26T22:51:28.4539893-05:00 not included in Protochips PNG metadata",
        ),
        ("em_lab/OPTICAL_SYSTEM_EM[optical_system_em]/camera_length", "m"),
    ],
    "load_from": [
        (
            "em_lab/EBEAM_COLUMN[ebeam_column]/electron_source/voltage",
            "AcceleratingVoltage",
        ),
        (
            "em_lab/EBEAM_COLUMN[ebeam_column]/DEFLECTOR[beam_blanker1]/state",
            "BeamBlankerState",
        ),
        (
            "em_lab/OPTICAL_SYSTEM_EM[optical_system_em]/camera_length",
            "CameraLengthValue",
        ),
        (
            "em_lab/OPTICAL_SYSTEM_EM[optical_system_em]/magnification",
            "MagnificationValue",
        ),
    ],
}


PNG_PROTOCHIPS_TO_NEXUS_CFG: Dict = {}
