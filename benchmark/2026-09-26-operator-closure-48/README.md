# #48 完整符号闭包板测

独立分支 `test/metasec-closure-48`，仅 operator 板61b06572。源 `fix/metasec-symbol-closure-48` @1d4af70，VM独立分支test/operator-closure-48；仅编译1个兼容C对象，复用sensor+5个旧对象，重链core libandroid。stock/sensor重现SHA一致；旧导出保留，新增指定15符号，NEEDED不变。

候选core SHA `c9969638b0175b7077332e1b7a65f4354392def62b5f6e1049ca763b9677148e`。上游闭包断言对完全链接库通过；另取现场liblog/libc/metasec，仅按动态符号独立核验226 hard UND，missing=0。离线解析完备不等同运行可靠，五轮新鲜profile分别记录真实uinput、原PID/birth、详情生命周期及结束正文截图。

A1 ART、85c789f4 shim、mc46 bridge、8b8d559c npth、tt targets/LD_PRELOAD、map_count1048576均保留。sensor旧core按SHA备份，仅替换core库。守护恢复实例不计原实例存活；失败如实保留。源中property为未设置返回值，__sF为resolve-only零对象，并非完整Bionic语义实现。

测试进行中；每轮要求原实例详情RESUMED后至少180s、正文可读、metasec exit=0、无缺符号重定位失败。本组不混入sensor-only旧组（3/4正文、c-r4 property致命退出）。
