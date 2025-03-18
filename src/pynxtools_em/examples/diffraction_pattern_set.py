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
"""Pieces of information relevant for the MaterialsProject EBSD Kikuchi pattern example."""
# https://doi.org/10.1093/mam/ozae044.178

import os
import re
from typing import Tuple, Union

import numpy as np

THIS_MODULE_PATH = os.path.abspath(__file__).replace("/diffraction_pattern_set.py", "")
EXAMPLE_FILE_PREFIX = "original_data/original_data_0/train/"
MATERIALS_PROJECT_METADATA = f"{THIS_MODULE_PATH}/diffraction_pattern_meta.yaml"
SUPPORTED_FORMATS = ["bmp", "gif", "jpg", "png", "tif", "tiff"]
SUPPORTED_MODES = ["L", "I"]


def get_materialsproject_id_and_spacegroup(
    fpath: str, verbose: bool = False
) -> Union[Tuple[str, int], Tuple[None, None]]:
    if 1 <= int(fpath[fpath.rfind("/") - 3 : fpath.rfind("/")]) <= 230:
        fname = fpath[fpath.rfind("/") + 1 :]
        materialsproject_id = re.compile(r"^mp-(?:\d+)_").search(fname)
        mp = materialsproject_id.group()[0:-1]
        spacegroup_id = re.compile(r"^(?:\d{1}|\d{2}|\d{3})_").search(
            fname.replace(materialsproject_id.group(), "")
        )
        spc = spacegroup_id.group()[0:-1]
        tail = fname.replace(
            f"{materialsproject_id.group()}{spacegroup_id.group()}", ""
        )
        if verbose:
            print(fpath)
            print(fname)
            print(f"{mp}____{type(mp)}")
            print(f"{spc}____{type(spc)}")
            print(f"{tail}____{type(tail)}")
        return mp, int(spc)
    return None, None


# https://pillow.readthedocs.io/en/stable/handbook/concepts.html#concept-modes
PIL_DTYPE_TO_NPY_DTYPE = {
    "L": np.uint8,
    "I": np.int32,
}
