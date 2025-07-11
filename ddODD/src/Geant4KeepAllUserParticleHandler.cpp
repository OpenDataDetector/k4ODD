// Framework include files
#include "Geant4KeepAllUserParticleHandler.h"
#include <DDG4/Factories.h>
#include <DDG4/Geant4Particle.h>
#include <DDG4/Geant4Kernel.h>


using namespace dd4hep::sim;
DECLARE_GEANT4ACTION(Geant4KeepAllUserParticleHandler)


/// Standard constructor
Geant4KeepAllUserParticleHandler::Geant4KeepAllUserParticleHandler(Geant4Context* ctxt, const std::string& nam)
: Geant4UserParticleHandler(ctxt,nam)
{}

/// Post-track action callback
void Geant4KeepAllUserParticleHandler::end(const G4Track* /* track */, Particle& /*p*/)  {
}

/// Post-event action callback
void Geant4KeepAllUserParticleHandler::end(const G4Event* /* event */)   {

}
