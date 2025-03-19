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
"""Configuration of the image_tiff_fei parser."""

from typing import Any, Dict

from pynxtools_em.utils.pint_custom_unit_registry import ureg

# FEI Tecnai TEM-specific metadata based on prototype example
# currently not mapped:
# Intensity____31.429 dimensionless
# Objective lens____92.941 dimensionless
# Diffraction lens____36.754 dimensionless
# TODO::changeme need to go elsewhere after the Autumn NIAC meeting NXem

FEI_TECNAI_STATIC_VARIOUS_NX: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/instrument",
    "prefix_src": "",
    "use": [("fabrication/vendor", "FEI")],
    "map_to_str": [
        ("fabrication/model", "Microscope"),
        ("ebeam_column/electron_source/emitter_type", "Gun type"),
    ],
}


FEI_TECNAI_DYNAMIC_OPTICS_NX: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/events/EVENT_DATA_EM[event_data_em*]/instrument/optics",
    "prefix_src": "",
    "map_to_str": [("filtermode_tmp", "Filter mode")],
    "map_to_u4": [("gunlens_tmp", "Gun lens"), ("spotsize_tmp", "Spot size")],
    "map_to_f8": [
        ("magnification", "Magnification"),
        ("camera_length", ureg.meter, "Camera length", ureg.meter),
        ("defocus", ureg.meter, "Defocus", ureg.micrometer),
        ("rotation", ureg.radian, "Stem rotation", ureg.degree),
        ("rotation_correction", ureg.radian, "Stem rotation correction", ureg.degree),
    ],
}


FEI_TECNAI_DYNAMIC_STAGE_NX: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/events/EVENT_DATA_EM[event_data_em*]/instrument/stage",
    "prefix_src": "",
    "map_to_f8": [
        ("tilt1", ureg.radian, "Stage A", ureg.degree),
        ("tilt2", ureg.radian, "Stage B", ureg.degree),
        (
            "position",
            ureg.meter,
            ["Stage X", "Stage Y", "Stage Z"],
            # ureg.micrometer,
        ),
    ],
}
# TODO:: L68 should be commented in again related to not handling list of ureg.Quantity
# as catched currently in case_five_list of concepts/mapping_functors_pint L361


FEI_TECNAI_DYNAMIC_VARIOUS_NX: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/events/EVENT_DATA_EM[event_data_em*]",
    "prefix_src": "",
    "map_to_str": [("instrument/ebeam_column/operation_mode", "Mode")],
    "map_to_f8": [
        (
            "instrument/ebeam_column/electron_source/voltage",
            ureg.volt,
            "High tension",
            ureg.kilovolt,
        ),
        (
            "instrument/ebeam_column/electron_source/extraction_voltage",
            ureg.volt,
            "Extraction voltage",
            ureg.kilovolt,
        ),
        (
            "instrument/ebeam_column/electron_source/emission_current",
            ureg.ampere,
            "Emission",
            ureg.microampere,
        ),
    ],
}


# FEI Helios NanoLab FIB/SEM-specific metadata based on prototypic example

FEI_HELIOS_DYNAMIC_DETECTOR_NX: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/events/EVENT_DATA_EM[event_data_em*]/instrument/DETECTOR[detector*]",
    "prefix_src": "Metadata.Detectors.ScanningDetector.",
    "map_to_str": [("local_name", "DetectorName")],
}


FEI_HELIOS_STATIC_VARIOUS_NX: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/instrument",
    "prefix_src": "Metadata.",
    "use": [("fabrication/vendor", "FEI")],
    "map_to_str": [
        ("fabrication/model", "Instrument.InstrumentClass"),
        ("fabrication/serial_number", "Instrument.InstrumentID"),
        ("ebeam_column/electron_source/emitter_type", "Acquisition.SourceType"),
    ],
}


FEI_HELIOS_DYNAMIC_OPTICS_NX: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/events/EVENT_DATA_EM[event_data_em*]/instrument/optics",
    "prefix_src": "Metadata.",
    "map_to_bool": [
        ("tilt_correction", "Optics.SampleTiltCorrectionOn"),
        ("cross_over", "Optics.CrossOverOn"),
    ],
    "map_to_f8": [
        (
            "probe_current",
            ureg.ampere,
            "Optics.BeamCurrent",
            ureg.ampere,
        ),  # probe == beam ?
        ("working_distance", ureg.meter, "Optics.WorkingDistance", ureg.meter),
        (
            "eucentric_distance",
            ureg.meter,
            "Optics.EucentricWorkingDistance",
            ureg.meter,
        ),
    ],
}


FEI_HELIOS_DYNAMIC_STAGE_NX: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/events/EVENT_DATA_EM[event_data_em*]/instrument/stage",
    "prefix_src": "Metadata.StageSettings.StagePosition.",
    "map_to_f8": [
        ("rotation", ureg.radian, "Rotation", ureg.radian),
        ("tilt1", ureg.radian, "Tilt.Alpha", ureg.radian),
        ("tilt2", ureg.radian, "Tilt.Beta", ureg.radian),
        (
            "position",
            ureg.meter,
            ["X", "Y", "Z"],
            ureg.meter,
        ),
    ],
}


FEI_HELIOS_DYNAMIC_STIGMATOR_NX: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/events/EVENT_DATA_EM[event_data_em*]/instrument/ebeam_column/corrector_ax",
    "prefix_src": "Metadata.Optics.StigmatorRaw.",
    "map_to_f8": [("value_x", "X"), ("value_y", "Y")],  # unit?
}


