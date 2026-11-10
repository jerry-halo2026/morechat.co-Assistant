# 自愿反馈与可携带接续

研究成果先交付。反馈始终可选；不要为了取得计数再运行研究或请求策略，不把没有反馈解释为没有成果。下列文件只留在用户选定项目目录，不能放进专家包、共享案例或公开附件。

## 记录真实执行范围

需要文件交付或跨会话续接时，在原有交付记录里补充：实际读取到的来源及范围、工具返回的查询/读取次数、同源去重、关键主张已支持/未知、反证、迁移条件、文件生成与读回状态。注明记录截止点，以及是工具计量、模型整理还是用户自报。未知次数/起止/成本写unknown/null；不得用计划预算、函数调用数或文件份数冒充已检索、独立来源或真实耗时。

策略选择、工具执行、正文读取、成果质量、用户接受与采用是不同证据。在线服务只覆盖实际发给它的闭合请求，不覆盖所有原生研究；成功HTTP也不等于成功研究。用户的相关性或采用反馈未给出时保留null。

## 有界的文件反馈流程

宿主已具备Node时，先加载 `scripts/strategy-client.mjs`。真实 `client.resolve(input)` 返回selected之后，可调用 `client.exportFeedbackBinding(decision.decision_id)`，以新文件保存到项目中的 `feedback-binding.json`。这只导出决定ID、摘要、预算、固定目标地址和反馈期限；不含简报、随机盐、原文、身份或完整策略，不恢复过期的在线计划。不曾取得selected时不伪造绑定。

准备反馈时才按已记录的执行证据填写闭合metrics：queries、reads、cases_checked、cases_usable、critical_fields_total、critical_fields_supported、transfer_conditions_total、transfer_conditions_met、transfer_conditions_unknown、counterevidence_checked；elapsed_ms、user_relevance、adoption可为null。必需计数未知时不要填0，不准备线上反馈，继续保留本地总结。计数不能超出已签发预算或子集分母。

按当前Skill实际路径调用 `scripts/feedback-file.mjs`，以下路径是用户自己选定的相对项目路径示例：

```text
node feedback-file.mjs prepare --in feedback-binding.json --metrics feedback-metrics.json --out feedback-prepared.json
```

prepare只生成新文件，不联网；用户未选择发送，停在这里即可。公开发送前展示将发送的计数、用途和目标服务。只有本轮用户明确同意，才执行：

```text
node feedback-file.mjs send --in feedback-prepared.json --out feedback-attempt-01.json --consent yes --target production
```

`--target development`只用于明确选择的本机合成测试，不能和production绑定互换。目标地址仅允许既定案例端点，不接受任意URL。

发送前独占创建并落盘attempt，随后只发一次原号原体；不会悄悄重试。结果另存`feedback-attempt-01.json.result.json`。文件已存在即停止，不能覆盖。只有严格的accepted或duplicate回执表示服务已记录匿名自报；任意200、损坏回执、超时或进程中断均不是成功证据。

优先读最新有效result；result为空、损坏或不存在时使用对应attempt，它保留原反馈号、原正文摘要与未知状态。再次得到本次发送同意后，以该文件为输入、**新的输出文件名**重试一次；不改号、不改计数、不重新resolve。accepted/duplicate、rejected、expired或withdrawn记录不再发送。

服务已接受但响应丢失时，24小时内同号同体通常可获得duplicate。服务在首次接受前重启并丢失决定时，返回decision_unrecognized，停止线上恢复、保留本地总结；不声称已解决服务端持久化。策略可用期仍是10分钟，反馈窗口最长24小时，二者互不延长。

## 撤回与原件保护

发送前用户改变主意，或未知结果后不愿再重试，可新建本地停止记录：

```text
node feedback-file.mjs withdraw --in feedback-attempt-01.json --out feedback-withdrawn.json
```

仅表示停止后续发送，不撤销已经到达服务的匿名聚合。accepted/duplicate后不能用本地撤回来假装服务删除。续接索引引用最新停止/结果记录，保留旧文件但不拿旧prepared绕过用户决定。文件摘要只检查意外修改，不认证身份、来源或真实执行；服务仍校验签发绑定和去重。
