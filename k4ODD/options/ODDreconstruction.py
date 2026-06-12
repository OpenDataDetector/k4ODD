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


# --- DEFAULTS = the calibrated REALISTIC-digi constants (options/calib_constants_real.env,
# --- derivation in doc/CALIBRATION_JOURNAL.md): realistic ECAL(Si)/HCAL(SiPM) digitisation ON,
# --- EM scale 1.0307, ECAL->Had 1.10 / HCAL->Had 1.90 (R1 rebalance). Override via env for sweeps.
# --- Calibration knobs: env-overridable so the calibration loop can sweep digi +
# --- Pandora constants without editing this file. Defaults reproduce the prior values.
def _env_float(name, default):
    v = os.environ.get(name)
    return float(v) if v not in (None, "") else float(default)


def _env_int(name, default):
    v = os.environ.get(name)
    return int(v) if v not in (None, "") else int(default)


def _env_floats(name, default):
    """Parse a comma/space-separated list of floats from env; else return default list."""
    v = os.environ.get(name)
    if v in (None, ""):
        return list(default)
    return [float(x) for x in v.replace(",", " ").split()]


def resolve_path(filename):
    from pathlib import Path

    path = Path(filename)
    if path.is_absolute() or path.parent != Path("."):
        return str(path)

    output_dir = os.environ.get("K4ODD_OUTPUT_DIR")
    if output_dir:
        return str(Path(output_dir) / path.name)

    return filename


parser_group = parser.add_argument_group("ODDreconstruction.py custom options")
parser_group.add_argument("--inputFile", default="ODD_sim_edm4hep.root", help="Input file")
parser_group.add_argument("--outputFile", help="Output file", default="ODD_calo_digi.root")
parser_group.add_argument("--events", type=int, default=int(os.environ.get("K4ODD_EVENTS", 100)),
                          help="Event maximum (-1 = all)")
parser_group.add_argument(
    "--pandoraPhotonTraining",
    action="store_true",
    help="Enable PhotonReconstruction PDF training mode.",
)
digi_args = parser.parse_known_args()[0]
digi_args.inputFile = resolve_path(digi_args.inputFile)
digi_args.outputFile = resolve_path(digi_args.outputFile)

iosvc = IOSvc()
iosvc.Input = digi_args.inputFile
iosvc.Output = digi_args.outputFile

id_service = UniqueIDGenSvc("UniqueIDGenSvc")

geoservice = GeoSvc("GeoSvc")


def resolve_odd_xml():
    from pathlib import Path

    install_dir = os.environ.get("ODD_INSTALL_DIR")
    if install_dir:
        candidate = Path(install_dir) / "share" / "OpenDataDetector" / "xml" / "OpenDataDetector.xml"
        if candidate.is_file():
            return str(candidate)

    repo_dir = os.environ.get("OpenDataDetector")
    if repo_dir:
        repo_path = Path(repo_dir)
        preferred = [repo_path / "install-ci", repo_path / "install"]
        installs = sorted(repo_path.glob("install-*"))
        for candidate_dir in preferred + installs:
            candidate = candidate_dir / "share" / "OpenDataDetector" / "xml" / "OpenDataDetector.xml"
            if candidate.is_file():
                return str(candidate)

    return "OpenDataDetector/install/share/OpenDataDetector/xml/OpenDataDetector.xml"


