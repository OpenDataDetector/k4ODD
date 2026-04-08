/*
 * Copyright (c) 2020-2024 Key4hep-Project.
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

// Framework include files
#include "Geant4KeepAllUserParticleHandler.h"
#include <DDG4/Factories.h>
#include <DDG4/Geant4Kernel.h>
#include <DDG4/Geant4Particle.h>

using namespace dd4hep::sim;
DECLARE_GEANT4ACTION(Geant4KeepAllUserParticleHandler)

/// Standard constructor
Geant4KeepAllUserParticleHandler::Geant4KeepAllUserParticleHandler(Geant4Context* ctxt, const std::string& nam)
    : Geant4UserParticleHandler(ctxt, nam) {}

/// Post-track action callback
void Geant4KeepAllUserParticleHandler::end(const G4Track* /* track */, Particle& /*p*/) {}

/// Post-event action callback
void Geant4KeepAllUserParticleHandler::end(const G4Event* /* event */) {}
