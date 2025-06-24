#[[
Copyright (c) 2020-2024 Key4hep-Project.

This file is part of Key4hep.
See https://key4hep.github.io/key4hep-doc/ for further info.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
]]
CMAKE_MINIMUM_REQUIRED(VERSION 3.12)


project(k4ODD LANGUAGES CXX)

# please keep this layout for version setting, used by the automatic tagging script
set(PACKAGE_VERSION_MAJOR 1)
set(PACKAGE_VERSION_MINOR 2)
set(PACKAGE_VERSION_PATCH 3)

set(PACKAGE_VERSION "${PACKAGE_VERSION_MAJOR}.${PACKAGE_VERSION_MINOR}.${PACKAGE_VERSION_PATCH}")

install(DIRECTORY ${CMAKE_CURRENT_LIST_DIR}/${CMAKE_PROJECT_NAME}/ DESTINATION ${PROJECT_BINARY_DIR}/${CMAKE_PROJECT_NAME})
#---------------------------------------------------------------

include(GNUInstallDirs)
include(CTest)

function(set_test_env testname)
  set_property(TEST ${testname} APPEND PROPERTY ENVIRONMENT "LD_LIBRARY_PATH=${PROJECT_BINARY_DIR}:${PROJECT_BINARY_DIR}/${PROJECT_NAME}:${PROJECT_BINARY_DIR}/${PROJECT_NAME}/genConfDir/${PROJECT_NAME}:${PROJECT_BINARY_DIR}/test/k4FWCoreTest:${PROJECT_BINARY_DIR}/test/k4FWCoreTest/genConfDir/k4FWCoreTest:$<$<TARGET_EXISTS:ROOT::Core>:$<TARGET_FILE_DIR:ROOT::Core>>:$<$<TARGET_EXISTS:EDM4HEP::edm4hep>:$<TARGET_FILE_DIR:EDM4HEP::edm4hep>>:$<$<TARGET_EXISTS:podio::podio>:$<TARGET_FILE_DIR:podio::podio>>:$ENV{LD_LIBRARY_PATH}")
  set_property(TEST ${testname} APPEND PROPERTY ENVIRONMENT "PYTHONPATH=${PROJECT_SOURCE_DIR}/python:${PROJECT_BINARY_DIR}/${PROJECT_NAME}/genConfDir:/${PROJECT_NAME}/genConfDir:$ENV{PYTHONPATH}")
endfunction()

add_test(NAME "clone_ODD"
  COMMAND bash -c "git clone --single-branch --branch addLayeredCaloData https://gitlab.cern.ch/azaborow/OpenDataDetector.git && cd OpenDataDetector && mkdir build install && cd build && cmake -S .. -B . -DCMAKE_INSTALL_PREFIX=../install && make install"
)
set_test_env("clone_ODD")
set_property(TEST "clone_ODD" APPEND PROPERTY FIXTURES_SETUP ODD)

set(DETECTOR ${PROJECT_BINARY_DIR}/OpenDataDetector/install/share/OpenDataDetector/xml/OpenDataDetector.xml)
# Define combinations of parameters for simulation
set(PARAM_COMBINATIONS
  "5\\;100"
  "10\\;100"
  "20\\;100"
  "50\\;100"
)

set(DDSIM_TEST_DEPENDENCIES "")  # Initialize an empty string/list
set(DIGI_TEST_DEPENDENCIES "")  # Initialize an empty string/list

