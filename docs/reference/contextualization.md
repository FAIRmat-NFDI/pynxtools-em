# How to map pieces of information to NeXus

Conceptually, mapping between representations of concepts and instance data is a key tasks in information science. The plugin pynxtools-em implements this specifically for serialization formats used within the research field of electron microscopy. The plugin offloads this code from other software to avoid that every user and software developer have to make individual changes in their own tools.

Technically, instance data representing concepts within the realm of one ontology or file format are considered the source (`src`). These instance data are mapped on instance data representing a concept in NeXus as the target (`trg`). A transformation can be as simple as that an instance `src` has an elementary data type (e.g. a string or single-precision floating point value) that is copied into an instance `trg` of the same data type. Often though, such a mapping demands further normalization. One example is when `src` represents say a quantity such as a tilt angle with a value in unit radiants but `trg` requires that this value should be stored in unit degrees. In this case, the transformation is composed of a read of the value from `src`, a multiplication to convert from radiants to degrees, and the return of the value as `trg`.

Such transformations are configured via the respective files in the *config* directory of pynxtools-em.
Upon parsing, it is this set of functions in *mapping_functor.py* which implement the actual transformations by reading the configuration and returning the properly formatted and transformed target to fill the `template` dictionary variable.

The name functor is used because mapping may demand (as above-mentioned) more than copying the instance data. It is this *template* variable from which core functions like *convert.py* of the pynxtools library then write the actual NeXus/HDF5 file. The latter tool is also referred to as the dataconverter of [pynxtools](https://github.com/FAIRmat-NFDI/pynxtools).

<!--This map is only performed by pynxtools-em, if `src` and `trg` can be transformed such that `src` and `trg` are connected via an `same_as` relationship.-->

[A more detailed definition of the mapping approach is documented here](mapping.md)

