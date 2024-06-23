#!/bin/bash

# call from within the top-level directory of pynxtools_em
dsrc="../../../../paper_paper_paper/scidat_nomad_ebsd/bb_analysis/data/development_imgs/ikz_robert"
dsrc="../../../../paper_paper_paper/scidat_nomad_ebsd/bb_analysis/data/development_axon/axon"
esrc="examples"
trg="debug"

# Reetu some SEM
# examples="kit/FeMoOx_AntiA_04_1k5x_CN.tif"

# IKZ SEM TFS Apreo for all imaging modes
#examples="0c8nA_3deg_003_AplusB_test.tif"  # T1
#examples="ALN_baoh_021.tif"  # T2
#examples="T3_image.tif"  # T3
#examples="ETD_image.tif"  # ETD
#examples="NavCam_normal_vis_light_ccd.tif"  # NavCam
examples="0c8nA_3deg_003_AplusB_test.tif ALN_baoh_021.tif T3_image.tif ETD_image.tif NavCam_normal_vis_light_ccd.tif"

#examples="axon/20210426T224437.049Raw0.png"
examples="ReductionOfFeOxSmall.zip.axon"
#examples="ReductionOfFeOx.zip.axon"


for example in $examples; do
	echo $example
	dataconverter convert $esrc/em.oasis.specific.yaml $esrc/eln_data.yaml $dsrc/$example --reader em --nxdl NXem --output=$trg/debug.$example.nxs 1>$trg/stdout.$example.nxs.txt 2>$trg/stderr.$example.nxs.txt
done
