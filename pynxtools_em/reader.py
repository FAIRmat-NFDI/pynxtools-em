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
from typing import Tuple, Any
import numpy as np

from pynxtools.dataconverter.readers.base.reader import BaseReader
from pynxtools_em.utils.io_case_logic import (
    EmUseCaseSelector,
)

# from pynxtools_em.subparsers.nxs_mtex import NxEmNxsMTexSubParser
from pynxtools_em.subparsers.nxs_pyxem import NxEmNxsPyxemSubParser
from pynxtools_em.subparsers.nxs_imgs import NxEmImagesSubParser

# from pynxtools_em.subparsers.nxs_nion import NxEmZippedNionProjectSubParser
from pynxtools_em.subparsers.rsciio_velox import RsciioVeloxSubParser
## from pynxtools_em.utils.default_plots import NxEmDefaultPlotResolver
# from pynxtools_em.geometry.convention_mapper import NxEmConventionMapper

# remaining subparsers to be implemented and merged into this one
# from pynxtools.dataconverter.readers.em_om.utils.orix_ebsd_parser \
#     import NxEmOmOrixEbsdParser
# from pynxtools.dataconverter.readers.em_om.utils.mtex_ebsd_parser \
#     import NxEmOmMtexEbsdParser
# from pynxtools.dataconverter.readers.em_om.utils.zip_ebsd_parser \
#     import NxEmOmZipEbsdParser
# from pynxtools.dataconverter.readers.em_om.utils.em_nexus_plots \
#     import em_om_default_plot_generator

from pynxtools_em.subparsers.oasis_config_reader import (
    NxEmNomadOasisConfigurationParser,
)
from pynxtools_em.subparsers.oasis_eln_reader import NxEmNomadOasisElnSchemaParser
from pynxtools_em.concepts.nxs_concepts import NxEmAppDef


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

        print("Parse (meta)data coming from a configuration of an RDM...")
        if len(case.cfg) == 1:
            # having or using a deployment-specific configuration is optional
            nx_em_cfg = NxEmNomadOasisConfigurationParser(case.cfg[0], entry_id)
            nx_em_cfg.report(template)

        print("Parse (meta)data coming from an ELN...")
        if len(case.eln) == 1:
            nx_em_eln = NxEmNomadOasisElnSchemaParser(case.eln[0], entry_id)
            nx_em_eln.report(template)

        print("Parse NeXus appdef-specific content...")
        nxs = NxEmAppDef()
        nxs.parse(template, entry_id, file_paths)

        # print("Parse conventions of reference frames...")
        # conventions = NxEmConventionMapper(entry_id)
        # conventions.parse(template)

        print("Parse and map pieces of information within files from tech partners...")
        if len(case.dat) == 1:
            images = NxEmImagesSubParser(entry_id, case.dat[0], verbose=False)
            images.parse(template)

            velox = RsciioVeloxSubParser(entry_id, case.dat[0], verbose=False)
            velox.parse(template)

            # nxs_mtex = NxEmNxsMTexSubParser(entry_id, case.dat[0], verbose=False)
            # nxs_mtex.parse(template)
            # TODO::check correct loop through!

            nxs_pyxem = NxEmNxsPyxemSubParser(entry_id, case.dat[0], verbose=False)
            nxs_pyxem.parse(template)

            # nxs_nion = NxEmZippedNionProjectSubParser(entry_id, case.dat[0], verbose=False)
            # nxs_nion.parse(template)
            # TODO::check correct loop through!

            # for dat_instance in case.dat_parser_type:
            #     print(f"Process pieces of information in {dat_instance} tech partner file...")
            #    continue
            #    # elif case.dat_parser_type == "zip":
            #    #     zip_parser = NxEmOmZipEbsdParser(case.dat[0], entry_id)
            #    #     zip_parser.parse(template)
        # em_default_plot_generator(template, 1)

        # run_block = False
        # if run_block is True:
        #     nxs_plt = NxEmDefaultPlotResolver()
        #     # if nxs_mtex is the sub-parser
        #     resolved_path = nxs_plt.nxs_mtex_get_nxpath_to_default_plot(
        #         entry_id, file_paths[0]
        #     )
        #     # print(f"DEFAULT PLOT IS {resolved_path}")
        #     if resolved_path != "":
        #         nxs_plt.annotate_default_plot(template, resolved_path)

        debugging = True  # print(template)
        if debugging:
            print("Reporting state of template before passing to HDF5 writing...")
            for keyword in template.keys():
                print(f"{keyword}: {template[keyword]}")

        print("Forward instantiated template to the NXS writer...")
        toc = perf_counter_ns()
        trg = f"/ENTRY[entry{entry_id}]/profiling"
        template[f"{trg}/current_working_directory"] = getcwd()
        template[f"{trg}/template_filling_elapsed_time"] = np.float64(
            (toc - tic) / 1.0e9
        )
        template[f"{trg}/template_filling_elapsed_time/@units"] = "s"
        return template


# This has to be set to allow the convert script to use this reader.
READER = EMReader
