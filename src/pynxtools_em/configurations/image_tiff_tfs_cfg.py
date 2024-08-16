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
"""Configuration of the image_tiff_tfs parser."""

from numpy import pi

RAD2DEG = 180.0 / pi


TFS_DETECTOR_STATIC_TO_NX_EM = {
    "prefix_trg": "/ENTRY[entry*]/measurement/em_lab/DETECTOR[detector*]",
    "map": [
        ("local_name", "Detectors/Name"),
    ],
}


TFS_APERTURE_STATIC_TO_NX_EM = {
    "prefix_trg": "/ENTRY[entry*]/measurement/em_lab/EBEAM_COLUMN[ebeam_column]/APERTURE_EM[aperture_em*]",
    "use": [("value/@units", "m")],
    "map": [
        ("description", "Beam/Aperture"),
        ("value", "EBeam/ApertureDiameter"),
    ],
}


TFS_VARIOUS_STATIC_TO_NX_EM = {
    "prefix_trg": "/ENTRY[entry*]/measurement/em_lab",
    "use": [("FABRICATION[fabrication]/vendor", "FEI")],
    "map": [
        ("FABRICATION[fabrication]/model", "System/SystemType"),
        ("FABRICATION[fabrication]/identifier", "System/BuildNr"),
        ("EBEAM_COLUMN[ebeam_column]/electron_source/emitter_type", "System/Source"),
    ],
}


TFS_OPTICS_DYNAMIC_TO_NX_EM = {
    "prefix_trg": "/ENTRY[entry*]/measurement/EVENT_DATA_EM_SET[event_data_em_set]/EVENT_DATA_EM[event_data_em*]/em_lab/OPTICAL_SYSTEM_EM[optical_system_em]",
    "use": [("beam_current/@units", "A"), ("working_distance/@units", "m")],
    "map": [
        ("beam_current", "EBeam/BeamCurrent"),
        ("working_distance", "EBeam/WD"),
    ],
}


TFS_STAGE_DYNAMIC_TO_NX_EM = {
    "prefix_trg": "/ENTRY[entry*]/measurement/EVENT_DATA_EM_SET[event_data_em_set]/EVENT_DATA_EM[event_data_em*]/em_lab/STAGE_LAB[stage_lab]",
    "use": [("tilt1/@units", "deg"), ("tilt2/@units", "deg")],
    "map_to_real_and_multiply": [
        ("tilt1", "EBeam/StageTa", RAD2DEG),
        ("tilt2", "EBeam/StageTb", RAD2DEG),
    ],
}


TFS_SCAN_DYNAMIC_TO_NX_EM = {
    "prefix_trg": "/ENTRY[entry*]/measurement/EVENT_DATA_EM_SET[event_data_em_set]/EVENT_DATA_EM[event_data_em*]/em_lab/SCANBOX_EM[scanbox_em]",
    "use": [
        ("dwell_time/@units", "s"),
    ],
    "map": [("dwell_time", "Scan/Dwelltime"), ("scan_schema", "System/Scan")],
}


TFS_VARIOUS_DYNAMIC_TO_NX_EM = {
    "prefix_trg": "/ENTRY[entry*]/measurement/EVENT_DATA_EM_SET[event_data_em_set]/EVENT_DATA_EM[event_data_em*]",
    "use": [("em_lab/EBEAM_COLUMN[ebeam_column]/electron_source/voltage/@units", "V")],
    "map": [
        ("em_lab/DETECTOR[detector*]/mode", "Detectors/Mode"),
        ("em_lab/EBEAM_COLUMN[ebeam_column]/operation_mode", "EBeam/UseCase"),
        ("em_lab/EBEAM_COLUMN[ebeam_column]/electron_source/voltage", "EBeam/HV"),
        ("event_type", "T1/Signal"),
        ("event_type", "T2/Signal"),
        ("event_type", "T3/Signal"),
        ("event_type", "ETD/Signal"),
    ],
}


# this example exemplifies the situation for the TFS/FEI SEM Apreo from the IKZ of Prof. Martin Albrecht
# thanks to Robert Kernke it was clarified the microscope has several detectors and imaging modes
# these imaging modes control the specific TFS/FEI concept instances stored in the respective TIFF file
# we here use a glossary of all concepts which we were able to parse out from an example image
# taken for each detector and imaging mode
# we then assume that one can work with the joint set of these concepts

