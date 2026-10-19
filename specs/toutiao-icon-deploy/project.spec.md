spec: project
name: "Toutiao icon candidate placement"
---
## 意图
仅发布新的头条手点重入控制包与唯一init入口，保留原运行时和回滚前像。
## 约束
- 唯一允许设备为61b；设备写前持锁，重新核对boot、前像SHA与元数据。
- 保护应用数据、历史stop、原payload和系统bootstrap，不启动或杀appspawn父进程。
