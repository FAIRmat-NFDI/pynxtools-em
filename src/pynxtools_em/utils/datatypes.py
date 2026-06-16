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
"""Utility code to identify compact data types."""


import numpy as np


def get_compact_integer_datatype(data):
    smallest = int(np.min(data))
    largest = int(np.max(data))
    if smallest >= 0:
        for dtype in (np.uint8, np.uint16, np.uint32, np.uint64):
            if np.iinfo(dtype).min <= smallest and largest <= np.iinfo(dtype).max:
                return dtype
        return np.uint64
    else:
        for dtype in (np.int8, np.int16, np.int32, np.int64):
            if np.iinfo(dtype).min <= smallest and largest <= np.iinfo(dtype).max:
                return dtype
        return np.int64
