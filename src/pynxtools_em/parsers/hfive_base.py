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
"""Parent class for all tech partner-specific HDF5 parsers for mapping on NXem."""

from typing import Dict, List

import h5py
import numpy as np
import yaml

from pynxtools_em.concepts.hfive_concepts import (
    IS_ATTRIBUTE,
    IS_COMPOUND_DATASET,
    IS_FIELD_IN_COMPOUND_DATASET,
    IS_GROUP,
    IS_REGULAR_DATASET,
    Concept,
)
from pynxtools_em.utils.custom_logging import logger
from pynxtools_em.utils.get_checksum import get_sha256_of_bytes_object

# the base parser implements the processing of standardized orientation maps via
# the pyxem software package from the electron microscopy community
# specifically so-called NeXus default plots are generated to add RDMS-relevant
# information to the NeXus file which supports scientists with judging the potential
# value of the dataset in the context of them using research data management systems (RDMS)
# in effect this parser is the partner of the MTex parser for all those file formats
# which are HDF5 based and which (at the time of working on this example Q3/Q4 2023)
# where not supported my MTex
# with offering this parser we also would like to embrace and acknowledge the efforts
# of other electron microscopists (like the pyxem team, hyperspy etc.) and their work
# towards software tools which are complementary to the MTex texture toolbox
# one could have also implemented the HDF5 parsing inside MTex but we leave this as a
# task for the community and instead focus here on showing a more diverse example
# towards more interoperability between the different tools in the community

NXEM_VOLATILE_NAMED_HDF_PATHS = (
    "/@HDF5_Version",
    "/@NeXus_release",
    "/@file_time",
    "/@file_update_time",
    "entry1/definition/@version",
    "entry1/profiling/program1/program/@version",
    "entry1/profiling/template_filling_elapsed_time",
    # "entry1/profiling/template_filling_elapsed_time/@units"
)
NXEM_VOLATILE_SUFFIX_HDF_PATHS = (
    "@axes",  # as these are stored as by default as byte objects vlen string array
    "file_name",  # cuz if these include the full path the absolute path may differ
)


