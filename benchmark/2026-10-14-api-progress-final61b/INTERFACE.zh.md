# 原实际回执最小接口

只需 root 给实际 outer128 接受 JSON 的 `{path,sha256}`；其余沿原 comparison/facts/双路审定路径绑定，不新增实验或封板门。`request.pending.json` 的 null/空列表须在独立实际 request 中补齐，原准备模板不升级为接受。

| 输入 | 最小已存内容 |
|---|---|
| authority | ACCEPT受限判词；`serial`或`board`为完整61b；`boot_id`为086d；`candidate_runtime_sha256`为完整f28；`canonical_keys=128`；root实际观察`driver_exited=true`、`driver_exit_code=null/unknown`（原detach未采全局退出码）；实际`scope`及非空`limitations`。允许既有额外字段，不要求V2已签。 |
| comparison | 一个或多个原JSON pins，合起来128唯一`rows[].key`；每行原`record` pin、`shots`或`actual_images`含t5及原t10/t20两图和SHA。原status/fatal/visual/限制不改。原observer文件可直接作为comparison，勿把历史signed/R4/R6参考图当actual。 |
| facts | 原collect产出的实际总facts `{path,sha256}`；原TOTAL为128key、256/256截图，逐key各2/2与121t10+7t20对应；alive计数按实际保留，不要求全alive。 |
| review_routes | 必须为`kind=bms`及`kind=nativepeer`两路原JSON pins。BMS observer或其BMS window-closeout都只属同一路；nativepeer直接消费main `benchmark/2026-10-14-final61b-full128-peer/window01–window08-review.json`，无须包装成record+双shots。两路分别覆盖同128key，最终接受仅来自authority。 |

核心会再核每行真实record的serial/boot/key/APK/截图pin一致；原manifest128及原tiers121/7固定fullSHA。当前只准备消费者和离线测试。正式调用：

从comparison原record路径机械定位同一round的8窗，无需root手写新逐key索引：再核原`round-complete.json.recorded_keys=128`、8份原`board-run-result.json`的smoke/after_lock/before_unlock真实整数0、每窗pre-lock/before/after三份同板同boot实际identity PASS。原driver SHA4938完整固定，源码末尾写completion路径可复核。它的`--detach`只存PID/log，不保存最终wait()退出码；本消费者保留全局null及未采原因，不硬要求/生成`completed_execute_rc=0`，不改driver或新跑一轮。

nativepeer原行的key/record_sha256/boot_id、显式apk_sha256（若原行有）、actual_image/fullSHA与BMS同key真实record及原末档t10/t20截图交叉核。reviewed_scheduled_seconds/demo_capture_seconds/shot_tiers_sha256有则核原值；W01原缺APK/档位字段时只依据已同SHA的canonical原record与末档图片校核，明确注明原peer字段缺失，不补造peer字段。verdict/observation原文与限制保留；peer的末档审定不冒称其额外看过全部t5图片。

```sh
python3 benchmark/2026-10-14-api-progress-final61b/increment.py build \
  --request "$ACTUAL_BOUND_REQUEST" --out "$FRESH_INDEPENDENT_API_OUTPUT"
python3 benchmark/2026-10-14-api-progress-final61b/increment.py check \
  --request "$ACTUAL_BOUND_REQUEST" --out "$FRESH_INDEPENDENT_API_OUTPUT"
```

正式output必须不存在，不能指向MAIN、原包或运行round。无实际authority、错SHA/板/boot/runtime、重复或不足128、错档位、缺图、缺双路均在写视图前拒绝；fixture仅本地临时用例，不允许作为实际build。315底表固定完整SHA，原314字段不改，仅NATIVE-173五字段增量；OH仅6.1.0.31、Android unknown/source-only、API未冻结、首屏不等于功能全可用。
