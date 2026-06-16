# Electron back scatter diffraction (EBSD) via MTex

[MTex](https://mtex-toolbox.github.io/index) is a software for texture analysis written in [MATLAB](https://de.mathworks.com/products/matlab.html). The software is one of the key tools of materials engineers and geologists to perform computations in orientation space to segment a characterized portion of material into a representation of its microstructure. The software offers the [largest and most mature solution](https://doi.org/10.1107/S002188981003027X) for analyzing and [plotting](https://doi.org/10.1107/S1600576716012942) texture analyses solving research questions about texture quantification and visualization using pole figures, orientation distribution functions, inverse pole figures, and grain-boundary-network characterization. Thanks to its support of all symmetry classes, the tool has not only found a wide acceptance within the field of materials engineering but is also vividly used in within the geoscience communities.

Computational results from MTex are most frequently preserved via MATLAB `.mat` files or using ad hoc reporting with text files and other binary containers with custom formatting. For `pynxtools-em` we explored an alternative strategy
of automatically converting MTex class objects to a standardized NeXus-based HDF5 file representation. To connect these HDF5 files to the pynxtools ecosystem and upload these for instance in NOMAD, a parser was generated.

| Orientation, phase | NeXus/HDF5 |
| --------------- | --------------  |
| Oxford Instruments ANG | :heavy_check_mark: |
| HKL Channel5 CPR/CRC | :heavy_check_mark: |
| OSC | :heavy_check_mark: |
| CTF | :heavy_check_mark: |


This parser has been moved into `pynxtools-microstructure`, [an own plugin](https://pypi.org/project/pynxtools-microstructure).

