# #93: Westlake HTTPS 链 vs route-A v3a —— 照抄清单(cx-t0)

来源:vm-copies/westlake-current 一手行号;route-A 侧 v3a 包逐 jar/so 检验。30 分钟第一版。

## 结论速览

**Westlake 没有 conscrypt.jar,没有 libjavacrypto.so,也不注册任何 TLS Security Provider。** Java app 的 HTTPS 走一条自建链:**板上自带的 OpenSSL 3.x**(`libssl_openssl.z.so`/`libcrypto_openssl.z.so`,OH 出厂件)+ native 边界 JNI + 往 BC Provider 补签名/PRNG/TrustManagerFactory 注册。v3a 包里这条链**完全缺失**(全部 payload jar 无 OhTrustBridge/WestlakeSSLSocket/WestlakeSecureRandomSpi;liboh_android_runtime.so 无 wl_tls 符号)。

## Westlake 侧三件(一手)

1. **native TLS 边界** — `framework/android-runtime/src/AndroidRuntime.cpp` **§441 L1595-2010**:
   - `wl_tls_init()` dlopen 板上 OpenSSL(platformsdk/chipset-sdk 多路径候选),`WlSslApi` 函数表(TLS_client_method/SSL_CTX_new/SSL_set1_host/SSL_connect/…)
   - 7 个 JNI 实现(`WL_TLS_handshake/read/write/peerCert/peerChain/info/close`),真验证 `/etc/ssl/certs/cacert.pem` + SSL_set1_host 主机名校验
   - 注册表 **L3285-3305 `wl_register_tls_natives`**:`RegisterNatives(adapter/compat/WestlakeSSLSocket, {nativeHandshake/nativeRead/nativeWrite/nativePeerCert/nativePeerChain/nativeInfo/nativeClose})`
2. **Java 侧 `adapter/compat/WestlakeSSLSocket`**(声明这 7 个 native 的 SSLSocket 包装;树内无 .java——历史构建脚本 `historical/.../gap-repair-20260904/build_tls_helper.py` 证实类在彼时 bridge-build 源树,cx-t0 需从 Westlake 运行时 jar 反编译或按 7 签名重写)
3. **JCA 注册** — `framework/appspawn-x/java/adapter/security/OhTrustBridge.java`(AppSpawnXInit **L594** 调 install):
   - 可选 `System.load($WESTLAKE_NET_HELPER_PATH)`(OH native 助手)
   - `BC provider.put("SecureRandom.WestlakeKernel", adapter.compat.WestlakeSecureRandomSpi)`(类在树内 `appspawn-x/java/adapter/compat/`)
   - 恢复 BC 的 RSA/EC DigestSignature 与 KeyFactory 注册(BCP 裁剪过)
   - `TrustManagerFactory.OH-PKIX/PKIX/X509` + `Security.setProperty("ssl.TrustManagerFactory.algorithm", "OH-PKIX")`
   - 注意 AppSpawnXInit **L296-303 的教训**:父进程**不要**提前 `Security.getProviders()`(JCA AssertionError 会永久钉死 Class;child 首触才安全)

## 照抄清单(交 cx-t0)

| # | 拿什么 | 从哪 | 放哪 | 怎么注册 |
|---|---|---|---|---|
| 1 | §441 TLS 边界整段(WlSslApi+wl_tls_*+7 JNI+注册函数;或用 historical `build_tls_helper.py` 的单编路线直接产 `liboh_tls_boundary.so`) | AndroidRuntime.cpp L1595-2010(+L3285) / historical gap-repair 脚本 | 编进 route 的 `liboh_android_runtime.so`,或独立 `liboh_tls_boundary.so` 入 payload | child 启动调 `wl_register_tls_natives(env)`(或脚本的 `westlake_tls_child_register`) |
| 2 | `adapter/compat/WestlakeSSLSocket.java`(7 native 声明;树内无源→按签名重写或反编译 Westlake 运行时 jar) | historical bridge-build 源树 / 运行时 jar | runtime jar(`oh-adapter-runtime.jar` 重建) | 由 1 的 RegisterNatives 绑定 |
| 3 | `adapter/security/OhTrustBridge.java` + `adapter/compat/WestlakeSecureRandomSpi.java` | `framework/appspawn-x/java/adapter/{security,compat}/` | runtime jar | `AppSpawnXInit`(=route 的 child init)启动处调 `OhTrustBridge.install()` |
| 4 | BC 补注册(RSA/EC 签名+KeyFactory) | OhTrustBridge.java 内联(无需单独文件) | 同上 | install() 内完成 |
| 5 | (可选)`WESTLAKE_NET_HELPER_PATH` native 助手 | 树内无源(历史产物) | payload/lib64 | env 指向;缺省可跳(OH-PKIX factory 走 OH 侧) |

**不需要拷**:conscrypt(不存在)、libjavacrypto.so(不存在)、任何 TlsShimProvider(v3a 与 Westlake 均无此名;外环问询项答"无")。

## v3a 现状核验(一手,今日)

- payload/android/framework/*.jar:unzip 过滤 `OhTrustBridge|WestlakeSSL|WestlakeSecureRandom` **零命中**
- payload/android/lib64/liboh_android_runtime.so:strings 无 `WESTLAKE-441`/`nativeHandshake`/`SSL_` —— **wl_tls 未编入**
- 结论:route-A 当前 HTTPS 依赖 app 自带 TLS 栈(OkHttp conscrypt-android 回退/BC)或直接失败;照抄上表即获得 Westlake 同款"真验证 TLS"。

## 诚实限界

- `WestlakeSSLSocket.java` 源不在 vm-copies 树(grep 全树仅 native 侧与构建脚本命中)——按 7 个 JNI 签名重写工作量小,但与 Westlake 字节级一致性无法保证;
- `WESTLAKE_NET_HELPER_PATH` 助手 .so 无源码,先跳过;
- 30 分钟窗口内未在板上验证 OpenSSL so 路径候选在 v3a 代环境同样可 dlopen(Westlake 与 v3a 同板系,风险低但未证)。
