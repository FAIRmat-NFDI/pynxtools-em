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

In this example the template path for the tuple in use on the *trg* side will be f"{prefix_trg}{use[0][0]}" with value use[0][1]. The template path for the tuple in map on the *trg* side will be f"{prefix_trg}{map[0][0]}" with the value read from the *src* side pointed to by keyword f"{prefix_src}{map[0][1]}".

* Required keyword **prefix_trg** specifies the prefix to use when resolving template paths on the *trg* side including separators.
* Required keyword **prefix_src** specifies the prefix to use when resolving template paths on the *src* side including separators.
* Optional keywords follow. Each encodes mapping instructions based on one list of tuples as value.
  * **use** instructs mapping explicitly instance data on *trg* without demanding a *src*.

   Specifically, tuples of the following two datatypes are allowed:
   (str, str | numpy datatype (scalar or array))
   (str, pint.Quantity)
   The first value resolves the symbol for the concept on the *trg* side.
   The second value resolves the instance data to take.
   The template path on the *trg* side is f"{prefix_trg}{tpl[0]}", prefix_src is ignored.
  * **map** | **map_to_dtype** | **map_to_dtype_and_join** instructs mapping instance data from *src* on *trg*.
  Differently typed tuples are allowed that encode compact mapping rules to deal with
  above-mentioned cases of mismatch. The suffix "_to\*" is added to solve mismatch 3.
  Mismatch cases 1 and 2 are solved based on how the tuple is structured.
  Mismatch case 3 is solved by adding a suffix like "_to_float64".
  This will instruct that *src* data are mapped if possible
  from their type on the numpy datatype written *dtype*.

  The suffix **_and_join** will accept a list of below
  mentioned tuples to concatenate information.

  Specifically, tuples of the following datatypes are allowed:

  (str, pint.ureg | str, str, pint.ureg | str)
  Used in cases of mismatch 1 and 2 with the aim to explicitly convert units between *src* and *trg*.

  The first value resolves the symbol for the concept on the *trg* side.
  The second value resolves the specific unit (if pint.ureg) on the *trg* side.
  The third value resolves the symbol for the concept on the *src* side.
  The fourth value resolves the specific unit (if pint.ureg) on the *src* side.

  For the second and the fourth values the strings "unitless" or "any" can be used
  if the quantities should map on NX_UNITLESS or NX_ANY.
  The pint.ureg('') maps on NX_DIMENSIONLESS.

  (str, str, pint.ureg | str)
  Used in cases of mismatch 1 with the aim to accept the unit from the *src* side.

  The first value resolves the symbol for the concept on the *trg* side.
  The second value resolves the symbol for the concept on the *src* side.
  The third value resolves the specific unit (if pint.ureg) on the *src* side.

  For the third value the strings "unitless" or "any" can be used
  if the quantities should map on NX_UNITLESS or NX_ANY.
  The pint.ureg('') maps on NX_DIMENSIONLESS.

  (str, pint.ureg | str, str)
  Used in cases of mismatch 1 and 2 with the aim to provide to explicitly
  convert to a specific unit on the *trg* side.

  The first value resolves the symbol for the concept on the *trg* side.
  The second value resolves the specific unit (if pint.ureg) on the *trg* side.
  The third value resolves the symbol for the concept on the *src* side.

  For the third value the strings "unitless" or "any" can be used
  if the quantities should map on NX_UNITLESS or NX_ANY.
  The pint.ureg('') maps on NX_DIMENSIONLESS.

  (str, str)
  Used in cases of mismatch 1. Units on *src* will be carried over onto the *trg* side.
  The first value resolves the symbol for the concept on the *trg* side.
  The second value resolves the symbol for the concept on the *src* side.

  (str)
  Used in cases when symbols on the *trg* and *src* side are the same and
  units should be carried through as is.

  * **map_to_iso8601**
