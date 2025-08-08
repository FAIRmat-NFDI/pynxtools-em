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
from glob import glob
from typing import Literal

import pytest
import yaml
from pynxtools.dataconverter.convert import convert, get_reader
from pynxtools.dataconverter.helpers import get_nxdl_root_and_path

# from pynxtools.testing.nexus_conversion import ReaderTest
from pynxtools_em.parsers.hfive_base import (
    NXEM_VOLATILE_NAMED_HDF_PATHS,
    NXEM_VOLATILE_SUFFIX_HDF_PATHS,
    HdfFiveBaseParser,
)

READER_NAME = "em"
READER_CLASS = get_reader(READER_NAME)
NXDLS = ["NXem"]

test_cases = [
    ("default", "NOMAD simple EM example"),
]

test_params = []

for test_case in test_cases:
    # ToDo: make tests for all supported appdefs possible
    for nxdl in NXDLS:
        test_params += [pytest.param(nxdl, test_case[0], id=f"{test_case[1]}, {nxdl}")]


def convert_using_example_data(files_or_dir, tmp_path, caplog, **kwargs) -> None:
    """Run the converter during the test."""
    # see pynxtools/testing/nexus_conversion/ReaderTest

    nxdl = "NXem"
    reader_name = "em"
    created_nexus = f"{tmp_path}/{os.sep}/output.nxs"
    caplog_level: Literal["ERROR", "WARNING"] = "WARNING"

    reader = get_reader(reader_name)
    assert hasattr(reader, "supported_nxdls"), (
        f"Reader{reader} must have supported_nxdls attribute"
    )
    assert nxdl in reader.supported_nxdls, f"Reader does not support {nxdl} NXDL."
    assert callable(reader.read), f"Reader{reader} must have read method"

    if isinstance(files_or_dir, (list, tuple)):
        example_files = files_or_dir
    else:
        example_files = sorted(glob(os.path.join(files_or_dir, "*")))
    input_files = [file for file in example_files]

    nxdl_root, nxdl_file = get_nxdl_root_and_path(nxdl)
    assert os.path.exists(nxdl_file), f"NXDL file {nxdl_file} not found"

    # Clear the log of `convert`
    caplog.clear()

    with caplog.at_level(caplog_level):
        _ = convert(
            input_file=tuple(input_files),
            reader=reader_name,
            nxdl=nxdl,
            skip_verify=False,
            ignore_undocumented=True,
            output=created_nexus,
            **kwargs,
        )


@pytest.mark.parametrize(
    "nxdl, sub_reader_data_dir",
    test_params,
)
@pytest.mark.skip(
    reason="Working for the default example location of large test data should be clarified though"
)
# explores an alternative testing strategy which checks for binary
# reproducibility at the individual HDF5 node using per node checksums
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
    # reader = READER_NAME
    # assert callable(reader.read)

    files_or_dir = os.path.join(
        *[os.path.dirname(__file__), "data", sub_reader_data_dir]
    )

    # test = ReaderTest(
    #     nxdl=nxdl,
    #     reader_name=READER_NAME,
    #     files_or_dir=files_or_dir,
    #     tmp_path=tmp_path,
    #     caplog=caplog,
    # )
    test_nexus_path = f"{tmp_path}/{os.sep}/output.nxs"
    convert_using_example_data(files_or_dir, tmp_path, caplog)

    hfive_parser = HdfFiveBaseParser(
        file_path=test_nexus_path, hashing=True, verbose=False
    )
    hfive_parser.get_content()
    hfive_parser.store_hashes(
        blacklist_by_key=NXEM_VOLATILE_NAMED_HDF_PATHS,
        blacklist_by_suffix=NXEM_VOLATILE_SUFFIX_HDF_PATHS,
        file_path=f"{test_nexus_path}.sha256.test.yaml",
    )

    # assert against reference YAML artifact
    test_artifact_file_path = f"{test_nexus_path}.sha256.test.yaml"
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