TIFF_TFS_PARENT_CONCEPTS = [
    "Accessories",
    "Beam",
    "ColdStage",
    "CompoundLensFilter",
    "Detectors",
    "EBeam",
    "EBeamDeceleration",
    "EScan",
    "ETD",
    "EasyLift",
    "GIS",
    "HiResIllumination",
    "HotStage",
    "HotStageHVHS",
    "HotStageMEMS",
    "IRBeam",
    "Image",
    "Nav-Cam",
    "PrivateFei",
    "Scan",
    "Specimen",
    "Stage",
    "System",
    "T1",
    "T2",
    "T3",
    "User",
    "Vacuum",
]

TIFF_TFS_ALL_CONCEPTS = [
    "Accessories/Number",
    "Beam/Beam",
    "Beam/BeamShiftX",
    "Beam/BeamShiftY",
    "Beam/FineStageBias",
    "Beam/HV",
    "Beam/ImageMode",
    "Beam/Scan",
    "Beam/ScanRotation",
    "Beam/Spot",
    "Beam/StigmatorX",
    "Beam/StigmatorY",
    "ColdStage/ActualTemperature",
    "ColdStage/Humidity",
    "ColdStage/SampleBias",
    "ColdStage/TargetTemperature",
    "CompoundLensFilter/IsOn",
    "CompoundLensFilter/ThresholdEnergy",
    "Detectors/Mode",
    "Detectors/Name",
    "Detectors/Number",
    "EasyLift/Rotation",
    "EBeam/Acq",
    "EBeam/Aperture",
    "EBeam/ApertureDiameter",
    "EBeam/ATubeVoltage",
    "EBeam/BeamCurrent",
    "EBeam/BeamMode",
    "EBeam/BeamShiftX",
    "EBeam/BeamShiftY",
    "EBeam/ColumnType",
    "EBeam/DynamicFocusIsOn",
    "EBeam/DynamicWDIsOn",
    "EBeam/EmissionCurrent",
    "EBeam/EucWD",
    "EBeam/FinalLens",
    "EBeam/HFW",
    "EBeam/HV",
    "EBeam/ImageMode",
    "EBeam/LensMode",
    "EBeam/LensModeA",
    "EBeam/MagnificationCorrection",
    "EBeam/PreTilt",
    "EBeam/ScanRotation",
    "EBeam/SemOpticalMode",
    "EBeam/Source",
    "EBeam/SourceTiltX",
    "EBeam/SourceTiltY",
    "EBeam/StageR",
    "EBeam/StageTa",
    "EBeam/StageTb",
    "EBeam/StageX",
    "EBeam/StageY",
    "EBeam/StageZ",
    "EBeam/StigmatorX",
    "EBeam/StigmatorY",
    "EBeam/TiltCorrectionAngle",
    "EBeam/TiltCorrectionIsOn",
    "EBeam/UseCase",
    "EBeam/VFW",
    "EBeam/WD",
    "EBeam/WehneltBias",
    "EBeamDeceleration/ImmersionRatio",
    "EBeamDeceleration/LandingEnergy",
    "EBeamDeceleration/ModeOn",
    "EBeamDeceleration/StageBias",
    "EScan/Dwell",
    "EScan/FrameTime",
    "EScan/HorFieldsize",
    "EScan/InternalScan",
    "EScan/LineIntegration",
    "EScan/LineTime",
    "EScan/Mainslock",
    "EScan/PixelHeight",
    "EScan/PixelWidth",
    "EScan/Scan",
    "EScan/ScanInterlacing",
    "EScan/VerFieldsize",
    "ETD/Brightness",
    "ETD/BrightnessDB",
    "ETD/Contrast",
    "ETD/ContrastDB",
    "ETD/Grid",
    "ETD/MinimumDwellTime",
    "ETD/Mix",
    "ETD/Setting",
    "ETD/Signal",
    "GIS/Number",
    "HiResIllumination/BrightFieldIsOn",
    "HiResIllumination/BrightFieldValue",
    "HiResIllumination/DarkFieldIsOn",
    "HiResIllumination/DarkFieldValue",
    "HotStage/ActualTemperature",
    "HotStage/SampleBias",
    "HotStage/ShieldBias",
    "HotStage/TargetTemperature",
    "HotStageHVHS/ActualTemperature",
    "HotStageHVHS/SampleBias",
    "HotStageHVHS/ShieldBias",
    "HotStageHVHS/TargetTemperature",
    "HotStageMEMS/ActualTemperature",
    "HotStageMEMS/HeatingCurrent",
    "HotStageMEMS/HeatingPower",
    "HotStageMEMS/HeatingVoltage",
    "HotStageMEMS/SampleBias",
    "HotStageMEMS/SampleResistance",
    "HotStageMEMS/TargetTemperature",
    "Image/Average",
    "Image/DigitalBrightness",
    "Image/DigitalContrast",
    "Image/DigitalGamma",
    "Image/DriftCorrected",
    "Image/Integrate",
    "Image/MagCanvasRealWidth",
    "Image/MagnificationMode",
    "Image/PostProcessing",
    "Image/ResolutionX",
    "Image/ResolutionY",
    "Image/ScreenMagCanvasRealWidth",
    "Image/ScreenMagnificationMode",
    "Image/Transformation",
    "Image/ZoomFactor",
    "Image/ZoomPanX",
    "Image/ZoomPanY",
    "IRBeam/HFW",
    "IRBeam/n",
    "IRBeam/ScanRotation",
    "IRBeam/SiDepth",
    "IRBeam/StageR",
    "IRBeam/StageTa",
    "IRBeam/StageTb",
    "IRBeam/StageX",
    "IRBeam/StageY",
    "IRBeam/StageZ",
    "IRBeam/VFW",
    "IRBeam/WD",
    "PrivateFei/BitShift",
    "PrivateFei/DataBarAvailable",
    "PrivateFei/DatabarHeight",
    "PrivateFei/DataBarSelected",
    "PrivateFei/TimeOfCreation",
    "Scan/Average",
    "Scan/Dwelltime",
    "Scan/FrameTime",
    "Scan/HorFieldsize",
    "Scan/Integrate",
    "Scan/InternalScan",
    "Scan/PixelHeight",
    "Scan/PixelWidth",
    "Scan/VerFieldsize",
    "Specimen/SpecimenCurrent",
    "Specimen/Temperature",
    "Stage/ActiveStage",
    "Stage/SpecTilt",
    "Stage/StageR",
    "Stage/StageT",
    "Stage/StageTb",
    "Stage/StageX",
    "Stage/StageY",
    "Stage/StageZ",
    "Stage/WorkingDistance",
    "System/Acq",
    "System/Aperture",
    "System/BuildNr",
    "System/Chamber",
    "System/Column",
    "System/DisplayHeight",
    "System/DisplayWidth",
    "System/Dnumber",
    "System/ESEM",
    "System/EucWD",
    "System/FinalLens",
    "System/Pump",
    "System/Scan",
    "System/Software",
    "System/Source",
    "System/Stage",
    "System/SystemType",
    "System/Type",
    "T1/Brightness",
    "T1/BrightnessDB",
    "T1/Contrast",
    "T1/ContrastDB",
    "T1/MinimumDwellTime",
    "T1/Setting",
    "T1/Signal",
    "T2/Brightness",
    "T2/BrightnessDB",
    "T2/Contrast",
    "T2/ContrastDB",
    "T2/MinimumDwellTime",
    "T2/Setting",
    "T2/Signal",
    "T3/Brightness",
    "T3/BrightnessDB",
    "T3/Contrast",
    "T3/ContrastDB",
    "T3/MinimumDwellTime",
    "T3/Signal",
    "User/Date",
    "User/Time",
    "User/User",
    "User/UserText",
    "User/UserTextUnicode",
    "Vacuum/ChPressure",
    "Vacuum/Gas",
    "Vacuum/Humidity",
    "Vacuum/UserMode",
]

# there is more to know and understand than just knowing TFS/FEI uses
# the above-mentioned concepts in their taxonomy:
# take the example of System/Source for which an example file (instance) has the
# value "FEG"
# similar like in NeXus "System/Source" labels a concept for which (assumption!) there
# is a controlled enumeration of symbols possible (as the example shows "FEG" is one such
# allowed symbol of the enumeration.
# The key issue is that the symbols for the leaf (here "FEG") means nothing eventually
# when one has another semantic world-view, like in NOMAD metainfo or NeXus
# (only us) humans understand that what TFS/FEI likely means with the symbol
# "FEG" is exactly the same as what we mean in NeXus when setting emitter_type of
# NXebeam_column to "cold_cathode_field_emitter"
# world with the controlled enumeration value "other" because we do not know
# if FEG means really a filament or a cold_cathode_field_emitter
