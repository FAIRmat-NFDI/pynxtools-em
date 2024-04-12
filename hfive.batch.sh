#!/bin/bash

# call from within the top-level directory of pynxtools_em
dsrc="../../../../paper_paper_paper/scidat_nomad_ebsd/bb_analysis/data/development_spctrscpy/pdi"
# dsrc="../../../../paper_paper_paper/scidat_nomad_ebsd/bb_analysis/data/development_spctrscpy/ikz"
# dsrc="../../../../paper_paper_paper/scidat_nomad_ebsd/bb_analysis/data/production_ebsd_pyxem"

esrc="examples"
trg="debug"


# bruker bcf
# pynx/46_ES-LP_L1_brg.bcf
# pynx/EELS_map_2_ROI_1_location_4.dm3
# oxford instruments h5oina
# pynx/H5OINA_examples_Specimen_1_Map_EDS_+_EBSD_Map_Data_2.h5oina"

# apex
# Laehnemann, PDI
examples="InGaN_nanowires_spectra.edaxh5"
# Bergmann, Kernke, Brückner, IKZ
# examples="AlGaO.nxs GeSi.nxs GeSi_13.h5 GeSn_13.nxs VInP_108_L2.h5"
# Pauly, Uni Saarland
# examples="207_2081.edaxh5"

for example in $examples; do
	echo $example
	dataconverter convert $esrc/em.oasis.specific.yaml $esrc/eln_data.yaml $dsrc/$example --reader em --nxdl NXem --output=$trg/debug.$example.nxs 1>$trg/stdout.$example.nxs.txt 2>$trg/stderr.$example.nxs.txt
done
