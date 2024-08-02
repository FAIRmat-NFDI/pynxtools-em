# Context

Configurations how concepts defined in specific serialization formats are mapped on concepts in NeXus:
* eln_cfg.py - NOMAD Oasis ELN export file format
* oasis_cfg.py - Specific configuration of the em parser in a specific local NOMAD Oasis
  to avoid having to enter these pieces of information with every ELN entry again
* image_png_protochips_cfg.py - PNG files exported with AXONStudio software from Protochips tech partner
* image_tiff_tfs_cfg.py - TIFF files exported with a ThermoFisher Apreo SEM from ThermoFisher/FEI tech partner
* rsciio_velox_cfg.py - Velox EMD file format from ThermoFisher/FEI tech partner


# Mapping approach

Mapping information from one serialization format onto another can face various cases of information content,
representation, and formatting mismatch as the data models can differ.
Assume that we wish to map instance data for concepts on the *src* side, e.g. content stored
from files collected during an measurement, onto instance data for concepts of a different data model
on the *trg* side. Several cases of mismatch can occur:

1. Mismatch in symbols (aka concept names) used for identifying concepts
  An example: *high_voltage* is expected by *trg* but *HV* is used as a symbol by *src*.
2. Mismatch in units
  An example: *trg* expects voltage quantities with unit *V* but *src* provides unit *kV*
  An example: *trg* expects angle as *radian* but *src* provides *deg*
3. Mismatch in data types
  An example: *np.float64* is expected by *trg* but *single precision float* is used by *src*.
  An example: *1* as an int is expected by *trg* but that number has been serialized as a string "1".
  An example: *trg* expects voltag-e as *V* but on *src* tech partners agreed to use SI unit but do not write these unit explicitly
4. Mismatch in the granularization of information or different standards used for representing information
  An example: *trg* expects ISO8601 with local time zone offset to UTC but *src* provides date, time, and timezone as individual strings
  An example: *trg* expects UNIX timestamp but *src* provides MS-DOS timestamp.
5. Mismatch in dimensions
  An example: *trg* requests an (>1,) array but *src* only provides a scalar

Configurations are the solutions which guide the parser how to map instance data for each concept.
Often the mismatch cannot be resolved because the *trg* and *src* have not exchanged precisely
defined versions of their data models. In this case, one often uses assumptions.

Configurations implement these assumptions and mapping decisions outside the actual source code
to offer a single place where preferentially such mismatches should be resolved. This enables users
to often avoid having to take a look into the backend code surplus this solutions avoids
that the mapping of potentially many individual concepts becomes too strongly hard-coded and
long mapping pathes need be repeated which would create code bloat.

Configurations should group mapping rules to reduce the overall size of the mapping dictionaries.
Configurations are stored as Python dictionaries with specific formatting.
Configurations use abbreviations wherever possible. All combined, this yields compact
descriptions that are hopefully easier to read and having fewer places where changes
need to be implemented when mapping paths change as the data models evolve.

Mismatch cases 1, 2, 3, 4 are dealt with. Mismatch case 5 is currently ignored.
Instead, instance data from *src* are copied to *trg* if no mismatch 1 -4 is observed.
This may cause though that the resulting collection of instance data on the *trg* side
does not end up fully compliant with an application definition.
However, this is not a problem because verification of the instance data
takes place during consumption of the serialized NeXus artifact/file.

The following example shows one typical such dictionary.

```python
AXON_STAGE_STATIC_TO_NX_EM = {
    "prefix_trg": "/ENTRY[entry*]/measurement/em_lab/STAGE_LAB[stage_lab]",
    "prefix_src": "MicroscopeControlImageMetadata.ActivePositionerSettings.PositionerSettings.[*].Stage.",
    "use": [("design", "heating_chip")],
    "map": [("alias", "Name")],
}
```

<!--The pint.ureg('') maps on NX_DIMENSIONLESS.-->

In this example the template path for the tuple in *use* on the *trg* side will be f"{prefix_trg}/{use[0][0]}" with value use[0][1].
The template path for the tuple in *map* on the *trg* side will be f"{prefix_trg}{map[0][0]}" with the value that is read from the *src* side
pointed to by keyword f"{prefix_src}{map[0][1]}".

Problems with the old algorithm can be exemplified with the following example
```
VELOX_STAGE_TO_NX_EM = {
    "prefix_trg": "/ENTRY[entry*]/measurement/event_data_em_set/EVENT_DATA_EM[event_data_em*]/em_lab/STAGE_LAB[stage_lab]",
    "use": [
        ("tilt1/@units", "rad"),
        ("tilt2/@units", "rad"),
        ("position/@units", "m"),
    ],
    "map_to_str": [("design", "Stage/HolderType")],
    "map_to_real": [
        ("tilt1", "Stage/AlphaTilt"),
        ("tilt2", "Stage/BetaTilt"),
        ("position", ["Stage/Position/x", "Stage/Position/y", "Stage/Position/z"]),
    ],
}
```

