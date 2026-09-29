cmake_minimum_required(VERSION 3.20)
project(application_attributes_tests LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
if(POLICY CMP0135)
    cmake_policy(SET CMP0135 NEW)
endif()

include(CTest)
include(FetchContent)
set(INSTALL_GTEST OFF CACHE BOOL "Install GoogleTest" FORCE)
set(BUILD_GMOCK OFF CACHE BOOL "Build GoogleMock" FORCE)
FetchContent_Declare(googletest
    URL https://codeload.github.com/google/googletest/tar.gz/refs/tags/v1.15.2
    URL_HASH SHA256=7b42b4d6ed48810c5362c265a17faebe90dc2373c885e5216439d37927f02926
)
FetchContent_MakeAvailable(googletest)

add_library(application_attributes_core STATIC ../src/version_code.cpp ../src/sdk_rules.cpp)
target_include_directories(application_attributes_core PUBLIC ../include)
target_compile_options(application_attributes_core PRIVATE -Wall -Wextra -Wpedantic -Werror)
option(APPLICATION_ATTRIBUTES_SANITIZERS "Instrument production code and tests" ON)
if(APPLICATION_ATTRIBUTES_SANITIZERS)
    if(NOT CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
        message(FATAL_ERROR "Sanitizers require a Clang or GCC toolchain")
    endif()
    target_compile_options(application_attributes_core PUBLIC
        -fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer)
    target_link_options(application_attributes_core PUBLIC
        -fsanitize=address,undefined -fno-sanitize-recover=all)
endif()

find_package(Python3 REQUIRED COMPONENTS Interpreter)
find_package(Java 1.8 REQUIRED COMPONENTS Runtime Development)
set(oracle_source "${CMAKE_CURRENT_SOURCE_DIR}/oracle/AndroidPackageInfoOracle.java")
set(oracle_header "${CMAKE_CURRENT_BINARY_DIR}/version_oracle_values.h")
add_custom_command(OUTPUT "${oracle_header}"
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/generate_version_oracle.py"
        --source "${oracle_source}"
        --source-sha256 9526fcef2a4128e1496c81790abae5bdc69e94735ac1b48be58109455d02604a
        --java "${Java_JAVA_EXECUTABLE}"
        --javac "${Java_JAVAC_EXECUTABLE}"
        --output "${oracle_header}"
    DEPENDS "${oracle_source}" "${CMAKE_CURRENT_SOURCE_DIR}/generate_version_oracle.py"
    VERBATIM
)
add_executable(application_attributes_version_test version_code_test.cpp "${oracle_header}")
target_include_directories(application_attributes_version_test PRIVATE "${CMAKE_CURRENT_BINARY_DIR}")
target_link_libraries(application_attributes_version_test PRIVATE application_attributes_core GTest::gtest_main)
target_compile_options(application_attributes_version_test PRIVATE -Wall -Wextra -Wpedantic -Werror)
if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    target_link_options(application_attributes_version_test PRIVATE -Wl,--no-undefined)
endif()
include(GoogleTest)
gtest_discover_tests(application_attributes_version_test DISCOVERY_TIMEOUT 30)

# Build the existing full APK parsers and descriptor digest implementation.
# HiLog is the only external edge replaced on this host; ZIP/XML logic is real.
FetchContent_Declare(parser_zlib
    URL https://zlib.net/fossils/zlib-1.3.1.tar.gz
    SOURCE_SUBDIR adapter-source-only
    URL_HASH SHA256=9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23
)
FetchContent_MakeAvailable(parser_zlib)
find_package(ZLIB REQUIRED)
add_library(parser_minizip STATIC
    "${parser_zlib_SOURCE_DIR}/contrib/minizip/unzip.c"
    "${parser_zlib_SOURCE_DIR}/contrib/minizip/ioapi.c")
target_include_directories(parser_minizip PUBLIC "${parser_zlib_SOURCE_DIR}/contrib/minizip")
target_link_libraries(parser_minizip PUBLIC ZLIB::ZLIB)
set(pm_root "${CMAKE_CURRENT_SOURCE_DIR}/../..")
add_library(application_attributes_manifest STATIC
    "${pm_root}/manifest_facts/src/manifest_facts_v1.cpp"
    "${pm_root}/jni/apk_manifest_parser.cpp"
    "${pm_root}/jni/axml_parser.cpp"
    "${pm_root}/package_transaction/src/package_transaction_v1.cpp"
    "${pm_root}/install_plan/src/sha256.c")
target_include_directories(application_attributes_manifest PUBLIC
    "${pm_root}/manifest_facts/include" "${pm_root}/package_transaction/include"
    "${pm_root}/install_plan/include" "${pm_root}/jni")
target_include_directories(application_attributes_manifest PRIVATE "${pm_root}/test/host_shims")
target_link_libraries(application_attributes_manifest PUBLIC application_attributes_core parser_minizip ZLIB::ZLIB)
add_executable(application_attributes_manifest_test manifest_version_test.cpp)
target_link_libraries(application_attributes_manifest_test PRIVATE application_attributes_manifest GTest::gtest_main)
target_compile_options(application_attributes_manifest_test PRIVATE -Wall -Wextra -Wpedantic -Werror)
gtest_discover_tests(application_attributes_manifest_test DISCOVERY_TIMEOUT 30)

add_executable(application_attributes_sdk_test sdk_rules_test.cpp)
target_link_libraries(application_attributes_sdk_test PRIVATE application_attributes_manifest GTest::gtest_main)
target_compile_options(application_attributes_sdk_test PRIVATE -Wall -Wextra -Wpedantic -Werror)
gtest_discover_tests(application_attributes_sdk_test DISCOVERY_TIMEOUT 30)

add_library(application_attributes_elf STATIC
    "${pm_root}/package_transaction/src/elf_prepass_analyzer.cpp"
    "${pm_root}/install_plan/src/sha256.c")
target_include_directories(application_attributes_elf PUBLIC "${pm_root}/package_transaction/include"
    PRIVATE "${pm_root}/install_plan/include")
target_link_libraries(application_attributes_elf PUBLIC application_attributes_core)
target_compile_options(application_attributes_elf PRIVATE -Wall -Wextra -Wpedantic -Werror)
add_executable(application_attributes_elf_test elf_prepass_test.cpp)
target_include_directories(application_attributes_elf_test PRIVATE "${pm_root}/install_plan/include")
target_compile_definitions(application_attributes_elf_test PRIVATE
    ELF_FIXTURE_DIRECTORY="${CMAKE_CURRENT_SOURCE_DIR}/fixtures/elf")
target_link_libraries(application_attributes_elf_test PRIVATE application_attributes_elf GTest::gtest_main ZLIB::ZLIB)
target_compile_options(application_attributes_elf_test PRIVATE -Wall -Wextra -Wpedantic -Werror)
gtest_discover_tests(application_attributes_elf_test DISCOVERY_TIMEOUT 30)

add_library(application_attributes_native_names STATIC "${pm_root}/jni/apk_native_inventory_names.cpp")
target_include_directories(application_attributes_native_names PUBLIC "${pm_root}/jni")
target_link_libraries(application_attributes_native_names PUBLIC application_attributes_elf)
target_compile_options(application_attributes_native_names PRIVATE -Wall -Wextra -Wpedantic -Werror)
add_executable(application_attributes_native_names_test native_names_test.cpp)
target_include_directories(application_attributes_native_names_test PRIVATE "${pm_root}/install_plan/include")
target_compile_definitions(application_attributes_native_names_test PRIVATE ELF_FIXTURE_DIRECTORY="${CMAKE_CURRENT_SOURCE_DIR}/fixtures/elf")
target_link_libraries(application_attributes_native_names_test PRIVATE application_attributes_native_names parser_minizip GTest::gtest_main)
target_compile_options(application_attributes_native_names_test PRIVATE -Wall -Wextra -Wpedantic -Werror)
gtest_discover_tests(application_attributes_native_names_test DISCOVERY_TIMEOUT 30)

# This contract probes real Linux sealing. Run the suite on a Linux build host;
# an unsupported host is a configuration error, never a skipped green test.
if(NOT CMAKE_SYSTEM_NAME STREQUAL "Linux")
    message(FATAL_ERROR "Native inventory tests require Linux memfd seals; see linux/README.md")
endif()
add_library(application_attributes_native_inventory STATIC "${pm_root}/jni/apk_native_inventory.cpp")
target_link_libraries(application_attributes_native_inventory PUBLIC application_attributes_native_names parser_minizip)
target_include_directories(application_attributes_native_inventory PRIVATE "${pm_root}/install_plan/include")
target_compile_options(application_attributes_native_inventory PRIVATE -Wall -Wextra -Wpedantic -Werror)
add_executable(application_attributes_native_inventory_test native_inventory_test.cpp)
target_include_directories(application_attributes_native_inventory_test PRIVATE "${pm_root}/install_plan/include")
target_compile_definitions(application_attributes_native_inventory_test PRIVATE
    ELF_FIXTURE_DIRECTORY="${CMAKE_CURRENT_SOURCE_DIR}/fixtures/elf")
target_link_libraries(application_attributes_native_inventory_test PRIVATE application_attributes_native_inventory GTest::gtest_main)
target_compile_options(application_attributes_native_inventory_test PRIVATE -Wall -Wextra -Wpedantic -Werror)
gtest_discover_tests(application_attributes_native_inventory_test DISCOVERY_TIMEOUT 30)

add_library(application_attributes_prepass STATIC "${pm_root}/package_transaction/src/prepass_bundle.cpp")
target_include_directories(application_attributes_prepass PRIVATE "${pm_root}/install_plan/include")
target_link_libraries(application_attributes_prepass PUBLIC application_attributes_elf)
target_compile_options(application_attributes_prepass PRIVATE -Wall -Wextra -Wpedantic -Werror)
add_executable(application_attributes_prepass_test prepass_bundle_test.cpp)
target_include_directories(application_attributes_prepass_test PRIVATE "${pm_root}/install_plan/include")
target_compile_definitions(application_attributes_prepass_test PRIVATE ELF_FIXTURE_DIRECTORY="${CMAKE_CURRENT_SOURCE_DIR}/fixtures/elf")
target_link_libraries(application_attributes_prepass_test PRIVATE application_attributes_prepass application_attributes_native_inventory GTest::gtest_main)
target_compile_options(application_attributes_prepass_test PRIVATE -Wall -Wextra -Wpedantic -Werror)
gtest_discover_tests(application_attributes_prepass_test DISCOVERY_TIMEOUT 30)

add_library(application_attributes_prepass_materializer STATIC "${pm_root}/jni/install_prepass_materializer.cpp")
target_include_directories(application_attributes_prepass_materializer PUBLIC "${pm_root}/jni")
target_link_libraries(application_attributes_prepass_materializer PUBLIC application_attributes_prepass)
target_compile_options(application_attributes_prepass_materializer PRIVATE -Wall -Wextra -Wpedantic -Werror)
add_executable(application_attributes_prepass_materializer_test prepass_materializer_test.cpp)
target_include_directories(application_attributes_prepass_materializer_test PRIVATE "${pm_root}/install_plan/include")
target_compile_definitions(application_attributes_prepass_materializer_test PRIVATE ELF_FIXTURE_DIRECTORY="${CMAKE_CURRENT_SOURCE_DIR}/fixtures/elf")
target_link_libraries(application_attributes_prepass_materializer_test PRIVATE application_attributes_prepass_materializer GTest::gtest_main)
target_compile_options(application_attributes_prepass_materializer_test PRIVATE -Wall -Wextra -Wpedantic -Werror)
target_link_options(application_attributes_prepass_materializer_test PRIVATE
    -Wl,--wrap=memfd_create,--wrap=write,--wrap=fcntl,--wrap=lseek)
gtest_discover_tests(application_attributes_prepass_materializer_test DISCOVERY_TIMEOUT 30)

add_library(application_attributes_prepass_context STATIC "${pm_root}/jni/prepass_context_wire.cpp")
target_include_directories(application_attributes_prepass_context PUBLIC "${pm_root}/jni")
target_link_libraries(application_attributes_prepass_context PUBLIC application_attributes_core)
target_compile_options(application_attributes_prepass_context PRIVATE -Wall -Wextra -Wpedantic -Werror)
add_executable(application_attributes_original_context_test "${pm_root}/test/test_prepass_context_wire.cpp")
target_include_directories(application_attributes_original_context_test PRIVATE "${pm_root}/jni")
target_compile_options(application_attributes_original_context_test PRIVATE -UNDEBUG)
target_link_libraries(application_attributes_original_context_test PRIVATE application_attributes_prepass_context)
add_executable(application_attributes_prepass_context_test prepass_context_test.cpp prepass_context_c_probe.c)
add_dependencies(application_attributes_prepass_context_test application_attributes_original_context_test)
target_compile_definitions(application_attributes_prepass_context_test PRIVATE CONTEXT_ORIGINAL_EXECUTABLE="$<TARGET_FILE:application_attributes_original_context_test>")
target_link_libraries(application_attributes_prepass_context_test PRIVATE application_attributes_prepass_context GTest::gtest_main)
target_compile_options(application_attributes_prepass_context_test PRIVATE -Wall -Wextra -Wpedantic -Werror)
set_property(TARGET application_attributes_prepass_context_test PROPERTY C_STANDARD 11)
gtest_discover_tests(application_attributes_prepass_context_test DISCOVERY_TIMEOUT 30)

add_library(application_attributes_install_wire STATIC "${pm_root}/jni/game_install_plan_wire.cpp"
    "${pm_root}/jni/game_install_plan_v1.cpp" "${pm_root}/jni/apk_install_plan_v2.cpp")
target_link_libraries(application_attributes_install_wire PUBLIC application_attributes_prepass_context
    application_attributes_prepass application_attributes_manifest)
target_include_directories(application_attributes_install_wire PRIVATE "${pm_root}/install_plan/include")
target_compile_options(application_attributes_install_wire PRIVATE -Wall -Wextra -Wpedantic -Werror)
add_executable(application_attributes_original_wire_test "${pm_root}/test/test_game_install_plan_wire.cpp")
target_compile_options(application_attributes_original_wire_test PRIVATE -UNDEBUG)
target_link_libraries(application_attributes_original_wire_test PRIVATE application_attributes_install_wire)
add_executable(application_attributes_install_wire_test install_wire_test.cpp install_wire_c_probe.c)
add_dependencies(application_attributes_install_wire_test application_attributes_original_wire_test)
target_compile_definitions(application_attributes_install_wire_test PRIVATE WIRE_ORIGINAL_EXECUTABLE="$<TARGET_FILE:application_attributes_original_wire_test>")
target_compile_definitions(application_attributes_install_wire_test PRIVATE
    WIRE_C_COMPILER="${CMAKE_C_COMPILER}" WIRE_JNI_DIRECTORY="${pm_root}/jni"
    WIRE_C_PROBE_SOURCE="${CMAKE_CURRENT_SOURCE_DIR}/install_wire_c_probe.c")
target_include_directories(application_attributes_install_wire_test PRIVATE "${pm_root}/install_plan/include")
target_link_libraries(application_attributes_install_wire_test PRIVATE application_attributes_install_wire GTest::gtest_main)
target_compile_options(application_attributes_install_wire_test PRIVATE -Wall -Wextra -Wpedantic -Werror)
set_property(TARGET application_attributes_install_wire_test PROPERTY C_STANDARD 11)
gtest_discover_tests(application_attributes_install_wire_test DISCOVERY_TIMEOUT 30)

add_library(application_attributes_install_input STATIC "${pm_root}/jni/install_input_v2.cpp")
target_include_directories(application_attributes_install_input PUBLIC ../include)
target_link_libraries(application_attributes_install_input PUBLIC application_attributes_install_wire)
target_compile_options(application_attributes_install_input PRIVATE -Wall -Wextra -Wpedantic -Werror)
add_executable(application_attributes_install_input_test install_input_test.cpp install_input_c_probe.c)
target_link_libraries(application_attributes_install_input_test PRIVATE application_attributes_install_input GTest::gtest_main)
target_link_options(application_attributes_install_input_test PRIVATE -Wl,--wrap=_Znwm -Wl,--wrap=fcntl)
target_compile_options(application_attributes_install_input_test PRIVATE -Wall -Wextra -Wpedantic -Werror)
set_property(TARGET application_attributes_install_input_test PROPERTY C_STANDARD 11)
gtest_discover_tests(application_attributes_install_input_test DISCOVERY_TIMEOUT 30)

set(APPLICATION_ATTRIBUTES_G1_APK "" CACHE FILEPATH "Explicit original G1 APK fixture for SPC-49")
add_executable(application_attributes_png_test png_codec_test.cpp)
add_dependencies(application_attributes_png_test application_attributes_manifest)
target_link_libraries(application_attributes_png_test PRIVATE application_attributes_core GTest::gtest_main)
target_compile_definitions(application_attributes_png_test PRIVATE
    PNG_PYTHON="${Python3_EXECUTABLE}" PNG_DRIVER="${CMAKE_CURRENT_SOURCE_DIR}/run_png_contract.py"
    PNG_PM_ROOT="${pm_root}" PNG_BUILD_DIR="${CMAKE_CURRENT_BINARY_DIR}"
    PNG_ZLIB_ROOT="${parser_zlib_SOURCE_DIR}" PNG_CC="${CMAKE_C_COMPILER}" PNG_CXX="${CMAKE_CXX_COMPILER}"
    PNG_G1_APK="${APPLICATION_ATTRIBUTES_G1_APK}")
gtest_discover_tests(application_attributes_png_test DISCOVERY_TIMEOUT 30)

# Consume the selected production GN graph during each test, so a missing GN
# source is a visible contract failure rather than preventing enumeration.
add_executable(application_attributes_transaction_test transaction_graph_test.cpp)
target_link_libraries(application_attributes_transaction_test PRIVATE application_attributes_core GTest::gtest_main)
target_compile_definitions(application_attributes_transaction_test PRIVATE
    TRANSACTION_PYTHON="${Python3_EXECUTABLE}" TRANSACTION_DRIVER="${CMAKE_CURRENT_SOURCE_DIR}/run_transaction_contract.py"
    TRANSACTION_PM_ROOT="${pm_root}" TRANSACTION_BUILD_DIR="${CMAKE_CURRENT_BINARY_DIR}"
    TRANSACTION_CC="${CMAKE_C_COMPILER}" TRANSACTION_CXX="${CMAKE_CXX_COMPILER}" TRANSACTION_AR="${CMAKE_AR}")
gtest_discover_tests(application_attributes_transaction_test DISCOVERY_TIMEOUT 30)
