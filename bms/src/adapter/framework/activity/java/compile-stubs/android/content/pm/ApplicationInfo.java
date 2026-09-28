/*
 * Compile-only projection of the hidden ApplicationInfo fields used by the
 * Bridge runtime helper.  The class is never dexed or packaged; the target
 * AOSP framework's boot-class-path ApplicationInfo remains the runtime owner.
 */
package android.content.pm;

import android.os.Bundle;

public class ApplicationInfo {
    public int flags;
    public String packageName;
    public String sourceDir;
    public String nativeLibraryDir;
    public String primaryCpuAbi;
    public Bundle metaData;
}
