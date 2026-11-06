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
"""Tests for how the em reader sorts its input files (Bug B6 in
https://github.com/FAIRmat-NFDI/pynxtools-plugin-audit/blob/main/pynxtools-unification/FINDINGS.md)."""

from pynxtools_em.utils.io_case_logic import EmUseCaseSelector


def test_mtex_file_is_counted_once():
    """A .mtex.h5 file also ends with .h5, but must only count as .mtex.h5."""
    case = EmUseCaseSelector(("a.mtex.h5",))
    assert case.is_valid
    assert case.dat == ["a.mtex.h5"]
    assert case.case[".h5"] == []
