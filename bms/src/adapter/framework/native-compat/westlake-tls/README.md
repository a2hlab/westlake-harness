# westlake-tls — liboh_tls_boundary.so(#93 native 侧,照抄 Westlake §441)

来源:`/Users/zhaoyue/orca/workspaces/vm-copies/westlake-current/framework/android-runtime/src/AndroidRuntime.cpp` §441 段(L1595-2010)。**块体逐字拷贝**;为独立编译补了 include 头(原块嵌在大文件内,无 include),并追加注册入口(照抄同文件 L3293-3302 的 7 方法表)。

## 文件

| 文件 | 说明 |
|---|---|
| `wl_tls_block.cpp`(623 行+注册段) | §441 全文:`WlSslApi` 函数表、`wl_tls_init()`(dlopen 板上 `libssl_openssl.z.so`/`libcrypto_openssl.z.so`,platformsdk/chipset-sdk 多路径候选)、7 个 JNI 实现(`WL_TLS_handshake/read/write/peerCert/peerChain/info/close`,真验证 `/etc/ssl/certs/cacert.pem` + `SSL_set1_host` 主机名校验)、`westlake_tls_child_register()`(绑定 `adapter/compat/WestlakeSSLSocket`) |
| `register_tls.h` | 注册入口声明 |
| `build.sh` | **已实测配方**(2026-09-29):VM pinned `clang-15` + OH sysroot + `westlake-current/third_party/jni/jni.h`(sysroot 无 jni.h);缺文件即失败;构建后三道门:file=ARM aarch64 ELF、`westlake_tls_child_register` 已导出、**dlopen-only(0 个未定义 SSL_/OPENSSL_ 符号,OpenSSL 不得静态链入)** |
| `build_tls_helper.py` | Westlake historical 的单编参考(原样拷贝;其路径是历史机器的,仅作对照) |
| `build/liboh_tls_boundary.so`(190,984B) | 构建产物(VM `clang-15`,`aarch64`) |

## 接线(cx-t0)

1. `.so` 置入 v3a 代 payload 的 lib 目录;
2. child init(runtime jar 可解析 `adapter/compat/WestlakeSSLSocket` 后)调 `westlake_tls_child_register(env)` 一次;
3. Java 侧需 `adapter/compat/WestlakeSSLSocket`(7 个 native 声明)+ `OhTrustBridge.install()`(JCA:BC 补注册 + `ssl.TrustManagerFactory.algorithm=OH-PKIX`)——见 #93 清单行 2/3,源分别为 historical bridge-build 树与 `vm-copies/.../appspawn-x/java/adapter/`。

## 构建弯路记档(供复用)

- dockbuild.sh `cc` 子命令只认 clang(`cc++` 不存在);`run` 模式 `$OH` 为空——直接在 VM 用 `~/a2hlab/ws/toolchains/ohos-sdk/native/llvm/bin/clang-15` 成功;
- OH sysroot **不含 jni.h**,用 `westlake-current/third_party/jni/jni.h`(-I 注入);
- pipefail 下 `grep -c` 零匹配 exit 1 会毒化门控——build.sh 的 dlopen-only 门已用 `|| true` 捕获修正。
