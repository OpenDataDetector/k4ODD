# k4-project-template


This repository can be a starting point and template for projects using the Key4hep software stack, in particular those writing Gaudi algorithms.


## Dependencies

* key4hep stack
* OpenDataDetector

## Preparation

``` bash
export OpenDataDetector=<Where_ODD_is>
source $OpenDataDetector/install/bin/this_odd.sh
source /cvmfs/sw-nightlies.hsf.org/key4hep/setup.sh
# temporary, fix implemented
export PYTHONPATH=/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-06-07/x86_64-almalinux9-gcc14.2.0-opt/k4gaudipandora/9b484e6a736829c3ef6558a4a77e689c864699cd_develop-la2gxj/python/:$PYTHONPATH
```

## Simulation

```
ddsim --steeringFile k4ODD/options/ODDsimulation.py  --enableGun --gun.distribution uniform --gun.etaMin 0 --gun.etaMax 0 --gun.energy "10*GeV" --gun.particle gamma --numberOfEvents 100 --outputFile gamma_10GeV_eta0_100ev_edm4hep.root --random.seed 123
```

## Digitisation

``` bash
k4run k4ODD/options/ODDdigitisation.py
```

## Validation

``` bash
python $OpenDataDetector/ci/analyse_single_shower.py -i gamma_10GeV_eta0_100ev_edm4hep.root
```

