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
"""Map content from Velox EMD file format onto NeXus concepts."""

from typing import Any, Dict

from pynxtools_em.utils.pint_custom_unit_registry import ureg

VELOX_WHICH_SPECTRUM = {
    "eV": ("spectrum_0d", ["axis_energy"]),
    "m_eV": ("spectrum_1d", ["axis_i", "axis_energy"]),
    "m_m_eV": ("spectrum_2d", ["axis_j", "axis_i", "axis_energy"]),
}
VELOX_WHICH_IMAGE = {
    "m": ("image_1d", ["axis_i"]),
    "1/m": ("image_1d", ["axis_i"]),
    "m_m": ("image_2d", ["axis_j", "axis_i"]),
    "1/m_1/m": ("image_2d", ["axis_j", "axis_i"]),
}


VELOX_STATIC_ENTRY_NX: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/instrument/programID[program1]",
    "prefix_src": "",
    "use": [
        (
            "program",
            "Not reported in original_metadata parsed from Velox EMD using rosettasciio",
        )
    ],
    "map_to_str": [("program/@version", "Instrument/ControlSoftwareVersion")],
}


VELOX_STATIC_EBEAM_NX: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/instrument/ebeam_column/electron_source",
    "prefix_src": "",
    "use": [("probe", "electron")],
    "map_to_str": [("emitter_type", "Acquisition/SourceType")],
}


VELOX_STATIC_FABRICATION_NX: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/instrument/fabrication",
    "prefix_src": "",
    "map_to_str": [
        ("vendor", "Instrument/Manufacturer"),
        ("model", "Instrument/InstrumentModel"),
        ("serial_number", "Instrument/InstrumentId"),
    ],
}


VELOX_DYNAMIC_SCAN_NX: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/eventID[event*]/instrument/ebeam_column/scan_controller",
    "prefix_src": "",
    "map_to_f8": [("dwell_time", ureg.second, "Scan/DwellTime", ureg.microsecond)],
}


VELOX_DYNAMIC_OPTICS_NX: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/eventID[event*]/instrument/optics",
    "prefix_src": "",
    "map_to_f8": [
        ("magnification", ureg.nx_dimensionless, "Optics/NominalMagnification"),
        ("camera_length", ureg.meter, "Optics/CameraLength", ureg.millimeter),
        ("defocus", ureg.meter, "Optics/Defocus", ureg.nanometer),
        (
            "semi_convergence_angle",
            ureg.radian,
            "Optics/BeamConvergence",
            ureg.milliradian,
        ),
        ("rotation", ureg.degrees, "Optics/ScanRotation", ureg.degrees),
        ("dose_rate", ureg.dose_rate, "Optics/DoseRate", ureg.dose_rate),
    ],
}
# assume BeamConvergence is the semi_convergence_angle, needs clarification from vendors and colleagues


VELOX_DYNAMIC_STAGE_NX: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/eventID[event*]/instrument/stageID[stage]",
    "prefix_src": "",
    "map_to_str": [("design", "Stage/HolderType")],
    "map_to_f8": [
        ("tilt1", ureg.radian, "Stage/AlphaTilt", ureg.degrees),
        ("tilt2", ureg.radian, "Stage/BetaTilt", ureg.degrees),
        (
            "position",
            ureg.meter,
            ["Stage/Position/x", "Stage/Position/y", "Stage/Position/z"],
            ureg.micrometer,
        ),
    ],
}
# we do not know whether the angle is radiant or degree, in all examples
# the instance values are very small so can be both :( needs clarification
# we also cannot document this into the NeXus file like @units = "check this"
# because then the dataconverter (rightly so complains) that the string "check this"
# is not a proper unit for an instance of NX_VOLTAGE


VELOX_DYNAMIC_VARIOUS_NX: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/eventID[event*]",
    "prefix_src": "",
    "unix_to_iso8601": [
        ("start_time", "Acquisition/AcquisitionStartDatetime/DateTime")
    ],
}


VELOX_DYNAMIC_EBEAM_NX: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/eventID[event*]/instrument/ebeam_column",
    "prefix_src": "",
    "map_to_str": [
        ("operation_mode", ["Optics/OperatingMode", "Optics/TemOperatingSubMode"])
    ],
    "map_to_f8": [
        ("electron_source/voltage", ureg.volt, "Optics/AccelerationVoltage", ureg.volt),
        ("electron_source/"),
    ],
}

# orientation of tiff images, https://github.com/python-pillow/Pillow/issues/4053

