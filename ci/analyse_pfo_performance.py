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

import argparse
import numpy
import ROOT

parser = argparse.ArgumentParser(description="Analyse Pandora PFO output")
parser.add_argument("--infile", "-i", required=True, type=str, nargs="+", help="EDM4hep file to analyse")
parser.add_argument("-o", "--outfile", type=str, default="pfoAnalysis.root", help="output file")
parser.add_argument("-n", "--ncpus", type=int, default=2, help="Number of CPUs to use in analysis")
parser.add_argument(
    "--collection",
    type=str,
    default="GaudiPandoraPFOs",
    help="ReconstructedParticle collection to analyse",
)
args = parser.parse_args()

ROOT.gSystem.Load("libedm4hep")
ROOT.gInterpreter.Declare(
    """
#include "edm4hep/MCParticleData.h"
#include "edm4hep/ReconstructedParticleData.h"
#include <cmath>
"""
)


def run(inputlist, outname, ncpu, collection_name):
    if ".root" not in outname:
        outname += ".root"

    ROOT.ROOT.EnableImplicitMT(ncpu)
    df = ROOT.RDataFrame("events", inputlist)
    print("Initialization done")

    df_pfo = (
        df.Define(
            "pfoEnergy",
            f"ROOT::VecOps::RVec<float> result; for (auto& p : {collection_name}) {{ result.push_back(p.energy); }} return result;",
        )
        .Define(
            "pfoCharge",
            f"ROOT::VecOps::RVec<float> result; for (auto& p : {collection_name}) {{ result.push_back(p.charge); }} return result;",
        )
        .Define("sumPfoEnergy", "std::accumulate(pfoEnergy.begin(), pfoEnergy.end(), 0.)")
        .Define("leadPfoEnergy", "pfoEnergy.empty() ? 0.f : *std::max_element(pfoEnergy.begin(), pfoEnergy.end())")
        .Define("nPfo", "static_cast<int>(pfoEnergy.size())")
        .Define(
            "nChargedPfo",
            "static_cast<int>(std::count_if(pfoCharge.begin(), pfoCharge.end(), [](float q) { return std::abs(q) > 1.e-6; }))",
        )
        .Define("nNeutralPfo", "nPfo - nChargedPfo")
        .Define(
            "gunMC",
            "std::sqrt(MCParticles[0].momentum.x * MCParticles[0].momentum.x + MCParticles[0].momentum.y * MCParticles[0].momentum.y + MCParticles[0].momentum.z * MCParticles[0].momentum.z)",
        )
        .Define("sumPfoRatio", "gunMC > 0 ? sumPfoEnergy / gunMC : 0.")
        .Define("leadPfoRatio", "gunMC > 0 ? leadPfoEnergy / gunMC : 0.")
    )

    h_n_pfo = df_pfo.Histo1D(("nPfo", "Number of Pandora PFOs;N PFOs;Events", 20, 0, 20), "nPfo")
    h_sum = df_pfo.Histo1D(("sumPfoEnergy", "Summed Pandora PFO energy;E [GeV];Events", 100, 0, 20), "sumPfoEnergy")
    h_sum_ratio = df_pfo.Histo1D(("sumPfoRatio", "Summed Pandora PFO energy / E_{MC};E_{PFO}/E_{MC};Events", 100, 0, 2), "sumPfoRatio")
    h_lead_ratio = df_pfo.Histo1D(("leadPfoRatio", "Leading Pandora PFO energy / E_{MC};E^{lead}_{PFO}/E_{MC};Events", 100, 0, 2), "leadPfoRatio")
    h_charged = df_pfo.Histo1D(("nChargedPfo", "Number of charged Pandora PFOs;N charged PFOs;Events", 20, 0, 20), "nChargedPfo")
    h_neutral = df_pfo.Histo1D(("nNeutralPfo", "Number of neutral Pandora PFOs;N neutral PFOs;Events", 20, 0, 20), "nNeutralPfo")

    print(f"PFO multiplicity: <N>= {h_n_pfo.GetMean()}\t RMS= {h_n_pfo.GetRMS()}")
    print(f"Summed PFO energy: <E>= {h_sum.GetMean()}\t RMS= {h_sum.GetRMS()}")
    print(f"Summed PFO response: <E_PFO/E_MC>= {h_sum_ratio.GetMean()}\t RMS= {h_sum_ratio.GetRMS()}")
    print(f"Leading PFO response: <E_lead/E_MC>= {h_lead_ratio.GetMean()}\t RMS= {h_lead_ratio.GetRMS()}")
    print(f"Charged PFO multiplicity: <N>= {h_charged.GetMean()}")
    print(f"Neutral PFO multiplicity: <N>= {h_neutral.GetMean()}")

    outfile = ROOT.TFile(outname, "RECREATE")
    outfile.cd()
    h_n_pfo.Write()
    h_sum.Write()
    h_sum_ratio.Write()
    h_lead_ratio.Write()
    h_charged.Write()
    h_neutral.Write()

    store_mean_n_pfo = numpy.zeros(1, dtype=float)
    store_mean_sum_e = numpy.zeros(1, dtype=float)
    store_mean_sum_ratio = numpy.zeros(1, dtype=float)
    store_mean_lead_ratio = numpy.zeros(1, dtype=float)
    store_mean_charged = numpy.zeros(1, dtype=float)
    store_mean_neutral = numpy.zeros(1, dtype=float)
    tree = ROOT.TTree("results", "PFO summary")
    tree.Branch("mean_n_pfo", store_mean_n_pfo, "mean_n_pfo/D")
    tree.Branch("mean_sum_energy", store_mean_sum_e, "mean_sum_energy/D")
    tree.Branch("mean_sum_ratio", store_mean_sum_ratio, "mean_sum_ratio/D")
    tree.Branch("mean_lead_ratio", store_mean_lead_ratio, "mean_lead_ratio/D")
    tree.Branch("mean_n_charged", store_mean_charged, "mean_n_charged/D")
    tree.Branch("mean_n_neutral", store_mean_neutral, "mean_n_neutral/D")
    store_mean_n_pfo[0] = h_n_pfo.GetMean()
    store_mean_sum_e[0] = h_sum.GetMean()
    store_mean_sum_ratio[0] = h_sum_ratio.GetMean()
    store_mean_lead_ratio[0] = h_lead_ratio.GetMean()
    store_mean_charged[0] = h_charged.GetMean()
    store_mean_neutral[0] = h_neutral.GetMean()
    tree.Fill()
    tree.Write()
    outfile.Close()

    canv = ROOT.TCanvas()
    canv.cd()
    h_sum.Draw()
    canv.SaveAs(f"preview_pfoEnergyFit_{inputlist[0].split('/')[-1:][0][:-5]}.pdf")


if __name__ == "__main__":
    run(args.infile, args.outfile, args.ncpus, args.collection)
