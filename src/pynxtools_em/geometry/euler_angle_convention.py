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
"""Definitions for different conventions associated with Euler angles.

Euler angles are a parameterization for orientations which use three consecutive
3D rotations to rotate a configuration of an attached Cartesian CS named A to align
it with an attached Cartesian CS named B. The sequence about which specific axes
and new/intermediate axes one rotates distinguishes different types of
Euler angle conventions (e.g. Tait, Kocks, Canova, Bunge). In materials science the
convention of H.-J. Bunge aka zxz convention is used most frequently.
"""

# "Bunge" https://doi.org/10.1016/C2013-0-11769-2
# "Rowenhorst" https://doi.org/10.1088/0965-0393/23/8/083501
# "Morawiec" https://doi.org/10.1007/978-3-662-09156-2
# "Britton" https://doi.org/10.1016/j.matchar.2016.04.008

euler_convention = {
    "xxx": (False, "", ""),
    "xxy": (True, "", ""),
    "xxz": (True, "", ""),
    "xyx": (True, "", ""),
    "xyy": (True, "", ""),
    "xyz": (True, "", ""),
    "xzx": (True, "", ""),
    "xzy": (True, "", ""),
    "xzz": (True, "", ""),
    "yxx": (True, "", ""),
    "yxy": (True, "", ""),
    "yxz": (True, "", ""),
    "yyx": (True, "", ""),
    "yyy": (False, "", ""),
    "yyz": (True, "", ""),
    "yzx": (True, "", ""),
    "yzy": (True, "", ""),
    "yzz": (True, "", ""),
    "zxx": (True, "", ""),
    "zxy": (True, "", ""),
    "zxz": (True, "Bunge", "proper"),
    "zyx": (True, "", ""),
    "zyy": (True, "", ""),
    "zyz": (True, "", ""),
    "zzx": (True, "", ""),
    "zzy": (True, "", ""),
    "zzz": (False, "", ""),
}
