## How to ingest different information sources
pynxtools-em provides a set of parsers that standardize diverse content stored from several proprietary and open-source data models into NeXus.
The tool needs to serve different methods how information should be combined given that in reality a single source of information like an
ELN or a file format does not necessarily store all pieces of information which one may have serialized using NeXus.
For this reason pynxtools-em uses supplementary text files for now which exemplify how information missing in one serialization format
can be supplemented and ingested during the parsing. This part of the documentation lists these file formats.

<!--**Write.NXem.Example.1.ipynb** provides an example how the pynxtools-em parser can be used as a standalone tool for converting
data and metadata from different sources into an HDF5 file that follows the NeXus application definition NXem.-->

**nxem.schema.archive.yaml** is a YAML file representing a custom NOMAD Oasis ELN schema whereby users can collect metadata
which are typically not stored in files provided by technology partners.

**eln_data.yaml** is a YAML/text file which contains relevant data which are typically not contained in files from technology partners.
These data are typically collected either by editing the file manually or by using an electronic lab notebook (ELN) such as the NOMAD ELN.
Every other ELN can be used with this parser provided that this ELN writes its data into a YAML file with the same keywords and
structure as it is exemplified in the above-mentioned YAML file.

**em.oasis.specific.yaml** is a YAML/text file which contains additional metadata and configuration details that are not necessarily
defined via an ELN but which should be considered during parsing. One use case where this file is ideal is for passing frequent metadata
that are often the same when using pynxtools-em. The oasis.specific config file can be used to offload once the entering of these
pieces of information to render the ELN more succinct and focused on collecting those metadata that do change frequently.
A typical example is a lab where one uses always the same microscope such that many (static) details of the microscope are expected
to end up in the static section of the NXem application definition i.e. */NXem/ENTRY/measurement/instrument*

## Documenting reference frame conventions
Unambiguous and complete documentation of all reference frames used or assumed is a necessary requirement to make every study
of crystal orientations understandable and interpretable.

**em.conventions.schema.archive.yaml** is a YAML file representing a custom NOMAD Oasis ELN schema whereby users can document these conventions
and export them into an eln_data.yaml file.

**em.conventions.yaml** is an example of one such resulting YAML file that can be used as additional input to pynxtools-em
to add respective conventions as additional content in the generated NeXus/HDF5 file.
