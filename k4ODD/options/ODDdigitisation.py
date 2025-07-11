#
# Copyright (c) 2020-2024 Key4hep-Project.
#
# This file is part of Key4hep.
# See https://key4hep.github.io/key4hep-doc/ for further info.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from Gaudi.Configuration import INFO
from k4FWCore import ApplicationMgr, IOSvc
from Configurables import EventDataSvc
from Configurables import DDCaloDigi, CollectionMerger

from Configurables import GeoSvc
from Configurables import UniqueIDGenSvc
from Configurables import RootHistSvc
from Configurables import Gaudi__Histograming__Sink__Root as RootHistoSink
import os

from k4FWCore.parseArgs import parser
parser_group = parser.add_argument_group("CLDReconstruction.py custom options")
parser_group.add_argument("--inputFile", default="ODD_sim_edm4hep.root", help="Input file")
parser_group.add_argument("--outputFile", help="Output file", default="ODD_calo_digi.root")
digi_args = parser.parse_known_args()[0]

iosvc = IOSvc()
iosvc.Input = digi_args.inputFile
iosvc.Output = digi_args.outputFile

id_service = UniqueIDGenSvc("UniqueIDGenSvc")

geoservice = GeoSvc("GeoSvc")

if "OpenDataDetector" in os.environ:
    geoservice.detectors = [
        os.environ["OpenDataDetector"]+"/install/share/OpenDataDetector/xml/OpenDataDetector.xml"
    ]
else:
    geoservice.detectors = [
        "OpenDataDetector/install/share/OpenDataDetector/xml/OpenDataDetector.xml"
    ]

geoservice.OutputLevel = INFO
geoservice.EnableGeant4Geo = False

calodigi = [
    DDCaloDigi("ECalBarrelDigi"),
    DDCaloDigi("ECalEndcapDigi"),
    DDCaloDigi("HCalBarrelDigi"),
    DDCaloDigi("HCalEndcapDigi"),
]

ECALorHCAL = [True, True, False, False]

inputcollections = [
    ["ECalBarrelCollection"],
    ["ECalEndcapCollection"],
    ["HCalBarrelCollection"],
    ["HCalEndcapCollection"],
]

outputcollections = [
    ["digiECalBarrelCollection"],
    ["digiECalEndcapCollection"],
    ["digiHCalBarrelCollection"],
    ["digiHCalEndcapCollection"],
]

relcollections = [
    ["digiLinkCaloHitECALBarrel"],
    ["digiLinkCaloHitECALEndcap"],
    ["digiLinkCaloHitHCALBarrel"],
    ["digiLinkCaloHitHCALEndcap"],
]

