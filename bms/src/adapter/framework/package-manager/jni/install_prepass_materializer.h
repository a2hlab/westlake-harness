#ifndef OH_ADAPTER_INSTALL_PREPASS_MATERIALIZER_H
#define OH_ADAPTER_INSTALL_PREPASS_MATERIALIZER_H
#include <string>

namespace oh_adapter {
// Materializes caller-validated canonical bytes; this is not authentication or
// an install decision. On success the caller owns one CLOEXEC FD at offset zero,
// immutable through WRITE/SHRINK/GROW/SEAL seals (not an O_RDONLY access mode).
// On failure returns false, sets errno, closes every FD created by this call,
// and writes -1 to output. output is a result cell, not an existing owned FD.
// Payload must be nonempty and within PrepassBundleCodec::MAX_PAYLOAD_BYTES.
// Linux/OH only; unsupported platforms fail with ENOTSUP, never fake sealing.
bool WriteCanonicalPrepassFd(const std::string& canonicalPayload, int* output) noexcept;
}
#endif
