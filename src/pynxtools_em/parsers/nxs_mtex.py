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
"""Parser mapping concepts and content from *.mtex.h5 files on NXem."""

# *.mtex.h5 is a specific HDF5 file that uses already some but not all relevant
# NeXus class instance to comply with NXem. The format is used for storing processing
# results obtained with the MTex texture toolbox for Matlab into an HDF5 file.
# The format uses NeXus base classes such as NXem_ebsd, NXmicrostructure_ipf
# but given that the processing step in MTex is typically not aware of all context
# in which the data have been collected we here use this parser and normalizer to
# i) add such missing metadata and ii) add further NX_class concept annotations to comply
# with NXem(_ebsd). A practical motivation for this parser was also to decouple the
# processing of the scientific results from the EBSD datasets
# (microstructure representation, IPFs, ODFs, etc.) which is a much more time
# consuming computational step. This also reduces the number of eventual reprocessing
# of the scientific data when just some organizational metadata from the EBSD database
# example demand reprocessing. The processing of the approx 2.4k EBSD datasets took
# approx. 120h on a sixteen-core workstation, datasets were processed sequentially but
# using multi-threading where provided via Matlab or MTex functions

import mmap
import pathlib
import re

import h5py
import numpy as np

from pynxtools_em.utils.config import DEFAULT_VERBOSITY
from pynxtools_em.utils.custom_logging import logger
from pynxtools_em.utils.get_checksum import get_sha256_of_file_content


def hfive_dataset_to_template(
    src: str, src_dst_name: str, trg: str, trg_dst_name: str, obj, template: dict
) -> dict:
    """Interpret data payload behind a node in HDF5 and reformat for template."""
    # dset_name != "" point to HDF5 dataset, == "" point to HDF5 group
    src_path = f"{src}/{src_dst_name}" if src_dst_name != "" else src
    trg_path = f"{trg}/{trg_dst_name}" if trg_dst_name != "" else trg
    if src_path not in obj:
        return template
    if obj[src_path].shape == ():
        value = obj[src_path][()]
        if isinstance(value, bytes):
            template[trg_path] = value.decode("UTF-8")
        else:
            template[trg_path] = value
    elif obj[src_path].shape == (1,):
        template[trg_path] = np.asarray(obj[src_path])[0]
    else:
        if (
            obj[src_path].compression is not None
            and obj[src_path].compression_opts is not None
        ):
            template[trg_path] = {
                "compress": np.asarray(obj[src_path][...], dtype=obj[src_path].dtype),
                "strength": obj[src_path].compression_opts,
            }
        else:
            template[trg_path] = np.asarray(
                obj[src_path][...], dtype=obj[src_path].dtype
            )
    return template


def hfive_attribute_to_template(
    src: str,
    src_dst_name: str,
    src_att_name: str,
    trg: str,
    trg_dst_name: str,
    trg_att_name: str,
    obj,
    template: dict,
) -> dict:
    """Check if named attributed attr_name is attached to dset_name to copy to template."""
    src_path = f"{src}/{src_dst_name}" if src_dst_name != "" else src
    # assume attribute name on the trg and src side are the same, is preharmonized!
    trg_path = (
        f"{trg}/{trg_dst_name}/@{trg_att_name}"
        if trg_dst_name != ""
        else f"{trg}/@{trg_att_name}"
    )
    if src_path not in obj:
        return template
    if src_att_name not in obj[src_path].attrs:
        return template
    template[trg_path] = obj[src_path].attrs[src_att_name]
    return template


