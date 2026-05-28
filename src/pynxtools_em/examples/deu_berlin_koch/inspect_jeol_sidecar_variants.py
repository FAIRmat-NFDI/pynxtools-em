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
from pathlib import Path

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
BUTT = rf"(?:{BREAK})?"
FLOAT = r"(?:\d+(?:\.\d*)?|\.\d+)"
INT = r"\d+"
# DATE = r"(0[1-9]|[12][0-9]|3[0-1])/(0[1-9]|[12][0-9]|3[0-1])/\d{4}"  # e.g. 5/25/2026
# DATE = r"(?:(?:0?[1-9]|1[0-2])/(?:0?[1-9]|[12][0-9]|3[01])|(?:0?[1-9]|[12][0-9]|3[01])/(?:0?[1-9]|1[0-2]))/\d{4}"
DATE = r"(?:\d{1,2}/\d{1,2}/\d{4}|\d{4}/\d{1,2}/\d{1,2})"
TIME = r"(?:(?:0?[1-9]|1[0-9]|2[0-3]):(?:[0-5][0-9]):(?:[0-5][0-9])(?: AM| PM)?|(?:(?:AM|PM) )?(?:0?[1-9]|1[0-9]|2[0-3]):(?:[0-5][0-9]))"
CHARS_NO_BREAK = r"[^\r\n]*"  # + one or more, * zero or more, ? zero or one
LENGTH = r"\d+(?:\.\d+)?\s?(?:nm|µm|mm|cm)"
SIGNAL = r"(TEM|DIFF|STEM DF|STEM BF|Spectrum|NON)"

# JEOL, Hannah/20210225_CsPbBrI40Big_TEMIsrael/1.txt
JEOL_LAYOUT_ONE: list[str] = [
    rf"^\$CM_FORMAT {BREAK}$",
    rf"^\$CM_VERSION {CHARS_NO_BREAK}{BREAK}$",
    rf"^\$CM_COMMENT {CHARS_NO_BREAK}{BREAK}$",
    rf"^\$CM_DATE {DATE}{BREAK}$",
    rf"^\$CM_TIME {TIME}{BREAK}$",
    rf"^\$CM_OPERATOR {CHARS_NO_BREAK}{BREAK}$",
    rf"^\$CM_INSTRUMENT JEM-2200FS{BREAK}$",
    rf"^\$CM_NAME {CHARS_NO_BREAK}{BREAK}$",  # often CHARS_NO_BREAK often Specimen
    rf"^\$CM_FRAME_SIZE {INT} {INT}{BREAK}$",
    rf"^\$CM_DATA_BIT {INT}{BREAK}$",
    rf"^\$CM_EFECT_BIT {INT}{BREAK}$",
    rf"^\$CM_ACCEL_VOLT {INT}{BREAK}$",  # for Koch group JEOL-2200FS observed 200 and 0
    rf"^\$CM_MAG {INT}{BREAK}$",
    rf"^\$CM_SIGNAL {SIGNAL}{BREAK}$",
    rf"^\$\$EM_PIXELSPERMETER_X {FLOAT}{BREAK}$",
    rf"^\$\$EM_PIXELSPERMETER_Y {FLOAT}{BUTT}$",
]

# Robert/2021_03_19_ZnGaO/STEM/ZnGaO_stem01_ADF_CL10cm_spot07nm_25kx_ZA100_ovw.txt
JEOL_LAYOUT_TWO: list[str] = [
    rf"^\$CM_FORMAT {BREAK}$",
    rf"^\$CM_VERSION 0.1{BREAK}$",
    rf"^\$CM_COMMENT {BREAK}$",
    rf"^\$CM_DATE {DATE}{BREAK}$",
    rf"^\$CM_TIME {TIME}{BREAK}$",
    rf"^\$CM_OPERATOR {CHARS_NO_BREAK}{BREAK}$",
    rf"^\$CM_INSTRUMENT JEM-2200FS{BREAK}$",
    rf"^\$CM_ACCEL_VOLT {FLOAT}{BREAK}$",
    rf"^\$CM_MAG {INT}{BREAK}$",
    rf"^\$CM_SIGNAL {CHARS_NO_BREAK}{BREAK}$",  # "DFI  " in the prototype
    rf"^\$\$SM_FILM_NUMBER {INT}{BREAK}$",
    rf"^\$\$SM_WD {FLOAT}{BREAK}$",
    rf"^\$\$SM_MICRON_BAR {INT}{BREAK}$",
    rf"^\$\$SM_MICRON_MARKER {LENGTH}{BREAK}$",
    rf"^\$\$SM_FONT_SIZE {INT} {INT}{BREAK}$",
    rf"^\$\$SM_DISPLAY_MODE {CHARS_NO_BREAK}{BUTT}$",
]


def does_file_conform_with_layout(
    path: str, layout: list[str], verbose: bool = False
) -> bool:
    """Check if path is a text file and if so follows the specific line-by-line layout as defined in layout."""
    if Path(path).stat().st_size == 0:
        return False

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
            if verbose:
                print(f"txt is None")
            return False

        if len(txt) == 0:
            return False

        print(f">>>>>>>>>>>{txt[0]}")
        if not txt[0].startswith("$CM_FORMAT"):  # JEOL text file signature
            return False

        n_lines_layout: int = len(layout)
        for idx, line in enumerate(txt):
            if idx < n_lines_layout:
                if not re.fullmatch(layout[idx], line):
                    if verbose:
                        print(
                            f"not fullmatch {layout[idx]}, {SEPARATOR}{line}{SEPARATOR}"
                        )
                    return False
            else:
                if verbose:
                    print(f"not {idx} < {n_lines_layout}, {SEPARATOR}{line}{SEPARATOR}")
                return False

    return True


def inspect_jeol_metadata(
    root_path: str, prefix: str, write: bool = True, verbose: bool = False
) -> None:
    """Recurse all files in root_path, if metadata sidecar file, check if matches any known formatting."""

    if write:
        layouts: dict[int, list[str]] = {1: JEOL_LAYOUT_ONE, 2: JEOL_LAYOUT_TWO}
        for root, dirs, files in os.walk(root_path):
            for name in files:
                path = os.path.join(root, name)
                if path.lower().endswith(".txt"):
                    # check if there is a matching main file (i.e. tif or bmp image)
                    if not os.path.isfile(
                        f"{path.rsplit('.', 1)[0]}.bmp"
                    ) and not os.path.isfile(f"{path.rsplit('.', 1)[0]}.tif"):
                        continue
                    if verbose:
                        charset_normalizer_analysis = from_path(path).best()
                        if charset_normalizer_analysis:
                            print(
                                f"{path}, {charset_normalizer_analysis.encoding}, {charset_normalizer_analysis.percent_chaos}"
                            )

                    layout_analysis: list[int] = []
                    for key, layout in layouts.items():
                        status = does_file_conform_with_layout(path, layout)
                        if status:
                            layout_analysis.append(key)

                    if len(layout_analysis) == 0:  # or verbose:
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
