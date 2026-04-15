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

import argparse
import math
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from statistics import pstdev


parser = argparse.ArgumentParser(description="Analyse gamma conversion truth vs reconstructed PFO IDs")
parser.add_argument("--infile", "-i", required=True, type=str, nargs="+", help="EDM4hep file to analyse")
parser.add_argument(
    "--collection",
    type=str,
    default="GaudiPandoraPFOs",
    help="ReconstructedParticle collection to analyse",
)
parser.add_argument(
    "--rmin-mm",
    type=float,
    default=None,
    help=(
        "Override the ECAL barrel inner radius in mm. "
        "By default this is read from OpenDataDetectorEnvelopes.xml "
        "(constant ecal_b_rmin)."
    ),
)
parser.add_argument(
    "--zmin-mm",
    type=float,
    default=None,
    help=(
        "Override the ECAL endcap inner z in mm. "
        "By default this is read from OpenDataDetectorEnvelopes.xml "
        "(constant ecal_e_min_z)."
    ),
)
parser.add_argument(
    "--plots-dir",
    type=str,
    default="plots",
    help=(
        "Directory for the unconverted gamma shower-shape canvases. "
        "Relative paths are resolved via K4ODD_OUTPUT_DIR. Existing files are overwritten."
    ),
)
args = parser.parse_args()


def resolve_path(filename):
    if os.path.isabs(filename) or os.path.dirname(filename):
        return filename

    output_dir = os.environ.get("K4ODD_OUTPUT_DIR")
    if output_dir:
        return os.path.join(output_dir, filename)

    return filename


@dataclass
class Stats:
    events: int = 0
    total_pfos: int = 0
    photon_pfos: int = 0
    neutron_pfos: int = 0
    other_pfos: int = 0
    sum_response: float = 0.0
    sum_multiplicity: float = 0.0
    binned_total_pfos: dict | None = None
    binned_photon_pfos: dict | None = None
    binned_neutron_pfos: dict | None = None


@dataclass
class ShowerObservables:
    ecal_barrel_fraction: float
    ecal_endcap_fraction: float
    hcal_barrel_fraction: float
    hcal_endcap_fraction: float
    shower_start_layer: float
    longitudinal_maximum: float
    occupied_layers: float
    transverse_width: float
    transverse_second_moment: float
    total_hit_count: float


ENERGY_BINS_GEV = [
    ("<1", 0.0, 1.0),
    ("1-5", 1.0, 5.0),
    ("5-10", 5.0, 10.0),
    ("10-20", 10.0, 20.0),
    ("20-50", 20.0, 50.0),
    (">50", 50.0, None),
]


def make_energy_bin_counter():
    return {label: 0 for label, _, _ in ENERGY_BINS_GEV}


def get_energy_bin_label(energy_gev):
    for label, low, high in ENERGY_BINS_GEV:
        if energy_gev < low:
            continue
        if high is None or energy_gev < high:
            return label
    return ENERGY_BINS_GEV[-1][0]


VARIABLE_SPECS = [
    ("ecal_barrel_fraction", "ECAL barrel energy fraction", 50),
    ("ecal_endcap_fraction", "ECAL endcap energy fraction", 50),
    ("hcal_barrel_fraction", "HCAL barrel energy fraction", 50),
    ("hcal_endcap_fraction", "HCAL endcap energy fraction", 50),
    ("shower_start_layer", "Shower start pseudo-layer", 60),
    ("longitudinal_maximum", "Longitudinal maximum pseudo-layer", 60),
    ("occupied_layers", "Number of occupied pseudo-layers", 60),
    ("transverse_width", "Transverse width [mm]", 80),
    ("transverse_second_moment", "Transverse second moment [mm^{2}]", 80),
    ("total_hit_count", "Total hit count", 160),
]


def make_shape_store():
    return {
        energy_label: {"gamma": {var: [] for var, *_ in VARIABLE_SPECS}, "neutron": {var: [] for var, *_ in VARIABLE_SPECS}}
        for energy_label, _, _ in ENERGY_BINS_GEV
    }


def find_primary_gamma(mc_particles):
    for particle in mc_particles:
        if particle.getGeneratorStatus() == 1 and particle.getPDG() == 22:
            return particle

    for particle in mc_particles:
        if particle.getPDG() == 22 and len(list(particle.getParents())) == 0:
            return particle

    return None


