# k4ODD

This repository started from the Key4hep project template.

## Dependencies

* key4hep stack
* OpenDataDetector (geometry)
* k4GaudiPandora (digitisation and reconstruction)

## Preparation

By default the helper scripts look for:

* `OpenDataDetector` in `./OpenDataDetector` or `../OpenDataDetector`
* `k4GaudiPandora` in `../k4GaudiPandora` or `./k4GaudiPandora`

The recommended setup is:

```bash
source setup.sh
```

This will:

* source the Key4hep stack
* source the newest local `OpenDataDetector/install*`
* prepend the newest local `k4GaudiPandora/install*`
* prepend the newest local `k4ODD/install*`

You can override repo locations with `ODD_DIR` and `K4GAUDIPANDORA_DIR`.

## Rebuild

To rebuild the local `OpenDataDetector`, `k4GaudiPandora`, and `k4ODD` repos against the currently sourced Key4hep stack:

```bash
bash ./ci/rebuild_local_stack.sh
```

# Simulation

```bash
ddsim --steeringFile k4ODD/options/ODDsimulation.py --enableGun --gun.distribution uniform --gun.etaMin 0 --gun.etaMax 0 --gun.energy "10*GeV" --gun.particle gamma --numberOfEvents 100 --outputFile gamma_10GeV_eta0_100ev_sim_edm4hep.root --random.seed 123
```

# Digitisation

```bash
k4run k4ODD/options/ODDdigitisation.py --inputFile gamma_10GeV_eta0_100ev_sim_edm4hep.root --outputFile gamma_10GeV_eta0_100ev_digi_edm4hep.root
```

# Reconstruction
[Work In Progress]

Then run Pandora reconstruction:
Note: input is the simulation output, not digi!

```bash
k4run k4ODD/options/ODDreconstruction.py --inputFile gamma_10GeV_eta0_100ev_sim_edm4hep.root --outputFile gamma_10GeV_eta0_100ev_reco_edm4hep.root
```

Check that the reconstruction output contains:

* `GaudiPandoraClusters`
* `GaudiPandoraPFOs`
* `GaudiPandoraStartVertices`

### Photon Training And Reco

Default ODD reco uses:

```bash
k4ODD/options/PandoraSettingsMinimal.xml
```

Photon training uses a dedicated minimal steering file:

```bash
k4ODD/options/PandoraSettingsPhotonTraining.xml
```

`ODDreconstruction.py` switches to the photon-training XML only when `--pandoraPhotonTraining` is passed. It writes a temporary copy when photon-specific overrides are requested, so the source XML files are not edited in place.

Train the photon likelihood XML with:

```bash
k4run k4ODD/options/ODDreconstruction.py \
  --inputFile gamma_10GeV_eta0_100ev_sim_edm4hep.root \
  --outputFile gamma_10GeV_eta0_100ev_photon_train_edm4hep.root \
  --pandoraPhotonTraining \
  --pandoraPhotonHistogramFile $PWD/PandoraLikelihoodData9EBin.xml
```

Then run reco with the standard minimal XML and the produced histogram file:

```bash
k4run k4ODD/options/ODDreconstruction.py \
  --inputFile gamma_10GeV_eta0_100ev_sim_edm4hep.root \
  --outputFile gamma_10GeV_eta0_100ev_photon_reco_edm4hep.root \
  --pandoraPhotonHistogramFile $PWD/PandoraLikelihoodData9EBin.xml
```

For useful photon ID training, the histogram XML should be built from both photon signal and non-photon background samples. A gamma-only sample is enough for a steering smoke test, but not for a realistic photon-ID calibration.


For development = if you want the script to start by rebuilding all three repos first, and regenerate the simulation:

```bash
REBUILD_STACK=1 PANDORA_SANITY_FORCE_SIM=1 bash ./ci/run_pandora_sanity.sh
```

## Validation
```bash
python ci/analyse_single_shower_root.py -i gamma_10GeV_eta0_100ev_sim_edm4hep.root
python ci/analyse_single_shower_podio.py -i gamma_10GeV_eta0_100ev_digi_edm4hep.root --digi
python ci/analyse_pfo_performance.py -i gamma_10GeV_eta0_100ev_reco_edm4hep.root
```

In CI the validation jobs save the ROOT summaries and preview PDFs as artifacts.

Fast regression checks compare:

* selected summary values from the `results` tree
* selected histogram bin contents

against committed reference ROOT files under `ci/reference/`.

The low-stat push and PR jobs do not use `resolution` as a gate. `resolution` is checked only in the manual higher-stat workflow-dispatch path, which runs a 1000-event simulation and digitisation chain.
