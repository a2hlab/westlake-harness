// J8/T7e (#osmand-map-info-null / fd-plus): full AOSP 14 r1 android.graphics.ColorMatrix, replacing the
// empty mainline stub. The 2-method stub was missing set(ColorMatrix) (and the backing 4x5 array), so
// OsmAnd's map rendering hit "NoSuchMethodError: No virtual method set(Landroid/graphics/ColorMatrix;)V
// in class Landroid/graphics/ColorMatrix;" upstream of its MapActivity MapInfoLayer NPE.
//
// Faithful reproduction of AOSP 14 r1 frameworks/base/graphics/java/android/graphics/ColorMatrix.java
// (a self-contained pure-Java 4x5 color transform value holder; set(ColorMatrix) =
// System.arraycopy(src.mArray, 0, mArray, 0, 20)). BOOT-class, so it ships in adapter-mainline-stubs.jar
// and the 27 boot images must be regenerated (T7e, FZ-005 toolchain).
package android.graphics;

public class ColorMatrix {
    private final float[] mArray = new float[20];

    /** Create a new colormatrix initialized to identity (as if reset() had been called). */
    public ColorMatrix() {
        reset();
    }

    /** Create a new colormatrix initialized with the specified array of values. */
    public ColorMatrix(float[] src) {
        System.arraycopy(src, 0, mArray, 0, 20);
    }

    /** Create a new colormatrix initialized with the specified colormatrix. */
    public ColorMatrix(ColorMatrix src) {
        System.arraycopy(src.mArray, 0, mArray, 0, 20);
    }

    /** Return the array of floats representing this colormatrix. */
    public final float[] getArray() {
        return mArray;
    }

    /** Set this colormatrix to identity. */
    public void reset() {
        final float[] a = mArray;
        for (int i = 19; i > 0; --i) {
            a[i] = 0;
        }
        a[0] = a[6] = a[12] = a[18] = 1;
    }

    /** Assign the src colormatrix into this matrix, copying all of its values. */
    public void set(ColorMatrix src) {
        System.arraycopy(src.mArray, 0, mArray, 0, 20);
    }

    /** Assign the array of floats into this matrix, copying all of its values. */
    public void set(float[] src) {
        System.arraycopy(src, 0, mArray, 0, 20);
    }

    /** Set this colormatrix to scale by the specified values. */
    public void setScale(float rScale, float gScale, float bScale, float aScale) {
        final float[] a = mArray;
        for (int i = 19; i > 0; --i) {
            a[i] = 0;
        }
        a[0] = rScale;
        a[6] = gScale;
        a[12] = bScale;
        a[18] = aScale;
    }

    /** Set the rotation on a color axis by the specified values. */
    public void setRotate(int axis, float degrees) {
        reset();
        double radians = degrees * Math.PI / 180d;
        float cosine = (float) Math.cos(radians);
        float sine = (float) Math.sin(radians);
        switch (axis) {
            case 0:
                mArray[6] = mArray[12] = cosine;
                mArray[7] = sine;
                mArray[11] = -sine;
                break;
            case 1:
                mArray[0] = mArray[12] = cosine;
                mArray[2] = -sine;
                mArray[10] = sine;
                break;
            case 2:
                mArray[0] = mArray[6] = cosine;
                mArray[1] = sine;
                mArray[5] = -sine;
                break;
            default:
                throw new RuntimeException();
        }
    }

    /** Set this colormatrix to the concatenation of the two specified colormatrices. */
    public void setConcat(ColorMatrix matA, ColorMatrix matB) {
        float[] tmp;
        if (matA == this || matB == this) {
            tmp = new float[20];
        } else {
            tmp = mArray;
        }
        final float[] a = matA.mArray;
        final float[] b = matB.mArray;
        int index = 0;
        for (int j = 0; j < 20; j += 5) {
            for (int i = 0; i < 4; i++) {
                tmp[index++] = a[j + 0] * b[i + 0] + a[j + 1] * b[i + 5]
                        + a[j + 2] * b[i + 10] + a[j + 3] * b[i + 15];
            }
            tmp[index++] = a[j + 0] * b[4] + a[j + 1] * b[9]
                    + a[j + 2] * b[14] + a[j + 3] * b[19] + a[j + 4];
        }
        if (tmp != mArray) {
            System.arraycopy(tmp, 0, mArray, 0, 20);
        }
    }

    /** Concat this colormatrix with the specified prematrix. */
    public void preConcat(ColorMatrix prematrix) {
        setConcat(this, prematrix);
    }

    /** Concat this colormatrix with the specified postmatrix. */
    public void postConcat(ColorMatrix postmatrix) {
        setConcat(postmatrix, this);
    }

    /** Set the matrix to affect the saturation of colors. */
    public void setSaturation(float sat) {
        reset();
        float[] m = mArray;
        final float invSat = 1 - sat;
        final float R = 0.213f * invSat;
        final float G = 0.715f * invSat;
        final float B = 0.072f * invSat;
        m[0] = R + sat; m[1] = G;       m[2] = B;
        m[5] = R;       m[6] = G + sat; m[7] = B;
        m[10] = R;      m[11] = G;      m[12] = B + sat;
    }

    /** Set the matrix to convert RGB to YUV. */
    public void setRGB2YUV() {
        reset();
        float[] m = mArray;
        m[0] = 0.299f;    m[1] = 0.587f;    m[2] = 0.114f;
        m[5] = -0.16874f; m[6] = -0.33126f; m[7] = 0.5f;
        m[10] = 0.5f;     m[11] = -0.41869f; m[12] = -0.08131f;
    }

    /** Set the matrix to convert from YUV to RGB. */
    public void setYUV2RGB() {
        reset();
        float[] m = mArray;
        m[2] = 1.402f;
        m[5] = 1;         m[6] = -0.34414f; m[7] = -0.71414f;
        m[10] = 1;        m[11] = 1.772f;   m[12] = 0;
    }

    @Override
    public boolean equals(Object obj) {
        if (this == obj) {
            return true;
        }
        if (!(obj instanceof ColorMatrix)) {
            return false;
        }
        final ColorMatrix other = (ColorMatrix) obj;
        return java.util.Arrays.equals(mArray, other.mArray);
    }

    @Override
    public int hashCode() {
        return java.util.Arrays.hashCode(mArray);
    }
}
