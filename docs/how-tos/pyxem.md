# Kikuchi diffraction via pyxem

In recent years shortcomings of classical text-based file formats for serializing Kikuchi diffraction data have been realized and lead to a replacement of these formats with proprietary and open-source alternatives that use the [Hierarchical Data Format (HDF)5](https://www.hdfgroup.org/solutions/hdf5) library. At the point when we started the implementation of the Kikuchi diffraction examples for the FAIRmat project several of these formats were not yet supported by MTex. In parallel, we recognize that pyxem and kikuchipy entered the stage to offer complementary analyses capabilities for Python users. Therefore, we decided that as a technical implementation example we will implement the first version of the Kikuchi diffraction ontology matching using the I/O and orientation math capabilities of these Python libraries.

As a result, this pyxem-based parsing of HDF5-serialized content equips the pynxtools-em parser and normalizer currently with functionalities to read the following content and map on respective NeXus concepts that are defined in the NXem application definition and the NXem_ebsd base class:

| Orientation, phase | NeXus/HDF5 |
| --------------- | --------------  |
| [Oxford Instruments H5OINA HDF5](https://github.com/oinanoanalysis/h5oina) | :heavy_check_mark: |
| [Bruker Esprit HDF5](https://www.bruker.com/de/products-and-solutions/elemental-analyzers/eds-wds-ebsd-SEM-Micro-XRF/software-esprit-family.html) | :heavy_check_mark: |
| [H5EBSD-based community format](https://link.springer.com/article/10.1186/2193-9772-3-4) | :heavy_check_mark: |
| [ThermoFisher Velox](https://www.thermofisher.com/de/de/home/electron-microscopy/products/software-em-3d-vis.html) | :heavy_check_mark: |
| [EDAX APEX](https://www.edax.com/products/ebsd/apex-software-for-ebsd) | :heavy_check_mark: |
| [DREAM.3D v6](https://dream3d.bluequartz.net) | (:heavy_check_mark:) |
| [EMsoft HDF5](https://github.com/EMsoft-org/EMsoft) | (:heavy_check_mark:) |