geoservice.detectors = [resolve_odd_xml()]

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

    calodigicol.CalibrECAL = _env_floats("K4ODD_CALIBR_ECAL", [37.5227197175, 37.5227197175])
    calodigicol.ECALEndcapCorrectionFactor = _env_float("K4ODD_ECAL_ENDCAP_CORR", 1.03245503522)
    calodigicol.ECALBarrelTimeWindowMax = 10.0
    calodigicol.ECALEndcapTimeWindowMax = 10.0
    calodigicol.CalibrHCALBarrel = _env_floats("K4ODD_CALIBR_HCAL_BARREL", [45.9956826061])
    calodigicol.CalibrHCALEndcap = _env_floats("K4ODD_CALIBR_HCAL_ENDCAP", [46.9252540291])
    calodigicol.CalibrHCALOther = _env_floats("K4ODD_CALIBR_HCAL_OTHER", [57.4588011802])
    calodigicol.HCALBarrelTimeWindowMax = 10.0
    calodigicol.HCALEndcapTimeWindowMax = 10.0

    calodigicol.energyPerEHpair = 3.6
    # ECAL
    calodigicol.IfDigitalEcal = 0
    calodigicol.ECALLayers = [48, 48]
    # One '0' (=silicon, SIECAL) per ECAL layer. The ODD ECAL is 48 Si-W layers; DDCaloDigi
    # pushes 2 layerTypes per char and the barrel/endcap branch indexes m_layerTypes[layer+1],
    # so the string must yield >= 49 entries or layers >=29 fall back to (-99,-99) and the
    # silicon realistic-digi guard (apply_realistic_digi=1) errors out (no-op). 48 zeros -> 96
    # entries covers all layers. (CLD's 15-char string only works because they run ECAL digi off.)
    calodigicol.ECAL_default_layerConfig = "0" * 48
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
    calodigicol.ECAL_apply_realistic_digi = _env_int("K4ODD_ECAL_REALISTIC_DIGI", 1)
    calodigicol.ECAL_deadCellRate = _env_float("K4ODD_ECAL_DEADCELL_RATE", 0.0)
    calodigicol.ECAL_deadCell_memorise = False
    calodigicol.ECAL_elec_noise_mips = _env_float("K4ODD_ECAL_NOISE_MIPS", 0.0)
    calodigicol.ECAL_maxDynamicRange_MIP = 2500.0
    calodigicol.ECAL_miscalibration_correl = 0.0
    calodigicol.ECAL_miscalibration_uncorrel = _env_float("K4ODD_ECAL_MISCAL", 0.0)
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
    calodigicol.HCALEndcapCorrectionFactor = _env_float("K4ODD_HCAL_ENDCAP_CORR", 1.000)
    calodigicol.HCALGapCorrection = 1
    calodigicol.HCALModuleGapCorrectionFactor = 0.5
    calodigicol.HCAL_PPD_N_Pixels = 400
    calodigicol.HCAL_PPD_N_Pixels_uncertainty = 0.05
    calodigicol.HCAL_PPD_PE_per_MIP = 10.0
    calodigicol.HCAL_apply_realistic_digi = _env_int("K4ODD_HCAL_REALISTIC_DIGI", 1)
    calodigicol.HCAL_deadCellRate = _env_float("K4ODD_HCAL_DEADCELL_RATE", 0.0)
    calodigicol.HCAL_deadCell_memorise = False
    calodigicol.HCAL_elec_noise_mips = _env_float("K4ODD_HCAL_NOISE_MIPS", 0.0)
    calodigicol.HCAL_maxDynamicRange_MIP = 200.0
    calodigicol.HCAL_miscalibration_correl = 0.0
    calodigicol.HCAL_miscalibration_uncorrel = _env_float("K4ODD_HCAL_MISCAL", 0.0)
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

# Track-creator selection. Set K4ODD_TRACK_CREATOR=DDTrackCreatorCLIC and
# K4ODD_TRACK_COLLECTION=<name> (e.g. ActsTracks) to feed reconstructed tracks
# from ACTS into Pandora; defaults preserve the calo-only path.
_track_creator_name = os.environ.get("K4ODD_TRACK_CREATOR", "DDTrackCreatorEmpty")
_track_collection_name = os.environ.get("K4ODD_TRACK_COLLECTION", "EmptyTracks")

options_dir = os.path.dirname(os.path.abspath(__file__))
pandora_settings = os.environ.get(
    "K4ODD_PANDORA_SETTINGS",
    os.path.join(options_dir, "PandoraSettingsMinimal.xml"),
)


def resolve_pandora_settings_xml(pandora_settings_file, photon_training):
    if photon_training and os.path.basename(pandora_settings_file) == "PandoraSettingsMinimal.xml":
        pandora_settings_file = os.path.join(options_dir, "PandoraSettingsPhotonTraining.xml")

    return os.path.abspath(pandora_settings_file)


