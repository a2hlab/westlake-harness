# Production install input C boundary (SPC-24)

`oh_adapter_acquire_install_input_v2` consumes the existing V2 plan byte span
and a signed user plus all 64 requested flag bits. The returned
`OhAdapterInstallInputV2` owns independent CLOEXEC copies of every descriptor.
The caller owns the output buffer. Acquisition succeeds only after the real
plan validator has checked the source set; it does not authenticate a producer,
grant requested flags, execute an installation or report a READY query DTO.
The T-40 install entry must consume this snapshot before the original transaction
uses it; caller policy and host readiness remain their existing owners' duties.
T-48 is responsible for GN/Java/JNI assembly. CMake symbol invocation proves this
boundary's behavior, not completed OH integration.

The test links a C11 probe to this production entry and the real V1/V2 validators.
The shared packet fixture builds raw APK bytes, invokes the production manifest
parser and canonical prepass codec, then uses real sealed Linux FDs. Signing is
raw input supplied at the verified-producer edge; no cryptographic decision is
reimplemented. V1 layout/legacy behavior remains covered by the unchanged
original wire executable via SPC-50.

The allocation and fcntl wrappers affect only allocator/OS edges. Every earlier
successful allocation is preserved while each successive operator-new call
fails once, until the first fully successful call. No boundary or business
validator is mocked. Other-exception and descriptor-failure cases verify cleanup;
eight concurrent readers use one immutable source and independent outputs.

An OOM discovered nlohmann's noexcept scalar comparison allocating a temporary
JSON string. Its structured destructor also allocates a flattening vector.
The production metadata path now compares string references, uses bounded SAX
DOM construction, enforces canonical key ordering before replacement, and clears
children without allocating before JSON destruction. This retains the original
64-container limit and canonical schema checks. No vendored library is patched.
