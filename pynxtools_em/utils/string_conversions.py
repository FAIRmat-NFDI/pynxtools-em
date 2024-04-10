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
"""Utility function to map quantities that have been serialized as strings back to other type."""


def string_to_number(arg: str):
    """Convert input string to int, float, or leave string."""
    if isinstance(arg, str):
        try:
            float(arg)
        except ValueError:
            return arg
        # val = np.array([str_val]).astype(np.float64)[0]
        val = float(arg)
        if val.is_integer():
            return int(val)
        else:
            return val
    else:
        raise TypeError(f"Input argument arg needs to be a string!")


# str_val = "-0.4899999"
# str_val = "-2."
# str_val = "-2.000000001"
# str_val = "test"
# print(f"{string_to_number(str_val)}, {type(string_to_number(str_val))}")


def rchop(s, suffix):
    if suffix and s.endswith(suffix):
        return s[: -len(suffix)]
    return s
