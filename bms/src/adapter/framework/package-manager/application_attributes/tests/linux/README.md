# Linux host tests

SPC-47 and the following FD contracts require real Linux `memfd_create` and seals.
Run CMake and CTest on Linux with C++17, Clang/GCC, CMake >=3.20, Python3, a JDK
>=8, zlib development headers and nlohmann JSON headers. GoogleTest and minizip
sources are fetched at the hashes fixed in CMake. No OH SDK or device is needed
for these local contracts. They do not replace original CTS/ACTS execution.

A Docker build recipe is provided for hosts such as macOS. From the repository
root (the image name is only an example; pass your actual image ID):

```sh
docker build -t application-attributes-linux \
  src/adapter/framework/package-manager/application_attributes/tests/linux
TEST_IMAGE=$(docker image inspect application-attributes-linux --format '{{.Id}}')
python3 src/adapter/framework/package-manager/application_attributes/tests/linux/run.py \
  --image "$TEST_IMAGE" --build-dir build/task_d9973539 -- \
  cmake -S src/adapter/framework/package-manager/application_attributes/tests \
  -B build/task_d9973539 -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++
python3 src/adapter/framework/package-manager/application_attributes/tests/linux/run.py \
  --image "$TEST_IMAGE" --build-dir build/task_d9973539 -- \
  cmake --build build/task_d9973539 --clean-first --parallel 4
python3 src/adapter/framework/package-manager/application_attributes/tests/linux/run.py \
  --image "$TEST_IMAGE" --build-dir build/task_d9973539 -- \
  ctest --test-dir build/task_d9973539 --output-on-failure --no-tests=error
```

Use a clean rebuild when validating edits across a shared host/container mount;
do not infer new object bytes from a successful incremental command alone.
Do not reuse a CMake cache from a different host, compiler or source location.
The wrapper passes argv directly, mounts source read-only at `/workspace` and
only the selected build tree writable. It does not patch, skip or fabricate test
results; `gtest_discover_tests` enumerates the actual Linux test binaries. Normal
container syscall support suffices; no privileged mode is required. Record the
resolved image ID, compiler, kernel, source commit and logs with each execution.
The Dockerfile is a bootstrap recipe, not a claim that mutable distribution
packages produce byte-identical images. An unavailable image/tool/seal is an
infrastructure failure, never an acceptance result.
