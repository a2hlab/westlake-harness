// App-namespace JNI entry point for the BoatAttack audio bridge. The actual
// AudioRenderer backend is preloaded by appspawn-x in the system namespace;
// this tiny loader has no OpenHarmony multimedia dependencies of its own.

#include <dlfcn.h>
#include <elf.h>
#include <jni.h>
#include <link.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>

namespace {

using RegisterAudioCompat = int (*)(JNIEnv*);

struct SymbolLookup {
    const char* objectName;
    const char* symbolName;
    void* address;
};

uint32_t gnuHash(const char* name) {
    uint32_t hash = 5381;
    for (const unsigned char* p =
             reinterpret_cast<const unsigned char*>(name); *p; ++p) {
        hash = hash * 33 + *p;
    }
    return hash;
}

template <typename T>
T* loadedPointer(Elf64_Addr value, Elf64_Addr base) {
    const uintptr_t address = value < base ? base + value : value;
    return reinterpret_cast<T*>(address);
}

int findSymbolInObject(dl_phdr_info* info, size_t, void* opaque) {
    auto* lookup = static_cast<SymbolLookup*>(opaque);
    if (!info->dlpi_name || !strstr(info->dlpi_name, lookup->objectName)) {
        return 0;
    }

    const Elf64_Dyn* dynamic = nullptr;
    for (Elf64_Half index = 0; index < info->dlpi_phnum; ++index) {
        if (info->dlpi_phdr[index].p_type == PT_DYNAMIC) {
            dynamic = reinterpret_cast<const Elf64_Dyn*>(
                info->dlpi_addr + info->dlpi_phdr[index].p_vaddr);
            break;
        }
    }
    if (!dynamic) return 0;

    const Elf64_Sym* symbols = nullptr;
    const char* strings = nullptr;
    const uint32_t* sysvHash = nullptr;
    const uint32_t* gnuHashTable = nullptr;
    for (const Elf64_Dyn* entry = dynamic; entry->d_tag != DT_NULL; ++entry) {
        switch (entry->d_tag) {
            case DT_SYMTAB:
                symbols = loadedPointer<const Elf64_Sym>(
                    entry->d_un.d_ptr, info->dlpi_addr);
                break;
            case DT_STRTAB:
                strings = loadedPointer<const char>(
                    entry->d_un.d_ptr, info->dlpi_addr);
                break;
            case DT_HASH:
                sysvHash = loadedPointer<const uint32_t>(
                    entry->d_un.d_ptr, info->dlpi_addr);
                break;
            case DT_GNU_HASH:
                gnuHashTable = loadedPointer<const uint32_t>(
                    entry->d_un.d_ptr, info->dlpi_addr);
                break;
            default:
                break;
        }
    }
    if (!symbols || !strings) return 0;

    if (sysvHash) {
        const uint32_t symbolCount = sysvHash[1];
        for (uint32_t index = 0; index < symbolCount; ++index) {
            const Elf64_Sym& symbol = symbols[index];
            if (symbol.st_shndx != SHN_UNDEF &&
                strcmp(strings + symbol.st_name, lookup->symbolName) == 0) {
                lookup->address = reinterpret_cast<void*>(
                    info->dlpi_addr + symbol.st_value);
                return 1;
            }
        }
    }

    if (gnuHashTable) {
        const uint32_t bucketCount = gnuHashTable[0];
        const uint32_t symbolOffset = gnuHashTable[1];
        const uint32_t bloomCount = gnuHashTable[2];
        const auto* bloom = reinterpret_cast<const Elf64_Addr*>(
            gnuHashTable + 4);
        const auto* buckets = reinterpret_cast<const uint32_t*>(
            bloom + bloomCount);
        const auto* chains = buckets + bucketCount;
        const uint32_t hash = gnuHash(lookup->symbolName);
        uint32_t index = buckets[hash % bucketCount];
        if (index < symbolOffset) return 0;
        for (;;) {
            const uint32_t chainHash = chains[index - symbolOffset];
            if ((chainHash | 1u) == (hash | 1u)) {
                const Elf64_Sym& symbol = symbols[index];
                if (symbol.st_shndx != SHN_UNDEF &&
                    strcmp(strings + symbol.st_name, lookup->symbolName) == 0) {
                    lookup->address = reinterpret_cast<void*>(
                        info->dlpi_addr + symbol.st_value);
                    return 1;
                }
            }
            if (chainHash & 1u) break;
            ++index;
        }
    }
    return 0;
}

void* findLoadedBackendSymbol() {
    SymbolLookup lookup{
        "libwestlake_audio_caps.so", "westlake_register_audio_compat", nullptr};
    dl_iterate_phdr(findSymbolInObject, &lookup);
    return lookup.address;
}

void writeStatus(const char* value) {
    FILE* file = fopen(
        "/data/storage/el2/base/files/westlake_audio_compat.status", "w");
    if (!file) return;
    fprintf(file, "%s\n", value);
    fclose(file);
}

}  // namespace

extern "C" __attribute__((visibility("default")))
jint JNI_OnLoad(JavaVM* vm, void*) {
    JNIEnv* env = nullptr;
    if (!vm || vm->GetEnv(reinterpret_cast<void**>(&env), JNI_VERSION_1_6) != JNI_OK ||
        !env) {
        writeStatus("AUDIO_BACKEND=NO_JNI_ENV");
        return JNI_ERR;
    }
    auto registerAudio = reinterpret_cast<RegisterAudioCompat>(
        dlsym(RTLD_DEFAULT, "westlake_register_audio_compat"));
    if (!registerAudio) {
        void* backend = dlopen(
            "/data/boat-attack-audio-c21/libwestlake_audio_caps.so",
            RTLD_NOW | RTLD_NOLOAD);
        if (backend) {
            registerAudio = reinterpret_cast<RegisterAudioCompat>(
                dlsym(backend, "westlake_register_audio_compat"));
        }
    }
    if (!registerAudio) {
        registerAudio = reinterpret_cast<RegisterAudioCompat>(
            findLoadedBackendSymbol());
    }
    if (!registerAudio) {
        writeStatus("AUDIO_BACKEND=NOT_VISIBLE");
        return JNI_ERR;
    }
    if (registerAudio(env) != 0) {
        writeStatus("AUDIO_BACKEND=REGISTER_FAILED");
        return JNI_ERR;
    }
    writeStatus("AUDIO_BACKEND=READY");
    return JNI_VERSION_1_6;
}