FEI_HELIOS_DYNAMIC_SCAN_NX: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/events/EVENT_DATA_EM[event_data_em*]/instrument/scan_controller",
    "prefix_src": "Metadata.ScanSettings.",
    "map_to_f8": [("dwell_time", ureg.second, "DwellTime", ureg.second)],
}


FEI_HELIOS_DYNAMIC_VARIOUS_NX: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/events/EVENT_DATA_EM[event_data_em*]",
    "prefix_src": "Metadata.",
    "use": [
        ("instrument/ebeam_column/SENSOR[sensor1]/measurement", "pressure"),
        ("instrument/ibeam_column/SENSOR[sensor1]/measurement", "pressure"),
    ],
    "map_to_f8": [
        (
            "instrument/ebeam_column/SENSOR[sensor1]/value",
            ureg.pascal,
            "VacuumProperties.ElectronChamberPressure",
            ureg.pascal,
        ),
        (
            "instrument/ibeam_column/SENSOR[sensor1]/value",
            ureg.pascal,
            "VacuumProperties.IonChamberPressure",
            ureg.pascal,
        ),
        (
            "instrument/ebeam_column/electron_source/voltage",
            ureg.volt,
            "Optics.AccelerationVoltage",
            ureg.volt,
        ),
        (
            "instrument/ebeam_column/DEFLECTOR[beam_decelerator]/voltage",
            ureg.volt,
            "Optics.DecelerationVoltage",
            ureg.volt,
        ),
        (
            "instrument/ebeam_column/DEFLECTOR[beam_shift1]/value_x",
            ureg.meter,
            "Optics.BeamShift.X",
            ureg.meter,
        ),
        (
            "instrument/ebeam_column/DEFLECTOR[beam_shift1]/value_y",
            ureg.meter,
            "Optics.BeamShift.Y",
            ureg.meter,
        ),
        (
            "instrument/ebeam_column/electron_source/DEFLECTOR[gun_tilt]/value_x",
            "Optics.GunTiltRaw.X",
        ),
        (
            "instrument/ebeam_column/electron_source/DEFLECTOR[gun_tilt]/value_y",
            "Optics.GunTiltRaw.Y",
        ),
        (
            "instrument/ebeam_column/APERTURE[aperture*]/size",
            ureg.meter,
            "Optics.Apertures.Aperture.Diameter",
            ureg.meter,
        ),
        # (
        #     "instrument/ebeam_column/BEAM[beam]/value",
        #     ureg.meter,
        #     "Optics.SpotSize",
        #     ureg.meter,
        # ),
        # replace by beam diameter
    ],
}

# currently not mapped:
# SEM_Image_-_SliceImage_-_109.tif
# Metadata.@xmlns:nil, http://schemas.fei.com/Metadata/v1/2013/07  this link no longer works (2024/11/04)
# Metadata.@xmlns:xsi, http://www.w3.org/2001/XMLSchema-instance
# Metadata.Core.Guid, 93b31de4-087f-4b44-8390-8d5e971bc94b
# Metadata.Core.UserID, Supervisor
# Metadata.Core.ApplicationSoftware, xT
# Metadata.Core.ApplicationSoftwareVersion, 0
# Metadata.Instrument.ControlSoftwareVersion, 10.1.7.5675
# Metadata.Acquisition.AcquisitionDatetime, 2021-03-03T11:31:14
# Metadata.Acquisition.BeamType, Electron         process beam type
# Metadata.Acquisition.ColumnType, Elstar
# Metadata.Detectors.ScanningDetector.DetectorType, TLD
# Metadata.Detectors.ScanningDetector.Signal, BSE
# Metadata.Detectors.ScanningDetector.Gain, 45.956145987158642
# Metadata.Detectors.ScanningDetector.Offset, -6.2495952023896315
# Metadata.Detectors.ScanningDetector.GridVoltage, 0
# Metadata.Detectors.ScanningDetector.ConverterElectrodeVoltage, 0
# Metadata.Detectors.ScanningDetector.ContrastNormalized, 80.446892241078331
# Metadata.Detectors.ScanningDetector.BrightnessNormalized, 23.960385596512875
# Metadata.VacuumProperties.SamplePressure, 0.00018694142371456488
# Metadata.GasInjectionSystems.Gis.[0].PortName, Port1
# Metadata.GasInjectionSystems.Gis.[0].NeedleState, Retracted
# Metadata.GasInjectionSystems.Gis.[0].Gases.Gas.GasType, G1
# Metadata.GasInjectionSystems.Gis.[1].PortName, Port2
# Metadata.GasInjectionSystems.Gis.[1].NeedleState, Retracted
# Metadata.GasInjectionSystems.Gis.[1].Gases.Gas.GasType, G2
# Metadata.BinaryResult.CompositionType, Single       composition_type_tmp
# Metadata.BinaryResult.FilterType, DriftCorrectedFrameIntegration  # filter_type_tmp
# Metadata.BinaryResult.FilterFrameCount, 1           filter_frame_count_tmp
# Metadata.ScanSettings.LineTime, 0.0031665
# Metadata.ScanSettings.LineIntegrationCount, 1
# Metadata.ScanSettings.LineInterlacing, 1
# Metadata.ScanSettings.FrameTime, 12.969984
# Metadata.ScanSettings.ScanRotation, 0
# Metadata.Optics.SamplePreTiltAngle, -0.66323502406567147
