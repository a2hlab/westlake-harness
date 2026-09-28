/*
 * Presence-only libmediandk provider for native guests with an unconditional
 * DT_NEEDED edge but no AMedia or AImage undefined symbols.
 *
 * This intentionally exports no pretend media API.  A guest that starts to
 * reference an NDK media symbol must fail relocation until a real adapter is
 * implemented.
 */

__attribute__((visibility("default")))
const char westlake_mediandk_presence_provenance[] =
    "westlake-mediandk-presence-v1-no-media-api";
