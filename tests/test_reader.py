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

import os

import pytest
import yaml
from pynxtools.dataconverter.convert import get_reader
from pynxtools.testing.nexus_conversion import ReaderTest

from pynxtools_em.parsers.hfive_base import NXEM_VOLATILE_METADATA, HdfFiveBaseParser

READER_NAME = "em"
READER_CLASS = get_reader(READER_NAME)
# ToDo: make tests for all supported application definitions possible
NXDLS = ["NXem"]  # READER_CLASS.supported_nxdls

test_cases = [("eln", "simple ELN"), ("eln_second", "another simple ELN")]

test_params = []

for test_case in test_cases:
    # ToDo: make tests for all supported appdefs possible
    for nxdl in NXDLS:
        test_params += [pytest.param(nxdl, test_case[0], id=f"{test_case[1]}, {nxdl}")]


@pytest.mark.parametrize(
    "nxdl, sub_reader_data_dir",
    test_params,
)
def test_nexus_conversion(nxdl, sub_reader_data_dir, tmp_path, caplog):
    """
    Test EM reader

    Parameters
    ----------
    nxdl : str
        Name of the NXDL application definition that is to be tested by
        this reader plugin (e.g. NXsts, NXmpes, etc)..
    sub_reader_data_dir : str
        Test data directory that contains all the files required for running the data
        conversion through one of the sub-readers. All of these data dirs
        are placed within tests/data/...
    tmp_path : pathlib.PosixPath
        Pytest fixture variable, used to clean up the files generated during
        the test.
    caplog : _pytest.logging.LogCaptureFixture
        Pytest fixture variable, used to capture the log messages during the
        test.

    Returns
    -------
    None.

    """
    caplog.clear()
    reader = READER_NAME
    # assert callable(reader.read)

    files_or_dir = os.path.join(
        *[os.path.dirname(__file__), "data", sub_reader_data_dir]
    )

    test = ReaderTest(
        nxdl=nxdl,
        reader_name=READER_NAME,
        files_or_dir=files_or_dir,
        tmp_path=tmp_path,
        caplog=caplog,
    )
    test.convert_to_nexus(caplog_level="WARNING", ignore_undocumented=True)

    hfive_parser = HdfFiveBaseParser(
        file_path=test.created_nexus, hashing=True, verbose=False
    )
    hfive_parser.get_content()
    hfive_parser.store_hashes(
        blacklist=NXEM_VOLATILE_METADATA,
        file_path=f"{test.created_nexus}.sha256.test.yaml",
    )

    # assert against reference YAML artifact
    test_artifact_file_path = f"{test.created_nexus}.sha256.test.yaml"
    with open(test_artifact_file_path, "r") as fp_test:
        try:
            test_artifact = yaml.safe_load(fp_test)
        except yaml.YAMLError as exc:
            print(f"Unable to load test_artifact {test_artifact_file_path} !")

    ref_artifact_file_path = os.path.join(
        *[
            os.path.dirname(__file__),
            "reference",
            sub_reader_data_dir,
            "output.nxs.sha256.ref.yaml",
        ]
    )
    with open(ref_artifact_file_path, "r") as fp_ref:
        try:
            reference_artifact = yaml.safe_load(fp_ref)
        except yaml.YAMLError as exc:
            print(f"Unable to load ref_artifact {ref_artifact_file_path} !")

    assert test_artifact == reference_artifact
    # test.check_reproducibility_of_nexus()

    # TODO remove if not working
