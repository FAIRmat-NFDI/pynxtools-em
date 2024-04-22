# Kikuchi diffraction via MTex

[MTex](https://mtex-toolbox.github.io/index) is a software for texture analysis that for use in [MATLAB](https://de.mathworks.com/products/matlab.html). The software is one of the key software tools that is used every day by materials engineers and geologists to perform computations in orientation space. The software offers the [largest and most mature solution](https://doi.org/10.1107/S002188981003027X) for analyzing and [plotting](https://doi.org/10.1107/S1600576716012942) texture analyses to answer related research questions about texture quantification and visualization using pole figure, orientation distribution, inverse pole figure, and grain boundary network based data. Thanks to its support of all symmetry classes, the tool has not only found a wide acceptance within the field of materials engineering but also many users in the geoscience communities.

As a result, this MTex-based parsing of certain Kikuchi diffraction relevant content equips the pynxtools-em parser and normalizer currently with functionalities to read the following content and map on respective NeXus concepts that are defined in the NXem application definition and the NXem_ebsd base class:

| Orientation, phase | NeXus/HDF5 |
| --------------- | --------------  |
| Oxford Instruments ANG | :heavy_check_mark: |
| HKL Channel5 CPR/CRC | :heavy_check_mark: |
| OSC | :heavy_check_mark: |
| CTF | :heavy_check_mark: |



<!--TODO: Technically, the parsing has to bridge between two software ecosystems: Python and MATLAB. For now, we went for the following strategy:
- A customized MTex export routine has been generated which automatically formats EBSD-specific content as represented in MTex to NeXus.
- That information is serialized into an HDF5 file with a structure matching that of NXem but not necessarily demanding that this file is complete.
- Pynxtools-em parses from this file using the nxs_mtex parser and adds additional pieces of information and decoration to obtain a complete NXem-compliant file.
[file formats used in EBSD](https://mtex-toolbox.github.io/EBSD.load.html)-->

<!--TODO: Give guidance (like commands) what to do with a file in MTex, conflict of interest with our paper, will be filled in and set active only at the point of the submission of the paper-->