class HdfFiveBaseParser:
    def __init__(
        self, file_path: str = "", hashing: bool = True, verbose: bool = False
    ):
        # tech_partner the company which designed this format
        # schema_name the specific name of the family of schemas supported by this reader
        # schema_version the specific version(s) supported by this reader
        # writer_name the specific name of the tech_partner's (typically proprietary) software
        #   with which an instance of a file formatted according to schema_name and schema_version
        #   was written e.g. Oxford Instruments AZTec software in some version may generate
        #   an instance of a file whose schema belongs to the H5OINA family of HDF5 container formats
        #   specifically using version 5
        if file_path:
            self.file_path = file_path
        self.prfx: str = ""
        self.tmp: Dict = {}
        self.source: str = ""
        # collection of instance path
        self.groups: Dict = {}
        self.datasets: Dict = {}
        self.attributes: Dict = {}
        self.instances: Dict = {}
        # collection of template
        self.template_groups: List = []
        self.template_datasets: List = []
        self.template_attributes: List = []
        self.templates: Dict = {}
        self.h5r = None
        self.is_hdf = True  # TODO::check if HDF5 file using magic cookie
        self.hashing = hashing
        self.verbose = verbose

    def init_cache(self, ckey: str) -> str:
        """Init a new cache for normalized EBSD data if not existent."""
        # purpose of the cache is to hold normalized information
        if ckey not in self.tmp:
            self.tmp[ckey] = {}  # reset to {} upon incomplete collection of the cache
            return ckey
        else:
            raise ValueError(f"Existent named cache {ckey} must not be overwritten !")

    def clear_cache(self, ckey: str):
        if ckey in self.tmp:
            self.tmp.pop(ckey)

    def open(self):
        if self.h5r is None:
            self.h5r = h5py.File(self.file_path, "r")

    def close(self):
        if self.h5r is not None:
            self.h5r.close()
            self.h5r = None

    def __call__(self, node_name, h5obj):
        # only h5py datasets have dtype attribute, so we can search on this
        if isinstance(h5obj, h5py.Dataset):
            if node_name not in self.datasets:
                if hasattr(h5obj, "dtype"):
                    if hasattr(h5obj.dtype, "fields") and hasattr(h5obj.dtype, "names"):
                        if h5obj.dtype.names is not None:
                            self.datasets[node_name] = (
                                "IS_COMPOUND_DATASET",
                                type(h5obj),
                                np.shape(h5obj),
                                h5obj[0],
                                f"{h5obj.dtype}__{get_sha256_of_bytes_object(h5obj[()])}"
                                if self.hashing
                                else "",
                            )
                            self.instances[node_name] = Concept(
                                node_name,
                                None,
                                None,
                                type(h5obj),
                                np.shape(h5obj),
                                None,
                                hdf_type="compound_dataset",
                            )
                            n_dims = len(np.shape(h5obj))
                            if n_dims == 1:
                                for name in h5obj.dtype.names:
                                    self.datasets[f"{node_name}/#{name}"] = (
                                        "IS_FIELD_IN_COMPOUND_DATASET",
                                        h5obj.fields(name)[()].dtype,
                                        np.shape(h5obj.fields(name)[()]),
                                        h5obj.fields(name)[0],
                                        f"{h5obj.fields(name)[()].dtype}__{get_sha256_of_bytes_object(h5obj.fields(name)[()])}"
                                        if self.hashing
                                        else "",
                                    )
                                    self.instances[f"{node_name}/{name}"] = Concept(
                                        node_name,
                                        None,
                                        None,
                                        h5obj.fields(name)[()].dtype,
                                        np.shape(h5obj.fields(name)[()]),
                                        None,
                                        hdf_type="compound_dataset_entry",
                                    )
                            else:
                                raise ValueError(
                                    f"Unknown formatting of an h5py.Dataset, inspect {node_name} !"
                                )
                        else:  # h5obj.dtype.names is a tuple of struct variable names
                            n_dims = len(np.shape(h5obj))
                            if n_dims == 0:
                                self.datasets[node_name] = (
                                    "IS_REGULAR_DATASET",
                                    type(h5obj),
                                    np.shape(h5obj),
                                    h5obj[()],
                                    f"{h5obj.ndim}__{h5obj.dtype}__{get_sha256_of_bytes_object(h5obj[()])}"
                                    if self.hashing
                                    else "",
                                )
                                self.instances[node_name] = Concept(
                                    node_name,
                                    None,
                                    None,
                                    type(h5obj),
                                    np.shape(h5obj),
                                    None,
                                    hdf_type="regular_dataset",
                                )
                            elif n_dims == 1:
                                if 0 not in np.shape(h5obj):
                                    self.datasets[node_name] = (
                                        "IS_REGULAR_DATASET",
                                        type(h5obj),
                                        np.shape(h5obj),
                                        h5obj[0],
                                        f"{h5obj.ndim}__{h5obj.dtype}__{get_sha256_of_bytes_object(h5obj[()])}"
                                        if self.hashing
                                        else "",
                                    )
                                    self.instances[node_name] = Concept(
                                        node_name,
                                        None,
                                        None,
                                        type(h5obj),
                                        np.shape(h5obj),
                                        None,
                                        hdf_type="regular_dataset",
                                    )
                                else:
                                    self.datasets[node_name] = (
                                        "IS_REGULAR_DATASET",
                                        type(h5obj),
                                        np.shape(h5obj),
                                        h5obj[()],
                                        f"{h5obj.ndim}__{h5obj.dtype}__{get_sha256_of_bytes_object(h5obj[()])}"
                                        if self.hashing
                                        else "",
                                    )
                                    self.instances[node_name] = Concept(
                                        node_name,
                                        None,
                                        None,
                                        type(h5obj),
                                        np.shape(h5obj),
                                        None,
                                        hdf_type="regular_dataset",
                                    )
                            elif n_dims == 2:
                                self.datasets[node_name] = (
                                    "IS_REGULAR_DATASET",
                                    type(h5obj),
                                    np.shape(h5obj),
                                    h5obj[0, 0],
                                    f"{h5obj.ndim}__{h5obj.dtype}__{get_sha256_of_bytes_object(h5obj[()])}"
                                    if self.hashing
                                    else "",
                                )
                                self.instances[node_name] = Concept(
                                    node_name,
                                    None,
                                    None,
                                    type(h5obj),
                                    np.shape(h5obj),
                                    None,
                                    hdf_type="regular_dataset",
                                )
                            elif n_dims == 3:
                                self.datasets[node_name] = (
                                    "IS_REGULAR_DATASET",
                                    type(h5obj),
                                    np.shape(h5obj),
                                    h5obj[0, 0, 0],
                                    f"{h5obj.ndim}__{h5obj.dtype}__{get_sha256_of_bytes_object(h5obj[()])}"
                                    if self.hashing
                                    else "",
                                )
                                self.instances[node_name] = Concept(
                                    node_name,
                                    None,
                                    None,
                                    type(h5obj),
                                    np.shape(h5obj),
                                    None,
                                    hdf_type="regular_dataset",
                                )
                            else:
                                self.datasets[node_name] = (
                                    "IS_REGULAR_DATASET",
                                    type(h5obj),
                                    np.shape(h5obj),
                                    None,
                                    f"{h5obj.ndim}__{h5obj.dtype}__{get_sha256_of_bytes_object(h5obj[()])}"
                                    if self.hashing
                                    else "",
                                    "Inspect in HDF5 file directly!",
                                )
                                self.instances[node_name] = Concept(
                                    node_name,
                                    None,
                                    None,
                                    type(h5obj),
                                    np.shape(h5obj),
                                    None,
                                    hdf_type="regular_dataset",
                                )
                    else:
                        raise ValueError(
                            f"hasattr(h5obj.dtype, 'fields') and hasattr("
                            f"h5obj.dtype, 'names') failed, inspect {node_name} !"
                        )
                else:
                    raise ValueError(
                        f"hasattr(h5obj, dtype) failed, inspect {node_name} !"
                    )
        else:
            if node_name not in self.groups:
                self.groups[node_name] = "IS_GROUP"
                self.instances[node_name] = Concept(
                    node_name,
                    None,
                    None,
                    type(h5obj),
                    np.shape(h5obj),
                    None,
                    hdf_type="group",
                )
        # if hasattr(h5obj, 'dtype') and not node_name in self.metadata:
        #     self.metadata[node_name] = ["dataset"]

    def get_attribute_data_structure(self, prefix, src_dct):
        # trg_dct is self.attributes
        for key, val in src_dct.items():
            if f"{prefix}/@{key}" not in self.attributes:
                if isinstance(val, str):
                    self.attributes[f"{prefix}/@{key}"] = (
                        "IS_ATTRIBUTE",
                        type(val),
                        np.shape(val),
                        str,
                        val,
                        f"str__{get_sha256_of_bytes_object(val.encode('utf-8'))}"
                        if self.hashing
                        else "",
                    )
                    self.instances[f"{prefix}/{key}"] = Concept(
                        f"{prefix}/@{key}",
                        None,
                        None,
                        type(val),
                        np.shape(val),
                        None,
                        hdf_type="attribute",
                    )
                elif hasattr(val, "dtype"):
                    self.attributes[f"{prefix}/@{key}"] = (
                        "IS_ATTRIBUTE",
                        type(val),
                        np.shape(val),
                        val.dtype,
                        val,
                        f"{val.dtype}__{get_sha256_of_bytes_object(bytes(val))}"
                        if self.hashing
                        else "",
                    )
                    self.instances[f"{prefix}/{key}"] = Concept(
                        f"{prefix}/@{key}",
                        None,
                        None,
                        type(val),
                        np.shape(val),
                        None,
                        hdf_type="attribute",
                    )
                else:
                    raise ValueError(
                        f"Unknown formatting of an attribute, inspect {prefix}/@{key} !"
                    )

    def get_content(self):
        """Walk recursively through the file to get content."""
        # if self.h5r is not None:  # if self.file_path is not None:
        with h5py.File(self.file_path, "r") as self.h5r:
            # parse the root header of the file, which typically has time data
            self.get_attribute_data_structure("", dict(self.h5r["/"].attrs))
            # automatic timestamping of objects in the HDF5 tree has already
            # been deactivated since several years

            # first step visit all groups and datasets recursively
            # get their full path within the HDF5 file
            self.h5r.visititems(self)
            # second step visit all these and get their attributes
            for h5path, h5ifo in self.groups.items():
                self.get_attribute_data_structure(h5path, dict(self.h5r[h5path].attrs))
            for h5path, h5ifo in self.datasets.items():
                if (
                    h5path.count("#") == 0
                ):  # skip resolved fields in compound data types
                    self.get_attribute_data_structure(
                        h5path, dict(self.h5r[h5path].attrs)
                    )

    def store_hashes(self, blacklist_by_key: List, blacklist_by_suffix: List, **kwargs):
        """Generate yaml file with sorted list of HDF5 grp, dst, and attrs

        including their datatype and SHA256 checksum computed from the each nodes data.
        This yaml file can be useful for unit tests of different NeXus files
        when differences in timestamps are expected but should not trigger
        the test to fail. The blacklist allows to exclude those HDF5 paths
        that should not be included in the yaml file."""
        # object timestamps are low-level features of HDF5 that if activated
        # would still render HDF5 files binarily different even though each
        # entry and payload in the content tree is the same binary content
        # however, these internal library administrative timestamps have been
        # are in newer versions of hdf5 deactivated by default see here:
        # https://github.com/h5py/h5py/issues/1953
        # https://forum.hdfgroup.org/t/object-timestamps-useful-or-not/8901/7
        # h5diff does not allow such a lean and customizable blacklist of nodes
        # to the best of my knowledge hence comparing two versions of HDF5 files
        # with h5diff is useful but if done in unit testing typically generate
        # two long text outputs via stdout that are maybe more difficult to
        # compare
        #
        # blacklist = ["@axes"
        #              "/@HDF5_version",
        #              "/@NX_class",
        #              "/@NeXus_repository",
        #              "/@NeXus_version",
        #              "/@default",
        #              "/@file_name",
        #              "/@file_time",
        #              "/@h5py_version"]
        hashes: Dict[str, str] = {}
        for key, ifo in self.groups.items():
            if key not in blacklist_by_key and not key.endswith(blacklist_by_suffix):
                hashes[key] = "is_a_grp"
        for key, ifo in self.datasets.items():
            if key not in blacklist_by_key and not key.endswith(blacklist_by_suffix):
                hashes[key] = f"is_a_dst__{ifo[-1]}"
        for key, ifo in self.attributes.items():
            if key not in blacklist_by_key and not key.endswith(blacklist_by_suffix):
                hashes[key] = f"is_a_attr__{ifo[-1]}"
        with open(
            kwargs.get(
                "file_path",
                f"""{self.file_path}.sha256{kwargs.get("suffix", "")}.yaml""",
            ),
            "w",
        ) as fp:
            yaml.dump(hashes, fp, default_flow_style=False, sort_keys=True)

    def report_groups(self):
        logger.info(f"{self.file_path} contains the following groups:")
        for key, ifo in self.groups.items():
            logger.info(f"{key}, {ifo}")

    def report_datasets(self):
        logger.info(f"{self.file_path} contains the following datasets:")
        for key, ifo in self.datasets.items():
            logger.info(f"{key}, {ifo}")

    def report_attributes(self):
        logger.info(f"{self.file_path} contains the following attributes:")
        for key, ifo in self.attributes.items():
            logger.info(f"{key}, {ifo}")

    def report_content(self):
        self.report_groups()
        self.report_datasets()
        self.report_attributes()

    def store_report(
        self,
        store_instances=False,
        store_instances_templatized=True,
        store_templates=False,
    ):
        if store_instances is True:
            logger.info(
                f"Storing analysis results in "
                f"{self.file_path[self.file_path.rfind('/') + 1 :]}."
                f"EbsdHdfFileInstanceNames.txt..."
            )
            with open(f"{self.file_path}.EbsdHdfFileInstanceNames.txt", "w") as txt:
                for instance_name, concept in self.instances.items():
                    txt.write(
                        f"{instance_name}, hdf: {concept.hdf}, "
                        f"type: {concept.dtype}, shape: {concept.shape}\n"
                    )

        if store_instances_templatized is True:
            logger.info(
                f"Storing analysis results in "
                f"{self.file_path[self.file_path.rfind('/') + 1 :]}"
                f".EbsdHdfFileInstanceNamesTemplatized.txt..."
            )
            with open(
                f"{self.file_path}.EbsdHdfFileInstanceNamesTemplatized.txt", "w"
            ) as txt:
                for instance_name, concept in self.instances.items():
                    txt.write(f"{instance_name}, hdf: {concept.hdf}\n")

        if store_templates is True:
            logger.info(
                f"Storing analysis results in "
                f"{self.file_path[self.file_path.rfind('/') + 1 :]}"
                f".EbsdHdfFileTemplateNames.txt..."
            )
            with open(f"{self.file_path}.EbsdHdfFileTemplateNames.txt", "w") as txt:
                for template_name, concept in self.templates.items():
                    txt.write(
                        f"{template_name}, hdf: {concept.hdf}, "
                        f"type: {concept.dtype}, shape: {concept.shape}\n"
                    )

    def get_attribute_value(self, h5path):
        if self.h5r is not None:
            if h5path in self.attributes:
                trg, attrnm = h5path.split("@")
                # with (self.file_path, "r") as h5r:
                obj = self.h5r[trg].attrs[attrnm]
                if isinstance(obj, np.bytes_):
                    return obj[0].decode("utf8")
                else:
                    return obj
        return None

    def get_dataset_value(self, h5path):
        if self.h5r is not None:
            if h5path in self.datasets:
                if self.datasets[h5path][0] == "IS_REGULAR_DATASET":
                    # with (self.file_path, "r") as h5r:
                    obj = self.h5r[h5path]
                    if isinstance(obj[0], np.bytes_):
                        return obj[0].decode("utf8")
                    else:
                        return obj  # [()].decode("utf8")
            # implement get the entire compound dataset
            if h5path.count("#") == 1:
                # with (self.file_path, "r") as h5r:
                obj = self.h5r[h5path[0 : h5path.rfind("#")]]
                return obj.fields(h5path[h5path.rfind("#") + 1 :])[:]
            return None

    def get_value(self, h5path):
        """Return tuple of normalized regular ndarray for h5path or None."""
        # h5path with exactly one @ after rfind("/") indicating an attribute
        # h5path with exactly one # after rfind("/") indicating a field name in compound type
        # most likely h5path names a dataset
        if h5path.count("@") == 0:
            return self.get_dataset_value(h5path)
        if h5path.count("@") == 1:
            return self.get_attribute_value(h5path)
        # no need to check groups as they have no value
        return None


