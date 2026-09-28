# T4 ANativeWindow 簇移植构建记录(离线段)

源:~/orca/00.Workspace @ 72a2f0a52(见 PORTING-NOTES.md)
编译(dockbuild.sh,锁 clang-15 + OH 6.1 sysroot):

    scripts/lab/dockbuild.sh cc -shared -fPIC       -I/home/zhaoyue/a2hlab/ws/android-source/libnativehelper/include_jni       -o benchmark/2026-09-28-ndk-libandroid/artifacts/anw_oh61_test.so       benchmark/2026-09-28-ndk-libandroid/src/anativewindow_oh61.c       -lnative_window

产物 sha256: a67bd1f912bcba537b51b8d6249068d7b6c106f59a3712111516896be1e04ea1
导出(nm -D): ANativeWindow_fromSurface/acquire/release/getWidth/getHeight/getFormat/setBuffersGeometry/query 共 8 个,全部 T 外部符号。
注:此为独立测试产物,尚未并入 libandroid 链接(等 T1 排序决定上板段);未触碰共享 libandroid。
