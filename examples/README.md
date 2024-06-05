## Context

**Write.NXem.Example.1.ipynb** provides an example how the em parser/reader/data extractor
can be used as a standalone tool for converting data and metadata from different sources into an NXem-formatted NeXus/HDF5 file.

**eln_data.yaml** is a YAML/text file which contains relevant data which are not
contained typically in files from technology partners. These data have been collected
either by editing the file manually or by using an electronic lab notebook (ELN),
such as the NOMAD ELN. Every other ELN can be used with this parser provided that
this ELN writes its data into a YAML file with the same keywords and structure as is
exemplified in the above-mentioned YAML file.

**em.oasis.specific.yaml** is a YAML/text file which contains additional metadata that are
not necessarily coming from an ELN but which should be considered during parsing.
One use case where this file is ideal is for passing frequent metadata that are often the
same and thus can be offloaded once from an ELN to make such ELN templates more
focused on metadata that do change frequently. A typical example is a lab where always the
same microscope is used, many static details of the microscope are expected to end up
in the static section of the NXem application definition i.e. */NXem/ENTRY/measurement/em_lab*

## Documenting reference frame conventions conveniently
Umambiguous and complete documentation of all reference frames used or assumed is a necessary
requirement to make every study of crystal orientations understandable and interpretable.
**em.conventions.schema.archive.yaml** is a YAML file with a custom NOMAD Oasis ELN schema
whereby users can document these conventions and export them into an eln_data.yaml file.
An example of one such resulting YAML file **em.conventions.yaml** is also provided. This
file can be used also as additional input to the em parser to annotate the conventions made
in ones NeXus/HDF5 files.
