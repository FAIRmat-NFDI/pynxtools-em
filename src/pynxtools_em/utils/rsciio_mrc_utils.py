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
"""Utility functions to interpret data from rosettasciio mrc file reader."""

from pynxtools_em.utils.custom_logging import logger
from pynxtools_em.utils.pint_custom_unit_registry import ureg


def get_dimension_analysis_keyword(hspy_axes_list: list[dict]) -> str:
    """Concatenate the dimensions of a hyperspy axes object to a keyword."""
    units: list[str] = []
    for dictionary in hspy_axes_list:
        if "units" in dictionary:
            if dictionary["units"] is None:
                units.append("dimensionless")
            else:
                units.append(f"{ureg(dictionary['units']).to_base_units().units}")
        else:
            logger.warning("get_dimension_analysis_keyword got malformed input")
            return ""
    return ";".join(units)
