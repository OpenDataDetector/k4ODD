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


def run(input_files, collection_name, ecal_barrel_rmin_override_mm, ecal_endcap_min_z_override_mm):
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

    print_stats("Converted before ECAL", converted)
    print_stats("Unconverted before ECAL", unconverted)


if __name__ == "__main__":
    run(
        [resolve_path(filename) for filename in args.infile],
        args.collection,
        args.rmin_mm,
        args.zmin_mm,
    )
