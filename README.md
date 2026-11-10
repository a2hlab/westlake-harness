# 南海+ 全景状态台（GitHub Pages）

- 页面：`index.html`（原型 V3.2），发布于 https://a2hlab.github.io/westlake-harness/
- 共享声明库后端：Vercel 项目 `nanhai-panorama-api`，接口 `https://nanhai-panorama-api.vercel.app/api/claims`
  - `GET` 公开读取全部共享声明；`POST` 需要 `x-panorama-key` 提交口令（向维护者索取）。
  - 服务器强制 `accepted:false`、拒绝自填 `verified`；声明不改变任何正式状态，正式状态只来自板采认快照。
  - 存储：Vercel Blob（hkg1），每条声明一个对象 `claims/<id>.json`，同 id 不覆盖。
- 这个分支只放页面；后端源码见 `api/` 目录。