# Like TIFF, HDF5 is a container file format
# Therefore, inspecting the mime type alone is insufficient to infer the schema
# with which the content in the HDF5 file is formatted
# Therefore, at least some of the content and how that content is
# formatted is inspected to make an informed decision which specific hfive
# parser can be expected to deal at all with the content of the HDF5 file

# For the example of EBSD there was once a suggestion made by the academic community
# to report EBSD results via HDF5, specifically via H5EBSD (Jackson et al.).
# Different tech partners and community projects though have implemented these
# ideas differently. In effect, there are now multiple HDF5 files circulating
# in the EBSD community where the same conceptual information is stored
# differently i.e. under different names

# This function shows an example how this dilemna can be
# solved for six examples that all are HDF5 variants used for "storing EBSD data"
# oxford - H5OINA format of Oxford Instrument
# edax - OIMself.input_file_path Analysis based reporting of EDAX/AMETEK
# apex - APEX based reporting of EDAX/AMETEK (can be considered the newer EDAX reporting)
# bruker - Bruker Esprit based reporting which replaces Bruker's bcf format that
#     is notoriously difficult to parse as it uses a commercial library SFS from AidAim
# emsort - HDF5-based reporting of parameter used by Marc de Graeff's EMsoft
#     dynamic electron diffraction simulation software
# hebsd - a variant of Jackson's proposal of the original H5EBSD the example here
#    explores from content of the community as used by e.g. T. B. Britton's group
# https://stackoverflow.com/questions/31146036/how-do-i-traverse-a-hdf5-file-using-h5py

