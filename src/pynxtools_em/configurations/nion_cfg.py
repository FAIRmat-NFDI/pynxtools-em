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
"""Dict mapping Nion custom schema instances on concepts in NXem."""

from typing import Any, Dict

from pynxtools_em.utils.pint_custom_unit_registry import ureg

WHICH_SPECTRUM = {
    "eV": ("spectrum_0d", ["energy"]),
    "nm_eV": ("spectrum_1d", ["i", "energy"]),
    "nm_nm_eV": ("spectrum_2d", ["j", "i", "energy"]),
    "nm_nm_nm_eV": ("spectrum_3d", ["k", "j", "i", "energy"]),
    "unitless_eV": ("stack_0d", ["spectrum_identifier", "energy"]),
    "unitless_nm_eV": ("stack_1d", ["spectrum_identifier", "energy"]),
    "unitless_nm_nm_eV": ("stack_2d", ["spectrum_identifier", "j", "i", "energy"]),
    "unitless_nm_nm_nm_eV": (
        "stack_3d",
        ["spectrum_identifier", "k", "j", "i", "energy"],
    ),
}
WHICH_IMAGE = {
    "nm": ("image_1d", ["i"]),
    "nm_nm": ("image_2d", ["j", "i"]),
    "nm_nm_nm": ("image_3d", ["k", "j", "i"]),
    "unitless_nm": ("stack_1d", ["image_identifier", "i"]),
    "unitless_nm_nm": ("stack_2d", ["image_identifier", "j", "i"]),
    "unitless_nm_nm_nm": ("stack_3d", ["image_identifier", "k", "j", "i"]),
}


MAG = "magnitude"
NION_DYNAMIC_ABERRATION_TO_NX_EM: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/EVENT_DATA_EM_SET[event_data_em_set]/EVENT_DATA_EM[event_data_em*]/em_lab/ebeam_column/corrector_cs/PROCESS[zemlin_tableau1]/PROCESS[process]/ABERRATION_MODEL[aberration_model]",
    "prefix_src": "metadata/scan/scan_device_properties/ImageScanned:",
    "use": [("model", "nion")],
    "map_to_f8": [
        (f"c_1_0/{MAG}", "C10"),
        (f"c_1_2_a/{MAG}", "C12.a"),
        (f"c_1_2_b/{MAG}", "C12.b"),
        (f"c_2_1_a/{MAG}", "C21.a"),
        (f"c_2_1_b/{MAG}", "C21.b"),
        (f"c_2_3_a/{MAG}", "C23.a"),
        (f"c_2_3_b/{MAG}", "C23.b"),
        (f"c_3_0/{MAG}", "C30"),
        (f"c_3_2_a/{MAG}", "C32.a"),
        (f"c_3_2_b/{MAG}", "C32.b"),
        (f"c_3_4_a/{MAG}", "C34.a"),
        (f"c_3_4_a/{MAG}", "C34.b"),
        (f"c_5_0/{MAG}", "C50"),
    ],
}


# TODO::check units currently using alibi units!
NION_DYNAMIC_VARIOUS_TO_NX_EM: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/EVENT_DATA_EM_SET[event_data_em_set]/EVENT_DATA_EM[event_data_em*]/em_lab",
    "prefix_src": "metadata/scan/scan_device_properties/ImageScanned:",
    "map_to_f8": [
        ("ebeam_column/electron_source/voltage", "EHT"),
        (
            "ebeam_column/BEAM[beam]/diameter",
            "GeometricProbeSize",
        ),  # diameter? radius ?
        (
            "OPTICAL_SETUP_EM[optical_setup]/semi_convergence_angle",
            ureg.radian,
            "probe_ha",
            ureg.radian,
        ),
        (
            "OPTICAL_SETUP_EM[optical_setup]/probe_current",
            ureg.picoampere,
            "SuperFEG.^EmissionCurrent",
            ureg.ampere,
        ),
        # ("OPTICAL_SETUP_EM[optical_setup]/field_of_view", ureg.meter, "fov_nm", ureg.nanometer),
        # G_2Db, HAADF_Inner_ha, HAADF_Outer_ha, LastTuneCurrent, PMT2_gain, PMTBF_gain,PMTDF_gain
    ],
}


