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
"""Configuration of the image_tiff_tfs subparser."""

from typing import Dict

TFS_DETECTOR_STATIC_TO_NX_EM = {
    "prefix": "/ENTRY[entry*]/measurement/em_lab/DETECTOR[detector*]",
    "load_from": [
        ("local_name", "Detectors/Name"),
    ],
}


TFS_APERTURE_STATIC_TO_NX_EM = {
    "prefix": "/ENTRY[entry*]/measurement/em_lab/EBEAM_COLUMN[ebeam_column]/APERTURE_EM[aperture_em*]",
    "use": [("value/@units", "m")],
    "load_from": [
        ("description", "Beam/Aperture"),
        ("value", "EBeam/ApertureDiameter"),
    ],
}


TFS_VARIOUS_STATIC_TO_NX_EM = {
    "prefix": "/ENTRY[entry*]/measurement/em_lab",
    "use": [("FABRICATION[fabrication]/vendor", "FEI")],
    "load_from": [
        ("FABRICATION[fabrication]/model", "System/SystemType"),
        ("FABRICATION[fabrication]/identifier", "System/BuildNr"),
        ("EBEAM_COLUMN[ebeam_column]/electron_source/emitter_type", "System/Source"),
    ],
}


TFS_OPTICS_DYNAMIC_TO_NX_EM = {
    "prefix": "/ENTRY[entry*]/measurement/em_lab/EVENT_DATA_EM_SET[event_data_em_set]/EVENT_DATA_EM[event_data_em*]/em_lab/OPTICAL_SYSTEM_EM[optical_system_em]",
    "use": [("beam_current/@units", "A"), ("working_distance/@units", "m")],
    "load_from": [
        ("beam_current", "EBeam/BeamCurrent"),
        ("working_distance", "EBeam/WD"),
    ],
}


TFS_STAGE_DYNAMIC_TO_NX_EM = {
    "prefix": "/ENTRY[entry*]/measurement/EVENT_DATA_EM_SET[event_data_em_set]/EVENT_DATA_EM[event_data_em*]/em_lab/STAGE_LAB[stage_lab]",
    "use": [("tilt1/@units", "deg"), ("tilt2/@units", "deg")],
    "load_from_rad_to_deg": [("tilt1", "EBeam/StageTa"), ("tilt2", "EBeam/StageTb")],
}


TFS_SCAN_DYNAMIC_TO_NX_EM = {
    "prefix": "/ENTRY[entry*]/measurement/EVENT_DATA_EM_SET[event_data_em_set]/EVENT_DATA_EM[event_data_em*]/em_lab/SCANBOX_EM[scanbox_em]",
    "use": [
        ("dwell_time/@units", "s"),
    ],
    "load_from": [("dwell_time", "Scan/Dwelltime"), ("scan_schema", "System/Scan")],
}


TFS_VARIOUS_DYNAMIC_TO_NX_EM = {
    "prefix": "/ENTRY[entry*]/measurement/EVENT_DATA_EM_SET[event_data_em_set]/EVENT_DATA_EM[event_data_em*]",
    "use": [("em_lab/EBEAM_COLUMN[ebeam_column]/electron_source/voltage/@units", "V")],
    "load_from": [
        ("em_lab/DETECTOR[detector*]/mode", "Detectors/Mode"),
        ("em_lab/EBEAM_COLUMN[ebeam_column]/operation_mode", "EBeam/UseCase"),
        ("em_lab/EBEAM_COLUMN[ebeam_column]/electron_source/voltage", "EBeam/HV"),
        ("event_type", "T1/Signal"),
        ("event_type", "T2/Signal"),
        ("event_type", "T3/Signal"),
        ("event_type", "ETD/Signal"),
    ],
}


TIFF_TFS_TO_NEXUS_CFG: Dict = {}
