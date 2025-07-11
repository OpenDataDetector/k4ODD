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
