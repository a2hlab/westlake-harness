/*
 * Copyright (C) 2019 The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package android.os.ext;

import java.util.Collections;
import java.util.Map;

/**
 * Adapter (AOSP-on-OH) thin stub for the SdkExtensions mainline-module class.
 *
 * RATIONALE (WestLake adapter, 铁律一致):
 *   android.os.ext.SdkExtensions belongs to the com.android.sdkext mainline
 *   APEX (packages/modules/SdkExtensions), which is NOT part of the AOSP
 *   frameworks/base BCP we bake into the boot image, and whose source root was
 *   absent from adapter-mainline-stubs' MAINLINE_SRC_ROOTS.  On the device the
 *   class was therefore unresolvable, and any caller (e.g. androidx.core.os
 *   BuildCompat extension-version probing, dispatched from an Activity
 *   lifecycle callback at Application.dispatchActivityPreCreated) threw
 *       java.lang.NoClassDefFoundError: Failed resolution of:
 *           Landroid/os/ext/SdkExtensions;
 *   killing MainActivity.onCreate before first frame.
 *
 *   This device ships NO SDK extensions, so the truthful answer for every
 *   extension is version 0 / an empty map.  This thin stub returns exactly
 *   that, with ZERO external dependencies (no SdkLevel / SystemProperties /
 *   IntDef), so it cannot itself fault during class init.  It is a Java-layer
 *   completeness stub for a genuinely-absent mainline class — it does not
 *   alter ART internals, the framework BCP semantics, or any IPC boundary.
 *
 *   It lives in adapter-mainline-stubs.jar (BCP), because the failing caller
 *   is the app's own classloader, which resolves android.os.ext.* only via
 *   parent delegation to the boot classloader — a non-BCP jar cannot satisfy
 *   it.  Changing this BCP jar mandates a coherent 27-segment boot re-bake
 *   (铁律 4).
 *
 * Public surface mirrors the real platform class exactly so caller bytecode
 * resolves (getExtensionVersion(int), getAllExtensionVersions(), AD_SERVICES).
 */
public class SdkExtensions {

    /** Extension identifier for the AdServices extension (mirrors platform constant). */
    public static final int AD_SERVICES = 1_000_000;

    private SdkExtensions() { }

    /**
     * Return the version of the specified extension.
     *
     * This device exposes no SDK extensions, so every valid extension reports 0.
     * The {@code < VERSION_CODES.R} (30) guard mirrors the platform contract so
     * callers that rely on IllegalArgumentException for bad input still behave.
     *
     * @param extension the extension to get the version of.
     * @throws IllegalArgumentException if extension is not a valid extension.
     */
    public static int getExtensionVersion(int extension) {
        // android.os.Build.VERSION_CODES.R == 30
        if (extension < 30) {
            throw new IllegalArgumentException("not a valid extension: " + extension);
        }
        return 0;
    }

    /**
     * Return all extension versions that exist on this device.
     *
     * @return an empty map (no SDK extensions present on this device).
     */
    public static Map<Integer, Integer> getAllExtensionVersions() {
        return Collections.emptyMap();
    }
}
