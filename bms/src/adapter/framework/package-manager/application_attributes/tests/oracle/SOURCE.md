# Version oracle provenance

The two methods in AndroidPackageInfoOracle.java are copied verbatim from
[Android PackageInfo.java, android-16.0.0_r4](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-16.0.0_r4/core/java/android/content/pm/PackageInfo.java).

- Full upstream file SHA-256: `6e0c608d55cf7c10ef6359d374c9e77e4452db8f03d4aae3087d330ef2276d8c`.
- Extracted methods SHA-256 (joined with two newlines, no trailing newline): `4058373d59afebf40852e8d02f7be401be2adcb260cb29ceca2c5924b576548c`.
- Methods: setLongVersionCode(long), composeLongVersionCode(int, int).
- The harness adds primitive fields and prints the 16 ordered boundary pairs;
  it does not depend on an Android runtime or replace either upstream method.
- Apache-2.0 notice is preserved in the Java source.

CMake compiles and runs this Java oracle on each source change. The C++ tests
consume generated values; they do not duplicate the composition formula.