# Velox 3.14 manual examples following that guided this configuration
## Camera image
# Detector Ceta (bottom-mounted) >> {IMAGE,SPECTRUM}/detector_identifier
# Magnification 36617 x >> ok
# Image size 4096 x 4096 >> ok

## STEM image
# Detector HAADF >> {IMAGE,SPECTRUM}/detector_identifier
# STEM Magnification 10.00 kx >> OK
# Scan rotation -180.0 ° >> OK
# Camera length 55.0 mm >> OK
# Dwell time 1.00 μs >> OK
# Image size 512 x 512 >> OK
# Collection angle range 104 - 200 mrad >> leave comment in NXevent_data_em that if acquisition parameter are not the same each image needs to have an own entry!
# Dose Rate 41897.51 e/Å2/s >> OK

## Spectrum image
# STEM Magnification 30.19 kx The STEM magnification (by definition 0.1 m / Field of view) >> OK
# Dwell time 20.0 μs >> OK
# Image size 512 x 512 >> OK
# Dispersion 10 eV The dispersion spectrum (width in eV of each bin). >> NXevent_data_em detector, dispersion
# Shaping time 1 μs The shaping time of the EDS detector. >> time_constant with https://www.globalsino.com/EM/page1379.html in NXem/detector inside NXevent_data_em
# Segments 1, 2, 3, 4 The enabled segments of a multi-segment EDS detector. >> add {parts,segments_used} no constraint on dim
# Dose Rate 41897.51 e/Å2/s >> OK

## General
# Detector BM-Ceta >> {IMAGE,SPECTRUM}/detector_identifier
# Pixel size 263.8 pm x 263.8 pm The pixel size of the image. >> OK
# Pixel offset -540.34 nm x -540.34 nm The coordinates of the top-left pixel in the image. >> fix potential flip of tiffs in pynxtools-em in general
# Acquisition start 4/19/2019 12:01 Format: m/d/yyyy h24:min >> needs carrying over via an example

## General for spectrum
# Detector SuperXG1 >> OK
# Pixel size 6.469 nm x 6.469 nm The pixel size of the image. >> OK
# Pixel offset -1.6561 μm x -1.6561 μm The physical position of the top-left pixel in the image >> this is currently not considered ...
# Intensity scale 1.000 kg/kg The intensity scale of the image, to convert intensities into (in this case) weight fraction.
# Intensity offset 0 fg/kg The offset of the intensity scale (usually zero).
# Acquisition start 12/19/2016 10:57 Format: m/d/yyyy h24:min

## Scan settings
# Dwell time 20.0 μs >> OK
# Scan size 512 x 512 >> OK
# Scan area (0, 0), 512 x 512 The scan size area: (top, left), width x height >> should be fixed when handling all tiff orientation cases
# Mains lock Off >> what is this?
# Frame time 5.87 s >> why relevant there is dwell time, isnt this n_pixels * dwell_time + flytime
# Scan rotation -180.0 ° >> OK

## Stage
# Position (x, y, z) -22.97 μm, 116.20 μm, -91.44 μm >> OK
# Tilt (α, β) 3.67 °, -0.60 ° >> OK
# Holder type FEI Double Tilt >> OK

## Optics
# C1 Aperture 2000 μm >> OK
# C2 Aperture 50 μm >> OK
# C3 Aperture 2000 μm >> OK
# OBJ Aperture Retracted >> OK
# SA Aperture Retracted >> OK
# Last measured screen current 684 pA
# Gun lens 1 >> OK
# Extractor 3950 V >> add in NXem/electron_source
# HT 300 kV
# Spot size 6
# C1 -36.57% >> OK
# C2 13.91% >> OK
# C3 37.52% >> OK
# Minicondenser 19.48% >> OK
# Objective 87.65% >> OK
# Lorentz -64.66% >> OK
# Diffraction 21.48% >> OK
# Intermediate 5.18% >> OK
# P1 25.19% >> OK
# P2 91.03% >> OK
# Beam convergence 19.6 mrad
# Full scan field of view 3.312 μm, 3.312 μm For STEM mode. The scan field of view (0.1 m / STEM magnification) >> OK
# Defocus 95 nm >> OK
# Operating mode STEM TEM or STEM >> OK
# Projector mode Diffraction Imaging or Diffraction >> add
# EFTEM Off >> add
# Objective lens mode HM >> add
# Illumination mode Probe >> add
# Probe mode Nano probe >> add, matrix Martin
# Magnification 36617 x For Projector mode: Imaging >> OK
# Camera length 60 mm For Imaging mode: Diffraction >> OK