NION_DYNAMIC_STAGE_TO_NX_EM: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/EVENT_DATA_EM_SET[event_data_em_set]/EVENT_DATA_EM[event_data_em*]/em_lab/STAGE_LAB[stage]",
    "prefix_src": "metadata/scan/scan_device_properties/ImageScanned:",
    "map_to_f8": [
        ("tilt1", ureg.radian, "StageOutA", ureg.radian),
        ("tilt2", ureg.radian, "StageOutB", ureg.radian),
    ],
    "map_to_f8": [
        (
            "position",
            ureg.picometer,
            ["StageOutX", "StageOutY", "StageOutZ"],
            ureg.meter,
        ),
    ],
}


NION_DYNAMIC_LENS_TO_NX_EM: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/EVENT_DATA_EM_SET[event_data_em_set]/EVENT_DATA_EM[event_data_em*]/em_lab/ebeam_column",
    "prefix_src": "metadata/scan/scan_device_properties/ImageScanned:",
    "use": [
        ("LENS_EM[lens1]/name", "C1"),
        ("LENS_EM[lens2]/name", "C2"),
        ("LENS_EM[lens3]/name", "C3"),
    ],
    "map_to_f8": [
        ("LENS_EM[lens1]/value", "C1 ConstW"),
        ("LENS_EM[lens2]/value", "C2 ConstW"),
        ("LENS_EM[lens3]/value", "C3 ConstW"),
    ],
}


NION_DYNAMIC_SCAN_TO_NX_EM: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/EVENT_DATA_EM_SET[event_data_em_set]/EVENT_DATA_EM[event_data_em*]/em_lab/scan_controller",
    "prefix_src": "metadata/scan/scan_device_properties",
    "map_to_str": [
        "ac_line_sync",
        "calibration_style",
        ("scan_schema", "channel_modifier"),
        # TODO::exemplar mapping of subscan metadata
    ],
    "map_to_bool": ["ac_frame_sync"],
    "map_to_f8": [
        ("center", ureg.meter, ["center_x_nm", "center_y_nm"], ureg.nanometer),
        ("flyback_time", ureg.second, "flyback_time_us", ureg.microsecond),
        ("line_time", ureg.second, "line_time_us", ureg.microsecond),
        (
            "dwell_time",
            ureg.second,
            "pixel_time_us",
            ureg.microsecond,
        ),  # requested_pixel_time_us
        ("rotation", ureg.radian, "rotation_rad", ureg.radian),
    ],
}
# TODO metadata/scan/scan_device_parameters/ the following remain unmapped
# center_nm, data_shape_override, external_clock_mode, external_clock_wait_time_ms,
# external_scan_mode, external_scan_ratio, pixel_size, scan_id, section_rect,
# size, state_override, subscan_fractional_center, subscan_fractional_size,
# subscan_pixel_size, subscan_rotation, subscan_type_partial, top_left_override


