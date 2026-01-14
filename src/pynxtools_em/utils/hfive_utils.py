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
"""Utility functions when working with parsing HDF5."""

from itertools import groupby

import numpy as np

from pynxtools_em.utils.pint_custom_unit_registry import ureg

EBSD_MAP_SPACEGROUP = {
    "P 6#sub3mc": 186,
    "P 6/mmm": 191,
    "P 6#sub3/mmc": 194,
    "F #ovl43m": 216,
    "P m#ovl3m": 221,
    "F m#ovl3m": 225,
    "Fd#ovl3m(*)": 227,
    "I m#ovl3m": 229,
}
# see here for typical examples http://img.chem.ucl.ac.uk/sgp/large/186az1.htm

DIRTY_FIX_SPACEGROUP: dict = {}
EULER_SPACE_SYMMETRY = [
    ureg.Quantity(2.0 * np.pi, ureg.radian),
    ureg.Quantity(1.0 * np.pi, ureg.radian),
    ureg.Quantity(2.0 * np.pi, ureg.radian),
]


def apply_euler_space_symmetry(triplet_set):
    """Apply orientation space symmetry"""
    # it is not robust in general to judge just from the collection of euler angles
    # whether they are reported in radiant or degree
    # indeed an EBSD map of a slightly deformed single crystal close to e.g. the cube ori
    # can have euler angles for each scan point within pi, 2pi respectively
    # similarly there was an example in the data 229_2096.oh5 where 3 out of 20.27 mio
    # scan points where not reported in radiant but rather using 4pi as a marker to indicate
    # there was a problem with the scan point
    if not isinstance(triplet_set, ureg.Quantity):
        raise ValueError(
            f"Argument triplet_set needs to be an ureg.Quantity with unit radian !"
        )
    if triplet_set.units != "radian":
        raise ValueError(f"Argument triplet_set needs to be in radian !")
    for column_id in [0, 1, 2]:
        here = np.where(triplet_set[:, column_id].magnitude < 0.0)
        if len(here[0]) > 0:
            triplet_set[here, column_id].magnitude += EULER_SPACE_SYMMETRY[
                column_id
            ].magnitude
    return triplet_set


def read_strings(obj):
    if isinstance(obj, np.ndarray):
        retval = []
        for entry in obj:
            if isinstance(entry, bytes):
                retval.append(entry.decode("utf-8"))
            elif isinstance(entry, str):
                retval.append(entry)
            else:
                continue
                # raise ValueError("Neither bytes nor str inside np.ndarray!")
        # specific implementation rule that all lists with a single string
        # will be returned in paraprobe as a scalar string
        if len(retval) > 1:
            return retval
        elif len(retval) == 1:
            return retval[0]
        else:
            return None
    elif isinstance(obj, bytes):
        return obj.decode("utf8")
    elif isinstance(obj, str):
        return obj
    else:
        return None
        # raise ValueError("Neither np.ndarray, nor bytes, nor str !")


def read_first_scalar(obj):
    if hasattr(obj, "shape"):
        if obj.shape == ():
            return obj[()]
        elif obj.shape == (1,):
            return obj[0]
        else:
            raise ValueError(
                f"Unexpected shape found in {__name__} from object {obj} !"
            )
    else:
        raise ValueError(f"Unexpected input passed to {__name__} with object {obj} !")


def all_equal(iterable):
    g = groupby(iterable)
    return next(g, True) and not next(g, False)
