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
"""NXobject (element of a labelled property graph) to store instance data."""

from typing import Dict

import numpy as np


class NxObject:
    """An object in a graph e.g. an attribute, dataset, or group in NeXus.
    name: name of the node
    unit: unit, not unit category, unitless if no unit, dimensionless if units cancel
    dtype np.dtype
    value: numpy scalar, tensor, or string if possible
    eqv_hdf: node type in HDF5 serialization, group, dset/field, attribute
    """

    def __init__(self, name: str, unit: str, dtype, value, **kwargs):
        if (name is not None) and (name == ""):
            raise ValueError(
                f"Value for argument name needs to be a non-empty string !"
            )
        if (unit is not None) and (unit == ""):
            raise ValueError(
                f"Value for argument unit needs to be a non-empty string !"
            )
        if (dtype is not None) and isinstance(dtype, type) is False:
            raise ValueError(
                f"Value of argument dtype must not be None "
                f" and a valid, ideally a numpy datatype !"
            )
        self.name = name
        self.unit = unit
        self.dtype = dtype
        if value is None or isinstance(dtype, str):
            self.unit = "unitless"
        self.value = value
        self.eqv_hdf = None
        if "eqv_hdf" in kwargs:
            if kwargs["eqv_hdf"] in ["group", "dataset", "attribute"]:
                self.eqv_hdf = kwargs["eqv_hdf"]
            else:
                raise ValueError(
                    f"Value of keyword argument eqv_hdf needs to be one of grp, dset, attr !"
                )

    def __repr__(self):
        """Report values."""
        return (
            f"name: {self.name}"
            f"unit: {self.unit}"
            f"dtype: {self.dtype}"
            f"np.shape(value): {np.shape(self.value)}"
            f"eqv_hdf: {self.eqv_hdf}"
        )
