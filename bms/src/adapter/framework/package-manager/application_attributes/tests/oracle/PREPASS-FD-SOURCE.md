# Prepass FD validation (SPC-51)

Production entry: `oh_adapter::WriteCanonicalPrepassFd` in
`jni/install_prepass_materializer.cpp`. Input comes from the real
`PrepassBundleCodec::Encode`; the native case additionally uses `InspectElf`
on the pinned GNU ELF64 fixture. No codec or ELF decision is duplicated here.

The no-native case preserves the readback and four-seal assertions of
`test/test_install_prepass_materializer.cpp`. Its complete context-based
`BuildInstallPrepass` caller is not yet run: context belongs to T-09 and legacy
include/call assembly to T-48. SPC-51 tests the actual canonical-byte FD boundary.

Linux reference semantics, checked 2026-09-12:

- [memfd_create](https://man7.org/linux/man-pages/man2/memfd_create.2.html):
  anonymous memory file, CLOEXEC and ALLOW_SEALING; the descriptor starts O_RDWR.
  Here immutable means the inode's four seals, not an O_RDONLY access mode.
- [write](https://man7.org/linux/man-pages/man2/write.2.html): a positive short
  write advances by actual bytes; interrupted calls with no bytes can be retried.
- [F_ADD_SEALS](https://man7.org/linux/man-pages/man2/F_ADD_SEALS.2const.html):
  WRITE, SHRINK, GROW and SEAL prevent subsequent modification/removal of seals.
- [F_DUPFD](https://man7.org/linux/man-pages/man2/F_DUPFD.2const.html): explicit
  owned CLOEXEC duplicate; failure is not a published output.
- [close](https://man7.org/linux/man-pages/man2/close.2.html): Linux releases the
  descriptor even for errors other than EBADF; do not retry close after EINTR.
- [GNU ld options](https://sourceware.org/binutils/docs/ld/Options.html): `--wrap`
  redirects external symbol references to test wrappers. Here they only inject
  OS failures/short writes. All successful operations call `__real_*` and use
  real Linux memfd, descriptors and seals. Unsupported wrapper commands abort.

Tests compare actual FD counts and EBADF after each failure; cover memfd EMFILE,
zero write, partial write then ENOSPC, seal EPERM, seek EIO and dup EMFILE. Positive
short-write/EINTR recovery also reaches the real kernel. The writer authenticates
no caller, publishes no plan and owns no host transaction; those boundaries remain
separate. Actual OH build, installation, CTS and ACTS are not claimed by this test.
