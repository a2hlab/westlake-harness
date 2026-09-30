spec: task
name: "Resolve N3b JNI contract against J5 and J5b DEX"
inherits: project
---

## 意图

把已经发生的WebView类名缺口变成主机门，阻止只有编译成功却无法按JNI签名解析的配套。

## 已定决策

- 以已编N3b runtime和源码SHA为锚，提取adapter类查找和方法描述符，核对应JNI导出。
- 解析DEX类和方法定义，核static/native标志；引用字符串不算定义，多DEX完整枚举。
- 原J5必须失败，真实J5b必须通过；若J5b未交付则保留待验，不用夹具冒充。

## 边界

### 允许修改
- scripts/lab/check_webview_jni.py
- benchmark/2026-09-30-webview-jni-contract/**
- tools/spec-checks/src/lib.rs
- specs/jni-webview-contract/**
- README.md 与 .octos/KNOWLEDGE-DIGEST.md

### 禁止
- 板操作、修改N3b/J5/J5b制品、跳过旧J5负控
- 把DEX契约通过写成JNI运行成功或Chromium可用

## 验收标准

场景: 精确DEX定义与负控
  测试: webview_jni_exact_definitions
  假设 固定native源码和产物可读取
  当 解析多DEX并匹配完整方法签名与标志
  那么 缺类和错误返回类型及非static和无native声明均被拒
  并且 仅字符串引用不算定义且重复定义不能静默覆盖

场景: 真实配对回归
  测试: webview_jni_real_pair
  假设 J5和J5b真实制品已交付
  当 对两个制品使用同一份N3b契约
  那么 J5缺类失败且J5b精确查找通过
  并且 完整输入SHA与未覆盖的运行期条件一并记录
