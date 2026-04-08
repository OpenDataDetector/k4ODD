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

/** \addtogroup Geant4Action
 *
 @{
   \package Geant4TVUserParticleHandler
 * \brief Rejects to keep particles, which are created outside a tracking cylinder.
 *
 *
@}
 */

#ifndef DD4HEP_DDG4_GEANT4KEEPALLUSERPARTICLEHANDLER_H
#define DD4HEP_DDG4_GEANT4KEEPALLUSERPARTICLEHANDLER_H

// Framework include files
#include <DD4hep/Primitives.h>
#include <DD4hep/Volumes.h>
#include <DDG4/Geant4UserParticleHandler.h>

/// Namespace for the AIDA detector description toolkit
namespace dd4hep {

/// Namespace for the Geant4 based simulation part of the AIDA detector description toolkit
namespace sim {

  ///  Rejects to keep particles, which are created outside a tracking volume.
  /** Geant4KEEPALLUserParticleHandler
   *
   *  KEEPALL to test particle history in calorimeters
   */
  class Geant4KeepAllUserParticleHandler : public Geant4UserParticleHandler {
    Volume m_trackingVolume;

  public:
    /// Standard constructor
    Geant4KeepAllUserParticleHandler(Geant4Context* context, const std::string& nam);

    /// Default destructor
    virtual ~Geant4KeepAllUserParticleHandler() {}

    /// Post-track action callback
    /** Allow the user to force the particle handling in the post track action
     *  set the reason mask to NULL in order to drop the particle.
     *  The parent's reasoning mask will be or'ed with the particle's mask
     *  to preserve the MC truth for the hit creation.
     *  The default implementation is empty.
     *
     *  Note: The particle passed is a temporary and will be copied if kept.
     */
    virtual void end(const G4Track* track, Particle& particle);

    /// Post-event action callback: avoid warning (...) was hidden [-Woverloaded-virtual]
    virtual void end(const G4Event* event);
  };
} // End namespace sim
} // End namespace dd4hep

#endif // DD4HEP_DDG4_GEANT4KeepAllUSERPARTICLEHANDLER_H
