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

from pynxtools_em.parsers.hfive_base import HdfFiveBaseParser

READER_NAME = "em"
READER_CLASS = get_reader(READER_NAME)
# ToDo: make tests for all supported application definitions possible
NXDLS = ["NXem"]  # READER_CLASS.supported_nxdls

test_cases = [
    ("eln", "simple ELN"),
]

test_params = []

for test_case in test_cases:
    # ToDo: make tests for all supported appdefs possible
    for nxdl in NXDLS:
        test_params += [pytest.param(nxdl, test_case[0], id=f"{test_case[1]}, {nxdl}")]

NXEM_VOLATILE_METADATA = [
    "/@HDF5_Version",
    "/@NeXus_release",
    "/@file_update_time",
    "entry1/definition/@version",
    "entry1/profiling/program1/program/@version",
    "entry1/profiling/template_filling_elapsed_time",
    # "entry1/profiling/template_filling_elapsed_time/@units"
]


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
    files_or_dir = os.path.join(
        *[
            os.path.dirname(__file__),
            "data",
            "eln",
        ]  # "data/eln/em.oasis.specific.yaml"]
    )

    print(f">>>>>>>> files_or_dir n00b >>>>>>>\n{files_or_dir}")

    test = ReaderTest(
        nxdl=nxdl,
        reader_name=READER_NAME,
        files_or_dir=files_or_dir,
        tmp_path=tmp_path,
        caplog=caplog,
    )
    test.convert_to_nexus(caplog_level="WARNING", ignore_undocumented=True)

    print(f">>>>>>>> test.created_nexus n00b >>>>>>>\n{test.created_nexus}")

    hfive_parser = HdfFiveBaseParser(
        file_path=test.created_nexus, hashing=True, verbose=False
    )
    hfive_parser.get_content()
    hfive_parser.store_hashes(blacklist=NXEM_VOLATILE_METADATA, suffix=".test")

    # assert against reference YAML artifact
    with open(f"{test.created_nexus}.sha256.test.yaml", "r") as fp_test:
        # try:
        test_artifact = yaml.safe_load(fp_test)
        # except Exception as e:
        # todo
        # error logs ?

    print(files_or_dir)

    with open(f"{files_or_dir}/output.nxs.sha256.ref.yaml", "r") as fp_ref:
        # try:
        reference_artifact = yaml.safe_load(fp_ref)
        # except Exception as e:
        # todo
        # erros logs ?

    assert test_artifact == reference_artifact
    # test.check_reproducibility_of_nexus()

    # TODO remove if not working
