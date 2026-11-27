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

"""Test metadata parsing of ThermoFisher TIFF files."""

import numpy as np
from PIL import Image

from pynxtools_em.parsers.image_tiff_tfs import TfsTiffParser

# Each section lists only some of the terms the parser knows about,
# like real files from different instruments and software versions
TFS_METADATA = (
    "[User]\r\n"
    "Date=05/18/2022\r\n"
    "\r\n"
    "[EBeam]\r\n"
    "HV=5000\r\n"
    "WD=0.004\r\n"
    "\r\n"
    "[EScan]\r\n"
    "PixelWidth=3.3724e-006\r\n"
    "PixelHeight=3.3724e-006\r\n"
    "\r\n"
    "[IRBeam]\r\n"
    "ScanRotation=0.00840385\r\n"
    "n=\r\n"
    "\r\n"
)


def test_tfs_tiff_metadata(tmp_path):
    file_path = str(tmp_path / "tfs.tif")
    Image.fromarray(np.zeros((4, 6), dtype=np.uint8)).save(
        file_path, tiffinfo={34682: TFS_METADATA}
    )
    parser = TfsTiffParser(file_path)
    assert parser.supported
    md = parser.metadata
    assert md["User/Date"] == "05/18/2022"
    assert md["EBeam/HV"] == 5000
    assert md["EBeam/WD"] == 0.004
    assert md["EScan/PixelWidth"] == 3.3724e-6
    assert md["EScan/PixelHeight"] == 3.3724e-6
    assert md["IRBeam/ScanRotation"] == 0.00840385
    # an empty value must not be taken from "ScanRotation=" on the line above
    assert md.get("IRBeam/n") is None
