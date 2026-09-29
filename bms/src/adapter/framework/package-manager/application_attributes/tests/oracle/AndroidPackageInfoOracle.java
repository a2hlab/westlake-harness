/*
 * Copyright (C) 2007 The Android Open Source Project
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

// Methods below are verbatim from android-16.0.0_r4 PackageInfo.java.
// Only the standalone harness and primitive field declarations are added.
public final class AndroidPackageInfoOracle {
    public int versionCode;
    private int versionCodeMajor;

    public void setLongVersionCode(long longVersionCode) {
        versionCodeMajor = (int) (longVersionCode>>32);
        versionCode = (int) longVersionCode;
    }

    public static long composeLongVersionCode(int major, int minor) {
        return (((long) major) << 32) | (((long) minor) & 0xffffffffL);
    }

    public static void main(String[] args) {
        int[] edges = {0, 0x7fffffff, 0x80000000, 0xffffffff};
        for (int major : edges) {
            for (int minor : edges) {
                long value = composeLongVersionCode(major, minor);
                AndroidPackageInfoOracle info = new AndroidPackageInfoOracle();
                info.setLongVersionCode(value);
                System.out.println(Integer.toUnsignedLong(major) + ","
                        + Integer.toUnsignedLong(minor) + ","
                        + Long.toUnsignedString(value) + "," + value + ","
                        + Integer.toUnsignedLong(info.versionCodeMajor) + ","
                        + Integer.toUnsignedLong(info.versionCode));
            }
        }
    }
}
