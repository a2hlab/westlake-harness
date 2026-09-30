import android.graphics.ColorMatrix;

public final class ColorMatrixCopyProbe {
    public static void main(String[] arguments) {
        ColorMatrix source = new ColorMatrix();
        source.setScale(2, 3, 4, 5);
        ColorMatrix target = new ColorMatrix();
        target.set(source);
        if (target.getArray()[0] != 2 || target.getArray()[6] != 3
                || target.getArray()[12] != 4 || target.getArray()[18] != 5) {
            throw new AssertionError("matrix values not copied");
        }
        source.reset();
        if (target.getArray()[0] != 2 || source.getArray()[0] != 1) {
            throw new AssertionError("copy aliases the source matrix");
        }
        System.out.println("PASS: ColorMatrix.set copies all scale slots without aliasing; no app-unlock claim");
    }
}