class NxEmNxsMTexParser:
    """Map content from *.nxs.mtex files on an instance of NXem."""

    def __init__(
        self, file_path: str = "", entry_id: int = 1, verbose: bool = DEFAULT_VERBOSITY
    ):
        if pathlib.Path(file_path).name.endswith((".mtex.h5", ".mtex.hdf5")):
            self.file_path = file_path
            self.entry_id = entry_id if entry_id > 0 else 1
            self.verbose = verbose
            self.supported = False
            self.check_if_mtex_hfive()
            if not self.supported:
                logger.debug(
                    f"Parser {self.__class__.__name__} finds no content in {file_path} that it supports"
                )
        else:
            self.supported = False

    def check_if_mtex_hfive(self):
        """Check if content matches expected content."""
        self.supported = False
        if self.file_path is None or not self.file_path.endswith(".mtex.h5"):
            return
        try:
            with open(self.file_path, "rb", 0) as file:
                s = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)
                magic = s.read(4)
                if magic != b"\x89HDF":
                    return
        except (OSError, FileNotFoundError):
            logger.warning(f"{self.file_path} either FileNotFound or IOError !")
            return
        # TODO add code which checks for available content
        # the file written out by MTex/Matlab this file is already preformatted for NeXus
        # check if there is relevant payload
        with h5py.File(self.file_path, "r") as h5r:
            for trg in [
                "/entry1/roi1/ebsd/indexing/phase1",
                "/entry1/roi1/ebsd/indexing/roi",
                "/entry1/roi1/ebsd/indexing/microstructure1/crystals",
            ]:
                if trg not in h5r:
                    logger.warning(f"{self.file_path} {trg} not found, file ignored!")
                    return
        self.supported = True

    def parse(self, template: dict) -> dict:
        """Pass because for *.nxs.mtex all data are already in the copy of the output."""
        if self.supported:
            with open(self.file_path, "rb", 0) as fp:
                self.file_path_sha256 = get_sha256_of_file_content(fp)
            logger.info(
                f"Parsing {self.file_path} MTex with SHA256 {self.file_path_sha256} ..."
            )
            # KNOWN BUGS
            # BUG in MTex script still sometimes () values written not as a scalar dataset
            # BUG in MTex script still sometimes booleans mapped to uint8
            # BUG in nxdata model memory should not be unitless
            # BUG in nxdata model NXem roi not recognized?
            self.parse_profiling(template)
            self.parse_mtex_config(template)
            self.parse_various(template)
            self.parse_roi(template)
            self.parse_phases(template)
            self.parse_microstructure(template)
        return template

    def parse_profiling(self, template: dict) -> dict:
        """Parse profiling data."""
        if self.verbose:
            logger.debug("Parse profiling...")
        with h5py.File(self.file_path, "r") as h5r:
            src = "/entry1/profiling"
            trg = f"/ENTRY[entry{self.entry_id}]/profiling/eventID[event_mtex]"
            for dst_name in ["ebsd", "load", "microstructure", "odf", "total"]:
                hfive_dataset_to_template(
                    src,
                    f"{dst_name}_elapsed_time",
                    trg,
                    f"{dst_name}_elapsed_time",
                    h5r,
                    template,
                )
                hfive_attribute_to_template(
                    src,
                    f"{dst_name}_elapsed_time",
                    "units",
                    trg,
                    f"{dst_name}_elapsed_time",
                    "units",
                    h5r,
                    template,
                )
        return template

    def parse_mtex_config(self, template: dict) -> dict:
        """Parse MTex content."""
        if self.verbose:
            logger.debug("Parse MTex content...")
        with h5py.File(self.file_path, "r") as h5r:
            src_prfx = "/entry1/roi1/ebsd/indexing/mtex"
            trg_prfx = f"/ENTRY[entry{self.entry_id}]/roiID[roi1]/ebsd/indexing/microstructureID[microstructure1]/configuration/programID[program1]/mtex"
            trg = trg_prfx
            # template[f"{trg}/@NX_class"] = "NXmicrostructure_mtex_config"
            # for grp_name in [
            #     "conventions",
            #     "plotting",
            #     "miscellaneous",
            #     "numerics",
            #     "system",
            # ]:
            #     template[f"{trg}/COLLECTION[{grp_name}]/@NX_class"] = "NXcollection"

            src = f"{src_prfx}/conventions"
            trg = f"{trg_prfx}/COLLECTION[conventions]"
            for dst_name in [
                # "a_axis_direction",
                # "b_axis_direction",
                "euler_angle",
                # "x_axis_direction",
                # "z_axis_direction",
            ]:
                template[f"{trg}/euler_angle"] = "bunge"  # BUG in MTex script
                # hfive_dataset_to_template(src, dst_name, trg, dst_name, h5r, template)

            """
            src = f"{src_prfx}/plotting"
            trg = f"{trg_prfx}/COLLECTION[plotting]"
            for dst_name in [
                "arrow_character",
                "color_map",
                "color_palette",
                "default_map",
                "degree_character",
                "figure_size",
                "font_size",
                "hit_test",
                "inner_plot_spacing",
                "marker",
                "marker_edge_color",
                "marker_face_color",
                "marker_size",
                "outer_plot_spacing",
                "pf_anno_fun_hdl",
                "show_coordinates",
                "show_micron_bar",
            ]:
                hfive_dataset_to_template(src, dst_name, trg, dst_name, h5r, template)
            """

            src = f"{src_prfx}/numerics"
            trg = f"{trg_prfx}/COLLECTION[numerics]"
            for dst_name in [
                "eps",
                "fft_accuracy",
                "max_sone_bandwidth",
                "max_stwo_bandwidth",
                "max_sothree_bandwidth",
            ]:
                hfive_dataset_to_template(src, dst_name, trg, dst_name, h5r, template)

            src = f"{src_prfx}/miscellaneous"
            trg = f"{trg_prfx}/COLLECTION[miscellaneous]"
            for dst_name in [
                "inside_poly",
                "methods_advise",
                "mosek",
                "stop_on_symmetry_mismatch",
            ]:
                template[f"{trg}/{dst_name}"] = bool(h5r[f"{src}/{dst_name}"])
            # BUG in MTex script, does not write pure HDF5 booleans but promotes these to uint8
            for dst_name in [
                "text_interpreter",
                "voronoi_method",
            ]:
                hfive_dataset_to_template(src, dst_name, trg, dst_name, h5r, template)

            src = f"{src_prfx}/system"
            trg = f"{trg_prfx}/COLLECTION[system]"  # "memory", "save_to_file"
            for dst_name in ["memory"]:
                hfive_dataset_to_template(src, dst_name, trg, dst_name, h5r, template)
                hfive_attribute_to_template(
                    src, dst_name, "unit", trg, dst_name, "units", h5r, template
                )  # BUG on the MTex script side!

            for idx in [1, 2]:
                src = f"{src_prfx}/program{idx}"
                trg = f"/ENTRY[entry{self.entry_id}]/profiling/eventID[event_mtex]/PROGRAM[program{idx}]"
                for dst_name in ["program"]:
                    hfive_dataset_to_template(
                        src, dst_name, trg, dst_name, h5r, template
                    )
                    hfive_attribute_to_template(
                        src,
                        dst_name,
                        "version",
                        trg,
                        dst_name,
                        "version",
                        h5r,
                        template,
                    )
        return template

    def parse_various(self, template: dict) -> dict:
        """Parse various quantities."""
        if self.verbose:
            logger.debug("Parse various...")
        with h5py.File(self.file_path, "r") as h5r:
            src = "/entry1/roi1/ebsd/indexing"
            trg = f"/ENTRY[entry{self.entry_id}]/roiID[roi1]/ebsd/indexing"
            for dst_name in [
                "indexing_rate",
                "number_of_scan_points",
                "pixel_shape",
                "pixel_unit_cell",
            ]:
                hfive_dataset_to_template(src, dst_name, trg, dst_name, h5r, template)
                hfive_attribute_to_template(
                    src, dst_name, "units", trg, dst_name, "units", h5r, template
                )
        return template

    def parse_roi(self, template: dict) -> dict:
        """Parse data for the region-of-interest default plot."""
        if self.verbose:
            logger.debug("Parse ROI default plot...")
        with h5py.File(self.file_path, "r") as h5r:
            src = "/entry1/roi1/ebsd/indexing/roi"
            trg = f"/ENTRY[entry{self.entry_id}]/roiID[roi1]/ebsd/indexing/roi"
            for att_name in ["axes", "signal"]:
                hfive_attribute_to_template(
                    src, "", att_name, trg, "", att_name, h5r, template
                )
            for att_name in ["axis_x_indices", "axis_y_indices"]:
                hfive_attribute_to_template(
                    src,
                    "",
                    att_name,
                    trg,
                    "",
                    f"AXISNAME_indices[@{att_name}]",
                    h5r,
                    template,
                )

            # process payload of the NXdata instance
            for dst_name in ["axis_x", "axis_y"]:
                hfive_dataset_to_template(src, dst_name, trg, dst_name, h5r, template)
                for attr in ["long_name", "units"]:
                    hfive_attribute_to_template(
                        src,
                        dst_name,
                        attr,
                        trg,
                        dst_name,
                        attr,
                        h5r,
                        template,
                    )
            for dst_name in ["data"]:
                hfive_dataset_to_template(src, dst_name, trg, dst_name, h5r, template)
                for att_name in [
                    "CLASS",
                    "IMAGE_VERSION",
                    "SUBCLASS_VERSION",
                    "long_name",
                ]:
                    hfive_attribute_to_template(
                        src, dst_name, att_name, trg, dst_name, att_name, h5r, template
                    )
            for dst_name in ["descriptor", "title"]:
                hfive_dataset_to_template(src, dst_name, trg, dst_name, h5r, template)
        return template

    def parse_phases(self, template: dict) -> dict:
        """Parse data for the phase-specific content."""
        if self.verbose:
            logger.debug("Parse phases...")
        with h5py.File(self.file_path, "r") as h5r:
            src_prfx = "/entry1/roi1/ebsd/indexing"
            trg_prfx = f"/ENTRY[entry{self.entry_id}]/roiID[roi1]/ebsd/indexing/phaseID"
            if src_prfx not in h5r:
                return template
            for grp_name in h5r[src_prfx]:
                if re.match("phase[0-9]+", grp_name) is None:
                    continue
                src = f"{src_prfx}/{grp_name}"
                trg = f"{trg_prfx}[{grp_name}]"  # endswith phaseID[phase0]
                for dst_name in [
                    "index_offset",
                    "name",
                    "number_of_scan_points",
                ]:
                    hfive_dataset_to_template(
                        src, dst_name, trg, dst_name, h5r, template
                    )
                if grp_name == "phase0":
                    continue  # no further data for notIndexed phase
                src = f"{src_prfx}/{grp_name}/unit_cell"
                trg = f"{trg_prfx}[{grp_name}]/unit_cell"
                for dst_name in [
                    "a",
                    "alpha",
                    "b",
                    "beta",
                    "c",
                    "gamma",
                    "point_group",
                ]:
                    if dst_name != "point_group":
                        hfive_dataset_to_template(
                            src, dst_name, trg, dst_name, h5r, template
                        )
                        hfive_attribute_to_template(
                            src,
                            dst_name,
                            "units",
                            trg,
                            dst_name,
                            "units",
                            h5r,
                            template,
                        )
                    else:
                        hfive_dataset_to_template(
                            src, dst_name, trg, dst_name, h5r, template
                        )
                for idx in [1]:  # skip 2, 3
                    src = f"{src_prfx}/{grp_name}/ipf{idx}"
                    trg = f"{trg_prfx}[{grp_name}]/ipfID[ipf{idx}]"
                    self.parse_phase_ipf(src, trg, h5r, template)
                for idx in [1]:
                    src = f"{src_prfx}/{grp_name}/odf{idx}"
                    trg = f"{trg_prfx}[{grp_name}]/odfID[odf{idx}]"
                    self.parse_phase_odf(src, trg, h5r, template)
        return template

    def parse_microstructure(self, template: dict) -> dict:
        """Parse microstructure geometry."""
        if self.verbose:
            logger.debug("Parse microstructure geometry...")
        with h5py.File(self.file_path, "r") as h5r:
            src_prfx = "/entry1/roi1/ebsd/indexing/microstructure1"
            trg_prfx = f"/ENTRY[entry{self.entry_id}]/roiID[roi1]/ebsd/indexing/microstructureID[microstructure1]"

            src = src_prfx
            trg = f"{trg_prfx}/configuration"
            for dst_name in ["dimensionality"]:
                hfive_dataset_to_template(src, dst_name, trg, dst_name, h5r, template)

            src = f"{src_prfx}/cg_point"
            trg = f"{trg_prfx}/points"
            for dst_name in ["cardinality", "dimensionality", "index_offset"]:
                hfive_dataset_to_template(src, dst_name, trg, dst_name, h5r, template)
            for dst_name in ["position"]:
                hfive_dataset_to_template(src, dst_name, trg, dst_name, h5r, template)
                hfive_attribute_to_template(
                    src, dst_name, "units", trg, dst_name, "units", h5r, template
                )

            src = f"{src_prfx}/cg_polyline"
            trg = f"{trg_prfx}/polylines"
            for dst_name in [
                "cardinality",
                "dimensionality",
                "index_offset",
                "number_of_vertices",
            ]:
                hfive_dataset_to_template(src, dst_name, trg, dst_name, h5r, template)
            for dst_name in ["length"]:
                hfive_dataset_to_template(src, dst_name, trg, dst_name, h5r, template)
                hfive_attribute_to_template(
                    src, dst_name, "units", trg, dst_name, "units", h5r, template
                )
            # BUG in MTex script indices_interfaces should be indices_interface
            for dst_name in ["indices"]:
                hfive_dataset_to_template(
                    src,
                    f"{dst_name}_interfaces",
                    trg,
                    f"{dst_name}_interface",
                    h5r,
                    template,
                )
                hfive_attribute_to_template(
                    src,
                    f"{dst_name}_interfaces",
                    "use_these",
                    trg,
                    f"{dst_name}_interface",
                    "depends_on",
                    h5r,
                    template,
                )  # BUG in the MTex script use_these should be depends_on
            for dst_name in ["polylines"]:
                hfive_dataset_to_template(src, dst_name, trg, dst_name, h5r, template)
                hfive_attribute_to_template(
                    src,
                    dst_name,
                    "use_these",
                    trg,
                    dst_name,
                    "depends_on",
                    h5r,
                    template,
                )  # BUG in the MTex script use_these should be depends_on

            src = f"{src_prfx}/configuration"
            trg = f"{trg_prfx}/configuration"
            template[f"{trg}/algorithm"] = (
                "disorientation_clustering"  # BUG in MTex script
            )
            for dst_name in ["comments", "discretization_threshold"]:
                hfive_dataset_to_template(src, dst_name, trg, dst_name, h5r, template)
            template[f"{trg}/disorientation_threshold"] = np.float64(15.0)
            template[f"{trg}/disorientation_threshold/@units"] = "°"
            # for dst_name in ["disorientation_threshold"]:
            #     hfive_dataset_to_template(src, dst_name, trg, dst_name, h5r, template)
            #     hfive_attribute_to_template(
            #         src, dst_name, "units", trg, dst_name, "units", h5r, template
            #     )
            # not stored by the MTex script
            # https://github.com/FAIRmat-NFDI/mtex/blob/91ef5185388419acdb75559fd4252099dcbf24de/
            # userScripts/FAIRmat-NFDI/nexus_write_ebsd_microstructure.m#L25

            src = f"{src_prfx}/crystals"
            trg = f"{trg_prfx}/crystals"
            for dst_name in [
                "area_by_pixel",
                "boundary_contact",
                "index_offset",
                "indices_phase",
                "number_of_crystals",
            ]:
                hfive_dataset_to_template(src, dst_name, trg, dst_name, h5r, template)
            if f"{src}/area_by_mtex" in h5r:
                template[f"{trg}/area"] = {
                    "compress": h5r[f"{src}/area_by_mtex"][...],
                    "strength": h5r[f"{src}/area_by_mtex"].compression_opts,
                }
                template[f"{trg}/area/@units"] = "micrometer ** 2"  # BUG in MTex
            # TODO orientation

            src = f"{src_prfx}/interfaces"
            trg = f"{trg_prfx}/interfaces"
            for dst_name in ["index_offset", "number_of_interfaces", "indices_phase"]:
                hfive_dataset_to_template(src, dst_name, trg, dst_name, h5r, template)
            for dst_name in ["indices_crystal"]:
                hfive_dataset_to_template(src, dst_name, trg, dst_name, h5r, template)
                hfive_attribute_to_template(
                    src,
                    dst_name,
                    "use_these",
                    trg,
                    dst_name,
                    "depends_on",
                    h5r,
                    template,
                )
            for dst_name in ["indices"]:
                hfive_dataset_to_template(
                    src,
                    f"{dst_name}_polylines",
                    trg,
                    f"{dst_name}_polyline",
                    h5r,
                    template,
                )
                hfive_attribute_to_template(
                    src,
                    f"{dst_name}_polylines",
                    "use_these",
                    trg,
                    f"{dst_name}_polyline",
                    "depends_on",
                    h5r,
                    template,
                )
            # TODO misorientation

            src = f"{src_prfx}/triple_junctions"
            trg = f"{trg_prfx}/triple_junctions"
            for dst_name in ["index_offset", "number_of_junctions"]:
                hfive_dataset_to_template(src, dst_name, trg, dst_name, h5r, template)
            for dst_name in ["crystal", "polyline", "interface"]:
                hfive_dataset_to_template(
                    src,
                    f"indices_{dst_name}",
                    trg,
                    h5r,
                    f"indices_{dst_name}",
                    template,
                )
                hfive_attribute_to_template(
                    src,
                    f"indices_{dst_name}",
                    "use_these",
                    trg,
                    f"indices_{dst_name}",
                    "depends_on",
                    h5r,
                    template,
                )

        return template

    def parse_phase_ipf(
        self, src_prfx: str, trg_prfx: str, h5r, template: dict
    ) -> dict:
        """Parse phase-specific inverse pole figure mapping."""
        src = src_prfx
        trg = trg_prfx
        for dst_name in ["color_model", "projection_direction"]:
            hfive_dataset_to_template(src, dst_name, trg, dst_name, h5r, template)

        for fig in ["map", "legend"]:
            src = f"{src_prfx}/{fig}"
            trg = f"{trg_prfx}/{fig}"
            for att_name in ["axes", "signal"]:
                hfive_attribute_to_template(
                    src, "", att_name, trg, "", att_name, h5r, template
                )
            for att_name in ["axis_x_indices", "axis_y_indices"]:
                hfive_attribute_to_template(
                    src,
                    "",
                    att_name,
                    trg,
                    "",
                    f"AXISNAME_indices[@{att_name}]",
                    h5r,
                    template,
                )
            for dst_name in ["axis_x", "axis_y"]:
                hfive_dataset_to_template(src, dst_name, trg, dst_name, h5r, template)
                for attr in ["long_name", "units"]:
                    if not (fig == "legend" and attr == "units"):
                        hfive_attribute_to_template(
                            src,
                            dst_name,
                            attr,
                            trg,
                            dst_name,
                            attr,
                            h5r,
                            template,
                        )
            for dst_name in ["data"]:
                hfive_dataset_to_template(src, dst_name, trg, dst_name, h5r, template)
                for att_name in [
                    "CLASS",
                    "IMAGE_VERSION",
                    "SUBCLASS_VERSION",
                    "long_name",
                ]:
                    hfive_attribute_to_template(
                        src, "data", att_name, trg, "data", att_name, h5r, template
                    )
            for dst_name in ["title"]:
                hfive_dataset_to_template(src, dst_name, trg, dst_name, h5r, template)
        return template

    def parse_phase_odf(
        self, src_prfx: str, trg_prfx: str, h5r, template: dict
    ) -> dict:
        """Parse phase-specific orientation distribution function."""
        src = f"{src_prfx}/characteristics"
        trg = f"{trg_prfx}/PROCESS[characteristics]"
        for dst_name in ["texture_index"]:
            hfive_dataset_to_template(src, dst_name, trg, dst_name, h5r, template)

        src = f"{src_prfx}/configuration"
        trg = f"{trg_prfx}/configuration"
        for dst_name in ["kernel_halfwidth", "resolution"]:
            hfive_dataset_to_template(src, dst_name, trg, dst_name, h5r, template)
            hfive_attribute_to_template(
                src, dst_name, "units", trg, dst_name, "units", h5r, template
            )
        for dst_name in [
            "crystal_symmetry_point_group",
            "specimen_symmetry_point_group",
            "kernel_name",
        ]:
            hfive_dataset_to_template(src, dst_name, trg, dst_name, h5r, template)

        src = f"{src_prfx}/phi_two_plot"
        trg = f"{trg_prfx}/phi_two_plot"
        for att_name in [
            "axes",
            "signal",
        ]:
            hfive_attribute_to_template(
                src, "", att_name, trg, "", att_name, h5r, template
            )
        for att_name in [
            "capital_phi_indices",
            "varphi_one_indices",
            "varphi_two_indices",
        ]:
            hfive_attribute_to_template(
                src,
                "",
                att_name,
                trg,
                "",
                f"AXISNAME_indices[@{att_name}]",
                h5r,
                template,
            )

        for dst_name in ["intensity"]:
            hfive_dataset_to_template(src, dst_name, trg, dst_name, h5r, template)
            for att_name in [
                "CLASS",
                "IMAGE_VERSION",
                "SUBCLASS_VERSION",
                "long_name",
            ]:
                hfive_attribute_to_template(
                    src, dst_name, att_name, trg, dst_name, att_name, h5r, template
                )
        # axes
        for dst_name in ["capital_phi", "varphi_one", "varphi_two"]:
            hfive_dataset_to_template(src, dst_name, trg, dst_name, h5r, template)
            for attr in ["long_name", "units"]:
                hfive_attribute_to_template(
                    src,
                    dst_name,
                    attr,
                    trg,
                    dst_name,
                    attr,
                    h5r,
                    template,
                )
        for dst_name in ["title"]:
            hfive_dataset_to_template(src, dst_name, trg, dst_name, h5r, template)
        return template
