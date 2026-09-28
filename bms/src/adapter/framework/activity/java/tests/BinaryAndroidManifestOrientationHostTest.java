package adapter.activity;

/** Host smoke test for the bounded binary AndroidManifest reader. */
public final class BinaryAndroidManifestOrientationHostTest {
    public static void main(String[] args) throws Exception {
        if (args.length != 4) {
            throw new IllegalArgumentException(
                    "apk package activity expectedOrientation");
        }
        int expected = Integer.parseInt(args[3]);
        int actual = BinaryAndroidManifestOrientation.read(
                args[0], args[1], args[2]);
        if (actual != expected) {
            throw new AssertionError("orientation expected=" + expected
                    + " actual=" + actual);
        }
        if (BinaryAndroidManifestOrientation.parse(new byte[0], args[1], args[2])
                != BinaryAndroidManifestOrientation.NOT_FOUND) {
            throw new AssertionError("empty AXML must fail open");
        }
        if (BinaryAndroidManifestOrientation.parse(
                new byte[] { 3, 0, 8, 0, 8, 0, 0, 0 }, args[1], args[2])
                != BinaryAndroidManifestOrientation.NOT_FOUND) {
            throw new AssertionError("truncated AXML must fail open");
        }
        System.out.println("PASS orientation=" + actual);
    }
}
