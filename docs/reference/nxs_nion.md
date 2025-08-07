# Nion Co. projects with NDATA and HDF5 files

The pynxtools-em parser and normalizer reads the following content and maps them on respective NeXus concepts that are defined in the NXem application definition:

| Concept | NeXus/HDF5 |
| --------------- | --------------  |
| metadata/hardware_source/EHT | :heavy_check_mark: |
| metadata/hardware_source/GeometricProbeSize | :heavy_check_mark: |
| metadata/hardware_source/ImageRonchigram/C1 ConstW | :heavy_check_mark: |
| metadata/hardware_source/ImageRonchigram/C10 | :heavy_check_mark: |
| metadata/hardware_source/ImageRonchigram/C12.a | :heavy_check_mark: |
| metadata/hardware_source/ImageRonchigram/C12.b | :heavy_check_mark: |
| metadata/hardware_source/ImageRonchigram/C2 ConstW | :heavy_check_mark: |
| metadata/hardware_source/ImageRonchigram/C21.a | :heavy_check_mark: |
| metadata/hardware_source/ImageRonchigram/C21.b | :heavy_check_mark: |
| metadata/hardware_source/ImageRonchigram/C23.a | :heavy_check_mark: |
| metadata/hardware_source/ImageRonchigram/C23.b | :heavy_check_mark: |
| metadata/hardware_source/ImageRonchigram/C3 ConstW | :heavy_check_mark: |
| metadata/hardware_source/ImageRonchigram/C30 | :heavy_check_mark: |
| metadata/hardware_source/ImageRonchigram/C32.a | :heavy_check_mark: |
| metadata/hardware_source/ImageRonchigram/C32.b | :heavy_check_mark: |
| metadata/hardware_source/ImageRonchigram/C34.a | :heavy_check_mark: |
| metadata/hardware_source/ImageRonchigram/C34.b | :heavy_check_mark: |
| metadata/hardware_source/ImageRonchigram/C50 | :heavy_check_mark: |
| metadata/hardware_source/ImageRonchigram/EHT | :heavy_check_mark: |
| metadata/hardware_source/ImageRonchigram/GeometricProbeSize | :heavy_check_mark: |
| metadata/hardware_source/ImageRonchigram/MajorOL | :heavy_check_mark: |
| metadata/hardware_source/ImageRonchigram/StageOutA | :heavy_check_mark: |
| metadata/hardware_source/ImageRonchigram/StageOutB | :heavy_check_mark: |
| metadata/hardware_source/ImageRonchigram/StageOutX | :heavy_check_mark: |
| metadata/hardware_source/ImageRonchigram/StageOutY | :heavy_check_mark: |
| metadata/hardware_source/ImageRonchigram/StageOutZ | :heavy_check_mark: |
| metadata/hardware_source/ImageRonchigram/SuperFEG.^EmissionCurrent | :heavy_check_mark: |
| metadata/hardware_source/ImageRonchigram/fov_nm | :heavy_check_mark: |
| metadata/hardware_source/ImageRonchigram/probe_ha | :heavy_check_mark: |
| metadata/hardware_source/ImageRonchigram/rotation_rad | :heavy_check_mark: |
| metadata/hardware_source/SuperFEG.^EmissionCurrent | :heavy_check_mark: |
| metadata/hardware_source/ac_frame_sync | :heavy_check_mark: |
| metadata/hardware_source/ac_line_sync | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageRonchigram/C1 ConstW | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageRonchigram/C2 ConstW | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageRonchigram/C3 ConstW | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageRonchigram/EHT | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageRonchigram/GeometricProbeSize | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageRonchigram/MajorOL | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageRonchigram/StageOutA | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageRonchigram/StageOutB | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageRonchigram/StageOutX | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageRonchigram/StageOutY | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageRonchigram/StageOutZ | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageRonchigram/SuperFEG.^EmissionCurrent | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageRonchigram/fov_nm | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageRonchigram/probe_ha | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageRonchigram/rotation_rad | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageScanned/C1 ConstW | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageScanned/C10 | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageScanned/C12.a | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageScanned/C12.b | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageScanned/C2 ConstW | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageScanned/C21.a | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageScanned/C21.b | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageScanned/C23.a | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageScanned/C23.b | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageScanned/C3 ConstW | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageScanned/C30 | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageScanned/C32.a | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageScanned/C32.b | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageScanned/C34.a | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageScanned/C34.b | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageScanned/C50 | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageScanned/EHT | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageScanned/GeometricProbeSize | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageScanned/MajorOL | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageScanned/StageOutA | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageScanned/StageOutB | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageScanned/StageOutX | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageScanned/StageOutY | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageScanned/StageOutZ | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageScanned/SuperFEG.^EmissionCurrent | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageScanned/fov_nm | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageScanned/probe_ha | :heavy_check_mark: |
| metadata/hardware_source/autostem/ImageScanned/rotation_rad | :heavy_check_mark: |
| metadata/hardware_source/calibration_style | :heavy_check_mark: |
| metadata/hardware_source/center_x_nm | :heavy_check_mark: |
| metadata/hardware_source/center_y_nm | :heavy_check_mark: |
| metadata/hardware_source/channel_modifier | :heavy_check_mark: |
| metadata/hardware_source/detector_configuration/beam_center_x | :heavy_check_mark: |
| metadata/hardware_source/detector_configuration/beam_center_y | :heavy_check_mark: |
| metadata/hardware_source/detector_configuration/bit_depth_image | :heavy_check_mark: |
| metadata/hardware_source/detector_configuration/bit_depth_readout | :heavy_check_mark: |
| metadata/hardware_source/detector_configuration/count_time | :heavy_check_mark: |
| metadata/hardware_source/detector_configuration/countrate_correction_applied | :heavy_check_mark: |
| metadata/hardware_source/detector_configuration/data_collection_date | :heavy_check_mark: |
| metadata/hardware_source/detector_configuration/description | :heavy_check_mark: |
| metadata/hardware_source/detector_configuration/detector_number | :heavy_check_mark: |
| metadata/hardware_source/detector_configuration/detector_readout_time | :heavy_check_mark: |
| metadata/hardware_source/detector_configuration/eiger_fw_version | :heavy_check_mark: |
| metadata/hardware_source/detector_configuration/flatfield_correction_applied | :heavy_check_mark: |
| metadata/hardware_source/detector_configuration/frame_time | :heavy_check_mark: |
| metadata/hardware_source/detector_configuration/pixel_mask_applied | :heavy_check_mark: |
| metadata/hardware_source/detector_configuration/sensor_material | :heavy_check_mark: |
| metadata/hardware_source/detector_configuration/sensor_thickness | :heavy_check_mark: |
| metadata/hardware_source/detector_configuration/software_version | :heavy_check_mark: |
| metadata/hardware_source/detector_configuration/threshold_energy | :heavy_check_mark: |
| metadata/hardware_source/detector_configuration/x_pixel_size | :heavy_check_mark: |
| metadata/hardware_source/detector_configuration/x_pixels_in_detector | :heavy_check_mark: |
| metadata/hardware_source/detector_configuration/y_pixel_size | :heavy_check_mark: |
| metadata/hardware_source/detector_configuration/y_pixels_in_detector | :heavy_check_mark: |
| metadata/hardware_source/external_clock_mode | :heavy_check_mark: |
| metadata/hardware_source/external_clock_wait_time_ms | :heavy_check_mark: |
| metadata/hardware_source/flyback_time_us | :heavy_check_mark: |
| metadata/hardware_source/fov_nm | :heavy_check_mark: |
| metadata/hardware_source/line_time_us | :heavy_check_mark: |
| metadata/hardware_source/pixel_time_us | :heavy_check_mark: |
| metadata/hardware_source/probe_ha | :heavy_check_mark: |
| metadata/hardware_source/rotation_rad | :heavy_check_mark: |
| metadata/instrument/ImageRonchigram/C1 ConstW | :heavy_check_mark: |
| metadata/instrument/ImageRonchigram/C10 | :heavy_check_mark: |
| metadata/instrument/ImageRonchigram/C12.a | :heavy_check_mark: |
| metadata/instrument/ImageRonchigram/C12.b | :heavy_check_mark: |
| metadata/instrument/ImageRonchigram/C2 ConstW | :heavy_check_mark: |
| metadata/instrument/ImageRonchigram/C21.a | :heavy_check_mark: |
| metadata/instrument/ImageRonchigram/C21.b | :heavy_check_mark: |
| metadata/instrument/ImageRonchigram/C23.a | :heavy_check_mark: |
| metadata/instrument/ImageRonchigram/C23.b | :heavy_check_mark: |
| metadata/instrument/ImageRonchigram/C3 ConstW | :heavy_check_mark: |
| metadata/instrument/ImageRonchigram/C30 | :heavy_check_mark: |
| metadata/instrument/ImageRonchigram/C32.a | :heavy_check_mark: |
| metadata/instrument/ImageRonchigram/C32.b | :heavy_check_mark: |
| metadata/instrument/ImageRonchigram/C34.a | :heavy_check_mark: |
| metadata/instrument/ImageRonchigram/C34.b | :heavy_check_mark: |
| metadata/instrument/ImageRonchigram/C50 | :heavy_check_mark: |
| metadata/instrument/ImageRonchigram/EHT | :heavy_check_mark: |
| metadata/instrument/ImageRonchigram/GeometricProbeSize | :heavy_check_mark: |
| metadata/instrument/ImageRonchigram/MajorOL | :heavy_check_mark: |
| metadata/instrument/ImageRonchigram/StageOutA | :heavy_check_mark: |
| metadata/instrument/ImageRonchigram/StageOutB | :heavy_check_mark: |
| metadata/instrument/ImageRonchigram/StageOutX | :heavy_check_mark: |
| metadata/instrument/ImageRonchigram/StageOutY | :heavy_check_mark: |
| metadata/instrument/ImageRonchigram/StageOutZ | :heavy_check_mark: |
| metadata/instrument/ImageRonchigram/SuperFEG.^EmissionCurrent | :heavy_check_mark: |
| metadata/instrument/ImageRonchigram/fov_nm | :heavy_check_mark: |
| metadata/instrument/ImageRonchigram/probe_ha | :heavy_check_mark: |
| metadata/instrument/ImageRonchigram/rotation_rad | :heavy_check_mark: |
| metadata/instrument/ImageScanned/C1 ConstW | :heavy_check_mark: |
| metadata/instrument/ImageScanned/C10 | :heavy_check_mark: |
| metadata/instrument/ImageScanned/C12.a | :heavy_check_mark: |
| metadata/instrument/ImageScanned/C12.b | :heavy_check_mark: |
| metadata/instrument/ImageScanned/C2 ConstW | :heavy_check_mark: |
| metadata/instrument/ImageScanned/C21.a | :heavy_check_mark: |
| metadata/instrument/ImageScanned/C21.b | :heavy_check_mark: |
| metadata/instrument/ImageScanned/C23.a | :heavy_check_mark: |
| metadata/instrument/ImageScanned/C23.b | :heavy_check_mark: |
| metadata/instrument/ImageScanned/C3 ConstW | :heavy_check_mark: |
| metadata/instrument/ImageScanned/C30 | :heavy_check_mark: |
| metadata/instrument/ImageScanned/C32.a | :heavy_check_mark: |
| metadata/instrument/ImageScanned/C32.b | :heavy_check_mark: |
| metadata/instrument/ImageScanned/C34.a | :heavy_check_mark: |
| metadata/instrument/ImageScanned/C34.b | :heavy_check_mark: |
| metadata/instrument/ImageScanned/C50 | :heavy_check_mark: |
| metadata/instrument/ImageScanned/EHT | :heavy_check_mark: |
| metadata/instrument/ImageScanned/GeometricProbeSize | :heavy_check_mark: |
| metadata/instrument/ImageScanned/MajorOL | :heavy_check_mark: |
| metadata/instrument/ImageScanned/StageOutA | :heavy_check_mark: |
| metadata/instrument/ImageScanned/StageOutB | :heavy_check_mark: |
| metadata/instrument/ImageScanned/StageOutX | :heavy_check_mark: |
| metadata/instrument/ImageScanned/StageOutY | :heavy_check_mark: |
| metadata/instrument/ImageScanned/StageOutZ | :heavy_check_mark: |
| metadata/instrument/ImageScanned/SuperFEG.^EmissionCurrent | :heavy_check_mark: |
| metadata/instrument/ImageScanned/fov_nm | :heavy_check_mark: |
| metadata/instrument/ImageScanned/probe_ha | :heavy_check_mark: |
| metadata/instrument/ImageScanned/rotation_rad | :heavy_check_mark: |
| metadata/instrument/autostem/ImageRonchigram/C1 ConstW | :heavy_check_mark: |
| metadata/instrument/autostem/ImageRonchigram/C2 ConstW | :heavy_check_mark: |
| metadata/instrument/autostem/ImageRonchigram/C3 ConstW | :heavy_check_mark: |
| metadata/instrument/autostem/ImageRonchigram/EHT | :heavy_check_mark: |
| metadata/instrument/autostem/ImageRonchigram/GeometricProbeSize | :heavy_check_mark: |
| metadata/instrument/autostem/ImageRonchigram/MajorOL | :heavy_check_mark: |
| metadata/instrument/autostem/ImageRonchigram/StageOutA | :heavy_check_mark: |
| metadata/instrument/autostem/ImageRonchigram/StageOutB | :heavy_check_mark: |
| metadata/instrument/autostem/ImageRonchigram/StageOutX | :heavy_check_mark: |
| metadata/instrument/autostem/ImageRonchigram/StageOutY | :heavy_check_mark: |
| metadata/instrument/autostem/ImageRonchigram/StageOutZ | :heavy_check_mark: |
| metadata/instrument/autostem/ImageRonchigram/SuperFEG.^EmissionCurrent | :heavy_check_mark: |
| metadata/instrument/autostem/ImageRonchigram/fov_nm | :heavy_check_mark: |
| metadata/instrument/autostem/ImageRonchigram/probe_ha | :heavy_check_mark: |
| metadata/instrument/autostem/ImageRonchigram/rotation_rad | :heavy_check_mark: |
| metadata/instrument/autostem/ImageScanned/C10 | :heavy_check_mark: |
| metadata/instrument/autostem/ImageScanned/C12.a | :heavy_check_mark: |
| metadata/instrument/autostem/ImageScanned/C12.b | :heavy_check_mark: |
| metadata/instrument/autostem/ImageScanned/C21.a | :heavy_check_mark: |
| metadata/instrument/autostem/ImageScanned/C21.b | :heavy_check_mark: |
| metadata/instrument/autostem/ImageScanned/C23.a | :heavy_check_mark: |
| metadata/instrument/autostem/ImageScanned/C23.b | :heavy_check_mark: |
| metadata/instrument/autostem/ImageScanned/C30 | :heavy_check_mark: |
| metadata/instrument/autostem/ImageScanned/C32.a | :heavy_check_mark: |
| metadata/instrument/autostem/ImageScanned/C32.b | :heavy_check_mark: |
| metadata/instrument/autostem/ImageScanned/C34.a | :heavy_check_mark: |
| metadata/instrument/autostem/ImageScanned/C34.b | :heavy_check_mark: |
| metadata/instrument/autostem/ImageScanned/C50 | :heavy_check_mark: |
| metadata/instrument/autostem/ImageScanned/EHT | :heavy_check_mark: |
| metadata/instrument/autostem/ImageScanned/GeometricProbeSize | :heavy_check_mark: |
| metadata/instrument/autostem/ImageScanned/StageOutA | :heavy_check_mark: |
| metadata/instrument/autostem/ImageScanned/StageOutB | :heavy_check_mark: |
| metadata/instrument/autostem/ImageScanned/StageOutX | :heavy_check_mark: |
| metadata/instrument/autostem/ImageScanned/StageOutY | :heavy_check_mark: |
| metadata/instrument/autostem/ImageScanned/StageOutZ | :heavy_check_mark: |
| metadata/instrument/autostem/ImageScanned/SuperFEG.^EmissionCurrent | :heavy_check_mark: |
| metadata/instrument/autostem/ImageScanned/fov_nm | :heavy_check_mark: |
| metadata/instrument/autostem/ImageScanned/probe_ha | :heavy_check_mark: |
| metadata/instrument/autostem/ImageScanned/rotation_rad | :heavy_check_mark: |
| metadata/scan/scan_device_parameters/EHT | :heavy_check_mark: |
| metadata/scan/scan_device_parameters/GeometricProbeSize | :heavy_check_mark: |
| metadata/scan/scan_device_parameters/SuperFEG.^EmissionCurrent | :heavy_check_mark: |
| metadata/scan/scan_device_parameters/ac_frame_sync | :heavy_check_mark: |
| metadata/scan/scan_device_parameters/ac_line_sync | :heavy_check_mark: |
| metadata/scan/scan_device_parameters/calibration_style | :heavy_check_mark: |
| metadata/scan/scan_device_parameters/center_x_nm | :heavy_check_mark: |
| metadata/scan/scan_device_parameters/center_y_nm | :heavy_check_mark: |
| metadata/scan/scan_device_parameters/channel_modifier | :heavy_check_mark: |
| metadata/scan/scan_device_parameters/external_clock_mode | :heavy_check_mark: |
| metadata/scan/scan_device_parameters/external_clock_wait_time_ms | :heavy_check_mark: |
| metadata/scan/scan_device_parameters/flyback_time_us | :heavy_check_mark: |
| metadata/scan/scan_device_parameters/fov_nm | :heavy_check_mark: |
| metadata/scan/scan_device_parameters/line_time_us | :heavy_check_mark: |
| metadata/scan/scan_device_parameters/pixel_time_us | :heavy_check_mark: |
| metadata/scan/scan_device_parameters/probe_ha | :heavy_check_mark: |
| metadata/scan/scan_device_parameters/rotation_rad | :heavy_check_mark: |
| metadata/scan/scan_device_properties/EHT | :heavy_check_mark: |
| metadata/scan/scan_device_properties/GeometricProbeSize | :heavy_check_mark: |
| metadata/scan/scan_device_properties/ImageScanned:C1 ConstW | :heavy_check_mark: |
| metadata/scan/scan_device_properties/ImageScanned:C10 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/ImageScanned:C12.a | :heavy_check_mark: |
| metadata/scan/scan_device_properties/ImageScanned:C12.b | :heavy_check_mark: |
| metadata/scan/scan_device_properties/ImageScanned:C2 ConstW | :heavy_check_mark: |
| metadata/scan/scan_device_properties/ImageScanned:C21.a | :heavy_check_mark: |
| metadata/scan/scan_device_properties/ImageScanned:C21.b | :heavy_check_mark: |
| metadata/scan/scan_device_properties/ImageScanned:C23.a | :heavy_check_mark: |
| metadata/scan/scan_device_properties/ImageScanned:C23.b | :heavy_check_mark: |
| metadata/scan/scan_device_properties/ImageScanned:C3 ConstW | :heavy_check_mark: |
| metadata/scan/scan_device_properties/ImageScanned:C30 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/ImageScanned:C32.a | :heavy_check_mark: |
| metadata/scan/scan_device_properties/ImageScanned:C32.b | :heavy_check_mark: |
| metadata/scan/scan_device_properties/ImageScanned:C34.a | :heavy_check_mark: |
| metadata/scan/scan_device_properties/ImageScanned:C34.b | :heavy_check_mark: |
| metadata/scan/scan_device_properties/ImageScanned:C50 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/ImageScanned:EHT | :heavy_check_mark: |
| metadata/scan/scan_device_properties/ImageScanned:GeometricProbeSize | :heavy_check_mark: |
| metadata/scan/scan_device_properties/ImageScanned:MajorOL | :heavy_check_mark: |
| metadata/scan/scan_device_properties/ImageScanned:StageOutA | :heavy_check_mark: |
| metadata/scan/scan_device_properties/ImageScanned:StageOutB | :heavy_check_mark: |
| metadata/scan/scan_device_properties/ImageScanned:StageOutX | :heavy_check_mark: |
| metadata/scan/scan_device_properties/ImageScanned:StageOutY | :heavy_check_mark: |
| metadata/scan/scan_device_properties/ImageScanned:StageOutZ | :heavy_check_mark: |
| metadata/scan/scan_device_properties/ImageScanned:SuperFEG.^EmissionCurrent | :heavy_check_mark: |
| metadata/scan/scan_device_properties/ImageScanned:fov_nm | :heavy_check_mark: |
| metadata/scan/scan_device_properties/ImageScanned:probe_ha | :heavy_check_mark: |
| metadata/scan/scan_device_properties/ImageScanned:rotation_rad | :heavy_check_mark: |
| metadata/scan/scan_device_properties/MagBoard 0 DAC 0 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/MagBoard 0 DAC 1 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/MagBoard 0 DAC 10 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/MagBoard 0 DAC 11 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/MagBoard 0 DAC 2 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/MagBoard 0 DAC 3 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/MagBoard 0 DAC 4 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/MagBoard 0 DAC 5 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/MagBoard 0 DAC 6 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/MagBoard 0 DAC 7 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/MagBoard 0 DAC 8 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/MagBoard 0 DAC 9 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/MagBoard 0 Relay | :heavy_check_mark: |
| metadata/scan/scan_device_properties/MagBoard 1 DAC 0 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/MagBoard 1 DAC 1 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/MagBoard 1 DAC 10 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/MagBoard 1 DAC 11 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/MagBoard 1 DAC 2 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/MagBoard 1 DAC 3 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/MagBoard 1 DAC 4 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/MagBoard 1 DAC 5 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/MagBoard 1 DAC 6 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/MagBoard 1 DAC 7 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/MagBoard 1 DAC 8 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/MagBoard 1 DAC 9 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/MagBoard 1 Relay | :heavy_check_mark: |
| metadata/scan/scan_device_properties/SuperFEG.^EmissionCurrent | :heavy_check_mark: |
| metadata/scan/scan_device_properties/ac_frame_sync | :heavy_check_mark: |
| metadata/scan/scan_device_properties/ac_line_sync | :heavy_check_mark: |
| metadata/scan/scan_device_properties/calibration_style | :heavy_check_mark: |
| metadata/scan/scan_device_properties/center_x_nm | :heavy_check_mark: |
| metadata/scan/scan_device_properties/center_y_nm | :heavy_check_mark: |
| metadata/scan/scan_device_properties/channel_modifier | :heavy_check_mark: |
| metadata/scan/scan_device_properties/external_clock_mode | :heavy_check_mark: |
| metadata/scan/scan_device_properties/external_clock_wait_time_ms | :heavy_check_mark: |
| metadata/scan/scan_device_properties/flyback_time_us | :heavy_check_mark: |
| metadata/scan/scan_device_properties/fov_nm | :heavy_check_mark: |
| metadata/scan/scan_device_properties/line_time_us | :heavy_check_mark: |
| metadata/scan/scan_device_properties/mag_boards/MagBoard 0 DAC 0 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/mag_boards/MagBoard 0 DAC 1 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/mag_boards/MagBoard 0 DAC 10 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/mag_boards/MagBoard 0 DAC 11 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/mag_boards/MagBoard 0 DAC 2 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/mag_boards/MagBoard 0 DAC 3 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/mag_boards/MagBoard 0 DAC 4 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/mag_boards/MagBoard 0 DAC 5 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/mag_boards/MagBoard 0 DAC 6 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/mag_boards/MagBoard 0 DAC 7 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/mag_boards/MagBoard 0 DAC 8 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/mag_boards/MagBoard 0 DAC 9 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/mag_boards/MagBoard 0 Relay | :heavy_check_mark: |
| metadata/scan/scan_device_properties/mag_boards/MagBoard 1 DAC 0 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/mag_boards/MagBoard 1 DAC 1 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/mag_boards/MagBoard 1 DAC 10 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/mag_boards/MagBoard 1 DAC 11 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/mag_boards/MagBoard 1 DAC 2 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/mag_boards/MagBoard 1 DAC 3 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/mag_boards/MagBoard 1 DAC 4 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/mag_boards/MagBoard 1 DAC 5 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/mag_boards/MagBoard 1 DAC 6 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/mag_boards/MagBoard 1 DAC 7 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/mag_boards/MagBoard 1 DAC 8 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/mag_boards/MagBoard 1 DAC 9 | :heavy_check_mark: |
| metadata/scan/scan_device_properties/mag_boards/MagBoard 1 Relay | :heavy_check_mark: |
| metadata/scan/scan_device_properties/pixel_time_us | :heavy_check_mark: |
| metadata/scan/scan_device_properties/probe_ha | :heavy_check_mark: |
| metadata/scan/scan_device_properties/rotation_rad | :heavy_check_mark: |
| metadata/scan_detector/autostem/ImageScanned/C1 ConstW | :heavy_check_mark: |
| metadata/scan_detector/autostem/ImageScanned/C10 | :heavy_check_mark: |
| metadata/scan_detector/autostem/ImageScanned/C12.a | :heavy_check_mark: |
| metadata/scan_detector/autostem/ImageScanned/C12.b | :heavy_check_mark: |
| metadata/scan_detector/autostem/ImageScanned/C2 ConstW | :heavy_check_mark: |
| metadata/scan_detector/autostem/ImageScanned/C21.a | :heavy_check_mark: |
| metadata/scan_detector/autostem/ImageScanned/C21.b | :heavy_check_mark: |
| metadata/scan_detector/autostem/ImageScanned/C23.a | :heavy_check_mark: |
| metadata/scan_detector/autostem/ImageScanned/C23.b | :heavy_check_mark: |
| metadata/scan_detector/autostem/ImageScanned/C3 ConstW | :heavy_check_mark: |
| metadata/scan_detector/autostem/ImageScanned/C30 | :heavy_check_mark: |
| metadata/scan_detector/autostem/ImageScanned/C32.a | :heavy_check_mark: |
| metadata/scan_detector/autostem/ImageScanned/C32.b | :heavy_check_mark: |
| metadata/scan_detector/autostem/ImageScanned/C34.a | :heavy_check_mark: |
| metadata/scan_detector/autostem/ImageScanned/C34.b | :heavy_check_mark: |
| metadata/scan_detector/autostem/ImageScanned/C50 | :heavy_check_mark: |
| metadata/scan_detector/autostem/ImageScanned/EHT | :heavy_check_mark: |
| metadata/scan_detector/autostem/ImageScanned/GeometricProbeSize | :heavy_check_mark: |
| metadata/scan_detector/autostem/ImageScanned/MajorOL | :heavy_check_mark: |
| metadata/scan_detector/autostem/ImageScanned/StageOutA | :heavy_check_mark: |
| metadata/scan_detector/autostem/ImageScanned/StageOutB | :heavy_check_mark: |
| metadata/scan_detector/autostem/ImageScanned/StageOutX | :heavy_check_mark: |
| metadata/scan_detector/autostem/ImageScanned/StageOutY | :heavy_check_mark: |
| metadata/scan_detector/autostem/ImageScanned/StageOutZ | :heavy_check_mark: |
| metadata/scan_detector/autostem/ImageScanned/SuperFEG.^EmissionCurrent | :heavy_check_mark: |
| metadata/scan_detector/autostem/ImageScanned/fov_nm | :heavy_check_mark: |
| metadata/scan_detector/autostem/ImageScanned/probe_ha | :heavy_check_mark: |
| metadata/scan_detector/autostem/ImageScanned/rotation_rad | :heavy_check_mark: |
