#!/bin/bash

# call from within the top-level directory of pynxtools_em
dsrc="../../../../paper_paper_paper/scidat_nomad_ebsd/bb_analysis/data/development_spiecker"
dsrc="../../../../paper_paper_paper/scidat_nomad_ebsd/bb_analysis/data/development_spctrscpy/adrien"
dsrc="../../../../paper_paper_paper/scidat_nomad_ebsd/bb_analysis/data/development_spctrscpy/fhi"
esrc="examples"
trg="debug"

# spiecker, FAU
examples="1340_Camera_Ceta_440_kx.emd 1403_STEM_HAADF-DF-I-DF-O-BF_3.80_Mx.emd 2102_SI_HAADF.emd 20240305_Spectrum_EDS_90000_x.emd"
# Teutrien, EPFL
examples="1613_Si_HAADF_610_kx.emd"
# Rohner, Moshantaf, Trunschke, FHI
examples="CG71113_1121_Ceta_310.0_kx_Camera.emd CG71113_1125_Ceta_1.1_Mx_Camera_0001.emd CG71113_1125_Ceta_1.1_Mx_Camera.emd CG71113_1126_Ceta_1.1_Mx_Camera.emd CG71113_1134_Ceta_660_mm__Camera.emd CG71113_1138_Ceta_660_mm_Camera.emd CG71113_1405_HAADF-DF4-DF2-BF_4.8_Mx_STEM.emd CG71113_1407_HAADF-DF4-DF2-BF_4.8_Mx_STEM.emd CG71113_1409_HAADF-DF4-DF2-BF_6.7_Mx_STEM.emd CG71113_1411_HAADF-DF4-DF2-BF_4.8_Mx_STEM.emd CG71113_1411_HAADF-DF4-DF2-BF_6.7_Mx_STEM.emd CG71113_1412_EDS-HAADF-DF4-DF2-BF_4.8_Mx_SI.emd CG71113_1422_EDS-HAADF-DF4-DF2-BF_1.2_Mx_SI.emd CG71113_1423_EDS-HAADF-DF4-DF2-BF_1.2_Mx_SI.emd CG71113_1444_EDS-HAADF-DF4-DF2-BF_595.5_kx_SI.emd CG71113_1513_HAADF-DF4-DF2-BF_1.2_Mx_STEM.emd CG71113_1514_EDS-HAADF-DF4-DF2-BF_1.2_Mx_SI.emd CG71113_1537_HAADF-DF4-DF2-BF_432.2_kx_STEM.emd"


for example in $examples; do
	echo $example
	dataconverter convert $esrc/em.oasis.specific.yaml $esrc/eln_data.yaml $dsrc/$example --reader em --nxdl NXem --output=$trg/debug.$example.nxs 1>$trg/stdout.$example.nxs.txt 2>$trg/stderr.$example.nxs.txt
done
