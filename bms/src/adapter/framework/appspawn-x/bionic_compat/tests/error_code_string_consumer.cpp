// Target-only link fixture: this consumer must acquire the C++ ABI from a
// direct libziparchive.so edge, never from libbionic_compat.
const char* ErrorCodeString(int);

extern "C" const char* WestLakeZipErrorConsumer(int code) {
  return ErrorCodeString(code);
}