for calodigicol, ecalorhcal, inputcol, outputcol, relcol in zip(
    calodigi, ECALorHCAL, inputcollections, outputcollections, relcollections
):
    calodigicol.InputColIsECAL = ecalorhcal  # True -- ECAL // False -- HCAL
    calodigicol.InputCaloHitCollection = inputcol
    calodigicol.OutputCaloHitCollection = outputcol
    calodigicol.RelationOutputCollection = relcol

    calodigicol.CalibrECAL = [37.5227197175, 37.5227197175]
    calodigicol.ECALEndcapCorrectionFactor = 1.03245503522
    calodigicol.ECALBarrelTimeWindowMax = 10.0
    calodigicol.ECALEndcapTimeWindowMax = 10.0
    calodigicol.CalibrHCALBarrel = [45.9956826061]
    calodigicol.CalibrHCALEndcap = [46.9252540291]
    calodigicol.CalibrHCALOther = [57.4588011802]
    calodigicol.HCALBarrelTimeWindowMax = 10.0
    calodigicol.HCALEndcapTimeWindowMax = 10.0

    calodigicol.energyPerEHpair = 3.6
    # ECAL
    calodigicol.IfDigitalEcal = 0
    calodigicol.ECALLayers = [48, 48]
    calodigicol.ECAL_default_layerConfig = "000000000000000"
    calodigicol.StripEcal_default_nVirtualCells = 9
    calodigicol.CalibECALMIP = 0.0001
    calodigicol.ECALThreshold = 5.0e-5
    calodigicol.ECALThresholdUnit = "GeV"
    calodigicol.ECALGapCorrection = 1
    calodigicol.ECALGapCorrectionFactor = 1
    calodigicol.ECALModuleGapCorrectionFactor = 0.0
    calodigicol.MapsEcalCorrection = 0
    calodigicol.ECAL_PPD_N_Pixels = 10000
    calodigicol.ECAL_PPD_N_Pixels_uncertainty = 0.05
    calodigicol.ECAL_PPD_PE_per_MIP = 7.0
    calodigicol.ECALApplyRealisticDigi = 0
    calodigicol.ECAL_deadCellRate = 0.0
    calodigicol.ECAL_deadCell_memorise = False
    calodigicol.ECAL_elec_noise_mips = 0.0
    calodigicol.ECAL_maxDynamicRange_MIP = 2500.0
    calodigicol.ECAL_miscalibration_correl = 0.0
    calodigicol.ECAL_miscalibration_uncorrel = 0.0
    calodigicol.ECAL_miscalibration_uncorrel_memorise = False
    calodigicol.ECAL_pixel_spread = 0.05
    calodigicol.ECAL_strip_absorbtionLength = 1.0e6
    calodigicol.UseEcalTiming = 1
    calodigicol.ECALCorrectTimesForPropagation = 1
    calodigicol.ECALTimeWindowMin = -1.0
    calodigicol.ECALSimpleTimingCut = True
    calodigicol.ECALDeltaTimeHitResolution = 10.0
    calodigicol.ECALTimeResolution = 10.0
    # HCAL
    calodigicol.IfDigitalHcal = 0
    calodigicol.HCALLayers = [36]
    calodigicol.CalibHCALMIP = 1.0e-4
    calodigicol.HCALThreshold = [0.00025]
    calodigicol.HCALThresholdUnit = "GeV"
    calodigicol.HCALEndcapCorrectionFactor = 1.000
    calodigicol.HCALGapCorrection = 1
    calodigicol.HCALModuleGapCorrectionFactor = 0.5
    calodigicol.HCAL_PPD_N_Pixels = 400
    calodigicol.HCAL_PPD_N_Pixels_uncertainty = 0.05
    calodigicol.HCAL_PPD_PE_per_MIP = 10.0
    calodigicol.HCALApplyRealisticDigi = 0
    calodigicol.HCAL_deadCellRate = 0.0
    calodigicol.HCAL_deadCell_memorise = False
    calodigicol.HCAL_elec_noise_mips = 0.0
    calodigicol.HCAL_maxDynamicRange_MIP = 200.0
    calodigicol.HCAL_miscalibration_correl = 0.0
    calodigicol.HCAL_miscalibration_uncorrel = 0.0
    calodigicol.HCAL_miscalibration_uncorrel_memorise = False
    calodigicol.HCAL_pixel_spread = 0.0
    calodigicol.UseHcalTiming = 1
    calodigicol.HCALCorrectTimesForPropagation = 1
    calodigicol.HCALTimeWindowMin = -1.0
    calodigicol.HCALSimpleTimingCut = True
    calodigicol.HCALDeltaTimeHitResolution = 10.0
    calodigicol.HCALTimeResolution = 10.0


merger = CollectionMerger(
    "CollectionMerger",
    InputCollections=[
        "digiLinkCaloHitECALBarrel",
        "digiLinkCaloHitECALEndcap",
        "digiLinkCaloHitHCALBarrel",
        "digiLinkCaloHitHCALEndcap",
    ],
    OutputCollection=["digiRelationCaloHit"],
)

hps = RootHistSvc("HistogramPersistencySvc")
root_hist_svc = RootHistoSink("RootHistoSink")
root_hist_svc.FileName = "ddcalodigi_hist.root"

ApplicationMgr(
    TopAlg=calodigi + [merger],
    EvtSel="NONE",
    EvtMax=100,
    ExtSvc=[EventDataSvc("EventDataSvc"), root_hist_svc],
    OutputLevel=INFO,
)
