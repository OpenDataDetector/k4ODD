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
import json
import math
import sys

import ROOT


def load_profile(spec_path, profile_name):
    with open(spec_path, encoding="utf-8") as spec_file:
        spec = json.load(spec_file)
    try:
        return spec[profile_name]
    except KeyError as exc:
        raise SystemExit(f"Unknown validation profile: {profile_name}") from exc


def read_results(input_path, tree_name):
    root_file = ROOT.TFile.Open(input_path)
    if not root_file or root_file.IsZombie():
        raise SystemExit(f"Failed to open ROOT file: {input_path}")

    tree = root_file.Get(tree_name)
    if not tree:
        raise SystemExit(f"Tree '{tree_name}' not found in {input_path}")
    if tree.GetEntries() < 1:
        raise SystemExit(f"Tree '{tree_name}' is empty in {input_path}")

    tree.GetEntry(0)
    values = {}
    for branch in tree.GetListOfBranches():
        branch_name = branch.GetName()
        values[branch_name] = float(getattr(tree, branch_name))
    root_file.Close()
    return values


def check_values(values, checks):
    failures = []
    for key, limits in checks.items():
        if key not in values:
            failures.append(f"Missing result '{key}'")
            continue
        value = values[key]
        if math.isnan(value):
            failures.append(f"{key} is NaN")
            continue
        minimum = limits.get("min")
        maximum = limits.get("max")
        if minimum is not None and value < minimum:
            failures.append(f"{key}={value:.6g} is below {minimum:.6g}")
        if maximum is not None and value > maximum:
            failures.append(f"{key}={value:.6g} is above {maximum:.6g}")
    return failures


def main():
    parser = argparse.ArgumentParser(description="Check validation summary values against expected ranges")
    parser.add_argument("--input", "-i", required=True, help="Validation ROOT file")
    parser.add_argument("--profile", "-p", required=True, help="Profile name in the JSON spec")
    parser.add_argument(
        "--spec",
        default="ci/validation_ranges.json",
        help="JSON file containing expected ranges",
    )
    args = parser.parse_args()

    profile = load_profile(args.spec, args.profile)
    values = read_results(args.input, profile.get("tree", "results"))
    failures = check_values(values, profile["checks"])

    print(f"Validation profile: {args.profile}")
    for key in sorted(values):
        print(f"  {key}: {values[key]:.6g}")

    if failures:
        print("Validation failed:")
        for failure in failures:
            print(f"  - {failure}")
        sys.exit(1)

    print("Validation passed.")


if __name__ == "__main__":
    main()
