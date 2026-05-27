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

"""Distinguish different formatting variants for JEOL plain text metadata files."""

# test code for working with data from jeol_data before putting it into pynxtools-em
# import magic  # ancient but most robust print(magic.from_file(path, mime=True))
import os
import re
import sys

import puremagic  # modern, pythonic replacement but not that covering
from charset_normalizer import from_bytes, from_path

from pynxtools_em.examples.get_sha256_of_directories import SEPARATOR

STRING_DECODER_CODECS = [
    "utf-8",
    "cp1252",
    "utf-16",
    "utf-16-be",
    "utf-16-le",
    "latin-1",  # TODO not as robust ?
]

BREAK = r"(?:\r\n?|\n)"
FLOAT = r"(?:\d+(?:\.\d*)?|\.\d+)"
INT = r"\d+"
DATE = r"([1-9]|0[1-9]|1[0-2])/(0[1-9]|[12][0-9]|3[0-1])/\d{4}"  # e.g. 5/25/2026
TIME = r"([0-2][0-9]):([0-6][0-9]):([0-6][0-9]) (AM|PM)"
CHARS_NO_BREAK = r"[^\r\n]*"  # + one or more, * zero or more, ? zero or one

# JEOL, Hannah/20210225_CsPbBrI40Big_TEMIsrael/1.txt
layout_one: list[str] = [
    rf"^\$CM_FORMAT {BREAK}$",
    rf"^\$CM_VERSION {CHARS_NO_BREAK}{BREAK}$",
    rf"^\$CM_COMMENT  {BREAK}$",
    rf"^\$CM_DATE {DATE}{BREAK}$",
    rf"^\$CM_TIME {TIME}{BREAK}$",
    rf"^\$CM_OPERATOR {CHARS_NO_BREAK}{BREAK}$",
    rf"^\$CM_INSTRUMENT JEM-2200FS{BREAK}$",
    rf"^\$CM_NAME Specimen{BREAK}$",
    rf"^\$CM_FRAME_SIZE {INT} {INT}{BREAK}$",
    rf"^\$CM_DATA_BIT {INT}{BREAK}$",
    rf"^\$CM_EFECT_BIT {INT}{BREAK}$",
    rf"^\$CM_ACCEL_VOLT 200{BREAK}$",
    rf"^\$CM_MAG {INT}{BREAK}$",
    rf"^\$CM_SIGNAL TEM{BREAK}$",
    rf"^\$\$EM_PIXELSPERMETER_X {FLOAT}{BREAK}$",
    rf"^\$\$EM_PIXELSPERMETER_Y {FLOAT}{BREAK}$",
]

# Robert/2021_03_19_ZnGaO/STEM/ZnGaO_stem01_ADF_CL10cm_spot07nm_25kx_ZA100_ovw.txt
layout_two: list[str] = [
    rf"^\$CM_FORMAT {BREAK}$",
    rf"^\$CM_VERSION 0.1{BREAK}$",
    rf"^\$CM_COMMENT {BREAK}$",
    rf"^\$CM_DATE {DATE}{BREAK}$",
    rf"^\$CM_TIME {TIME}{BREAK}$",
    rf"^\$CM_OPERATOR {CHARS_NO_BREAK}{BREAK}$",
    rf"^\$CM_INSTRUMENT JEM-2200FS{BREAK}$",
    rf"^\$CM_ACCEL_VOLT {FLOAT}{BREAK}$",
    rf"^\$CM_MAG {INT}{BREAK}$",
    rf"^\$CM_SIGNAL DFI  {BREAK}$",
    rf"^\$\$SM_FILM_NUMBER {INT}{BREAK}$",
    rf"^\$\$SM_WD {FLOAT}{BREAK}$",
    rf"^\$\$SM_MICRON_BAR {INT}{BREAK}$",
    rf"^\$\$SM_MICRON_MARKER 1µm{BREAK}$",
    rf"^\$\$SM_FONT_SIZE {INT} {INT}{BREAK}$",
    rf"^\$\$SM_DISPLAY_MODE {CHARS_NO_BREAK}{BREAK}$",
]


def does_file_conform_with_layout(path: str, layout: list[str]) -> bool:
    """Check if path is a text file and if so follows the specific line-by-line layout as defined in layout."""
    conforms: bool = True
    # if magic.from_file(path, mime=True) == "text/plain":  # libmagic alternative but outdated compared to
    if puremagic.from_file(path) == ".txt":
        txt: list[str] | None = None
        for codec in STRING_DECODER_CODECS:
            try:
                with open(path, encoding=codec) as fp:
                    txt = fp.readlines()
                break
            except UnicodeDecodeError:
                continue
        if txt is None:
            print(f"txt is None")
            return False

        """
        # utf-8
        try:
            txt = raw.decode("utf-8")
            print("utf-8")
        except UnicodeDecodeError:
            pass

        # typical windows encoding
        with open(path, encoding="cp1252") as fp:
            txt = fp.readlines() # type: ignore[assignment]
            print(f"cp1252")

        # utf byte order mark
        for enc, bom in [
            ("utf-8-sig", b"\xef\xbb\xbf"),
            ("utf-16-le", b"\xff\xfe"),
            ("utf-16-be", b"\xfe\xff"),
        ]:
            try:
                if raw.startswith(bom):
                    txt = raw.decode(enc)
                    print(f"{enc}")
            except UnicodeDecodeError:
                pass

        best = from_bytes(raw).best()
        if best:
            txt = str(best)
            print(f"best")
        else:
            return False
        """

        n_lines_layout: int = len(layout)
        for idx, line in enumerate(txt):
            if idx < n_lines_layout:
                if not re.fullmatch(layout[idx], line):
                    print(f"not fullmatch {layout[idx]}, {SEPARATOR}{line}{SEPARATOR}")
                    conforms = False
                    break
            else:
                conforms = False
                print(f"not {idx} < {n_lines_layout}, {SEPARATOR}{line}{SEPARATOR}")
                break
    return conforms


def inspect_jeol_metadata(root_path: str, prefix: str, write: bool = True) -> None:
    """Recurse all files in root_path, if metadata sidecar file, check if matches any known formatting."""

    if write:
        # summary: dict[str, list[str]] = {"layout_one": []}
        for root, dirs, files in os.walk(root_path):
            for name in files:
                path = os.path.join(root, name)
                if path.lower().endswith(".txt"):
                    print(path)
                    charset_normalizer_analysis = from_path(path).best()
                    if charset_normalizer_analysis:
                        print(
                            f"{path}, {charset_normalizer_analysis.encoding}, {charset_normalizer_analysis.percent_chaos}"
                        )

                    layout_analysis: list[str] = []
                    for name, layout in [
                        ("layout_1", layout_one),
                        ("layout_2", layout_two),
                    ]:
                        status = does_file_conform_with_layout(path, layout)
                        if status:
                            layout_analysis.append(name)

                    print(f"{path}, {layout_analysis}")

        # with open(f"{prefix}.directories.csv", "w") as fp:
        #     fp.write("\n".join(csv_directories))


def main():
    # e.g. call via
    # `python3 inspect_jeol_metadata_variants.py /microscope_data inspect_jeol_metadata`
    if len(sys.argv) > 1:
        root_path = sys.argv[1]
    else:
        root_path = "."

    if len(sys.argv) > 2:
        prefix = sys.argv[2]
    else:
        prefix = "inspect_jeol_metadata"

    inspect_jeol_metadata(root_path, prefix)


if __name__ == "__main__":
    main()
