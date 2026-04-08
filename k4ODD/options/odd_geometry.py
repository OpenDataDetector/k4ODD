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
import glob
import os


def _candidate_install_dirs():
    explicit_install = os.environ.get("ODD_INSTALL_DIR")
    if explicit_install:
        yield explicit_install

    repo_dir = os.environ.get("OpenDataDetector")
    if repo_dir:
        yield os.path.join(repo_dir, "install")
        for candidate in sorted(glob.glob(os.path.join(repo_dir, "install*"))):
            yield candidate

    yield os.path.join("OpenDataDetector", "install")
    yield os.path.join("OpenDataDetector", "install-ci")


def odd_compact_xml():
    suffix = os.path.join("share", "OpenDataDetector", "xml", "OpenDataDetector.xml")
    fallback = None

    for install_dir in _candidate_install_dirs():
        candidate = os.path.join(install_dir, suffix)
        if fallback is None:
            fallback = candidate
        if os.path.exists(candidate):
            return candidate

    return fallback
