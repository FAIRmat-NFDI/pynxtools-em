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
"""Map content from Velox EMD file format onto NeXus concepts.

# TODO move to pynxtools-em Velox parser documentation
"Core/MetadataDefinitionVersion": ["7.9"]
"Core/MetadataSchemaVersion": ["v1/2013/07"]
all *.emd files from https://ac.archive.fhi.mpg.de/D62142 parsed with
rosettasciio 0.2, hyperspy 1.7.6
unique original_metadata keys
keys with hash instance duplicates removed r"([0-9a-f]{32})"
keys with detector instance duplicates removed r"(Detector-[0-9]+)"
keys with aperture instance duplicates removed r"(Aperture-[0-9]+)"
remaining instance duplicates for BM-Ceta and r"(SuperXG[0-9]{2})" removed manually
Concept names like Projector1Lens<term> and Projector2Lens<term> mean two different concept instances
of the same concept Projector*Lens<term> in NeXus this would become lens_em1(NXlens_em) name: projector, and field named <term>

("/ENTRY[entry*]/measurement/event_data_em_set/EVENT_DATA_EM[event_data_em*]/em_lab/LENS_EM[lens_em*]/name", "is", "C1"),
("/ENTRY[entry*]/measurement/event_data_em_set/EVENT_DATA_EM[event_data_em*]/em_lab/LENS_EM[lens_em*]/value", "map", "Optics/C1LensIntensity"),
("/ENTRY[entry*]/", "map", "Optics/C2LensIntensity")
this can not work but has to be made explicit with an own function that is Velox
MetadataSchema-version and NeXus NXem-schema-version-dependent for the lenses
"""

from pynxtools_em.utils.pint_custom_unit_registry import ureg

VELOX_STATIC_ENTRY_TO_NX_EM = {
    "prefix_trg": "/ENTRY[entry*]/measurement/em_lab/control_program",
    "prefix_src": "",
    "use": [
        (
            "program",
            "Not reported in original_metadata parsed from Velox EMD using rosettasciio",
        )
    ],
    "map": [("program/@version", "Instrument/ControlSoftwareVersion")],
}


VELOX_STATIC_EBEAM_TO_NX_EM = {
    "prefix_trg": "/ENTRY[entry*]/measurement/em_lab/ebeam_column/electron_source",
    "prefix_src": "",
    "use": [("probe", "electron")],
    "map": [("emitter_type", "Acquisition/SourceType")],
}


VELOX_STATIC_FABRICATION_TO_NX_EM = {
    "prefix_trg": "/ENTRY[entry*]/measurement/em_lab/fabrication",
    "prefix_src": "",
    "map": [
        ("identifier", "Instrument/InstrumentId"),
        ("model", "Instrument/InstrumentModel"),
        ("vendor", "Instrument/Manufacturer"),
        ("model", ["Instrument/InstrumentClass", "Instrument/InstrumentModel"]),
    ],
}


VELOX_DYNAMIC_SCAN_TO_NX_EM = {
    "prefix_trg": "/ENTRY[entry*]/measurement/event_data_em_set/EVENT_DATA_EM[event_data_em*]/em_lab/scan_controller",
    "prefix_src": "",
    "map_to_f8": [("dwell_time", ureg.second, "Scan/DwellTime", ureg.second)],
}


VELOX_DYNAMIC_OPTICS_TO_NX_EM = {
    "prefix_trg": "/ENTRY[entry*]/measurement/event_data_em_set/EVENT_DATA_EM[event_data_em*]/em_lab/OPTICAL_SYSTEM_EM[optical_system_em]",
    "prefix_src": "",
    "map_to_f8": [
        ("magnification", "Optics/NominalMagnification"),
        ("camera_length", ureg.meter, "Optics/CameraLength", ureg.meter),
        ("defocus", ureg.meter, "Optics/Defocus", ureg.meter),
        ("semi_convergence_angle", ureg.radian, "Optics/BeamConvergence", ureg.radian),
    ],
}
# assume BeamConvergence is the semi_convergence_angle, needs clarification from vendors and colleagues


VELOX_DYNAMIC_STAGE_TO_NX_EM = {
    "prefix_trg": "/ENTRY[entry*]/measurement/event_data_em_set/EVENT_DATA_EM[event_data_em*]/em_lab/STAGE_LAB[stage_lab]",
    "prefix_src": "",
    "map": [("design", "Stage/HolderType")],
    "map_to_f8": [
        ("tilt1", ureg.radian, "Stage/AlphaTilt", ureg.radian),
        ("tilt2", ureg.radian, "Stage/BetaTilt", ureg.radian),
        (
            "position",
            ureg.meter,
            ["Stage/Position/x", "Stage/Position/y", "Stage/Position/z"],
            ureg.meter,
        ),
    ],
}
# we do not know whether the angle is radiant or degree, in all examples
# the instance values are very small so can be both :( needs clarification
# we also cannot document this into the NeXus file like @units = "check this"
# because then the dataconverter (rightly so complains) that the string "check this"
# is not a proper unit for an instance of NX_VOLTAGE


VELOX_DYNAMIC_VARIOUS_TO_NX_EM = {
    "prefix_trg": "/ENTRY[entry*]/measurement/event_data_em_set/EVENT_DATA_EM[event_data_em*]",
    "prefix_src": "",
    "unix_to_iso8601": [
        ("start_time", "Acquisition/AcquisitionStartDatetime/DateTime")
    ],
}


VELOX_DYNAMIC_EBEAM_TO_NX_EM = {
    "prefix_trg": "/ENTRY[entry*]/measurement/event_data_em_set/EVENT_DATA_EM[event_data_em*]/em_lab/ebeam_column",
    "prefix_src": "",
    "map": [("operation_mode", ["Optics/OperatingMode", "Optics/TemOperatingSubMode"])],
    "map_to_f8": [
        ("electron_source/voltage", ureg.volt, "Optics/AccelerationVoltage", ureg.volt)
    ],
}
