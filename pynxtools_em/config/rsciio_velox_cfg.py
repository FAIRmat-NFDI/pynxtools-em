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
"""Map Velox to NeXus concepts."""

# Velox *.emd
# "Core/MetadataDefinitionVersion": ["7.9"]
# "Core/MetadataSchemaVersion": ["v1/2013/07"]
# all *.emd files from https://ac.archive.fhi.mpg.de/D62142 parsed with
# rosettasciio 0.2, hyperspy 1.7.6
# unique original_metadata keys
# keys with hash instance duplicates removed r"([0-9a-f]{32})"
# keys with detector instance duplicates removed r"(Detector-[0-9]+)"
# keys with aperture instance duplicates removed r"(Aperture-[0-9]+)"
# remaining instance duplicates for BM-Ceta and r"(SuperXG[0-9]{2})" removed manually
# Concept names like Projector1Lens<term> and Projector2Lens<term> mean two different concept instances
# of the same concept Projector*Lens<term> in NeXus this would become lens_em1(NXlens_em) name: projector, and field named <term>

# ("/ENTRY[entry*]/measurement/event_data_em_set/EVENT_DATA_EM[event_data_em*]/em_lab/LENS_EM[lens_em*]/name", "is", "C1"),
# ("/ENTRY[entry*]/measurement/event_data_em_set/EVENT_DATA_EM[event_data_em*]/em_lab/LENS_EM[lens_em*]/value", "load", "Optics/C1LensIntensity"),
# ("/ENTRY[entry*]/", "load", "Optics/C2LensIntensity")
# this can not work but has to be made explicit with an own function that is Velox MetadataSchema-version and NeXus NXem-schema-version-dependent for the lenses

VELOX_ENTRY_TO_NX_EM = {
    "prefix": "/ENTRY[entry*]/measurement/em_lab/control_program",
    "use": [
        (
            "program",
            "Not reported in original_metadata parsed from Velox EMD using rosettasciio",
        )
    ],
    "load": [("program/@version", "Instrument/ControlSoftwareVersion")],
}


VELOX_EBEAM_STATIC_TO_NX_EM = {
    "prefix": "/ENTRY[entry*]/measurement/em_lab/EBEAM_COLUMN[ebeam_column]/electron_source",
    "use": [("probe", "electron")],
    "load": [("emitter_type", "Acquisition/SourceType")],
}


VELOX_FABRICATION_TO_NX_EM = {
    "prefix": "/ENTRY[entry*]/measurement/em_lab/FABRICATION[fabrication]",
    "load": [
        ("identifier", "Instrument/InstrumentId"),
        ("model", "Instrument/InstrumentModel"),
        ("vendor", "Instrument/Manufacturer"),
    ],
    "join_str": [
        ("model", ["Instrument/InstrumentClass", "Instrument/InstrumentModel"])
    ],
}


VELOX_SCAN_TO_NX_EM = {
    "prefix": "/ENTRY[entry*]/measurement/event_data_em_set/EVENT_DATA_EM[event_data_em*]/em_lab/SCANBOX_EM[scanbox_em]",
    "use": [("dwell_time/@units", "s")],
    "map_to_real": [("dwell_time", "Scan/DwellTime")],
}


VELOX_OPTICS_TO_NX_EM = {
    "prefix": "/ENTRY[entry*]/measurement/event_data_em_set/EVENT_DATA_EM[event_data_em*]/em_lab/OPTICAL_SYSTEM_EM[optical_system_em]",
    "use": [
        ("camera_length/@units", "m"),
        ("defocus/@units", "m"),
        ("semi_convergence_angle/@units", "rad"),
    ],
    "map_to_real": [
        ("magnification", "Optics/NominalMagnification"),
        ("camera_length", "Optics/CameraLength"),
        ("defocus", "Optics/Defocus"),
    ],
    "map_to_real_and_multiply": [
        ("semi_convergence_angle", "Optics/BeamConvergence", 1.0),
    ],
}
# assume BeamConvergence is the semi_convergence_angle, needs clarification from vendors and colleagues


VELOX_STAGE_TO_NX_EM = {
    "prefix": "/ENTRY[entry*]/measurement/event_data_em_set/EVENT_DATA_EM[event_data_em*]/em_lab/STAGE_LAB[stage_lab]",
    "use": [
        ("tilt1/@units", "rad"),
        ("tilt2/@units", "rad"),
        ("position/@units", "m"),
    ],
    "map_to_str": [("design", "Stage/HolderType")],
    "map_to_real": [
        ("tilt1", "Stage/AlphaTilt"),
        ("tilt2", "Stage/BetaTilt"),
        ("position", ["Stage/Position/x", "Stage/Position/y", "Stage/Position/z"]),
    ],
}
# we do not know whether the angle is radiant or degree, in all examples
# the instance values are very small so can be both :( needs clarification
# we also cannot document this into the NeXus file like @units = "Check this"
# because then the dataconverter (rightly so complains) that the string "Check this"
# is not a proper unit for an instance of NX_VOLTAGE


VELOX_DYNAMIC_TO_NX_EM = {
    "prefix": "/ENTRY[entry*]/measurement/event_data_em_set/EVENT_DATA_EM[event_data_em*]",
    "unix_to_iso8601": [
        ("start_time", "Acquisition/AcquisitionStartDatetime/DateTime")
    ],
}


VELOX_EBEAM_DYNAMIC_TO_NX_EM = {
    "prefix": "/ENTRY[entry*]/measurement/event_data_em_set/EVENT_DATA_EM[event_data_em*]/em_lab/EBEAM_COLUMN[ebeam_column]",
    "use": [
        ("electron_source/voltage/@units", "V"),
    ],
    "concatenate": [
        ("operation_mode", ["Optics/OperatingMode", "Optics/TemOperatingSubMode"])
    ],
    "map_to_real": [("electron_source/voltage", "Optics/AccelerationVoltage")],
}
