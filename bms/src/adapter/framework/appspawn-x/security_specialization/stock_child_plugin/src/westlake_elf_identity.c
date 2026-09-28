#include "westlake_elf_identity.h"

#include "westlake_sha256.h"

#include <dlfcn.h>
#include <elf.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static uint8_t HexNibble(char value)
{
    if (value >= '0' && value <= '9') {
        return (uint8_t)(value - '0');
    }
    if (value >= 'a' && value <= 'f') {
        return (uint8_t)(value - 'a' + 10);
    }
    return UINT8_C(255);
}

static int DecodeHex(uint8_t *output, size_t output_size,
                     const char *hex, size_t hex_size)
{
    size_t index;
    if (output == NULL || hex == NULL ||
        hex_size != output_size * 2U + 1U ||
        hex[hex_size - 1U] != '\0') {
        return -1;
    }
    for (index = 0; index < output_size; ++index) {
        uint8_t high = HexNibble(hex[index * 2U]);
        uint8_t low = HexNibble(hex[index * 2U + 1U]);
        if (high == UINT8_C(255) || low == UINT8_C(255)) {
            return -1;
        }
        output[index] = (uint8_t)((high << 4U) | low);
    }
    return 0;
}

static int ReadExactAt(int descriptor, void *output, size_t size,
                       off_t offset)
{
    uint8_t *bytes = (uint8_t *)output;
    size_t consumed = 0U;
    while (consumed < size) {
        ssize_t count = pread(descriptor, bytes + consumed,
                              size - consumed,
                              offset + (off_t)consumed);
        if (count > 0) {
            consumed += (size_t)count;
            continue;
        }
        if (count < 0 && errno == EINTR) {
            continue;
        }
        return -1;
    }
    return 0;
}

static size_t AlignNoteSize(uint32_t size)
{
    return ((size_t)size + 3U) & ~(size_t)3U;
}

static int VerifyBuildId(
    int descriptor, const struct stat *status, uint16_t expected_machine,
    const uint8_t expected[20], size_t expected_size)
{
    Elf64_Ehdr header;
    uint32_t build_id_count = UINT32_C(0);
    uint8_t difference = UINT8_C(0);
    size_t program_index;
    if (descriptor < 0 || status == NULL || expected == NULL ||
        expected_machine == UINT16_C(0) ||
        (expected_size != 16U && expected_size != 20U) ||
        ReadExactAt(descriptor, &header, sizeof(header), 0) != 0 ||
        memcmp(header.e_ident, ELFMAG, SELFMAG) != 0 ||
        header.e_ident[EI_CLASS] != ELFCLASS64 ||
        header.e_ident[EI_DATA] != ELFDATA2LSB ||
        header.e_type != ET_DYN || header.e_machine != expected_machine ||
        header.e_phentsize != sizeof(Elf64_Phdr) ||
        header.e_phnum == 0U || header.e_phnum > 128U ||
        header.e_phoff > (Elf64_Off)status->st_size ||
        (Elf64_Xword)header.e_phnum * sizeof(Elf64_Phdr) >
            (Elf64_Xword)status->st_size - header.e_phoff) {
        return -1;
    }
    for (program_index = 0U; program_index < header.e_phnum;
         ++program_index) {
        Elf64_Phdr program;
        uint8_t *notes;
        size_t cursor = 0U;
        if (ReadExactAt(
                descriptor, &program, sizeof(program),
                (off_t)(header.e_phoff +
                        program_index * sizeof(Elf64_Phdr))) != 0) {
            return -1;
        }
        if (program.p_type != PT_NOTE) {
            continue;
        }
        if (program.p_filesz == 0U || program.p_filesz > UINT64_C(65536) ||
            program.p_offset > (Elf64_Off)status->st_size ||
            program.p_filesz >
                (Elf64_Xword)status->st_size - program.p_offset) {
            return -1;
        }
        notes = (uint8_t *)malloc((size_t)program.p_filesz);
        if (notes == NULL || ReadExactAt(
                descriptor, notes, (size_t)program.p_filesz,
                (off_t)program.p_offset) != 0) {
            free(notes);
            return -1;
        }
        while (cursor + sizeof(Elf64_Nhdr) <= program.p_filesz) {
            Elf64_Nhdr note;
            size_t name_size;
            size_t description_size;
            size_t payload;
            (void)memcpy(&note, notes + cursor, sizeof(note));
            cursor += sizeof(note);
            name_size = AlignNoteSize(note.n_namesz);
            description_size = AlignNoteSize(note.n_descsz);
            if (name_size > SIZE_MAX - description_size) {
                free(notes);
                return -1;
            }
            payload = name_size + description_size;
            if (payload > (size_t)program.p_filesz - cursor) {
                free(notes);
                return -1;
            }
            if (note.n_type == NT_GNU_BUILD_ID && note.n_namesz == 4U &&
                note.n_descsz == expected_size &&
                memcmp(notes + cursor, "GNU", 4U) == 0) {
                size_t index;
                const uint8_t *actual = notes + cursor + name_size;
                ++build_id_count;
                for (index = 0; index < expected_size; ++index) {
                    difference = (uint8_t)(difference |
                        (actual[index] ^ expected[index]));
                }
            }
            cursor += payload;
        }
        free(notes);
    }
    return build_id_count == UINT32_C(1) && difference == UINT8_C(0) ?
        0 : -1;
}

