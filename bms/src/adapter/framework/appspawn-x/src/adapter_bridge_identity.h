#pragma once

namespace appspawnx {

/* Verify the fixed file before dlopen can run constructors, then rebind it. */
bool LoadVerifiedAdapterBridge(void **out_handle);
bool LoadVerifiedAndroidRuntime(void **out_handle);

/* Verify an already-loaded bridge without causing any load side effect. */
bool VerifyLoadedAdapterBridge(void *handle);
bool VerifyLoadedAndroidRuntime(void *handle);

}  // namespace appspawnx