# rules is a dictionary of pairs: first, a templatized path, second, an identifier
# what is a templatized path? take this example from an v4 H5OINA file with SEM/ESBD data
# 1/Data Processing/Analyses/IPF1, IS_GROUP
# 1/Data Processing/Analyses/IPF2, IS_GROUP
# both pathes are conceptually instances of the same concept
# */Data Processing/Analyses/IPF*
# where the stars in this templatized path serve as placeholders
# masking different instance ids
# Contextualization:
# HDF5 is a container (file) format lik TIFF.
# Therefore, neither the mime type nor the file name suffix can substantiate
# which not just format but version an instance comes formatted with.
# Therefore, the specific content and formatting of an instance
# e.g. do we talk about an HDF5 file whose content matches the rules
# of an e.g. Oxford Instrument v4 H5OINA file?
# the versioning is key to understand and read
# tech partners can make changes to I/O routines in their software
# this can result in that data end up formatted differently across file
# instances written over time
# therefore, it is necessary to ensure (before interpreting the file) that
# it matches a certain set of expectations (versioned format) so that the
# information content aka the knowledge, the pieces of information, in that file
# can be logically interpreted correctly
# The existence of a libraries and only best practices but not generally accepted
# rules how content in container files should be formatted enables for a
# potentially large number of possibilities how the same piece of information
# is encoded
# Consider the following simple example from electron microscopy with two quantities:
# hv (high_voltage) and wd (working_distance)
# these are two numbers each with a unit category or actual unit instance
# (voltage) and (length) respectively
# in hdf5 one could store the same information very differently technically
# as a dataset instance named "hv" with a scalar number and an attribute
# instance with a scalar string for the unit
# (this is assumed somewhat the best practice)
# however neither this is required nor assured
# in practice one could do much more e.g.
# as a group named hv_voltage with an attribute value
# as a compound dataset with two values packed as a struct with pairs of value and string
# first the value for hv followed by its unit, thereafter the value of wd followed by its unit
# also nobody is required to name an HDF5 instance using English because nodes in HDF5
# end up as links and these can have UTF8 encoding, so in principle even group and dataset names
# can use terms from other languages than English, one can use also special characters
# there can be typos or synonyms used like hv and high_voltage or voltage
# the key point is all these representations are allowed when we use HDF5 files
# but for each of these combinations a different code has to be implemented to extract
# and verify these pieces of information when one would like to use these pieces
# for further processing, this observation holds for every serialization of information
# into a file and thus one cannot escape the necessity that one needs to define
# a clear set of rules based on which one can decide if some instance is interpretable or
# not, in general we therefore see that there is much more work need that just to acknowledge
# that it is clear that one cannot infer the potential relevance of a file for an analysis
# based on its file format ending (mime type, magic cookie) etc
# although interesting this is exactly what the magic cookie
# (the initial few bytes to the beginning of the byte stream of a file)
# were originally conceptualized for