C0 = "CIRCUIT[magboard0]"
C1 = "CIRCUIT[magboard1]"
NION_DYNAMIC_MAGBOARDS_TO_NX_EM: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/EVENT_DATA_EM_SET[event_data_em_set]/EVENT_DATA_EM[event_data_em*]/em_lab/scan_controller",
    "prefix_src": "metadata/scan/scan_device_properties/mag_boards/",
    "map_to_f8": [
        (f"{C0}/dac0", "MagBoard 0 DAC 0"),
        (f"{C0}/dac1", "MagBoard 0 DAC 1"),
        (f"{C0}/dac2", "MagBoard 0 DAC 2"),
        (f"{C0}/dac3", "MagBoard 0 DAC 3"),
        (f"{C0}/dac4", "MagBoard 0 DAC 4"),
        (f"{C0}/dac5", "MagBoard 0 DAC 5"),
        (f"{C0}/dac6", "MagBoard 0 DAC 6"),
        (f"{C0}/dac7", "MagBoard 0 DAC 7"),
        (f"{C0}/dac8", "MagBoard 0 DAC 8"),
        (f"{C0}/dac9", "MagBoard 0 DAC 9"),
        (f"{C0}/dac10", "MagBoard 0 DAC 10"),
        (f"{C0}/dac11", "MagBoard 0 DAC 11"),
        (f"{C0}/relay", "MagBoard 0 Relay"),
        (f"{C1}/dac0", "MagBoard 1 DAC 0"),
        (f"{C1}/dac1", "MagBoard 1 DAC 1"),
        (f"{C1}/dac2", "MagBoard 1 DAC 2"),
        (f"{C1}/dac3", "MagBoard 1 DAC 3"),
        (f"{C1}/dac4", "MagBoard 1 DAC 4"),
        (f"{C1}/dac5", "MagBoard 1 DAC 5"),
        (f"{C1}/dac6", "MagBoard 1 DAC 6"),
        (f"{C1}/dac7", "MagBoard 1 DAC 7"),
        (f"{C1}/dac8", "MagBoard 1 DAC 8"),
        (f"{C1}/dac9", "MagBoard 1 DAC 9"),
        (f"{C1}/dac10", "MagBoard 1 DAC 10"),
        (f"{C1}/dac11", "MagBoard 1 DAC 11"),
        (f"{C1}/relay", "MagBoard 1 Relay"),
    ],
}


NION_STATIC_DETECTOR_TO_NX_EM: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/em_lab/DETECTOR[detector*]",
    "prefix_src": "metadata/hardware_source/detector_configuration/",
    "map_to_str": [
        ("FABRICATION[fabrication]/model", "description"),
        ("FABRICATION[fabrication]/identifier", "detector_number"),
        "eiger_fw_version",
        "sensor_material",
        "software_version",
    ],
    "map_to_u4": [
        ("x_pixel", "x_pixels_in_detector"),
        ("x_pixel", "x_pixels_in_detector"),
    ],
    "map_to_f8": [
        ("x_pixel_size", ureg.meter, "x_pixel_size", ureg.meter),
        ("y_pixel_size", ureg.meter, "y_pixel_size", ureg.meter),
        ("sensor_thickness", ureg.meter, "sensor_thickness", ureg.meter),
    ],
}

NION_DYNAMIC_DETECTOR_TO_NX_EM: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/em_lab/DETECTOR[detector*]",
    "prefix_src": "metadata/hardware_source/detector_configuration/",
    "map_to_bool": [
        "countrate_correction_applied",
        "pixel_mask_applied",
        (
            "flatfield_applied",
            "flatfield_correction_applied",
        ),  # example for concept_name mismatch Dectris and NeXus
    ],
    "map_to_i1": ["bit_depth_readout", "bit_depth_image"],
    "map_to_f8": [
        "beam_center_x",
        "beam_center_y",
        ("detector_readout_time", ureg.second, "detector_readout_time", ureg.second),
        ("frame_time", ureg.second, "frame_time", ureg.second),
        ("count_time", ureg.second, "count_time", ureg.second),
        ("threshold_energy", ureg.eV, "threshold_energy", ureg.eV),
    ],
}


NION_PINPOINT_EVENT_TIME = {
    "prefix_trg": "/ENTRY[entry*]/measurement/EVENT_DATA_EM_SET[event_data_em_set]/EVENT_DATA_EM[event_data_em*]",
    "prefix_src": "metadata/hardware_source/detector_configuration/",
    "map": [("start_time", "data_collection_date")],
    # this could be a poor assumption as we do not know when during the acquisition
    # this timestamp is taken
}

# the following concepts from metadata/hardware_source/detector_configuration
# have no representative in NeXus for now, TODO add them as undocumented ?
# auto_summation, chi_increment, chi_start, compression, countrate_correction_count_cutoff,
# detector_translation, element, frame_count_time, frame_period, kappa_increment,
# kappa_start, nimages, ntrigger, number_of_excluded_pixels, omega_increment,
# omega_start, phi_increment, phi_start, photon_energy, roi_mode, trigger_mode,
# two_theta_increment, two_theta_start, virtual_pixel_correction_applied, wavelength
