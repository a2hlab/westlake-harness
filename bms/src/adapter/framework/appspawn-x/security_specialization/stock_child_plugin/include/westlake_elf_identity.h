#ifndef WESTLAKE_ELF_IDENTITY_H
#define WESTLAKE_ELF_IDENTITY_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define WLEI_SHA256_HEX_SIZE (64U + 1U)
#define WLEI_BUILD_ID_HEX_SIZE (40U + 1U)
#define WLEI_RESOLVED_PATH_SIZE 4096U

typedef struct WleiVerifiedFile {
    int descriptor;
    uint32_t reserved_zero;
    uint64_t device;
    uint64_t inode;
    uint64_t size;
    char resolved_path[WLEI_RESOLVED_PATH_SIZE];
} WleiVerifiedFile;

/*
 * Opens and retains the exact verified object.  The descriptor remains owned
 * by the caller until WLEI_CloseVerifiedFile, so a later pathname replacement
 * cannot change the inode supplied to the loader.
 */
int WLEI_OpenVerifiedFileHex(
    const char *expected_absolute_path,
    uint16_t expected_machine,
    const char sha256_hex[WLEI_SHA256_HEX_SIZE],
    const char build_id_hex[WLEI_BUILD_ID_HEX_SIZE],
    WleiVerifiedFile *out_verified);

/* OH system roots are exact path/SHA/Build-ID/inode bound. */
int WLEI_OpenVerifiedSystemFileHex(
    const char *expected_absolute_path,
    uint16_t expected_machine,
    const char sha256_hex[WLEI_SHA256_HEX_SIZE],
    const char build_id_hex[WLEI_BUILD_ID_HEX_SIZE],
    WleiVerifiedFile *out_verified);

int WLEI_CloseVerifiedFile(WleiVerifiedFile *verified);

int WLEI_VerifyFileHex(
    const char *expected_absolute_path,
    uint16_t expected_machine,
    const char sha256_hex[WLEI_SHA256_HEX_SIZE],
    const char build_id_hex[WLEI_BUILD_ID_HEX_SIZE],
    char *out_resolved_path, size_t out_resolved_path_size);

int WLEI_VerifyLoadedSymbolHex(
    void *handle, const char *symbol_name,
    const char *expected_absolute_path,
    uint16_t expected_machine,
    const char sha256_hex[WLEI_SHA256_HEX_SIZE],
    const char build_id_hex[WLEI_BUILD_ID_HEX_SIZE],
    void **out_symbol);

#ifdef __cplusplus
}
#endif

#endif
