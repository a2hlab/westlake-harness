/*
 * BinaryAndroidManifestOrientation.java
 *
 * Minimal, read-only Android binary XML reader for the activity orientation
 * fields needed by the OpenHarmony APK launch bridge.  This deliberately does
 * not instantiate Android PackageParser: that parser reaches framework system
 * services which are not all present in the compatibility process.
 */
package adapter.activity;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.Charset;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

public final class BinaryAndroidManifestOrientation {
    public static final int NOT_FOUND = Integer.MIN_VALUE;

    private static final int RES_STRING_POOL_TYPE = 0x0001;
    private static final int RES_XML_TYPE = 0x0003;
    private static final int RES_XML_START_ELEMENT_TYPE = 0x0102;
    private static final int UTF8_FLAG = 0x00000100;
    private static final int TYPE_STRING = 0x03;
    private static final int MAX_MANIFEST_BYTES = 8 * 1024 * 1024;
    private static final Charset UTF8 = Charset.forName("UTF-8");
    private static final Charset UTF16LE = Charset.forName("UTF-16LE");

    private BinaryAndroidManifestOrientation() { }

    public static int read(String apkPath, String expectedPackage,
            String expectedActivity) throws IOException {
        if (apkPath == null || expectedPackage == null || expectedActivity == null) {
            return NOT_FOUND;
        }
        byte[] xml;
        try (ZipFile apk = new ZipFile(apkPath)) {
            ZipEntry entry = apk.getEntry("AndroidManifest.xml");
            if (entry == null || entry.getSize() > MAX_MANIFEST_BYTES) return NOT_FOUND;
            try (InputStream input = apk.getInputStream(entry)) {
                xml = readFully(input);
            }
        }
        return parse(xml, expectedPackage, expectedActivity);
    }

    static int parse(byte[] xml, String expectedPackage, String expectedActivity) {
        if (xml == null || xml.length < 8 || u16(xml, 0) != RES_XML_TYPE) {
            return NOT_FOUND;
        }
        int xmlSize = checkedSize(xml, 0);
        if (xmlSize < 8) return NOT_FOUND;

        StringPool strings = null;
        String manifestPackage = null;
        int offset = u16(xml, 2);
        while (offset >= 8 && offset + 8 <= xmlSize) {
            int type = u16(xml, offset);
            int headerSize = u16(xml, offset + 2);
            int chunkSize = checkedSize(xml, offset);
            if (headerSize < 8 || chunkSize < headerSize || offset + chunkSize > xmlSize) {
                return NOT_FOUND;
            }

            if (type == RES_STRING_POOL_TYPE) {
                strings = StringPool.read(xml, offset, headerSize, chunkSize);
                if (strings == null) return NOT_FOUND;
            } else if (type == RES_XML_START_ELEMENT_TYPE && strings != null) {
                if (headerSize < 16 || offset + headerSize + 20 > offset + chunkSize) {
                    return NOT_FOUND;
                }
                int extension = offset + headerSize;
                String elementName = strings.get(s32(xml, extension + 4));
                int attributeStart = u16(xml, extension + 8);
                int attributeSize = u16(xml, extension + 10);
                int attributeCount = u16(xml, extension + 12);
                if (attributeSize < 20) return NOT_FOUND;
                int attributes = extension + attributeStart;
                long attributeEnd = (long) attributes + (long) attributeSize * attributeCount;
                if (attributes < extension || attributeEnd > offset + chunkSize) {
                    return NOT_FOUND;
                }

                if ("manifest".equals(elementName)) {
                    manifestPackage = stringAttribute(xml, strings, attributes,
                            attributeSize, attributeCount, "package");
                } else if ("activity".equals(elementName)
                        && expectedPackage.equals(manifestPackage)) {
                    String activity = stringAttribute(xml, strings, attributes,
                            attributeSize, attributeCount, "name");
                    if (normalize(expectedPackage, expectedActivity).equals(
                            normalize(expectedPackage, activity))) {
                        return orientationAttribute(xml, strings, attributes,
                                attributeSize, attributeCount);
                    }
                }
            }
            offset += chunkSize;
        }
        return NOT_FOUND;
    }

    /** Launcher alias semantics adapted from ManifestComponentProjection.readComponent.
     * Reuses this baseline's bounded AXML reader, avoiding a new PM/service closure.
     * null means a declared ordinary activity; errors never silently become aliases.
     */
    public static String readAliasTarget(String apkPath, String expectedPackage,
            String expectedActivity) throws IOException {
        try (ZipFile apk = new ZipFile(apkPath)) {
            ZipEntry entry = apk.getEntry("AndroidManifest.xml");
            if (entry == null || entry.getSize() > MAX_MANIFEST_BYTES) {
                throw new IOException("Missing or oversized AndroidManifest.xml");
            }
            try (InputStream input = apk.getInputStream(entry)) {
                return parseAliasTarget(readFully(input), expectedPackage, expectedActivity);
            }
        }
    }

