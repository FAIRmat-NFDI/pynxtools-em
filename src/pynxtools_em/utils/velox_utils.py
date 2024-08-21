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
"""Utility function for working with mapping of Velox content."""

import pint
from pynxtools_em.utils.pint_custom_unit_registry import ureg

RSCIIO_AXES_MIN = ["name", "navigate", "offset", "scale", "size", "units"]
RSCIIO_AXES_MAX = ["index_in_array"] + RSCIIO_AXES_MIN


def velox_image_spectrum_or_generic_nxdata(list_of_dict) -> str:
    """Encode sequence of units to tell whether NXimage_set, NXspectrum_set, NXdata."""
    if len(list_of_dict) >= 1:
        token = []
        for obj in list_of_dict:
            if isinstance(obj, dict):
                sorted_keys = sorted(obj.keys())
                if sorted_keys == RSCIIO_AXES_MIN or sorted_keys == RSCIIO_AXES_MAX:
                    if obj["units"] == "":
                        token.append("unitless")
                    else:
                        token.append(obj["units"])
                else:
                    raise ValueError(
                        f"{obj.keys()} are not exactly the expected keywords!"
                    )
            else:
                raise ValueError(f"{obj} is not a dict!")
        if len(token) >= 1:
            print("_".join(token))
            unit_categories = []
            for unit in token:
                if unit != "unitless":
                    try:
                        q = ureg.Quantity(unit)
                        base_unit = q.to_base_units().units
                        if base_unit == "1/meter":
                            unit_categories.append("1/m")
                        elif base_unit == "meter":
                            unit_categories.append("m")
                        elif base_unit == "kilogram * meter ** 2 / second ** 2":
                            unit_categories.append("eV")
                        elif base_unit == "second":
                            unit_categories.append("s")
                        else:
                            raise ValueError(
                                f"Hitting an undefined case for base_unit {base_unit} !"
                            )
                    except pint.UndefinedUnitError:
                        return ""
                else:
                    unit_categories.append(unit)
            return "_".join(unit_categories)
    return ""
