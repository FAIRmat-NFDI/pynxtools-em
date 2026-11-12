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
"""Safe parsing of XML from uploaded files (Bug B36 in
https://github.com/FAIRmat-NFDI/pynxtools-plugin-audit/blob/main/pynxtools-unification/FINDINGS.md)."""

import re
from pathlib import Path

import pytest
import xmltodict
from packaging.requirements import Requirement

PYPROJECT = Path(__file__).parents[1] / "pyproject.toml"


def test_xmltodict_has_a_safe_minimum_version():
    """xmltodict before 0.11 expanded entities, so the dependency needs a minimum."""
    # read pyproject.toml as text: tomllib is not available on Python 3.10
    (xmltodict_dep,) = re.findall(r'"(xmltodict[^"]*)"', PYPROJECT.read_text())
    xmltodict_req = Requirement(xmltodict_dep)
    assert not xmltodict_req.specifier.contains("0.10.2")
    assert xmltodict_req.specifier.contains("0.13.0")


def test_xmltodict_does_not_expand_entities():
    """XML with an entity declaration, as could come in an uploaded file, is rejected."""
    xml = (
        '<?xml version="1.0"?>'
        '<!DOCTYPE root [<!ENTITY secret "expanded">]>'
        "<root>&secret;</root>"
    )
    with pytest.raises(ValueError, match="entities are disabled"):
        xmltodict.parse(xml)
