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
"""Utility functions to interpret data from hyperspy-project-specific representation."""

import numpy as np


def all_req_keywords_in_dict(dct: dict, keywords: list) -> bool:
    """Check if dict dct has all keywords in keywords as keys from."""
    # falsifiable?
    for key in keywords:
        if key in dct:
            continue
        return False
    return True


def get_named_axis(axes_metadata, dim_name):
    """Return numpy array with tuple (axis pos, unit) along dim_name or None."""
    retval = None
    if len(axes_metadata) >= 1:
        for axis in axes_metadata:
            if isinstance(axis, dict):
                if "name" in axis:
                    if axis["name"] == dim_name:
                        # "index_in_array" and "navigate" are currently not required
                        # and ignored but might become important
                        for req in ["offset", "scale", "size", "units"]:
                            if req not in axis:
                                print(f"{req} not in {axis}!")
                                return None
                        retval = (
                            np.asarray(
                                axis["offset"]
                                + np.linspace(
                                    0.0,
                                    axis["size"] - 1.0,
                                    num=int(axis["size"]),
                                    endpoint=True,
                                )
                                * axis["scale"],
                                dtype=np.float32,
                            ),
                            axis["units"],
                        )
    return retval


def get_axes_dims(axes_metadata):
    """Return list of (axis) name, index_in_array tuple or empty list."""
    retval = []
    if len(axes_metadata) >= 1:
        for axis in axes_metadata:
            if isinstance(axis, dict):
                if "name" in axis:
                    if "index_in_array" in axis:
                        retval.append((axis["name"], axis["index_in_array"]))
                    else:
                        if len(axes_metadata) == 1:
                            retval.append((axis["name"], 0))
                        else:
                            raise ValueError(
                                f"get_axes_dims {axes_metadata} "
                                f"is a case not implemented!"
                            )
    # TODO::it seems that hyperspy sorts this by index_in_array
    return retval


def get_axes_units(axes_metadata):
    """Return list of units or empty list."""
    retval = []
    if len(axes_metadata) >= 1:
        for axis in axes_metadata:
            if isinstance(axis, dict):
                if "units" in axis:
                    retval.append(axis["units"])
    # TODO::it seems that hyperspy sorts this by index_in_array
    return retval
