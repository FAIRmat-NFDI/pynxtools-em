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
"""Configuration of the image_tiff_point_electronic EBIC parser."""

from typing import Any, Dict

from pynxtools_em.utils.pint_custom_unit_registry import ureg

DISS_DYNAMIC_VARIOUS_NX: Dict[str, Any] = {
    "prefix_trg": "/ENTRY[entry*]/measurement/EVENT_DATA_EM[event*]",
    "prefix_src": "",
    "map_to_f8": [
        ("instrument/optics/magnification", "Mag"),
        (
            "instrument/optics/working_distance",
            ureg.meter,
            "WD/value",
            "WD/Unit",
        ),
        (
            "instrument/ebeam_column/electron_source/voltage",
            ureg.volt,
            "HV/value",
            "HV/Unit",
        ),
    ],
}
