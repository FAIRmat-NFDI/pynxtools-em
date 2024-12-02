---
hide: toc
---

# Documentation for pynxtools-em

pynxtools-em is a free and open-source data software for creating standardized semantic serializations of electron microscopy data and metadata for research data management using NeXus, implemented with the goal to make scientific research data FAIR (findable, accessible, interoperable and reusable).

pynxtools-em, which is a plugin for pynxtools, provides a tool for reading data from various proprietary and open data formats from technology partners and the wider electron microscopy community and standardizing it such that it is compliant with the NeXus application definition NXem.

pynxtools-em is developed both as a standalone reader and as a tool within NOMAD, which is the open-source research data management platform for Materials Science that is developed by the [FAIRmat consortium of the German National Research Data Infrastructure (German NFDI)](https://www.nfdi.de/consortia-fairmat/?lang=en).

pynxtools-em solves the challenge that comes with using heterogeneous and semantically ambiguous serialization formats that are commonly used in electron microscopy. In addition, the plugin provides an interface for writing readers for different file formats to be mapped to NeXus.

pynxtools-em is useful for scientists from the electron microscopy community who deal with heterogeneous data, for technology partners, software developers, and data providers who search for ways to make their data more completely aligned with the aims of the FAIR principles. Specifically the tool is useful for research groups who wish to organize their research data based on an interoperable.

<!-- A single sentence that says what the product is, succinctly and memorably -->
<!-- A paragraph of one to three short sentences, that describe what the product does. -->
<!-- A third paragraph of similar length, this time explaining what need the product meets -->
<!-- Finally, a paragraph that describes whom the product is useful for. -->

<div markdown="block" class="home-grid">
<div markdown="block">

### Tutorial
<!--This is the place where to add documentation of [diátaxis](https://diataxis.fr) content type tutorial.-->

- [Convert electron microscopy content to NeXus](tutorial/standalone.md)
- [How to use a NeXus/HDF5 file](tutorial/nexusio.md)
- [How to combine different information sources](tutorial/examples.md)

</div>
<div markdown="block">

### How-to guides
<!--This is the place where to add documentation of [diátaxis](https://diataxis.fr) content type how-to guides.-->

- [Kikuchi diffraction](how-tos/kikuchi.md)

</div>

<div markdown="block">

### Learn
<!--This is the place where to add documentation of [diátaxis](https://diataxis.fr) content type explanation.-->

- [Implementation design](explanation/implementation.md)

</div>
<div markdown="block">

### Reference
<!--This is the place where to add documentation of [diátaxis](https://diataxis.fr) content type reference.-->
Here you can learn which specific pieces of information and concepts pynxtools-em currently supports
for the respective file formats of technology partners of the electron microscopy community.

- [How to map pieces of information to NeXus](reference/contextualization.md)

- [Conventions collected with a text file or ELN](reference/conventions.md)
- [Metadata collected with an ELN and RDM-specific configurations](reference/eln_and_cfg.md)

- [AXON Protochips Portable Network Graphics PNG](reference/zip_png_axon.md)
- [EDAX APEX](reference/hfive_apex.md)
- [Gatan DigitalMicrograph DM3/DM4](reference/rsciio_gatan.md)
- [Hitachi Tagged Image File Format TIFF](reference/tiff_hitachi.md)
- [JEOL Tagged Image File Format TIFF](reference/tiff_jeol.md)
- [Nion Co. projects with NDATA and HDF5 files](reference/nxs_nion.md)
- [Point Electronic DISS Tagged Image File Format TIFF](reference/tiff_point.md)
- [TESCAN Tagged Image File Format TIFF](reference/tiff_tescan.md)
- [ThermoFisher Tagged Image File Format TIFF](reference/tiff_tfs.md)
- [ThermoFisher Velox EMD](reference/rsciio_velox.md)
- [FEI Legacy Tagged Image File Format TIFF](reference/tiff_fei.md)
- [Zeiss Tagged Image File Format TIFF](reference/tiff_zeiss.md)
- [EBSD-centric content for the parsing route via MTex](how-tos/mtex.md)
- [EBSD-centric content for the parsing route via pyxem](how-tos/pyxem.md)

</div>
</div>

<h2>Project and community</h2>
<!-- - [NOMAD code guidelines](https://nomad-lab.eu/prod/v1/staging/docs/reference/code_guidelines.html) -->

Any questions or suggestions? [Get in touch!](https://www.fair-di.eu/fairmat/about-fairmat/team-fairmat)

[The work is funded by the Deutsche Forschungsgemeinschaft (DFG, German Research Foundation) – 460197019 (FAIRmat)](https://gepris.dfg.de/gepris/projekt/460197019?language=en).
