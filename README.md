# k4-project-template


This repository can be a starting point and template for projects using the Key4hep software stack, in particular those writing Gaudi algorithms.


## Dependencies

* key4hep stack
* OpenDataDetector (https://gitlab.cern.ch/azaborow/OpenDataDetector/-/commit/f1f7a723f3e9c066c32ca97c929e451f6a49622d)

## Preparation

``` bash
export OpenDataDetector=<Where_ODD_is>
source $OpenDataDetector/install/bin/this_odd.sh
source /cvmfs/sw-nightlies.hsf.org/key4hep/setup.sh # checked with         source /cvmfs/sw-nightlies.hsf.org/key4hep/setup.sh -r 2025-06-16
source $OpenDataDetector/install/bin/this_odd.sh # For unknown reasons needed twice (otherwise factory complaint)
```

## Simulation

```
ddsim --steeringFile k4ODD/options/ODDsimulation.py  --enableGun --gun.distribution uniform --gun.etaMin 0 --gun.etaMax 0 --gun.energy "10*GeV" --gun.particle gamma --numberOfEvents 100 --outputFile gamma_10GeV_eta0_100ev_sim_edm4hep.root --random.seed 123
```

## Digitisation

``` bash
k4run k4ODD/options/ODDdigitisation.py --inputFile gamma_10GeV_eta0_100ev_sim_edm4hep.root --outputFile gamma_10GeV_eta0_100ev_digi_edm4hep.root
```

## Validation

``` bash
python $OpenDataDetector/ci/analyse_single_shower.py -i gamma_10GeV_eta0_100ev_sim_edm4hep.root
python $OpenDataDetector/ci/analyse_single_shower.py -i gamma_10GeV_eta0_100ev_digi_edm4hep.root --digi
```

Please note that the collections are rewritten so both analyses can be performed on the same (second) file.