def parse_length(expression):
    match = re.fullmatch(r"\s*([0-9]+(?:\.[0-9]+)?)\.?\s*\*\s*(mm|cm|m)\s*", expression)
    if not match:
        raise ValueError(f"Unsupported length expression: {expression}")

    value = float(match.group(1))
    unit = match.group(2)
    scale = {"mm": 1.0, "cm": 10.0, "m": 1000.0}[unit]
    return value * scale


def find_envelope_xml():
    candidates = []

    odd_install_dir = os.environ.get("ODD_INSTALL_DIR")
    if odd_install_dir:
        candidates.append(os.path.join(odd_install_dir, "share", "OpenDataDetector", "xml", "OpenDataDetectorEnvelopes.xml"))

    odd_repo = os.environ.get("OpenDataDetector") or os.environ.get("ODD_DIR")
    if odd_repo:
        candidates.append(os.path.join(odd_repo, "xml", "OpenDataDetectorEnvelopes.xml"))

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    candidates.append(os.path.join(repo_root, "OpenDataDetector", "xml", "OpenDataDetectorEnvelopes.xml"))

    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate

    raise FileNotFoundError("Could not locate OpenDataDetectorEnvelopes.xml")


def load_ecal_boundaries():
    envelope_xml = find_envelope_xml()
    tree = ET.parse(envelope_xml)
    root = tree.getroot()
    constants = {
        node.attrib["name"]: parse_length(node.attrib["value"])
        for node in root.findall(".//constant")
        if node.attrib.get("name") in {"ecal_b_rmin", "ecal_e_min_z"}
    }

    if "ecal_b_rmin" not in constants or "ecal_e_min_z" not in constants:
        raise RuntimeError(f"Missing ECAL boundary constants in {envelope_xml}")

    return envelope_xml, constants["ecal_b_rmin"], constants["ecal_e_min_z"]


def is_before_ecal(vertex, ecal_barrel_rmin_mm, ecal_endcap_min_z_mm):
    radius = math.hypot(vertex.x, vertex.y)
    return radius < ecal_barrel_rmin_mm and abs(vertex.z) < ecal_endcap_min_z_mm


def has_pre_ecal_conversion(mc_particle, ecal_barrel_rmin_mm, ecal_endcap_min_z_mm):
    daughters = list(mc_particle.getDaughters())
    if not daughters:
        return False

    electrons = [daughter for daughter in daughters if daughter.getPDG() == 11]
    positrons = [daughter for daughter in daughters if daughter.getPDG() == -11]

    if electrons and positrons:
        vertex = electrons[0].getVertex()
        if is_before_ecal(vertex, ecal_barrel_rmin_mm, ecal_endcap_min_z_mm):
            return True

    for daughter in daughters:
        if daughter.getPDG() == 22 and has_pre_ecal_conversion(daughter, ecal_barrel_rmin_mm, ecal_endcap_min_z_mm):
            return True

    return False


def update_stats(stats, pfos, gun_energy):
    if stats.binned_total_pfos is None:
        stats.binned_total_pfos = make_energy_bin_counter()
        stats.binned_photon_pfos = make_energy_bin_counter()
        stats.binned_neutron_pfos = make_energy_bin_counter()

    stats.events += 1
    stats.total_pfos += len(pfos)
    stats.sum_multiplicity += len(pfos)
    stats.sum_response += sum(pfo.getEnergy() for pfo in pfos) / gun_energy if gun_energy > 0 else 0.0

    for pfo in pfos:
        pdg = pfo.getPDG()
        bin_label = get_energy_bin_label(pfo.getEnergy())
        stats.binned_total_pfos[bin_label] += 1
        if pdg == 22:
            stats.photon_pfos += 1
            stats.binned_photon_pfos[bin_label] += 1
        elif pdg == 2112:
            stats.neutron_pfos += 1
            stats.binned_neutron_pfos[bin_label] += 1
        else:
            stats.other_pfos += 1


