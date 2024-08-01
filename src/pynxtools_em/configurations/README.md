# Context

Configurations how concepts defined in specific serialization formats are mapped on concepts in NeXus:
* eln_cfg.py - NOMAD Oasis ELN export file format
* oasis_cfg.py - Specific configuration of the em parser in a specific local NOMAD Oasis
  to avoid having to enter these pieces of information with every ELN entry again
* image_png_protochips_cfg.py - PNG files exported with AXONStudio software from Protochips tech partner
* image_tiff_tfs_cfg.py - TIFF files exported with a ThermoFisher Apreo SEM from ThermoFisher/FEI tech partner
* rsciio_velox_cfg.py - Velox EMD file format from ThermoFisher/FEI tech partner


# Mapping approach

Mapping information from one serialization format to another typically faces the challenge that
the data models differ. Assume that we wish to map instance data representing concepts on the *src* side
to store these instance data using potentially a different data model on the *trg* side.
Several situation have to be covered:

1. Mismatch in symbols used for identifying concepts (aka concept names)
  An example: *high_voltage* is expected by *trg* but *HV* is used as a symbol by *src*.
2. Mismatch in units
  An example: *trg* expects voltage as *V* but *src* provides *kV*
  An example: *trg* expects angle as *radian* but *src* provides *deg*
3. Mismatch in data types
  An example: *np.float64* is expected by *trg* but *single precision float* is used by *src*.
  An example: *1* as an int is expected by *trg* but that number has been serialized as string "1".
  An example: *trg expects voltage as *V* but tech partner on *src* assumes SI unit hence does not add them
4. Mismatch in the granularization of information or different standards used for representing information
  An example: *trg* expects ISO8601 with local time zone offset to UTC but *src* provides date, time, and timezone as individual strings
  An example: *trg* expects UNIX time stamp but *src* provides some other time stamp.
5. Mismatch in dimensions
  An example: *trg* requests an (>1,) array but *src* only provides a scalar

Configurations are the solutions which guide the parser how to map instance data for each concept.
Often the mismatch cannot be resolved because the *trg* and *src* have not exchanged precisely
defined versions of their data model. In this case on often uses assumptions.

Configurations implement these rules outside the actual source code (aka a frontend) to provide
a single place where preferentially such mismatches should be resolved. This enables that the
backend code can iterate over the cases and is not too strongly hard-coded for specific
assumptions.

Configurations should group mapping rules to reduce the overall size of the mapping tables.
Configurations are stored as Python dictionaries with specific formatting.
Configurations use abbreviations wherever possible to yield compact descriptions.

Mismatch cases 1, 2, 3, 4 are dealt with. Mismatch case 5 is ignored.
Instead, instance data from *src* are copied to *trg* if no other mismatch is observed.
This may cause the resulting collection of instance data on the *trg* side, which for
pynxtools-em currently is NeXus to end up not fully compliant with an application definition.
However, this is not a problem because verification of the instance data takes place
during consumption of the serialized NeXus artifact/file.

The following example shows one typical such dictionary.

```python
AXON_STAGE_STATIC_TO_NX_EM = {
    "prefix_trg": "/ENTRY[entry*]/measurement/em_lab/STAGE_LAB[stage_lab]",
    "prefix_src": "MicroscopeControlImageMetadata.ActivePositionerSettings.PositionerSettings.[*].Stage.",
    "use": [("design", "heating_chip")],
    "map": [("alias", "Name")],
}
```

* Required keyword **prefix_trg** specifies the prefix to use when resolving template paths on the *trg* side including separators.
* Required keyword **prefix_src** specifies the prefix to use when resolving template paths on the *src* side including separators.
* Optional keywords follow. Each has one list of tuples as a value. These keywords are:
  * **use** are special to instruct explicit writing of values.
   Two types of tuples are possible:
   (str, str | numpy datatype (scalar or array))
   (str, pint.Quantity)
   The first value of the tuple resolves the *trg* side.
   The second value resolves the instance data to take.
   The template path on the *trg* side is f"{prefix_trg}{tpl[0]}", prefix_src is ignored.
  * **map**

