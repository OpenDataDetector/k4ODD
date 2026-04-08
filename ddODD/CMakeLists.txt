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
set(DDODD_NAME ddODD)

find_package(DD4hep REQUIRED COMPONENTS DDG4 DDCore)

# Create the plugin library
add_dd4hep_plugin(${DDODD_NAME} SHARED
  src/Geant4KeepAllUserParticleHandler.cpp
)

target_include_directories(${DDODD_NAME} PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(${DDODD_NAME} PUBLIC  DD4hep::DDG4 )

install(TARGETS ${DDODD_NAME} DESTINATION lib)
install(DIRECTORY include/ DESTINATION include)

dd4hep_instantiate_package(${DDODD_NAME})
