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
"""Utility function for working with mapping of Gatan DigitalMicrograph content."""

from pint import UndefinedUnitError
from pynxtools_em.utils.pint_custom_unit_registry import ureg


def gatan_image_spectrum_or_generic_nxdata(list_of_dict) -> str:
    """Encode sequence of units to tell whether NXimage_set, NXspectrum_set, NXdata."""
    if len(list_of_dict) >= 1:
        token = []
        for obj in list_of_dict:
            if isinstance(obj, dict):
                if list(obj.keys()) == [
                    "name",
                    "size",
                    "index_in_array",
                    "scale",
                    "offset",
                    "units",
                    "navigate",
                ]:
                    if obj["units"] == "":
                        token.append("unitless")
                    else:
                        token.append(obj["units"])
                else:
                    print(f"{obj.keys()} are not exactly the expected keywords!")
            else:
                print(f"{obj} is not a dict!")
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
                        else:
                            print(
                                f"Hitting an undefined case for base_unit {base_unit} !"
                            )
                    except UndefinedUnitError:
                        return ""
                else:
                    unit_categories.append(unit)
            return "_".join(unit_categories)
    return ""
