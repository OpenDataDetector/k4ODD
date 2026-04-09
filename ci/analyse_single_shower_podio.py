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
from math import sqrt

import numpy
import ROOT
from podio.data_source import CreateDataFrame

parser = argparse.ArgumentParser(description="Analyse calo shower data")
parser.add_argument("--infile", "-i", required=True, type=str, nargs="+", help="EDM4hep file to analyse")
parser.add_argument("-o", "--outfile", type=str, default="showerAnalysis.root", help="output file")
parser.add_argument("-n", "--ncpus", type=int, default=2, help="Number of CPUs to use in analysis")
parser.add_argument("--endcap", action="store_true", help="Perform analysis for endcap instead of barrel")
parser.add_argument("--hcal", action="store_true", help="Perform analysis for HCal instead of ECal")
parser.add_argument("--digi", action="store_true", help="Perform analysis for digitised hits instead of sim")
args = parser.parse_args()

ROOT.gSystem.Load("libedm4hep")
ROOT.gInterpreter.Declare(
    """
#include "edm4hep/SimCalorimeterHitCollection.h"
#include "edm4hep/CalorimeterHitCollection.h"
#include "edm4hep/MCParticleCollection.h"
"""
)


def run(inputlist, outname, ncpu, endcap_instead_of_barrel, hcal_instead_of_ecal):
    if ".root" not in outname:
        outname += ".root"
    collname = "Endcap" if endcap_instead_of_barrel else "Barrel"
    collprefix = "digi" if args.digi else ""

    ROOT.ROOT.EnableImplicitMT(ncpu)
    df = CreateDataFrame(inputlist)
    print("Initialization done")

    if hcal_instead_of_ecal:
        h_cal = (
            df.Define(
                "edepEcal",
                f"ROOT::VecOps::RVec<float> result; for (auto p: {collprefix}ECal{collname}Collection) {{ result.push_back(p.getEnergy()); }} return result;",
            )
            .Define("sumEdepEcal", "std::accumulate(edepEcal.begin(), edepEcal.end(), 0.)")
            .Define(
                "edepHcal",
                f"ROOT::VecOps::RVec<float> result; for (auto p: {collprefix}HCal{collname}Collection) {{ result.push_back(p.getEnergy()); }} return result;",
            )
            .Define("sumEdepHcal", "std::accumulate(edepHcal.begin(), edepHcal.end(), 0.)")
            .Define("sumEdep", "sumEdepEcal+sumEdepHcal")
            .Histo1D("sumEdep")
        )
    else:
        h_cal = (
            df.Define(
                "edep",
                f"ROOT::VecOps::RVec<float> result; for (auto p: {collprefix}ECal{collname}Collection) {{ result.push_back(p.getEnergy()); }} return result;",
            )
            .Define("sumEdep", "std::accumulate(edep.begin(),edep.end(),0.)")
            .Histo1D("sumEdep")
        )

    h_mc = (
        df.Define(
            "eMC",
            "ROOT::VecOps::RVec<float> result; for(auto m:MCParticles){const auto mom=m.getMomentum(); result.push_back(sqrt(mom.x*mom.x+mom.y*mom.y+mom.z*mom.z));} return result;",
        )
        .Define("gunMC", "eMC[0]")
        .Histo1D("gunMC")
    )

    if hcal_instead_of_ecal:
        h_ratio = (
            df.Define(
                "edepEcal",
                f"ROOT::VecOps::RVec<float> result; for (auto p: {collprefix}ECal{collname}Collection) {{ result.push_back(p.getEnergy()); }} return result;",
            )
            .Define("sumEdepEcal", "std::accumulate(edepEcal.begin(),edepEcal.end(),0.)")
            .Define(
                "edepHcal",
                f"ROOT::VecOps::RVec<float> result; for (auto p: {collprefix}HCal{collname}Collection) {{ result.push_back(p.getEnergy()); }} return result;",
            )
            .Define("sumEdepHcal", "std::accumulate(edepHcal.begin(),edepHcal.end(),0.)")
            .Define("sumEdep", "sumEdepEcal+sumEdepHcal")
            .Define(
                "eMC",
                "ROOT::VecOps::RVec<float> result; for(auto m:MCParticles){const auto mom=m.getMomentum(); result.push_back(sqrt(mom.x*mom.x+mom.y*mom.y+mom.z*mom.z));} return result;",
            )
            .Define("gunMC", "eMC[0]")
            .Define("eratio", "sumEdep/gunMC")
            .Histo1D("eratio")
        )
    else:
        h_ratio = (
            df.Define(
                "edep",
                f"ROOT::VecOps::RVec<float> result; for (auto p: {collprefix}ECal{collname}Collection) {{ result.push_back(p.getEnergy()); }} return result;",
            )
            .Define("sumEdep", "std::accumulate(edep.begin(),edep.end(),0.)")
            .Define(
                "eMC",
                "ROOT::VecOps::RVec<float> result; for(auto m:MCParticles){const auto mom=m.getMomentum(); result.push_back(sqrt(mom.x*mom.x+mom.y*mom.y+mom.z*mom.z));} return result;",
            )
            .Define("gunMC", "eMC[0]")
            .Define("eratio", "sumEdep/gunMC")
            .Histo1D("eratio")
        )

    print(f"E distribution in Cal: <E>= {h_cal.GetMean()}\t RMS= {h_cal.GetRMS()}")
    print(f"E distribution MC particles: E_MC= {h_mc.GetMean()}\t RMS= {h_mc.GetRMS()}")
    print(f"sampling fraction calculated as <E>/E_MC: {h_ratio.GetMean()}")
    gun_mean = h_mc.GetMean()

    f_prefit = ROOT.TF1("firstGaus", "gaus", h_cal.GetMean() - 2.0 * h_cal.GetRMS(), h_cal.GetMean() + 2.0 * h_cal.GetRMS())
    result_pre = h_cal.Fit(f_prefit, "SRQN")
    f_fit = ROOT.TF1(
        "finalGaus",
        "gaus",
        result_pre.Get().Parameter(1) - 2.0 * result_pre.Get().Parameter(2),
        result_pre.Get().Parameter(1) + 2.0 * result_pre.Get().Parameter(2),
    )
    result = h_cal.Fit(f_fit, "SRQ")
    result_mean = result.Get().Parameter(1)
    result_mean_error = result.Get().Error(1)
    result_resolution = result.Get().Parameter(2) / result.Get().Parameter(1)
    tmp_resolution_error_sigma = result.Get().Error(2) / result.Get().Parameter(1)
    tmp_resolution_error_mean = result.Get().Error(1) * result.Get().Parameter(2) / (result.Get().Parameter(1) ** 2)
    result_resolution_error = sqrt(tmp_resolution_error_sigma ** 2 + tmp_resolution_error_mean ** 2)

    outfile = ROOT.TFile(outname, "RECREATE")
    outfile.cd()
    h_cal.Write("energy_cal")
    h_mc.Write("energy_MC0")
    h_ratio.Write("energy_ratio")
    store_mean = numpy.zeros(1, dtype=float)
    store_mean_err = numpy.zeros(1, dtype=float)
    store_resolution = numpy.zeros(1, dtype=float)
    store_resolution_err = numpy.zeros(1, dtype=float)
    store_emc = numpy.zeros(1, dtype=float)
    tree = ROOT.TTree("results", "Fit parameters and E_MC")
    tree.Branch("en_mean", store_mean, "store_mean/D")
    tree.Branch("en_meanErr", store_mean_err, "store_meanErr/D")
    tree.Branch("en_resolution", store_resolution, "store_resolution/D")
    tree.Branch("en_resolutionErr", store_resolution_err, "store_resolutionErr/D")
    tree.Branch("enMC", store_emc, "store_EMC/D")
    store_mean[0] = result_mean
    store_mean_err[0] = result_mean_error
    store_resolution[0] = result_resolution
    store_resolution_err[0] = result_resolution_error
    store_emc[0] = gun_mean
    tree.Fill()
    tree.Write()
    outfile.Close()

    canv = ROOT.TCanvas()
    canv.cd()
    h_cal.Draw()
    canv.SaveAs(f"preview_energyFit_{inputlist[0].split('/')[-1:][0][:-5]}.pdf")


if __name__ == "__main__":
    run(args.infile, args.outfile, args.ncpus, args.endcap, args.hcal)
