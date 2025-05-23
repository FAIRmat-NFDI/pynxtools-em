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
"""Entry points for EM examples."""

try:
    from nomad.config.models.plugins import (
        AppEntryPoint,
        ExampleUploadEntryPoint,
    )
    from nomad.config.models.ui import (
        App,
        Column,
        Menu,
        MenuItemHistogram,
        MenuItemPeriodicTable,
        MenuItemTerms,
        SearchQuantities,
    )
except ImportError as exc:
    raise ImportError(
        "Could not import nomad package. Please install the package 'nomad-lab'."
    ) from exc


em_example = ExampleUploadEntryPoint(
    title="Electron Microscopy",
    category="FAIRmat examples",
    description="""
        This example presents the capabilities of the NOMAD platform to store and standardize electron microscopy.
        It shows the generation of a NeXus file according to the
        [NXem](https://fairmat-nfdi.github.io/nexus_definitions/classes/contributed_definitions/NXem.html#nxem)
        application definition.
        The example contains a small set of electron microscopy datasets to get started and keep the size of your
        NOMAD installation small. Ones started, we recommend to change the respective input file in the NOMAD Oasis
        ELN to run the example with your own datasets.
    """,
    plugin_package="pynxtools_em",
    resources=["nomad/examples/*"],
)