    static String parseAliasTarget(byte[] xml, String expectedPackage,
            String expectedActivity) throws IOException {
        if (xml == null || xml.length < 8 || u16(xml, 0) != RES_XML_TYPE) {
            throw new IOException("Invalid binary Android manifest");
        }
        int size = checkedSize(xml, 0);
        if (size < 8 || size > xml.length) throw new IOException("Invalid manifest size");
        StringPool strings = null;
        String manifestPackage = null;
        String selected = normalize(expectedPackage, expectedActivity);
        String target = null;
        boolean found = false;
        java.util.Set<String> activities = new java.util.HashSet<>();
        for (int offset = u16(xml, 2); offset >= 8 && offset + 8 <= size;) {
            int type = u16(xml, offset);
            int header = u16(xml, offset + 2);
            int chunk = checkedSize(xml, offset);
            if (header < 8 || chunk < header || (long) offset + chunk > size) {
                throw new IOException("Invalid manifest chunk");
            }
            if (type == RES_STRING_POOL_TYPE) {
                strings = StringPool.read(xml, offset, header, chunk);
                if (strings == null) throw new IOException("Invalid manifest strings");
            } else if (type == RES_XML_START_ELEMENT_TYPE && strings != null) {
                int ext = offset + header;
                if (header < 16 || (long) ext + 20 > offset + chunk) {
                    throw new IOException("Invalid manifest element");
                }
                String tag = strings.get(s32(xml, ext + 4));
                int attrSize = u16(xml, ext + 10), count = u16(xml, ext + 12);
                int attrs = ext + u16(xml, ext + 8);
                if (attrSize < 20 || attrs < ext || (long) attrs + (long) attrSize * count > offset + chunk) {
                    throw new IOException("Invalid manifest attributes");
                }
                if ("manifest".equals(tag)) {
                    manifestPackage = stringAttribute(xml, strings, attrs, attrSize, count, "package");
                    if (!expectedPackage.equals(manifestPackage)) throw new IOException("Manifest package mismatch");
                } else if ("activity".equals(tag) || "activity-alias".equals(tag)) {
                    if (!expectedPackage.equals(manifestPackage)) throw new IOException("Component before package");
                    String name = normalize(expectedPackage,
                            stringAttribute(xml, strings, attrs, attrSize, count, "name"));
                    if ("activity".equals(tag)) activities.add(name);
                    if (selected.equals(name)) {
                        if (found) throw new IOException("Duplicate launch declaration: " + name);
                        found = true;
                        if ("activity-alias".equals(tag)) {
                            target = normalize(expectedPackage,
                                    stringAttribute(xml, strings, attrs, attrSize, count, "targetActivity"));
                            if (target.isEmpty() || target.equals(name)) {
                                throw new IOException("Invalid alias target: alias=" + name + " target=" + target);
                            }
                        }
                    }
                }
            }
            offset += chunk;
        }
        if (!found) throw new IOException("Launch activity absent: " + selected);
        if (target != null && !activities.contains(target)) {
            throw new IOException("Alias target is not a declared activity: alias=" + selected + " target=" + target);
        }
        return target;
    }

    private static String stringAttribute(byte[] xml, StringPool strings,
            int attributes, int attributeSize, int count, String wantedName) {
        for (int i = 0; i < count; i++) {
            int attribute = attributes + i * attributeSize;
            if (!wantedName.equals(strings.get(s32(xml, attribute + 4)))) continue;
            int rawValue = s32(xml, attribute + 8);
            if (rawValue >= 0) return strings.get(rawValue);
            int dataType = xml[attribute + 15] & 0xff;
            int data = s32(xml, attribute + 16);
            return dataType == TYPE_STRING ? strings.get(data) : null;
        }
        return null;
    }

    private static int orientationAttribute(byte[] xml, StringPool strings,
            int attributes, int attributeSize, int count) {
        for (int i = 0; i < count; i++) {
            int attribute = attributes + i * attributeSize;
            if (!"screenOrientation".equals(strings.get(s32(xml, attribute + 4)))) {
                continue;
            }
            int dataType = xml[attribute + 15] & 0xff;
            int data = s32(xml, attribute + 16);
            if (dataType != TYPE_STRING) return data;
            int rawValue = s32(xml, attribute + 8);
            String value = strings.get(rawValue >= 0 ? rawValue : data);
            return orientationName(value);
        }
        // Android's declared default when the activity exists but has no
        // screenOrientation attribute.
        return -1;
    }

    private static int orientationName(String value) {
        if (value == null) return -1;
        switch (value) {
            case "landscape": return 0;
            case "portrait": return 1;
            case "user": return 2;
            case "behind": return 3;
            case "sensor": return 4;
            case "nosensor": return 5;
            case "sensorLandscape": return 6;
            case "sensorPortrait": return 7;
            case "reverseLandscape": return 8;
            case "reversePortrait": return 9;
            case "fullSensor": return 10;
            case "userLandscape": return 11;
            case "userPortrait": return 12;
            case "fullUser": return 13;
            case "locked": return 14;
            default: return -1;
        }
    }

