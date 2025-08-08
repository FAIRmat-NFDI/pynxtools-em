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
"""A customized unit registry for handling units with pint."""

import numpy as np
import pint

try:
    from pynxtools.units import ureg
except ImportError as exc:
    from pint import UnitRegistry

    ureg = UnitRegistry()

# ureg.formatter.default_format = "D"
# https://pint.readthedocs.io/en/stable/user/formatting.html

# customizations for Zeiss
ureg.define("Hours = 1 * h")
ureg.define("Secs = 1 * s")
ureg.define("Volt = 1 * V")
ureg.define("um2 = 1 * micrometer * micrometer")

# customizations for NeXus
ureg.define("nx_unitless = 1")
ureg.define("nx_dimensionless = 1")
ureg.define("nx_any = 1")

ureg.define("dose_rate = 1 / angstrom ** 2 / second")

NX_UNITLESS = ureg.Quantity(1, ureg.nx_unitless)
NX_DIMENSIONLESS = ureg.Quantity(1, ureg.nx_dimensionless)
NX_ANY = ureg.Quantity(1, ureg.nx_any)


def is_not_special_unit(qnt: pint.Quantity) -> bool:
    """True if not a special NeXus unit category."""
    for special_units in [NX_UNITLESS.units, NX_DIMENSIONLESS.units, NX_ANY.units]:
        if qnt.units == special_units:
            return False
    return True


PINT_MAPPING_TESTS = {
    "use": [
        ("str_str_01", ""),
        ("str_str_02", "one"),
        ("str_qnt_01", NX_UNITLESS),
        ("str_qnt_02", NX_DIMENSIONLESS),
        ("str_qnt_03", NX_ANY),
        ("str_qnt_04", ureg.Quantity(1, ureg.meter)),
        ("str_qnt_05", ureg.Quantity(1, ureg.nx_unitless)),
        ("str_qnt_06", ureg.Quantity(1, ureg.nx_dimensionless)),
        ("str_qnt_07", ureg.Quantity(1, ureg.nx_any)),
        ("str_qnt_08", ureg.Quantity(np.uint32(1), ureg.meter)),
        ("str_qnt_09", ureg.Quantity(np.uint32(1), ureg.nx_unitless)),
        ("str_qnt_10", ureg.Quantity(np.uint32(1), ureg.nx_dimensionless)),
        ("str_qnt_11", ureg.Quantity(np.uint32(1), ureg.nx_any)),
        ("str_qnt_12", ureg.Quantity(np.asarray([1, 2, 3], np.uint32), ureg.meter)),
    ],
    "map": [],
}
