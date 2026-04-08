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
from Gaudi.Configuration import INFO, DEBUG, VERBOSE
from k4FWCore import ApplicationMgr, IOSvc
from Configurables import EventDataSvc
from Configurables import DDCaloDigi, CollectionMerger
from Configurables import CreateEmptyTracks
from Configurables import DDPandoraPFANewAlgorithm

from Configurables import GeoSvc
from Configurables import UniqueIDGenSvc
from Configurables import RootHistSvc
from Configurables import Gaudi__Histograming__Sink__Root as RootHistoSink
import os

from k4FWCore.parseArgs import parser
parser_group = parser.add_argument_group("ODDreconstruction.py custom options")
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
    calodigicol.ECAL_apply_realistic_digi = 0
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
    calodigicol.HCAL_apply_realistic_digi = 0
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

tracks = CreateEmptyTracks("CreateEmptyTracks")

options_dir = os.path.dirname(os.path.abspath(__file__))
pandora_settings = os.environ.get(
    "K4ODD_PANDORA_SETTINGS",
    os.path.join(options_dir, "PandoraSettingsSanity.xml"),
)

params = {
    "FinalEnergyDensityBin": 110.0,
    "MaxClusterEnergyToApplySoftComp": 200.0,
    "TrackCollections": ["EmptyTracks"],
    "ECalCaloHitCollections": ["digiECalBarrelCollection", "digiECalEndcapCollection"],
    "HCalCaloHitCollections": ["digiHCalBarrelCollection", "digiHCalEndcapCollection"],
    "LCalCaloHitCollections": [],
    "LHCalCaloHitCollections": [],
    "MuonCaloHitCollections": [],
    "MCParticleCollections": ["MCParticles"],
    "RelCaloHitCollections": ["digiRelationCaloHit"],
    "RelTrackCollections": [],
    "KinkVertexCollections": [],
    "ProngVertexCollections": [],
    "SplitVertexCollections": [],
    "V0VertexCollections": [],
    "ClusterCollectionName": ["GaudiPandoraClusters"],
    "PFOCollectionName": ["GaudiPandoraPFOs"],
    "CreateGaps": False,
    "MinBarrelTrackerHitFractionOfExpected": 0,
    "MinFtdHitsForBarrelTrackerHitFraction": 0,
    "MinFtdTrackHits": 0,
    "MinMomentumForTrackHitChecks": 0,
    "MinTrackECalDistanceFromIp": 0,
    "MinTrackHits": 0,
    "ReachesECalBarrelTrackerOuterDistance": -100,
    "ReachesECalBarrelTrackerZMaxDistance": -50,
    "ReachesECalFtdZMaxDistance": 1,
    "ReachesECalMinFtdLayer": 0,
    "ReachesECalNBarrelTrackerHits": 0,
    "ReachesECalNFtdHits": 0,
    "UnmatchedVertexTrackMaxEnergy": 5,
    "UseNonVertexTracks": 1,
    "UseUnmatchedNonVertexTracks": 0,
    "UseUnmatchedVertexTracks": 1,
    "Z0TrackCut": 200,
    "Z0UnmatchedVertexTrackCut": 5,
    "ZCutForNonVertexTracks": 250,
    "MaxTrackHits": 5000,
    "MaxTrackSigmaPOverP": 0.15,
    "CurvatureToMomentumFactor": 0.00015,
    "D0TrackCut": 200,
    "D0UnmatchedVertexTrackCut": 5,
    "StartVertexAlgorithmName": "PandoraPFANew",
    "StartVertexCollectionName": ["GaudiPandoraStartVertices"],
    "YokeBarrelNormalVector": [0, 0, 1],
    "HCalBarrelNormalVector": [0, 0, 1],
    "ECalBarrelNormalVector": [0, 0, 1],


    "EMConstantTerm": 0.01,
    "EMStochasticTerm": 0.17,
    "HadConstantTerm": 0.03,
    "HadStochasticTerm": 0.6,
    "InputEnergyCorrectionPoints": [],
    "LayersFromEdgeMaxRearDistance": 250,
    "NOuterSamplingLayers": 3,
    "TrackStateTolerance": 0,
    "MaxBarrelTrackerInnerRDistance": 200,
    "MinCleanCorrectedHitEnergy": 0.1,
    "MinCleanHitEnergy": 0.5,
    "MinCleanHitEnergyFraction": 0.01,
    "MuonHitEnergy": 0.5,
    "ShouldFormTrackRelationships": 1,
    "TrackCreatorName": "DDTrackCreatorEmpty",
    "TrackSystemName": "",
    "OutputEnergyCorrectionPoints": [],
    "UseEcalScLayers": 0,
    "ECalScMipThreshold": 0,
    "ECalScToEMGeVCalibration": 1,
    "ECalScToHadGeVCalibrationBarrel": 1,
    "ECalScToHadGeVCalibrationEndCap": 1,
    "ECalScToMipCalibration": 1,
    "ECalSiMipThreshold": 0,
    "ECalSiToEMGeVCalibration": 1,
    "ECalSiToHadGeVCalibrationBarrel": 1,
    "ECalSiToHadGeVCalibrationEndCap": 1,
    "ECalSiToMipCalibration": 1,
    "StripSplittingOn": 0,
    # Settings for CalorimeterIntegrationTimeWindow = 10 ns
    "PandoraSettingsXmlFile": pandora_settings,
    "SoftwareCompensationWeights": [
        2.40821,
        -0.0515852,
        0.000711414,
        -0.0254891,
        -0.0121505,
        -1.63084e-05,
        0.062149,
        0.0690735,
        -0.223064,
    ],
    "ECalToMipCalibration": "175.439",
    "HCalToMipCalibration": "45.6621",
    "ECalMipThreshold": "0.5",
    "HCalMipThreshold": "0.3",
    "ECalToEMGeVCalibration": "1.01776966108",
    "HCalToEMGeVCalibration": "1.01776966108",
    "ECalToHadGeVCalibrationBarrel": "1.11490774181",
    "ECalToHadGeVCalibrationEndCap": "1.11490774181",
    "HCalToHadGeVCalibration": "1.00565042407",
    "MuonToMipCalibration": "20703.9",
    "DigitalMuonHits": "0",
    "MaxHCalHitHadronicEnergy": "10000000.",
}

pandora = DDPandoraPFANewAlgorithm("PandoraPFANewProcessor", **params, OutputLevel=VERBOSE)

hps = RootHistSvc("HistogramPersistencySvc")
root_hist_svc = RootHistoSink("RootHistoSink")
root_hist_svc.FileName = "ddcalodigi_hist.root"

ApplicationMgr(
    TopAlg=calodigi + [merger, tracks, pandora],
    EvtSel="NONE",
    EvtMax=100,
    ExtSvc=[EventDataSvc("EventDataSvc"), root_hist_svc],
    OutputLevel=VERBOSE,
)