def print_stats(label, stats):
    if stats.events == 0:
        print(f"{label}: no events")
        return

    photon_fraction = stats.photon_pfos / stats.total_pfos if stats.total_pfos else 0.0
    neutron_fraction = stats.neutron_pfos / stats.total_pfos if stats.total_pfos else 0.0
    other_fraction = stats.other_pfos / stats.total_pfos if stats.total_pfos else 0.0
    mean_response = stats.sum_response / stats.events
    mean_multiplicity = stats.sum_multiplicity / stats.events

    print(label)
    print(f"  events: {stats.events}")
    print(f"  mean PFO multiplicity: {mean_multiplicity}")
    print(f"  mean summed PFO response: {mean_response}")
    print(f"  photon PFO fraction (PDG 22): {photon_fraction}")
    print(f"  neutron PFO fraction (PDG 2112): {neutron_fraction}")
    print(f"  other PFO fraction: {other_fraction}")
    print(f"  total PFO counts: 22={stats.photon_pfos}, 2112={stats.neutron_pfos}, other={stats.other_pfos}")
    print("  reco PFO energy bins [GeV]: total, photons(22), neutrons(2112), photon_fraction")
    for label, _, _ in ENERGY_BINS_GEV:
        total = stats.binned_total_pfos[label]
        photons = stats.binned_photon_pfos[label]
        neutrons = stats.binned_neutron_pfos[label]
        fraction = photons / total if total else 0.0
        print(f"    {label}: total={total}, photons={photons}, neutrons={neutrons}, photon_fraction={fraction}")


def add_observables(target, energy_label, reco_label, observables):
    bucket = target[energy_label][reco_label]
    bucket["ecal_barrel_fraction"].append(observables.ecal_barrel_fraction)
    bucket["ecal_endcap_fraction"].append(observables.ecal_endcap_fraction)
    bucket["hcal_barrel_fraction"].append(observables.hcal_barrel_fraction)
    bucket["hcal_endcap_fraction"].append(observables.hcal_endcap_fraction)
    bucket["shower_start_layer"].append(observables.shower_start_layer)
    bucket["longitudinal_maximum"].append(observables.longitudinal_maximum)
    bucket["occupied_layers"].append(observables.occupied_layers)
    bucket["transverse_width"].append(observables.transverse_width)
    bucket["transverse_second_moment"].append(observables.transverse_second_moment)
    bucket["total_hit_count"].append(observables.total_hit_count)


def cluster_axis(cluster):
    theta = cluster.getITheta()
    phi = cluster.getIPhi()
    sin_theta = math.sin(theta)
    axis = (
        sin_theta * math.cos(phi),
        sin_theta * math.sin(phi),
        math.cos(theta),
    )
    norm = math.sqrt(sum(component * component for component in axis))
    if norm <= 0.0:
        pos = cluster.getPosition()
        norm = math.sqrt(pos.x * pos.x + pos.y * pos.y + pos.z * pos.z)
        if norm <= 0.0:
            return (0.0, 0.0, 1.0)
        return (pos.x / norm, pos.y / norm, pos.z / norm)
    return tuple(component / norm for component in axis)


def compute_cluster_observables(cluster):
    hits = list(cluster.getHits())
    if not hits:
        return None

    axis = cluster_axis(cluster)
    longitudinals = []
    transverse_r2 = []
    hit_energies = []

    for hit in hits:
        position = hit.getPosition()
        hit_vector = (position.x, position.y, position.z)
        longitudinal = sum(component * direction for component, direction in zip(hit_vector, axis))
        radius2 = sum(component * component for component in hit_vector) - longitudinal * longitudinal
        longitudinals.append(longitudinal)
        transverse_r2.append(max(radius2, 0.0))
        hit_energies.append(hit.getEnergy())

    longitudinal_min = min(longitudinals)
    layer_pitch_mm = 10.0
    pseudo_layers = [int((value - longitudinal_min) / layer_pitch_mm) for value in longitudinals]

    energy_per_layer = {}
    for layer, energy in zip(pseudo_layers, hit_energies):
        energy_per_layer[layer] = energy_per_layer.get(layer, 0.0) + energy

    total_energy = sum(hit_energies)
    if total_energy <= 0.0:
        total_energy = cluster.getEnergy()
    if total_energy <= 0.0:
        return None

    occupied_layers = len(energy_per_layer)
    shower_start_layer = min(energy_per_layer)
    longitudinal_maximum = max(energy_per_layer, key=energy_per_layer.get)
    second_moment = sum(energy * radius2 for energy, radius2 in zip(hit_energies, transverse_r2)) / total_energy
    transverse_width = math.sqrt(max(second_moment, 0.0))

    subdetector_energies = list(cluster.getSubdetectorEnergies())
    ecal_barrel_energy = subdetector_energies[0] if len(subdetector_energies) > 0 else 0.0
    ecal_endcap_energy = subdetector_energies[1] if len(subdetector_energies) > 1 else 0.0
    hcal_barrel_energy = subdetector_energies[2] if len(subdetector_energies) > 2 else 0.0
    hcal_endcap_energy = subdetector_energies[3] if len(subdetector_energies) > 3 else 0.0

    return ShowerObservables(
        ecal_barrel_fraction=ecal_barrel_energy / total_energy if total_energy > 0 else 0.0,
        ecal_endcap_fraction=ecal_endcap_energy / total_energy if total_energy > 0 else 0.0,
        hcal_barrel_fraction=hcal_barrel_energy / total_energy if total_energy > 0 else 0.0,
        hcal_endcap_fraction=hcal_endcap_energy / total_energy if total_energy > 0 else 0.0,
        shower_start_layer=float(shower_start_layer),
        longitudinal_maximum=float(longitudinal_maximum),
        occupied_layers=float(occupied_layers),
        transverse_width=transverse_width,
        transverse_second_moment=second_moment,
        total_hit_count=float(len(hits)),
    )


