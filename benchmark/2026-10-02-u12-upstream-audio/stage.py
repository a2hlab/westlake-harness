import difflib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError("upstream anchor drift: " + old[:80])
    return source.replace(old, new, 1)


def candidate_source():
    source = (HERE / "upstream/opensles_android_adapter.c").read_text()
    source = replace_once(source, '#include <unistd.h>', '#include <unistd.h>\n#include "iid_width.h"')
    for name in ["android_sbq", "android_config"]:
        source = replace_once(source, 'struct SLInterfaceID_ westlake_sl_iid_' + name,
                              'struct U12AndroidId westlake_sl_iid_' + name)
        source = replace_once(source, '= &westlake_sl_iid_' + name + ';', '= (SLInterfaceID) &westlake_sl_iid_' + name + ';')
    old = '''static int iid_is(SLInterfaceID a, SLInterfaceID b)
{
    return a != NULL && b != NULL && (a == b || memcmp(a, b, sizeof(*a)) == 0);
}'''
    new = '''static int iid_is(SLInterfaceID android, SLInterfaceID target)
{
    if (!android || !target) return 0;
    if (android == target) return 1;
    if (target == SL_IID_ANDROIDSIMPLEBUFFERQUEUE || target == SL_IID_ANDROIDCONFIGURATION)
        return U12EqualAndroidIds(android, target);
    return U12EqualAndroidOwnerId(android, target);
}'''
    source = replace_once(source, old, new)
    source = replace_once(source, new, 'extern const SLInterfaceID SL_IID_ANDROIDCONFIGURATION;\n' + new)
    old = '''        if (oh_iids[i] != NULL && (oh_iids[i] == id || memcmp(oh_iids[i], id, sizeof(*id)) == 0)) {
            return oh_iids[i];
        }'''
    new = '''        if (oh_iids[i] == id) return id;
        if (U12EqualAndroidOwnerId(id, oh_iids[i])) return oh_iids[i];'''
    source = replace_once(source, old, new)
    source = replace_once(source, '(unsigned) iid->time_low', '(unsigned) ((const struct U12AndroidId*)iid)->time_low')
    start = source.index('static int oh_resolve(void)')
    end = source.index("/* Android's simple-buffer-queue ID", start)
    source = source[:start] + '''int U12BindOpenSLESResidentOwner(void* handle)
{
    if (handle == NULL) return 0;
    if (oh.lib != NULL) return oh.lib == handle;
    void* function = dlsym(handle, "slCreateEngine");
    Dl_info identity;
    if (function == NULL || !dladdr(function, &identity) || identity.dli_fname == NULL ||
        strcmp(identity.dli_fname, "/system/lib64/libOpenSLES.so") != 0) return 0;
    const SLInterfaceID* engine = dlsym(handle, "SL_IID_ENGINE");
    const SLInterfaceID* play = dlsym(handle, "SL_IID_PLAY");
    const SLInterfaceID* volume = dlsym(handle, "SL_IID_VOLUME");
    const SLInterfaceID* queue = dlsym(handle, "SL_IID_OH_BUFFERQUEUE");
    const SLInterfaceID* standard = dlsym(handle, "SL_IID_BUFFERQUEUE");
    if (!engine || !play || !volume || !queue || !*engine || !*play || !*volume || !*queue) return 0;
    oh.create_engine = (__typeof__(oh.create_engine))function;
    oh.engine = *engine;
    oh.play = *play;
    oh.volume = *volume;
    oh.oh_bq = *queue;
    oh.std_bq = standard ? *standard : NULL;
    oh.lib = handle;
    return 1;
}

static int oh_resolve(void)
{
    return oh.lib != NULL && oh.create_engine != NULL;
}

''' + source[end:]
    return source


def main():
    source = candidate_source()
    target = HERE / "candidate/opensles_android_adapter.c"
    target.parent.mkdir(exist_ok=True)
    target.write_text(source)
    old = (HERE / "upstream/opensles_android_adapter.c").read_text()
    (HERE / "candidate/source.patch").write_text("".join(difflib.unified_diff(old.splitlines(True), source.splitlines(True),
                                                       fromfile="upstream/c7d2992", tofile="route-A/candidate")))
    print(json.dumps(dict(candidate_source=str(target), fresh_open_added=False, owner_binding="injected exact canonical resident handle, publication unimplemented",
                    play_completion_implemented=False, media_owner_registered=False)))


if __name__ == "__main__":
    main()
