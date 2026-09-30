# J2 (0715c964) on U0, single variable: no regression, NewPipe's bind wall not cleared

5ea on U0 with only the JAR swapped r17r -> J2 (J1-final + a synthesized `android` framework package
for `getPackageInfo("android")`). Facts: `TOTAL keys=8 screenshots_captured=16/16 alive_t5=8 alive_t20=8`.
All eight t20 screenshots show the app's own UI (Aegis, Thunderbird, BinaryEye, Etar, K-9, Tusky,
Markor, NewPipe): no regression (`evidence/sheet-t20.jpeg`).

The NewPipe fix fires (`[B8-ANDROIDPKG] getPackageInfo(android) null -> synthesized system package`)
but the in-process bind of `PlayerService` still fails with `InvocationTargetException` in the same
millisecond (`evidence/newpipe-bind-lines.txt`), and the wrapped cause is still not printed. The
android-package lookup was one layer; the next cause is unknown until the bind logs `getCause()`.

5ea was returned to U0 (JAR r17r) after the run.
