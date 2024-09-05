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

import os
from time import perf_counter_ns
from typing import Any, List, Tuple
import numpy as np
from pynxtools.dataconverter.readers.base.reader import BaseReader

from pynxtools_em.concepts.nxs_concepts import NxEmAppDef
from pynxtools_em.parsers.conventions import NxEmConventionParser
from pynxtools_em.parsers.hfive_apex import HdfFiveEdaxApexParser
from pynxtools_em.parsers.hfive_bruker import HdfFiveBrukerEspritParser

# from pynxtools_em.parsers.hfive_dreamthreed import HdfFiveDreamThreedParser
from pynxtools_em.parsers.hfive_ebsd import HdfFiveEbsdCommunityParser
from pynxtools_em.parsers.hfive_edax import HdfFiveEdaxOimAnalysisParser

# from pynxtools_em.parsers.hfive_emsoft import HdfFiveEmSoftParser
from pynxtools_em.parsers.hfive_oxford import HdfFiveOxfordInstrumentsParser
from pynxtools_em.parsers.image_png_protochips import ProtochipsPngSetParser
from pynxtools_em.parsers.image_tiff_hitachi import HitachiTiffParser
from pynxtools_em.parsers.image_tiff_jeol import JeolTiffParser
from pynxtools_em.parsers.image_tiff_point_electronic import PointElectronicTiffParser
from pynxtools_em.parsers.image_tiff_tescan import TescanTiffParser
from pynxtools_em.parsers.image_tiff_tfs import TfsTiffParser
from pynxtools_em.parsers.image_tiff_zeiss import ZeissTiffParser
from pynxtools_em.parsers.nxs_mtex import NxEmNxsMTexParser
from pynxtools_em.parsers.nxs_nion import NionProjectParser
from pynxtools_em.parsers.oasis_config import NxEmNomadOasisConfigParser
from pynxtools_em.parsers.oasis_eln import NxEmNomadOasisElnSchemaParser
from pynxtools_em.parsers.rsciio_gatan import RsciioGatanParser
from pynxtools_em.parsers.rsciio_velox import RsciioVeloxParser
from pynxtools_em.utils.io_case_logic import EmUseCaseSelector
from pynxtools_em.utils.nx_atom_types import NxEmAtomTypesResolver
from pynxtools_em.parsers.image_diffraction_pattern_set import (
    DiffractionPatternSetParser,
)

# from pynxtools_em.parsers.zip_ebsd_parser import NxEmOmZipEbsdParser
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
        print(os.getcwd())
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
            nx_em_cfg = NxEmNomadOasisConfigParser(case.cfg[0], entry_id)
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
        if len(case.dat) == 1:  # no sidecar file
            """
            HdfFiveEdaxApexParser,
            # HdfFiveBrukerEspritParser,
            # HdfFiveDreamThreedParser,
            # HdfFiveEbsdCommunityParser,
            # HdfFiveEdaxOimAnalysisParser,
            # HdfFiveEmSoftParser,
            HdfFiveOxfordInstrumentsParser,
            TfsTiffParser,
            ZeissTiffParser,
            PointElectronicTiffParser,
            ProtochipsPngSetParser,
            RsciioVeloxParser,
            RsciioGatanParser,
            NxEmNxsMTexParser,
            NionProjectParser,
            """
            parsers: List[type] = [
                DiffractionPatternSetParser,
            ]
            for parser_type in parsers:
                parser = parser_type(case.dat[0], entry_id, verbose=False)
                parser.parse(template)

            # zip_parser = NxEmOmZipEbsdParser(case.dat[0], entry_id, verbose=False)
            # zip_parser.parse(template)
        if len(case.dat) >= 1:  # optional sidecar file
            tescan = TescanTiffParser(case.dat, entry_id, verbose=False)
            tescan.parse(template)

        if len(case.dat) == 2:  # for sure with sidecar file
            for parser_type in [JeolTiffParser, HitachiTiffParser]:
                parser = parser_type(case.dat, entry_id, verbose=False)
                parser.parse(template)

        nxplt = NxEmDefaultPlotResolver()
        nxplt.priority_select(template)

        smpl = NxEmAtomTypesResolver(entry_id)
        smpl.identify_atomtypes(template)

        debugging = False
        if debugging:
            print("Reporting state of template before passing to HDF5 writing...")
            for keyword, value in template.items():
                print(f"{keyword}____{type(value)}")  # : {template[keyword]}")

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
