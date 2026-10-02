// Add to adapter.activity.BinaryAndroidManifestOrientation (mirrors readAliasTarget/parseAliasTarget).
// Reads the android:theme (a TYPE_REFERENCE attribute) of the <activity android:name=targetActivity> element.

public static int readActivityTheme(String apkPath, String expectedPackage, String activityName) throws IOException {
    try (ZipFile apk = new ZipFile(apkPath)) {
        ZipEntry entry = apk.getEntry("AndroidManifest.xml");
        if (entry == null || entry.getSize() > MAX_MANIFEST_BYTES) {
            throw new IOException("Missing or oversized AndroidManifest.xml");
        }
        try (InputStream input = apk.getInputStream(entry)) {
            return parseActivityTheme(readFully(input), expectedPackage, activityName);
        }
    }
}

// parseActivityTheme: identical element walk to parseAliasTarget, but when the <activity name=activityName> element is
// found, return its android:theme reference value (0 if absent). Reuses the existing chunk/attr validation.
static int parseActivityTheme(byte[] xml, String expectedPackage, String activityName) throws IOException {
    // ... same prologue + element loop as parseAliasTarget ...
    //   when tag == "activity" and normalize(expectedPackage, name) equals normalize(expectedPackage, activityName):
    //       return refAttribute(xml, strings, attrs, attrSize, count, "theme");   // 0 if not present
    // returns 0 (NOT_FOUND maps to no-op in AliasTargetThemeFix).
    throw new UnsupportedOperationException("sketch: mirror parseAliasTarget; cc-t3 slots into the real reader");
}

// refAttribute: like the existing orientationAttribute but returns the raw reference data for a named attr.
private static int refAttribute(byte[] xml, StringPool strings, int attributes, int attributeSize, int count,
        String wantedName) {
    for (int i = 0; i < count; i++) {
        int attribute = attributes + i * attributeSize;
        if (!wantedName.equals(strings.get(s32(xml, attribute + 4)))) continue;
        int dataType = xml[attribute + 15] & 0xff;      // TYPE_REFERENCE == 0x01
        return s32(xml, attribute + 16);                 // the resource id (e.g. 0x7f120252)
    }
    return 0;
}
