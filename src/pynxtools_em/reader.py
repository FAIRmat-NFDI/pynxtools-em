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
"""Parser suite for mapping various types of EM data onto NXem."""

import os
from time import perf_counter_ns
from typing import Any

import numpy as np
from pynxtools.dataconverter.readers.base.reader import BaseReader

from pynxtools_em.concepts.nxs_concepts import NxEmAppDef
from pynxtools_em.examples.custom_reference_frame import (
    NxEmCustomElnCustomReferenceFrame,
)
from pynxtools_em.examples.ebsd_database_eln import NxEmCustomElnEbsdDatabase
from pynxtools_em.examples.ger_berlin_koch_eln import NxEmCustomElnGerBerlinKoch
from pynxtools_em.parsers.hfive_apex import HdfFiveEdaxApexParser
from pynxtools_em.parsers.hfive_bruker import HdfFiveBrukerEspritParser

# from pynxtools_em.parsers.hfive_dreamthreed_legacy import HdfFiveDreamThreedLegacyParser
# from pynxtools_em.parsers.hfive_ebsd import HdfFiveEbsdCommunityParser
from pynxtools_em.parsers.hfive_edax import HdfFiveEdaxOimAnalysisParser

# from pynxtools_em.parsers.hfive_emsoft import HdfFiveEmSoftParser
from pynxtools_em.parsers.hfive_oxford import HdfFiveOxfordInstrumentsParser
from pynxtools_em.parsers.image_diffraction_pattern_set import (
    DiffractionPatternSetParser,
)
from pynxtools_em.parsers.image_png_protochips import ProtochipsPngSetParser
from pynxtools_em.parsers.image_tiff_fei_legacy import FeiLegacyTiffParser
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
from pynxtools_em.utils.custom_logging import logger
from pynxtools_em.utils.io_case_logic import EmUseCaseSelector
from pynxtools_em.utils.nx_atom_types import NxEmAtomTypesResolver

# from pynxtools_em.parsers.zip_ebsd_parser import NxEmOmZipEbsdParser
from pynxtools_em.utils.nx_default_plots import NxEmDefaultPlotResolver


class EMReader(BaseReader):
    """Parse content from file formats of the electron microscopy community."""

    supported_nxdls = ["NXem"]

    def read(
        self,
        template: dict | None = None,
        file_paths: tuple[str] = None,
        objects: tuple[Any] = None,
    ):
        """
        Read method to prepare the template.
        """
        logger.info(os.getcwd())
        tic = perf_counter_ns()
        template.clear()

        # so we need the following input:
        # logical analysis which use case
        # optional data input from a NOMAD Oasis-specific configuration YAML
        # data input from an ELN (using an ELN-agnostic) YAML representation
        # data input from technology partner files (different formats)
        # functionalities for creating NeXus default plots

        entry_id = 1
        logger.debug(
            "Identify information sources (RDM config, ELN, tech-partner files) to deal with..."
        )
        case = EmUseCaseSelector(file_paths)
        if not case.is_valid:
            logger.warning(
                "Such a combination of input-file(s, if any) is not supported !"
            )
            return {}

        if len(case.cfg) == 1:  # optional deployment-specific configurations
            logger.debug("Parse (meta)data coming from a custom NOMAD OASIS RDM...")
            nx_em_cfg = NxEmNomadOasisConfigParser(case.cfg[0], entry_id)
            nx_em_cfg.parse(template)

        if len(case.eln) == 1:
            logger.debug("Parse (meta)data coming from a NOMAD OASIS ELN...")
            nx_em_eln = NxEmNomadOasisElnSchemaParser(case.eln[0], entry_id)
            nx_em_eln.parse(template)

        # difference between the two above-mentioned yaml parsers is that they
        # do not have a header line that identifies them as a specific parser
        # TODO make even better connected to NOMAD
        if len(case.cst) == 1:
            logger.debug("Parse (meta)data coming from a customized ELN...")
            custom_eln_parser_types: list[tuple[str, type]] = [
                ("ger_berlin_koch_group", NxEmCustomElnGerBerlinKoch),
                ("ger_berlin_ebsd_database", NxEmCustomElnEbsdDatabase),
                ("custom_reference_frame", NxEmCustomElnCustomReferenceFrame),
            ]
            for parser_id, parser_type in custom_eln_parser_types:
                if case.cst[0]["parser"] == parser_id:
                    custom_parser = parser_type(case.cst[0]["file"], entry_id)
                    custom_parser.parse(template)

        logger.debug("Parse NeXus appdef-specific content...")
        nxs = NxEmAppDef(entry_id)
        nxs.parse(template)

        logger.debug(
            "Parse and map pieces of information within files from tech partners..."
        )
        # there are parsers with no, optional, or required sidecar file
        if len(case.dat) == 1:
            parsers_no_sidecar_file: list[type] = [
                HdfFiveBrukerEspritParser,
                # HdfFiveDreamThreedLegacyParser,
                # HdfFiveEbsdCommunityParser,
                # HdfFiveEmSoftParser,
                HdfFiveEdaxOimAnalysisParser,
                HdfFiveEdaxApexParser,
                HdfFiveOxfordInstrumentsParser,
                TfsTiffParser,
                ZeissTiffParser,
                PointElectronicTiffParser,
                ProtochipsPngSetParser,
                RsciioVeloxParser,
                RsciioGatanParser,
                NxEmNxsMTexParser,
                NionProjectParser,
                DiffractionPatternSetParser,
                FeiLegacyTiffParser,
            ]
            for parser_type in parsers_no_sidecar_file:
                parser = parser_type(case.dat[0], entry_id)
                parser.parse(template)

        if len(case.dat) >= 1:
            parsers_opt_sidecar: list[type] = [TescanTiffParser]
            for parser_type in parsers_opt_sidecar:
                parser = parser_type(case.dat, entry_id)
                parser.parse(template)

        if len(case.dat) == 2:
            parsers_req_sidecar: list[type] = [JeolTiffParser, HitachiTiffParser]
            for parser_type in parsers_req_sidecar:
                parser = parser_type(case.dat, entry_id)
                parser.parse(template)

        nxplt = NxEmDefaultPlotResolver()
        nxplt.priority_select(template, entry_id)

        sample = NxEmAtomTypesResolver(entry_id)
        sample.identify_atom_types(template)

        debugging = False
        if debugging:
            logger.debug(
                "Reporting state of template before passing to HDF5 writing..."
            )
            for keyword, value in sorted(template.items()):
                logger.info(f"{keyword}____{type(value)}____{value}")

        logger.debug("Forward instantiated template to the NXS writer...")
        toc = perf_counter_ns()
        trg = f"/ENTRY[entry{entry_id}]/profiling/template_filling_elapsed_time"
        template[f"{trg}"] = np.float64((toc - tic) / 1.0e9)
        template[f"{trg}/@units"] = "s"
        return template


# This has to be set to allow the convert script to use this reader.
READER = EMReader
