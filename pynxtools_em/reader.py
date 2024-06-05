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
"""Parser for loading generic orientation microscopy data based on ."""

from os import getcwd
from time import perf_counter_ns
from typing import Any, Tuple

import numpy as np
from pynxtools.dataconverter.readers.base.reader import BaseReader

from pynxtools_em.concepts.nxs_concepts import NxEmAppDef
from pynxtools_em.subparsers.convention_reader import NxEmConventionParser
from pynxtools_em.subparsers.nxs_imgs import NxEmImagesSubParser
from pynxtools_em.subparsers.nxs_mtex import NxEmNxsMTexSubParser
from pynxtools_em.subparsers.nxs_nion import ZipNionProjectSubParser
from pynxtools_em.subparsers.nxs_pyxem import NxEmNxsPyxemSubParser
from pynxtools_em.subparsers.oasis_config_reader import (
    NxEmNomadOasisConfigurationParser,
)
from pynxtools_em.subparsers.oasis_eln_reader import NxEmNomadOasisElnSchemaParser
from pynxtools_em.subparsers.rsciio_velox import RsciioVeloxSubParser
from pynxtools_em.utils.io_case_logic import EmUseCaseSelector
from pynxtools_em.utils.nx_atom_types import NxEmAtomTypesResolver

# from pynxtools_em.subparsers.zip_ebsd_parser import NxEmOmZipEbsdParser
from pynxtools_em.utils.nx_default_plots import NxEmDefaultPlotResolver


class EMReader(BaseReader):
    """Parse content from file formats of the electron microscopy community."""

    # pylint: disable=too-few-public-methods

    # Whitelist for the NXDLs that the reader supports and can process
    supported_nxdls = ["NXem"]

    # pylint: disable=duplicate-code
    def read(
        self,
        template: dict = None,
        file_paths: Tuple[str] = None,
        objects: Tuple[Any] = None,
    ) -> dict:
        """Read data from given file, return filled template dictionary em."""
        # pylint: disable=duplicate-code
        tic = perf_counter_ns()
        template.clear()

        # so we need the following input:
        # logical analysis which use case
        # optional data input from a NOMAD Oasis-specific configuration YAML
        # data input from an ELN (using an ELN-agnostic) YAML representation
        # data input from technology partner files (different formats)
        # functionalities for creating NeXus default plots

        entry_id = 1
        print(
            "Identify information sources (RDM config, ELN, tech-partner files) to deal with..."
        )
        case = EmUseCaseSelector(file_paths)
        if not case.is_valid:
            print("Such a combination of input-file(s, if any) is not supported !")
            return {}

        if len(case.cfg) == 1:
            print("Parse (meta)data coming from a configuration of an RDM...")
            # having or using a deployment-specific configuration is optional
            nx_em_cfg = NxEmNomadOasisConfigurationParser(case.cfg[0], entry_id)
            nx_em_cfg.report(template)

        if len(case.eln) == 1:
            print("Parse (meta)data coming from an ELN...")
            nx_em_eln = NxEmNomadOasisElnSchemaParser(case.eln[0], entry_id)
            nx_em_eln.report(template)

        print("Parse NeXus appdef-specific content...")
        nxs = NxEmAppDef(entry_id)
        nxs.parse(template)

        print("Parse conventions of reference frames...")
        if len(case.cvn) == 1:
            # using conventions currently is optional
            conventions = NxEmConventionParser(case.cvn[0], entry_id)
            conventions.parse(template)

        print("Parse and map pieces of information within files from tech partners...")
        if len(case.dat) == 1:
            images = NxEmImagesSubParser(entry_id, case.dat[0], verbose=False)
            images.parse(template)

            velox = RsciioVeloxSubParser(entry_id, case.dat[0], verbose=False)
            velox.parse(template)

            nxs_mtex = NxEmNxsMTexSubParser(entry_id, case.dat[0], verbose=False)
            nxs_mtex.parse(template)

            nxs_pyxem = NxEmNxsPyxemSubParser(entry_id, case.dat[0], verbose=False)
            nxs_pyxem.parse(template)

            nxs_nion = ZipNionProjectSubParser(entry_id, case.dat[0], verbose=False)
            nxs_nion.parse(template)

            # zip_parser = NxEmOmZipEbsdParser(case.dat[0], entry_id)
            # zip_parser.parse(template)

        nxplt = NxEmDefaultPlotResolver()
        nxplt.priority_select(template)

        smpl = NxEmAtomTypesResolver(entry_id)
        smpl.identify_atomtypes(template)

        debugging = False
        if debugging:
            print("Reporting state of template before passing to HDF5 writing...")
            for keyword in template:
                print(f"{keyword}")  # : {template[keyword]}")

        print("Forward instantiated template to the NXS writer...")
        toc = perf_counter_ns()
        trg = f"/ENTRY[entry{entry_id}]/profiling"
        # template[f"{trg}/current_working_directory"] = getcwd()
        template[f"{trg}/template_filling_elapsed_time"] = np.float64(
            (toc - tic) / 1.0e9
        )
        template[f"{trg}/template_filling_elapsed_time/@units"] = "s"
        return template


# This has to be set to allow the convert script to use this reader.
READER = EMReader