def compute_pfo_observables(pfo):
    clusters = list(pfo.getClusters())
    if not clusters:
        return None

    cluster_observables = [compute_cluster_observables(cluster) for cluster in clusters]
    cluster_observables = [item for item in cluster_observables if item is not None]
    if not cluster_observables:
        return None

    if len(cluster_observables) == 1:
        return cluster_observables[0]

    cluster_energies = [cluster.getEnergy() for cluster in clusters]
    total_cluster_energy = sum(cluster_energies)
    if total_cluster_energy <= 0.0:
        total_cluster_energy = float(len(cluster_observables))

    weighted = lambda attr: sum(getattr(obs, attr) * energy for obs, energy in zip(cluster_observables, cluster_energies)) / total_cluster_energy
    return ShowerObservables(
        ecal_barrel_fraction=weighted("ecal_barrel_fraction"),
        ecal_endcap_fraction=weighted("ecal_endcap_fraction"),
        hcal_barrel_fraction=weighted("hcal_barrel_fraction"),
        hcal_endcap_fraction=weighted("hcal_endcap_fraction"),
        shower_start_layer=min(obs.shower_start_layer for obs in cluster_observables),
        longitudinal_maximum=max(obs.longitudinal_maximum for obs in cluster_observables),
        occupied_layers=sum(obs.occupied_layers for obs in cluster_observables),
        transverse_width=weighted("transverse_width"),
        transverse_second_moment=weighted("transverse_second_moment"),
        total_hit_count=sum(obs.total_hit_count for obs in cluster_observables),
    )


def mean_and_stdev(values):
    if not values:
        return (0.0, 0.0)
    mean = sum(values) / len(values)
    return (mean, pstdev(values))


def print_unconverted_shape_stats(shape_store):
    print("Unconverted gamma shower-shape study by reconstructed PFO ID")
    for energy_label, _, _ in ENERGY_BINS_GEV:
        print(f"  Energy bin {energy_label} GeV")
        for reco_label, reco_title in [("gamma", "Reco gamma (PDG 22)"), ("neutron", "Reco neutron-like (PDG 2112)")]:
            print(f"    {reco_title}")
            for variable, title, *_ in VARIABLE_SPECS:
                values = shape_store[energy_label][reco_label][variable]
                mean, stdev = mean_and_stdev(values)
                print(f"      {title}: N={len(values)}, mean={mean}, stdev={stdev}")


