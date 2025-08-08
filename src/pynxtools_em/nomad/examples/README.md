# EM example

## Introduction

This example demonstrates how NOMAD can convert, standardize, and store EM data. It shows the generation of a NeXus file according to the [`NXem`](https://fairmat-nfdi.github.io/nexus_definitions/classes/applications/NXem.html#nxem) application definition.

## Viewing uploaded data

Below, you find an overview of your uploaded data.
Click on the `> /` button to get a list of your file or select **FILES** from the top menu of this upload.

The general structure of this example is the following:

- The starting point is the `em.schema.archive.yaml` file. This file defines a schema for the electronic lab notebook (ELN) for EM data. The ELN follows the general structure of NOMAD ELN templates. You can learn about NOMAD ELNs in the [documentation](https://nomad-lab.eu/prod/v1/staging/docs/howto/manage/eln.html). This schema contains key NeXus concepts that are defined in the `NXem` application definition that are often not provided through the files collected in experiments via proprietary software. Hence, these are the information that often the user should enter.
- The `downloads.archive.yaml` file instructs NOMAD to download an SEM/EDX dataset that is used converted in this example. As an example the file `InGaN_nanowires_spectra.edaxh5` is gets converted. This can be replaced though with own datasets.
- In the next step, the `em.archive.json` is used to generate a NeXus file according to the `NXem` application definition by calling the `NexusDataConverter` from `pynxtools`. It uses as input file either said `InGaN_nanowires_spectra.edaxh5` or you aforementioned own dataset, as well as the newly generated file with name ending `eln_data.yaml` to create the NeXus file `output.nxs` (by calling the EM reader from the package `pynxtools-em`). You may view your supplied or generated NeXus files here with the H5Web viewer. To do so open the **FILES** tab and just select the `.nxs` file.
- Finally, the `NexusParser` from `pynxtools` is called to read in the data in the NeXus file into the NOMAD metainfo. You can explore the parsed data in the **DATA** tab.

You may add your own files to the upload or experiment with the pre-existing electronic lab notebook (ELN) example.

## Which data schema is used?
The ELN template is configured such that its terminology matches with the [NXem](https://fairmat-nfdi.github.io/nexus_definitions/classes/contributed_definitions/NXem.html#nxem) NeXus application definition.

## Acknowledgements
[This example comes with real world datasets contributed by the international electron microscopy community.](https://zenodo.org/records/11208725)

## Where to go from here?

If you're interested in using this pipeline and NOMAD in general you'll find support at [FAIRmat](https://www.fairmat-nfdi.eu/fairmat/).

For questions regarding the experiment or this specific example contact [Markus Kühbach](https://www.fairmat-nfdi.eu/fairmat/about-fairmat/team-fairmat) or the rest of the [FAIRmat team](https://www.fairmat-nfdi.eu/fairmat/about-fairmat/team-fairmat).