foreach(PAIR IN LISTS PARAM_COMBINATIONS)
  list(GET PAIR 0 PARAM1)
  list(GET PAIR 1 PARAM2)
  string(REPLACE ";" "_" SUFFIX "${PAIR}")

  add_test(
    NAME ddsim_gamma_${SUFFIX}
    COMMAND bash -c "source ${PROJECT_BINARY_DIR}/OpenDataDetector/install/bin/this_odd.sh && ddsim  --compactFile ${DETECTOR} --steeringFile k4ODD/options/ODDsimulation.py  --enableGun --gun.distribution uniform --gun.etaMin 0 --gun.etaMax 0 --gun.energy ${PARAM1}*GeV --gun.particle gamma --numberOfEvents ${PARAM2} --outputFile gamma_${PARAM1}GeV_eta0_${PARAM2}ev_sim_edm4hep.root --random.seed 123"
  )
  set_test_env("ddsim_gamma_${SUFFIX}")
  set_property(TEST "ddsim_gamma_${SUFFIX}" APPEND PROPERTY FIXTURES_REQUIRED ODD)
  add_test(NAME ddsim_gamma_validation_${SUFFIX}
    COMMAND python ${PROJECT_BINARY_DIR}/OpenDataDetector//ci/analyse_single_shower.py -i gamma_${PARAM1}GeV_eta0_${PARAM2}ev_sim_edm4hep.root
  )
  set_test_env("ddsim_gamma_validation_${SUFFIX}")
  set_property(TEST "ddsim_gamma_validation_${SUFFIX}" APPEND PROPERTY FIXTURES_REQUIRED "ddsim_gamma_${SUFFIX}")
  # Accumulate test names for joint test dependency
  list(APPEND DDSIM_TEST_DEPENDENCIES "\\;ddsim_gamma_validation_${SUFFIX}")

  add_test(NAME digi_gamma_${SUFFIX}
    COMMAND bash -c "source ${PROJECT_BINARY_DIR}/OpenDataDetector/install/bin/this_odd.sh && export PYTHONPATH=/cvmfs/sw-nightlies.hsf.org/key4hep/releases/2025-06-07/x86_64-almalinux9-gcc14.2.0-opt/k4gaudipandora/9b484e6a736829c3ef6558a4a77e689c864699cd_develop-la2gxj/python/:$PYTHONPATH && python `which k4run` k4ODD/options/ODDdigitisation.py --inputFile ${PROJECT_BINARY_DIR}/gamma_${PARAM1}GeV_eta0_${PARAM2}ev_sim_edm4hep.root --outputFile gamma_${PARAM1}GeV_eta0_${PARAM2}ev_digi_edm4hep.root"

  )
  set_test_env("digi_gamma_${SUFFIX}")
  set_property(TEST "digi_gamma_${SUFFIX}" APPEND PROPERTY FIXTURES_REQUIRED "ddsim_gamma_${SUFFIX};ODD")

  add_test(NAME digi_gamma_validation_${SUFFIX}
    COMMAND python ${PROJECT_BINARY_DIR}/OpenDataDetector/ci/analyse_single_shower.py -i gamma_${PARAM1}GeV_eta0_${PARAM2}ev_digi_edm4hep.root --digi
  )
  set_test_env("digi_gamma_validation_${SUFFIX}")
  set_property(TEST "digi_gamma_validation_${SUFFIX}" APPEND PROPERTY FIXTURES_REQUIRED "digi_gamma_${SUFFIX}")
  # Accumulate test names for joint test dependency
  list(APPEND DIGI_TEST_DEPENDENCIES "\\;digi_gamma_validation_${SUFFIX}")
endforeach()

add_test(
  NAME ddsim_gamma_validation_join
  COMMAND bash -c "find . -type f -name '*sim_edm4hep.root' -exec sh -c 'python3 ${PROJECT_BINARY_DIR}/OpenDataDetector/ci/analyse_single_shower.py -i {} -o `basename {} edm4hep.root`results.root'  \; && python3 ${PROJECT_BINARY_DIR}/OpenDataDetector/ci/analyse_combine_showers.py -i *sim_results.root -o combined_performance.root && python3 ${PROJECT_BINARY_DIR}/OpenDataDetector/ci/graphCmp.py -i combined_performance.root ${PROJECT_BINARY_DIR}/OpenDataDetector/ci/reference/combined_performance_ECalBarrel.root -l simulated ODD_reference"
)
set_test_env("ddsim_gamma_validation_join")
set_property(TEST "ddsim_gamma_validation_join" APPEND PROPERTY FIXTURES_REQUIRED DDSIM_TEST_DEPENDENCIES)

add_test(
  NAME digi_gamma_validation_join
  COMMAND bash -c "find . -type f -name '*digi_edm4hep.root' -exec sh -c 'python3 ${PROJECT_BINARY_DIR}/OpenDataDetector/ci/analyse_single_shower.py -i {} -o `basename {} edm4hep.root`results.root'  \; && python3 ${PROJECT_BINARY_DIR}/OpenDataDetector/ci/analyse_combine_showers.py -i *digi_results.root -o combined_performance.root && python3 ${PROJECT_BINARY_DIR}/OpenDataDetector/ci/graphCmp.py -i combined_performance.root ${PROJECT_BINARY_DIR}/OpenDataDetector/ci/reference/combined_performance_ECalBarrel.root -l digitised ODD_reference"
)
set_test_env("digi_gamma_validation_join")
set_property(TEST "digi_gamma_validation_join" APPEND PROPERTY FIXTURES_REQUIRED DIGI_TEST_DEPENDENCIES)