Keywords *use* and *map* were processed of in a loop and thus template pathes like *tilt1/@units* were set
independent from an potential issues with finding the corresponding value *tilt1*. In summary,
the old mapping dictionary was less compact and problematic as a comparison to the new formatting shows:
```
VELOX_STAGE_TO_NX_EM = {
    "prefix_trg": "/ENTRY[entry*]/measurement/event_data_em_set/EVENT_DATA_EM[event_data_em*]/em_lab/STAGE_LAB[stage_lab]",
    "map": [("design", "Stage/HolderType")],
    "map_to_float64": [
        ("tilt1", ureg.radiant, "Stage/AlphaTilt"),
        ("tilt2", ureg.radiant, "Stage/BetaTilt"),
        ("position", ureg.meter, ["Stage/Position/x", "Stage/Position/y", "Stage/Position/z"]),
    ],
}
```

The example shows though that it is not necessarily use to try an encoding of all mapping conventions
into such dictionaries. Indeed, if there is a mismatch between the reference frames of *src* compared
to *trg* an instruction like concatenate the three values *Stage/Position/x, y, z* into an array of
np.float64 and convert to unit meter may not be sufficient enough as offsets or rotations of the
reference frame are required. In this case a more complicated mapping dictionary is required.
This is an open question we leave for the future. Instead, we currently implement such as explicit
mapping and translations as hard-coded instructions.


* Required keyword **prefix_trg** specifies the prefix to use when resolving template paths on the *trg* side excluding the / separator.
* Required keyword **prefix_src** specifies the prefix to use when resolving template paths on the *src* side including separators.
* Optional keywords follow. Each encodes mapping instructions based on one list of tuples as value.
  * **use** instructs mapping explicitly instance data on *trg* without demanding a *src*.
    Specifically, tuples of the following two datatypes are allowed:
    (str, str | numpy datatype (scalar or array))
    (str, pint.Quantity)
    The first value resolves the symbol for the concept on the *trg* side.
    The second value resolves the instance data to store on the *trg* side.
    The template path on the *trg* side is f"{prefix_trg}/{tpl[0]}", if provided prefix_src will be ignored.
  * **map** | **map_to_dtype** | **map_to_dtype_and_join** instructs mapping instance data from *src* on *trg*.
    Differently typed tuples are allowed that encode compact mapping rules to deal with
    above-mentioned cases of mismatch. The suffix "_to\*" is added to solve mismatch 3.
    Mismatch cases 1 and 2 are solved based on how the tuple is structured.
    Mismatch case 3 is solved by adding a suffix like "_to_float64" which will instruct
    that the *src* data will be mapped if possible from original datatype and precision
    on the numpy datatype and precision specified by *dtype*.

    The suffix **_and_join** will accept a list of below mentioned tuples to concatenate information.

    TODO more work needs to be done here

    Specifically, tuples of the following datatypes are allowed or a str but in only one case:
    * ```(str, pint.ureg, str | list[str], pint.ureg)``` aka case five.
      Used in cases of mismatch 1 and 2 with the aim to explicitly convert units between *src* and *trg*.

      The first value resolves the symbol for the concept on the *trg* side.
      The second value resolves the specific unit on the *trg* side.
      The third value resolves the symbol for the concept on the *src* side.
      The fourth value resolves the specific unit on the *src* side.

      The third value can be a list of strings of symbols for concepts on the *src* side.
      This is useful for joining individual scalar values in an array,
      like x, y, z coordinates.

    * ```(str, str | list[str], pint.ureg)``` aka case four.
      Used in cases of mismatch 1 with the aim to accept the unit from the *src* side.

      The first value resolves the symbol for the concept on the *trg* side.
      The second value resolves the symbol for the concept on the *src* side.
      The third value resolves the specific unit on the *src* side.

      In an implementation, this case can be avoided when the value on the *src* side
      is already normalized into a pint.Quantity. The second value can be a list of
      strings of symbols for concepts on the *src* side.

    * ```(str, pint.ureg, str | list[str])``` aka case three.
      Used in cases of mismatch 1 and 2 with the aim to explicitly convert to
      a specific unit on the *trg* side.

      The first value resolves the symbol for the concept on the *trg* side.
      The second value resolves the specific unit on the *trg* side.
      The third value resolves the symbol for the concept on the *src* side.

      The third value can be a list of strings of symbols for concepts on the *src* side.
      In an implementation, this case can be avoided when there is another look-up dictionary or
      cache from which the unit to use is defined explicitly.
      The practical issue with NeXus though is that often concepts are constrained
      only as strong as to match a specific unit category, e.g. voltage, i.e. all possible
      units that are convertible into the base unit V.

      Therefore, in practice it makes sense to use this case to be specific about
      which unit should be used on the *trg* side. However, for parsers which cover
      many file formats, like pynxtools-em, this will ask people to add potentially duplicated
      information. In summary, it is best to use a global look-up dictionary for all concepts
      in an application definition and then infer the unit from this dictionary. The actual
      unit conversion is performable then e.g. with pint.

    * ```(str, str | list[str])``` aka case two.
      Used in cases of mismatch 1. Units on *src* will be carried over onto the *trg* side.

      The first value resolves the symbol for the concept on the *trg* side.
      The second value resolves the symbol for the concept on the *src* side.

      The second value can be a list of strings of symbols for concepts on the *src* side.
      This case is an especially useful short-hand notation for concepts with string,
      unitless, dimensionless quantities.

    * ```str``` aka case one.
      Used in cases when symbols on the *trg* and *src* side are the same and
      units should be carried through as is.

      This case is a further simplification for writing even more compact mapping dictionaries.
      Python allows for a having a mixture of string and tuples in the lists.

<!-- * **map_to_iso8601** -->
