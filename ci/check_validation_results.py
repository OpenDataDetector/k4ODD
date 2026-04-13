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
import json
import math
import os
import sys

import ROOT


def load_profile(spec_path, profile_name):
    with open(spec_path, encoding="utf-8") as spec_file:
        spec = json.load(spec_file)
    try:
        return spec[profile_name]
    except KeyError as exc:
        raise SystemExit(f"Unknown validation profile: {profile_name}") from exc


def open_root_file(path):
    root_file = ROOT.TFile.Open(path)
    if not root_file or root_file.IsZombie():
        raise SystemExit(f"Failed to open ROOT file: {path}")
    return root_file


def read_results(root_file, tree_name):
    tree = root_file.Get(tree_name)
    if not tree:
        raise SystemExit(f"Tree '{tree_name}' not found in {root_file.GetName()}")
    if tree.GetEntries() < 1:
        raise SystemExit(f"Tree '{tree_name}' is empty in {root_file.GetName()}")

    tree.GetEntry(0)
    values = {}
    for branch in tree.GetListOfBranches():
        branch_name = branch.GetName()
        values[branch_name] = float(getattr(tree, branch_name))
    return values


def read_histogram(root_file, hist_name):
    hist = root_file.Get(hist_name)
    if not hist:
        raise SystemExit(f"Histogram '{hist_name}' not found in {root_file.GetName()}")
    return hist


def describe_limit(limits):
    parts = []
    if "abs" in limits:
        parts.append(f"abs<={limits['abs']:.6g}")
    if "rel" in limits:
        parts.append(f"rel<={limits['rel']:.6g}")
    return ", ".join(parts) if parts else "exact"


def allowed_delta(expected, limits):
    absolute = float(limits.get("abs", 0.0))
    relative = float(limits.get("rel", 0.0)) * abs(expected)
    return max(absolute, relative)


def check_summary_values(values, reference_values, checks):
    failures = []
    for key, limits in checks.items():
        if key not in values:
            failures.append(f"summary {key}: missing from candidate file")
            continue
        if key not in reference_values:
            failures.append(f"summary {key}: missing from reference file")
            continue

        value = values[key]
        expected = reference_values[key]
        if math.isnan(value):
            failures.append(f"summary {key}: observed NaN")
            continue

        delta = abs(value - expected)
        limit = allowed_delta(expected, limits)
        if delta > limit:
            failures.append(
                f"summary {key}: observed {value:.6g}, expected {expected:.6g}, |delta|={delta:.6g} > {describe_limit(limits)}"
            )
    return failures


def check_histograms(candidate_file, reference_file, checks):
    failures = []
    max_failures = 20

    for hist_name, limits in checks.items():
        candidate_hist = read_histogram(candidate_file, hist_name)
        reference_hist = read_histogram(reference_file, hist_name)

        if candidate_hist.GetNbinsX() != reference_hist.GetNbinsX():
            failures.append(
                f"histogram {hist_name}: candidate has {candidate_hist.GetNbinsX()} bins, reference has {reference_hist.GetNbinsX()}"
            )
            continue

        first_bin = 0 if limits.get("include_overflow", False) else 1
        last_bin = candidate_hist.GetNbinsX() + 1 if limits.get("include_overflow", False) else candidate_hist.GetNbinsX()
        bin_limit = float(limits.get("bin_abs", 0.0))

        for bin_idx in range(first_bin, last_bin + 1):
            observed = candidate_hist.GetBinContent(bin_idx)
            expected = reference_hist.GetBinContent(bin_idx)
            delta = abs(observed - expected)
            if delta > bin_limit:
                failures.append(
                    f"histogram {hist_name} bin {bin_idx}: observed {observed:.6g}, expected {expected:.6g}, |delta|={delta:.6g} > abs<={bin_limit:.6g}"
                )
                if len(failures) >= max_failures:
                    failures.append("additional histogram failures suppressed")
                    return failures

    return failures


def main():
    parser = argparse.ArgumentParser(description="Check validation outputs against reference ROOT files")
    parser.add_argument("--input", "-i", required=True, help="Validation ROOT file")
    parser.add_argument("--profile", "-p", required=True, help="Profile name in the JSON spec")
    parser.add_argument(
        "--spec",
        default="ci/validation_ranges.json",
        help="JSON file containing reference paths and tolerances",
    )
    parser.add_argument(
        "--reference",
        help="Override reference ROOT file path from the profile",
    )
    args = parser.parse_args()

    profile = load_profile(args.spec, args.profile)
    reference_path = args.reference or profile.get("reference")
    if not reference_path:
        raise SystemExit(f"Profile '{args.profile}' does not define a reference ROOT file")
    if not os.path.isabs(reference_path):
        reference_path = os.path.join(os.getcwd(), reference_path)

    candidate_file = open_root_file(args.input)
    reference_file = open_root_file(reference_path)

    tree_name = profile.get("tree", "results")
    values = read_results(candidate_file, tree_name)
    reference_values = read_results(reference_file, tree_name)

    failures = []
    failures.extend(check_summary_values(values, reference_values, profile.get("summary_checks", {})))
    failures.extend(check_histograms(candidate_file, reference_file, profile.get("histogram_checks", {})))

    print(f"Validation profile: {args.profile}")
    print(f"Reference file: {reference_path}")
    for key in sorted(values):
        if key in reference_values:
            print(f"  {key}: observed={values[key]:.6g} expected={reference_values[key]:.6g}")
        else:
            print(f"  {key}: observed={values[key]:.6g}")

    candidate_file.Close()
    reference_file.Close()

    if failures:
        print("Validation failed:")
        for failure in failures:
            print(f"  - {failure}")
        sys.exit(1)

    print("Validation passed.")


if __name__ == "__main__":
    main()