def write_shape_plots(shape_store, plots_dir):
    import ROOT

    ROOT.gROOT.SetBatch(True)
    plots_dir = resolve_path(plots_dir)
    os.makedirs(plots_dir, exist_ok=True)

    for energy_label, _, _ in ENERGY_BINS_GEV:
        canvas = ROOT.TCanvas(f"c_{energy_label}", f"Unconverted gamma shower shapes {energy_label}", 3600, 2400)
        canvas.Divide(4, 2)
        keep_alive = []

        for pad_index, (variable, title, nbins) in enumerate(VARIABLE_SPECS, start=1):
            gamma_values = shape_store[energy_label]["gamma"][variable]
            neutron_values = shape_store[energy_label]["neutron"][variable]
            all_values = gamma_values + neutron_values

            if all_values:
                xlow = min(all_values)
                xhigh = max(all_values)
                if math.isclose(xlow, xhigh):
                    pad = 1.0 if math.isclose(xlow, 0.0) else 0.1 * abs(xlow)
                    xlow -= pad
                    xhigh += pad
                else:
                    pad = 0.05 * (xhigh - xlow)
                    xlow -= pad
                    xhigh += pad
            else:
                xlow, xhigh = 0.0, 1.0

            gamma_hist = ROOT.TH1D(f"{variable}_gamma_{energy_label}", f"{title};{title};Entries", nbins, xlow, xhigh)
            neutron_hist = ROOT.TH1D(f"{variable}_neutron_{energy_label}", f"{title};{title};Entries", nbins, xlow, xhigh)

            for value in gamma_values:
                gamma_hist.Fill(value)
            for value in neutron_values:
                neutron_hist.Fill(value)

            gamma_hist.SetLineColor(ROOT.kBlue + 1)
            gamma_hist.SetLineWidth(2)
            neutron_hist.SetLineColor(ROOT.kRed + 1)
            neutron_hist.SetLineWidth(2)

            canvas.cd(pad_index)
            ROOT.gPad.SetGrid()
            maximum = max(gamma_hist.GetMaximum(), neutron_hist.GetMaximum(), 1.0)
            gamma_hist.SetMaximum(1.2 * maximum)
            gamma_hist.Draw("hist")
            neutron_hist.Draw("hist same")

            legend = ROOT.TLegend(0.55, 0.72, 0.88, 0.88)
            legend.SetBorderSize(0)
            legend.AddEntry(gamma_hist, "Reco gamma (22)", "l")
            legend.AddEntry(neutron_hist, "Reco neutron-like (2112)", "l")
            legend.Draw()
            keep_alive.extend([gamma_hist, neutron_hist, legend])

        canvas.SaveAs(os.path.join(plots_dir, f"unconverted_gamma_shower_shapes_{energy_label.replace('>', 'gt').replace('<', 'lt')}.pdf"))


def run(input_files, collection_name, ecal_barrel_rmin_override_mm, ecal_endcap_min_z_override_mm, plots_dir):
    from podio import root_io

    envelope_xml, default_ecal_barrel_rmin_mm, default_ecal_endcap_min_z_mm = load_ecal_boundaries()
    ecal_barrel_rmin_mm = (
        ecal_barrel_rmin_override_mm
        if ecal_barrel_rmin_override_mm is not None
        else default_ecal_barrel_rmin_mm
    )
    ecal_endcap_min_z_mm = (
        ecal_endcap_min_z_override_mm
        if ecal_endcap_min_z_override_mm is not None
        else default_ecal_endcap_min_z_mm
    )

    print(f"Default ECAL boundaries from: {envelope_xml}")
    print(f"  default ecal_b_rmin = {default_ecal_barrel_rmin_mm} mm")
    print(f"  default ecal_e_min_z = {default_ecal_endcap_min_z_mm} mm")
    if ecal_barrel_rmin_override_mm is not None or ecal_endcap_min_z_override_mm is not None:
        print("Using overridden ECAL boundaries:")
    else:
        print("Using ECAL boundaries from XML:")
    print(f"  ecal_b_rmin = {ecal_barrel_rmin_mm} mm")
    print(f"  ecal_e_min_z = {ecal_endcap_min_z_mm} mm")

    converted = Stats()
    unconverted = Stats()
    shape_store = make_shape_store()

    for filename in input_files:
        reader = root_io.Reader(filename)
        for event in reader.get("events"):
            mc_particles = event.get("MCParticles")
            primary_gamma = find_primary_gamma(mc_particles)
            if primary_gamma is None:
                continue

            momentum = primary_gamma.getMomentum()
            gun_energy = math.sqrt(momentum.x * momentum.x + momentum.y * momentum.y + momentum.z * momentum.z)
            pfos = list(event.get(collection_name))

            if has_pre_ecal_conversion(primary_gamma, ecal_barrel_rmin_mm, ecal_endcap_min_z_mm):
                update_stats(converted, pfos, gun_energy)
            else:
                update_stats(unconverted, pfos, gun_energy)
                for pfo in pfos:
                    pdg = pfo.getPDG()
                    if pdg not in (22, 2112):
                        continue
                    observables = compute_pfo_observables(pfo)
                    if observables is None:
                        continue
                    energy_label = get_energy_bin_label(pfo.getEnergy())
                    reco_label = "gamma" if pdg == 22 else "neutron"
                    add_observables(shape_store, energy_label, reco_label, observables)

    print_stats("Converted before ECAL", converted)
    print_stats("Unconverted before ECAL", unconverted)
    print_unconverted_shape_stats(shape_store)
    write_shape_plots(shape_store, plots_dir)


if __name__ == "__main__":
    run(
        [resolve_path(filename) for filename in args.infile],
        args.collection,
        args.rmin_mm,
        args.zmin_mm,
        args.plots_dir,
    )
