cmake_minimum_required(VERSION 3.18)

# create the project
project(rlb)

# when using debuggers such as gdb, the following line can be used
#set(CMAKE_BUILD_TYPE Debug)

SET(MAIN_FILE "main_file" CACHE STRING "File to build")

# if you did not build RadioLib as shared library (see wiki),
# you will have to add it as source directory
# the following is just an example, yours will likely be different
add_subdirectory("${CMAKE_CURRENT_SOURCE_DIR}/../repos/RadioLib" "${CMAKE_CURRENT_BINARY_DIR}/RadioLib")
add_subdirectory("${CMAKE_CURRENT_SOURCE_DIR}/../repos/RadioBoards" "${CMAKE_CURRENT_BINARY_DIR}/RadioBoards")
add_subdirectory("${CMAKE_CURRENT_SOURCE_DIR}/../repos/rf-powermon/lib/rf-powermon-client" "${CMAKE_CURRENT_BINARY_DIR}/rf-powermon-client")
add_subdirectory("${CMAKE_CURRENT_SOURCE_DIR}/../repos/dc-powermon/lib/dc-powermon-client" "${CMAKE_CURRENT_BINARY_DIR}/dc-powermon-client")

# add the executable
add_executable(${PROJECT_NAME} ${MAIN_FILE})

# link both libraries
target_link_libraries(${PROJECT_NAME} RadioLib RadioBoards lgpio rf-powermon-client dc-powermon-client)

# you can also specify RadioLib compile-time flags here
#target_compile_definitions(RadioLib PUBLIC RADIOLIB_DEBUG_BASIC RADIOLIB_DEBUG_SPI)
#target_compile_definitions(RadioLib PUBLIC RADIOLIB_DEBUG_PORT=stdout)

target_include_directories(${PROJECT_NAME} PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}/../repos/rf-powermon/lib/rf-powermon-client")
target_include_directories(${PROJECT_NAME} PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}/../repos/rf-powermon/lib/dc-powermon-client")