    private static String normalize(String packageName, String activityName) {
        if (activityName == null || activityName.isEmpty()) return "";
        if (activityName.charAt(0) == '.') return packageName + activityName;
        return activityName.indexOf('.') < 0
                ? packageName + "." + activityName : activityName;
    }

    private static byte[] readFully(InputStream input) throws IOException {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        byte[] buffer = new byte[8192];
        int total = 0;
        int count;
        while ((count = input.read(buffer)) != -1) {
            total += count;
            if (total > MAX_MANIFEST_BYTES) throw new IOException("manifest too large");
            output.write(buffer, 0, count);
        }
        return output.toByteArray();
    }

    private static int checkedSize(byte[] bytes, int offset) {
        long value = u32(bytes, offset + 4);
        return value <= Integer.MAX_VALUE ? (int) value : -1;
    }

    private static int u16(byte[] bytes, int offset) {
        if (offset < 0 || offset + 2 > bytes.length) return -1;
        return (bytes[offset] & 0xff) | ((bytes[offset + 1] & 0xff) << 8);
    }

    private static int s32(byte[] bytes, int offset) {
        return (int) u32(bytes, offset);
    }

    private static long u32(byte[] bytes, int offset) {
        if (offset < 0 || offset + 4 > bytes.length) return 0xffffffffL;
        return ((long) bytes[offset] & 0xff)
                | (((long) bytes[offset + 1] & 0xff) << 8)
                | (((long) bytes[offset + 2] & 0xff) << 16)
                | (((long) bytes[offset + 3] & 0xff) << 24);
    }

    private static final class StringPool {
        final byte[] xml;
        final int chunkOffset;
        final int chunkEnd;
        final int stringsStart;
        final int[] offsets;
        final boolean utf8;

        private StringPool(byte[] xml, int chunkOffset, int chunkEnd,
                int stringsStart, int[] offsets, boolean utf8) {
            this.xml = xml;
            this.chunkOffset = chunkOffset;
            this.chunkEnd = chunkEnd;
            this.stringsStart = stringsStart;
            this.offsets = offsets;
            this.utf8 = utf8;
        }

        static StringPool read(byte[] xml, int offset, int headerSize, int chunkSize) {
            if (headerSize < 28 || offset + 28 > xml.length) return null;
            int count = s32(xml, offset + 8);
            int flags = s32(xml, offset + 16);
            int stringsStart = s32(xml, offset + 20);
            if (count < 0 || count > 1_000_000 || stringsStart < headerSize
                    || offset + headerSize + (long) count * 4 > offset + chunkSize
                    || offset + stringsStart > offset + chunkSize) {
                return null;
            }
            int[] offsets = new int[count];
            for (int i = 0; i < count; i++) {
                offsets[i] = s32(xml, offset + headerSize + i * 4);
                if (offsets[i] < 0 || offset + stringsStart + offsets[i] >= offset + chunkSize) {
                    return null;
                }
            }
            return new StringPool(xml, offset, offset + chunkSize,
                    stringsStart, offsets, (flags & UTF8_FLAG) != 0);
        }

        String get(int index) {
            if (index < 0 || index >= offsets.length) return null;
            int cursor = chunkOffset + stringsStart + offsets[index];
            try {
                if (utf8) {
                    cursor = skipLength8(cursor);
                    int[] byteLength = length8(cursor);
                    cursor = byteLength[1];
                    if (byteLength[0] < 0 || cursor + byteLength[0] > chunkEnd) return null;
                    return new String(xml, cursor, byteLength[0], UTF8);
                }
                int[] charLength = length16(cursor);
                cursor = charLength[1];
                long bytes = (long) charLength[0] * 2;
                if (charLength[0] < 0 || cursor + bytes > chunkEnd) return null;
                return new String(xml, cursor, (int) bytes, UTF16LE);
            } catch (IndexOutOfBoundsException ignored) {
                return null;
            }
        }

        private int skipLength8(int cursor) {
            return length8(cursor)[1];
        }

        private int[] length8(int cursor) {
            if (cursor < 0 || cursor >= chunkEnd) return new int[] { -1, chunkEnd };
            int first = xml[cursor++] & 0xff;
            if ((first & 0x80) == 0) return new int[] { first, cursor };
            if (cursor >= chunkEnd) return new int[] { -1, chunkEnd };
            return new int[] { ((first & 0x7f) << 8) | (xml[cursor++] & 0xff), cursor };
        }

        private int[] length16(int cursor) {
            if (cursor < 0 || cursor + 2 > chunkEnd) return new int[] { -1, chunkEnd };
            int first = u16(xml, cursor);
            cursor += 2;
            if ((first & 0x8000) == 0) return new int[] { first, cursor };
            if (cursor + 2 > chunkEnd) return new int[] { -1, chunkEnd };
            int second = u16(xml, cursor);
            cursor += 2;
            return new int[] { ((first & 0x7fff) << 16) | second, cursor };
        }
    }
}
