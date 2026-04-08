/*
 * Copyright (c) 2020-2025 Key4hep-Project.
 *
 * This file is part of Key4hep.
 * See https://key4hep.github.io/key4hep-doc/ for further info.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#include "Gaudi/Property.h"
#include "k4FWCore/Producer.h"

#include "edm4hep/TrackCollection.h"

#include <string>

struct CreateEmptyTracks final : k4FWCore::Producer<edm4hep::TrackCollection()> {
  CreateEmptyTracks(const std::string& name, ISvcLocator* svcLoc)
      : Producer(name, svcLoc, {}, KeyValues("OutputLocation", {"EmptyTracks"})) {}

  edm4hep::TrackCollection operator()() const override {
    auto coll = edm4hep::TrackCollection();
    return coll;
  }
};

DECLARE_COMPONENT(CreateEmptyTracks)