static int OpenVerifiedFileHex(
    const char *expected_absolute_path,
    uint16_t expected_machine,
    const char sha256_hex[WLEI_SHA256_HEX_SIZE],
    const char *build_id_hex,
    WleiVerifiedFile *out_verified)
{
    uint8_t expected_sha[WLSHA256_DIGEST_SIZE];
    uint8_t expected_build_id[20] = {0};
    uint8_t actual_sha[WLSHA256_DIGEST_SIZE];
    uint8_t buffer[16384];
    WlSha256Context context;
    struct stat status;
    char resolved_path[PATH_MAX];
    uint8_t difference = UINT8_C(0);
    size_t index;
    size_t build_id_digits;
    size_t build_id_size;
    int descriptor;
    struct stat final_status;
    if (out_verified == NULL || expected_absolute_path == NULL ||
        expected_absolute_path[0] != '/' || sha256_hex == NULL ||
        DecodeHex(expected_sha, sizeof(expected_sha), sha256_hex,
                  WLEI_SHA256_HEX_SIZE) != 0 ||
        build_id_hex == NULL ||
        ((build_id_digits = strlen(build_id_hex)) != 32U &&
         build_id_digits != 40U) ||
        ((build_id_size = build_id_digits / 2U) == 0U) ||
        DecodeHex(expected_build_id, build_id_size, build_id_hex,
                  build_id_digits + 1U) != 0 ||
        realpath(expected_absolute_path, resolved_path) == NULL ||
        strcmp(resolved_path, expected_absolute_path) != 0 ||
        strlen(resolved_path) >= WLEI_RESOLVED_PATH_SIZE) {
        return -1;
    }
    (void)memset(out_verified, 0, sizeof(*out_verified));
    out_verified->descriptor = -1;
    descriptor = open(resolved_path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (descriptor < 0 || fstat(descriptor, &status) != 0 ||
        !S_ISREG(status.st_mode) || status.st_size <= 0 ||
        VerifyBuildId(descriptor, &status, expected_machine,
                      expected_build_id, build_id_size) != 0) {
        if (descriptor >= 0) {
            (void)close(descriptor);
        }
        return -1;
    }
    WLSha256Init(&context);
    for (;;) {
        ssize_t count = read(descriptor, buffer, sizeof(buffer));
        if (count > 0) {
            if (WLSha256Update(&context, buffer, (size_t)count) != 0) {
                (void)close(descriptor);
                return -1;
            }
            continue;
        }
        if (count < 0 && errno == EINTR) {
            continue;
        }
        if (count < 0) {
            (void)close(descriptor);
            return -1;
        }
        break;
    }
    if (WLSha256Final(&context, actual_sha) != 0 ||
        fstat(descriptor, &final_status) != 0 ||
        final_status.st_dev != status.st_dev ||
        final_status.st_ino != status.st_ino ||
        final_status.st_size != status.st_size) {
        (void)close(descriptor);
        return -1;
    }
    for (index = 0; index < sizeof(expected_sha); ++index) {
        difference = (uint8_t)(difference |
            (expected_sha[index] ^ actual_sha[index]));
    }
    if (difference != UINT8_C(0)) {
        (void)close(descriptor);
        return -1;
    }
    out_verified->descriptor = descriptor;
    out_verified->device = (uint64_t)status.st_dev;
    out_verified->inode = (uint64_t)status.st_ino;
    out_verified->size = (uint64_t)status.st_size;
    (void)memcpy(out_verified->resolved_path, resolved_path,
                 strlen(resolved_path) + 1U);
    return 0;
}

int WLEI_OpenVerifiedFileHex(
    const char *expected_absolute_path,
    uint16_t expected_machine,
    const char sha256_hex[WLEI_SHA256_HEX_SIZE],
    const char build_id_hex[WLEI_BUILD_ID_HEX_SIZE],
    WleiVerifiedFile *out_verified)
{
    return OpenVerifiedFileHex(expected_absolute_path, expected_machine,
                               sha256_hex, build_id_hex, out_verified);
}

int WLEI_OpenVerifiedSystemFileHex(
    const char *expected_absolute_path,
    uint16_t expected_machine,
    const char sha256_hex[WLEI_SHA256_HEX_SIZE],
    const char build_id_hex[WLEI_BUILD_ID_HEX_SIZE],
    WleiVerifiedFile *out_verified)
{
    return OpenVerifiedFileHex(expected_absolute_path, expected_machine,
                               sha256_hex, build_id_hex, out_verified);
}

int WLEI_CloseVerifiedFile(WleiVerifiedFile *verified)
{
    int result;
    if (verified == NULL || verified->descriptor < 0) {
        return -1;
    }
    result = close(verified->descriptor);
    verified->descriptor = -1;
    return result;
}

int WLEI_VerifyFileHex(
    const char *expected_absolute_path,
    uint16_t expected_machine,
    const char sha256_hex[WLEI_SHA256_HEX_SIZE],
    const char build_id_hex[WLEI_BUILD_ID_HEX_SIZE],
    char *out_resolved_path, size_t out_resolved_path_size)
{
    WleiVerifiedFile verified;
    int result = WLEI_OpenVerifiedFileHex(
        expected_absolute_path, expected_machine, sha256_hex, build_id_hex,
        &verified);
    if (result != 0) {
        return -1;
    }
    if (out_resolved_path != NULL) {
        size_t length = strlen(verified.resolved_path);
        if (out_resolved_path_size <= length) {
            (void)WLEI_CloseVerifiedFile(&verified);
            return -1;
        }
        (void)memcpy(out_resolved_path, verified.resolved_path, length + 1U);
    }
    return WLEI_CloseVerifiedFile(&verified);
}

int WLEI_VerifyLoadedSymbolHex(
    void *handle, const char *symbol_name,
    const char *expected_absolute_path,
    uint16_t expected_machine,
    const char sha256_hex[WLEI_SHA256_HEX_SIZE],
    const char build_id_hex[WLEI_BUILD_ID_HEX_SIZE],
    void **out_symbol)
{
    Dl_info information;
    char file_path[PATH_MAX];
    char symbol_path[PATH_MAX];
    void *symbol;
    if (handle == NULL || symbol_name == NULL || out_symbol == NULL ||
        WLEI_VerifyFileHex(
            expected_absolute_path, expected_machine, sha256_hex,
            build_id_hex, file_path, sizeof(file_path)) != 0) {
        return -1;
    }
    (void)dlerror();
    symbol = dlsym(handle, symbol_name);
    if (symbol == NULL || dlerror() != NULL ||
        dladdr(symbol, &information) == 0 || information.dli_fname == NULL ||
        realpath(information.dli_fname, symbol_path) == NULL ||
        strcmp(symbol_path, file_path) != 0) {
        return -1;
    }
    *out_symbol = symbol;
    return 0;
}