pandora_settings = resolve_pandora_settings_xml(
    pandora_settings,
    digi_args.pandoraPhotonTraining,
)

params = {
    "FinalEnergyDensityBin": 110.0,
    "MaxClusterEnergyToApplySoftComp": 200.0,
    "TrackCollections": [_track_collection_name],
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
    # NOTE: ACTS's EDM4hepTrackOutputConverter writes an inflated omega covariance
    # (sigma(p)/p ~ 2-3 for clean 10 GeV / 27-hit / chi2/ndf<1 tracks; the omega VALUE
    # is correct, only its error estimate is ~5e4x too large). The physical default
    # 0.15 therefore drops every good ACTS track. Override via K4ODD_MAX_TRACK_SIGMA_POVERP
    # (set high, e.g. 999, for ACTS-track runs) until the covariance conversion is fixed.
    "MaxTrackSigmaPOverP": float(os.environ.get("K4ODD_MAX_TRACK_SIGMA_POVERP", "0.15")),
    "CurvatureToMomentumFactor": 0.00015,
    "D0TrackCut": 200,
    "D0UnmatchedVertexTrackCut": 5,
    "StartVertexAlgorithmName": "PandoraPFANew",
    "StartVertexCollectionName": ["GaudiPandoraStartVertices"],
    "YokeBarrelNormalVector": [0, 0, 1],
    "HCalBarrelNormalVector": [0, 0, 1],
    "ECalBarrelNormalVector": [0, 0, 1],


    "EMConstantTerm": _env_float("K4ODD_EM_CONST", 0.01),
    "EMStochasticTerm": _env_float("K4ODD_EM_STOCH", 0.17),
    "HadConstantTerm": _env_float("K4ODD_HAD_CONST", 0.03),
    "HadStochasticTerm": _env_float("K4ODD_HAD_STOCH", 0.6),
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
    "TrackCreatorName": _track_creator_name,
    "UseDD4hepField": True,
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
    "SoftwareCompensationWeights": _env_floats(
        "K4ODD_SOFTCOMP_WEIGHTS",
        [
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
    ),
    "ECalToMipCalibration": "175.439",
    "HCalToMipCalibration": "45.6621",
    "ECalMipThreshold": "0.5",
    "HCalMipThreshold": "0.3",
    "ECalToEMGeVCalibration": _env_float("K4ODD_ECAL_EM_SCALE", 1.0307411173318997),
    "HCalToEMGeVCalibration": _env_float("K4ODD_HCAL_EM_SCALE", 1.0307411173318997),
    "ECalToHadGeVCalibrationBarrel": _env_float("K4ODD_ECAL_HAD_SCALE_BARREL", 1.10),
    "ECalToHadGeVCalibrationEndCap": _env_float("K4ODD_ECAL_HAD_SCALE_ENDCAP", 1.10),
    "HCalToHadGeVCalibration": _env_float("K4ODD_HCAL_HAD_SCALE", 1.90),
    "MuonToMipCalibration": "20703.9",
    "DigitalMuonHits": "0",
    "MaxHCalHitHadronicEnergy": "10000000.",
}

_pandora_level = DEBUG if os.environ.get("K4ODD_PANDORA_DEBUG") else INFO
pandora = DDPandoraPFANewAlgorithm("PandoraPFANewProcessor", **params, OutputLevel=_pandora_level)

hps = RootHistSvc("HistogramPersistencySvc")
root_hist_svc = RootHistoSink("RootHistoSink")
root_hist_svc.FileName = resolve_path("ddcalodigi_hist.root")

evt_max = -1 if digi_args.pandoraPhotonTraining else digi_args.events

ApplicationMgr(
    TopAlg=calodigi + [merger, tracks, pandora],
    EvtSel="NONE",
    EvtMax=evt_max,
    ExtSvc=[EventDataSvc("EventDataSvc"), root_hist_svc],
    OutputLevel=INFO,
)
