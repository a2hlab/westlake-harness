import json
from pathlib import Path
import subprocess
import tempfile

from settings import ACCEPTED, HERE, file, save, sha


def replay():
    result = {}
    sources = {"r3": file(ACCEPTED + "/inputs/host-r3.c"),
               "n11h": file(ACCEPTED + "/src/candidate-stock-host.c")}
    pins = {"inputs/host-r3.c": "507bf160dfae87851345c8fc564c9378356a773cc84272d2ec0635b1c0ef0c50",
            "src/candidate-stock-host.c": "e5f82b9971f64cb32f9f32cbba900fb68d690c11c45764c543d89d460213f1af",
            "inputs/resident-compat.h": "e4f7321547d6cafac5734a7ff3b9338cc0e8a93e94ff5932bafa3caa23cb35e0",
            "n11h-owner.h": "17975d2f82f15b0ea6883c777cbcef4bf6101ae149e9af6e519269310c2e4476"}
    for name, expected in pins.items():
        if sha(file(ACCEPTED + "/" + name)) != expected:
            raise ValueError("accepted callback source drift: " + name)
    with tempfile.TemporaryDirectory() as temporary:
        folder = Path(temporary)
        (folder / "dlfcn.h").write_text('''#pragma once
typedef struct { char name[256]; } Dl_namespace;
#define RTLD_NOW 2
#define RTLD_NOLOAD 4
#define RTLD_LOCAL 0
#define RTLD_GLOBAL 256
int dlns_get(const char*, Dl_namespace*);
void* dlopen_ns(Dl_namespace*, const char*, int);
void* dlsym(void*, const char*);
int dlclose(void*);
char* dlerror(void);
''')
        for variant, source in sources.items():
            text = source.read_text()
            start = text.index("static int NamespaceNameOwnedByCurrentProcess(")
            end = text.index("static uint8_t HexNibble(", start)
            (folder / "callback-body.h").write_text(text[start:end])
            command = ["/usr/bin/cc", "-std=c11", "-I" + str(folder), "-I" + str(file(ACCEPTED + "/n11h-owner.h").parent),
                       "-I" + str(file(ACCEPTED + "/inputs/resident-compat.h").parent),
                       str(HERE / "timing_fixture.c"), "-o", str(folder / "replay")]
            subprocess.run(command, check=True)
            result[variant] = {}
            for case in ["early", "late", "absent", "private"]:
                completed = subprocess.run([str(folder / "replay"), case], capture_output=True, text=True, check=True)
                row = json.loads(next(line[7:] for line in completed.stdout.splitlines() if line.startswith("RESULT ")))
                row.update(source=str(source.relative_to(file(ACCEPTED + "/README.md").parents[2])),
                           source_sha256=sha(source), fixture="actual callbacks with simulated bootstrap-side compat mapping",
                           trace=completed.stdout.splitlines(), stderr=completed.stderr)
                result[variant][case] = row
    return dict(schema_version=1, device_access=False, accepted_candidate_modified=False, cases=result)


def main():
    result = replay()
    cases = result["cases"]
    assert cases["r3"]["late"]["verified"] == 1 and cases["n11h"]["late"]["unavailable"] == 1
    assert cases["r3"]["private"]["compat_queries"] == 2 and cases["n11h"]["private"]["compat_queries"] == 0
    assert all(row["callback_rc"] == 0 for values in cases.values() for row in values.values())
    save(HERE / "evidence/timing-replay.json", result)
    for variant, values in cases.items():
        for case, row in values.items():
            print(variant + "/" + case + ": rc=" + str(row["callback_rc"]) + " query@" + str(row["first_compat_query"]) +
                  " bootstrap@" + str(row["bootstrap_sequence"]) + " verified=" + str(row["verified"]) + " unavailable=" + str(row["unavailable"]))


if __name__ == "__main__":
    main()
