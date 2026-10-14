/**
 * appspawn-x child process entry point.
 *
 * The selected stock Route A calls runAfterStockSpecialization() only after
 * consuming a typed stock-security receipt. The legacy security-owning run()
 * entry remains ABI-compatible but fails closed.
 */

#pragma once

#include "spawn_msg.h"
#include <jni.h>

namespace appspawnx {

class AppSpawnXRuntime;

class ChildMain {
public:
    // Run in child process after fork.
    // This function does not return – it enters ActivityThread.main() event loop.
    [[noreturn]] static void run(const SpawnMsg& msg, AppSpawnXRuntime* runtime);

    // Route A entry. The caller is the stock OH appspawn child looper and may
    // invoke this only after the stock stage-31 tail receipt is complete.
    // This path deliberately contains no token, DAC, mount/sandbox, UID/GID,
    // capability, or SELinux operation.
    [[noreturn]] static void runAfterStockSpecialization(
        const SpawnMsg& msg, AppSpawnXRuntime* runtime);

private:
    // OH security specialization
    static int applyDac(const SpawnMsg& msg);
    static int applySandbox(const SpawnMsg& msg);
    static int applySELinux(const SpawnMsg& msg);
    static int applyAccessToken(const SpawnMsg& msg);

    // Android initialization — both use the runtime's cached PathClassLoader
    // (when available) to find classes in oh-adapter-runtime.jar, avoiding
    // bootstrap-classloader re-load of liboh_adapter_bridge.so.
    static int initAdapterLayer(JNIEnv* env, AppSpawnXRuntime* runtime);
    static void launchActivityThread(JNIEnv* env, const SpawnMsg& msg,
                                     AppSpawnXRuntime* runtime);
};

} // namespace appspawnx
