# 本轮身份信息

- 阶段：`CT-BRIDGE-DIAGNOSTIC`
- 设备：`5583f5be00000000000000000323012c`
- 系统：`OpenHarmony 6.1.0.31`
- 启动标识：`31783e6b-2f2f-4c82-aad2-a28f573ae562`
- SELinux：`Permissive`（开发板恢复脚本的已知运行条件）
- 工作区源码 HEAD：`0095fb7fe203044f571c92cdf1785aef3c8565fc`
- 已部署逻辑产物代次：历史 PR03 `74e6f75976087d7890088b29c08482f17573a588fa5857cb6ca39264838ce16d`，加无编译触摸闭包

## 精确目标

- APK：`APKS/ZigZag/dist/zigzag.apk`
- APK SHA-256：`aaa7c9cce4886eef1280e917fd25bf434c53065cf0bf8b5704b83738137275bc`
- 已安装 `base.apk` SHA-256：`aaa7c9cce4886eef1280e917fd25bf434c53065cf0bf8b5704b83738137275bc`
- 包名：`com.a2hlab.bridge.zigzag`
- Activity：`com.unity3d.player.UnityPlayerActivity`
- UID：`20010054`
- 已安装 `libmain.so`：`b44d4efd55e713b73a35778b8e7335528f8d2011cb4d4bec17f1edd7b2a6c3ed`
- 已安装 `libil2cpp.so`：`74825000b3e6d3ec252755bff9c0d37de4bd8a589d5579c1009f0c1c58cf43a1`
- 已安装 `libtuanjie.so`：`c5b4a64cbf91267152691710c076002b7fbe6a5c6b1f660cfc5d2af71c630783`

## 当前有效的 Bridge 闭包

| 产物 | SHA-256 |
|---|---|
| `appspawn-x` | `43d5a319fa43e30fb712c2e39d29ba55e4bf82d171e97af1e6da9fcacc28920c` |
| 子进程载荷（child） | `66afb06c10db5e986d294a465cf787f4be3302ce6be3a17d49309b368b1ec090` |
| 封印路线 provider | `6787ea7d3c4ec0a382621360e3434885b0167446e22217a439b8d17745e54630` |
| Android runtime | `9ccf64f8d1f6e1748665057273eaa4c2770098934d39afa160f2c6b4c18b06db` |
| adapter | `7db99e1b760cf843b1a99db1382a3299f189c8cbca786ec411b7c35a2af6ffb9` |
| runtime JAR | `06141543bec26c5036931d8d2d71b0efaa45d5ffd73434557d165cd42672be0d` |

## 结论上限

本轮设备事实只绑定到上面的精确哈希。已部署的历史产物不是由当前工作区 HEAD 构建，因此本轮**不能**证明当前源码已经合格，也没有闭合严格的 `source -> build -> installed -> boot` M1 关系。
