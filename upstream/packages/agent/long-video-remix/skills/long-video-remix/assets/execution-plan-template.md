# Execution Package · Editorial Execution Plan

> 第二次 Direct 的输出之一。输入是 Detail 的 evidence package、真实关键帧和独立 handoff；与 execution-reference.md、素材 / 约束和原机器授权一起构成完整 Execution Package。Execute 只落实确认后的包。

## 本轮 Scope Lock

- 当前阶段 / current stage：<!-- lvr:param plan.scope.current-stage -->Direct 2<!-- /lvr:param plan.scope.current-stage -->
- 可修改 / editable：<!-- lvr:param plan.scope.editable --><!-- /lvr:param plan.scope.editable -->
- 不可修改 / locked：<!-- lvr:param plan.scope.locked --><!-- /lvr:param plan.scope.locked -->
- 已否决 / rejected：<!-- lvr:param plan.scope.rejected --><!-- /lvr:param plan.scope.rejected -->

## 最终主线

- thesis / narrative spine：<!-- lvr:param plan.narrative.thesis-narrative-spine --><!-- /lvr:param plan.narrative.thesis-narrative-spine -->
- 与第一次 Narrative Direction 的变化（如有）：<!-- lvr:param plan.narrative.narrative-direction --><!-- /lvr:param plan.narrative.narrative-direction -->
- 变化依据：<!-- lvr:param plan.narrative.change-basis --><!-- /lvr:param plan.narrative.change-basis -->

## 最终素材取舍
<!-- lvr:container plan.segments -->
### Segment 1
- selected verified unit(s)：<!-- lvr:param seg1.selected-verified-unit-s --><!-- /lvr:param seg1.selected-verified-unit-s -->
- adopted utterance IDs / adopted_utterance_refs：<!-- lvr:param seg1.adopted-utterance-ids-adopted-utterance-refs --><!-- /lvr:param seg1.adopted-utterance-ids-adopted-utterance-refs -->
- selected Deep observation(s) / observation_id：<!-- lvr:param seg1.selected-deep-observation-s-observation-id --><!-- /lvr:param seg1.selected-deep-observation-s-observation-id -->
- planned selected source range(s)（D2 内容选择；非最终帧级切点）：<!-- lvr:param seg1.planned-selected-source-range-s-d2 --><!-- /lvr:param seg1.planned-selected-source-range-s-d2 -->
- selected edit boundary / boundary_id：<!-- lvr:param seg1.selected-edit-boundary-boundary-id --><!-- /lvr:param seg1.selected-edit-boundary-boundary-id -->
- planned in / out：<!-- lvr:param seg1.planned-in-out --><!-- /lvr:param seg1.planned-in-out -->
- referenced safe in / out windows / handles：<!-- lvr:param seg1.referenced-safe-in-out-windows-handles --><!-- /lvr:param seg1.referenced-safe-in-out-windows-handles -->
- must-keep range(s)：<!-- lvr:param seg1.must-keep-range-s --><!-- /lvr:param seg1.must-keep-range-s -->
- Execute Step 0 boundary calibration：<!-- lvr:param seg1.execute-step-0-boundary-calibration -->allowed / locked（默认仅 safe windows / handles 内）<!-- /lvr:param seg1.execute-step-0-boundary-calibration -->
- boundary override：<!-- lvr:param seg1.boundary-override -->no / yes<!-- /lvr:param seg1.boundary-override -->
- boundary override reason（仅 yes 时）：<!-- lvr:param seg1.boundary-override-reason-yes --><!-- /lvr:param seg1.boundary-override-reason-yes -->
- boundary override review refs（仅 yes 时）：<!-- lvr:param seg1.boundary-override-review-refs-yes --><!-- /lvr:param seg1.boundary-override-review-refs-yes -->
- narrative function：<!-- lvr:param seg1.narrative-function --><!-- /lvr:param seg1.narrative-function -->
- 必须保留的 context / protected ranges：<!-- lvr:param seg1.context-protected-ranges --><!-- /lvr:param seg1.context-protected-ranges -->
- 原声 / BGM / ambience 策略：<!-- lvr:param seg1.bgm-ambience --><!-- /lvr:param seg1.bgm-ambience -->
- 每条源音轨完整取段及 audio review_refs（含 J/L-cut 扩展）：<!-- lvr:param seg1.audio-review-refs-j-l-cut --><!-- /lvr:param seg1.audio-review-refs-j-l-cut -->
- 独立声音的完整 utterance、成片放置、track 级截句例外 / 政策原因（如有）：<!-- lvr:param seg1.utterance-track --><!-- /lvr:param seg1.utterance-track -->
- 文字意图（如有）：<!-- lvr:param seg1.copy-intent --><!-- /lvr:param seg1.copy-intent -->
- 预计时长：<!-- lvr:param seg1.duration --><!-- /lvr:param seg1.duration -->
- transition / time cue：<!-- lvr:param seg1.transition-time-cue --><!-- /lvr:param seg1.transition-time-cue -->

### Segment 2
- selected verified unit(s)：<!-- lvr:param seg2.selected-verified-unit-s --><!-- /lvr:param seg2.selected-verified-unit-s -->
- adopted utterance IDs / adopted_utterance_refs：<!-- lvr:param seg2.adopted-utterance-ids-adopted-utterance-refs --><!-- /lvr:param seg2.adopted-utterance-ids-adopted-utterance-refs -->
- selected Deep observation(s) / observation_id：<!-- lvr:param seg2.selected-deep-observation-s-observation-id --><!-- /lvr:param seg2.selected-deep-observation-s-observation-id -->
- planned selected source range(s)（D2 内容选择；非最终帧级切点）：<!-- lvr:param seg2.planned-selected-source-range-s-d2 --><!-- /lvr:param seg2.planned-selected-source-range-s-d2 -->
- selected edit boundary / boundary_id：<!-- lvr:param seg2.selected-edit-boundary-boundary-id --><!-- /lvr:param seg2.selected-edit-boundary-boundary-id -->
- planned in / out：<!-- lvr:param seg2.planned-in-out --><!-- /lvr:param seg2.planned-in-out -->
- referenced safe in / out windows / handles：<!-- lvr:param seg2.referenced-safe-in-out-windows-handles --><!-- /lvr:param seg2.referenced-safe-in-out-windows-handles -->
- must-keep range(s)：<!-- lvr:param seg2.must-keep-range-s --><!-- /lvr:param seg2.must-keep-range-s -->
- Execute Step 0 boundary calibration：<!-- lvr:param seg2.execute-step-0-boundary-calibration -->allowed / locked（默认仅 safe windows / handles 内）<!-- /lvr:param seg2.execute-step-0-boundary-calibration -->
- boundary override：<!-- lvr:param seg2.boundary-override -->no / yes<!-- /lvr:param seg2.boundary-override -->
- boundary override reason（仅 yes 时）：<!-- lvr:param seg2.boundary-override-reason-yes --><!-- /lvr:param seg2.boundary-override-reason-yes -->
- boundary override review refs（仅 yes 时）：<!-- lvr:param seg2.boundary-override-review-refs-yes --><!-- /lvr:param seg2.boundary-override-review-refs-yes -->
- narrative function：<!-- lvr:param seg2.narrative-function --><!-- /lvr:param seg2.narrative-function -->
- 必须保留的 context / protected ranges：<!-- lvr:param seg2.context-protected-ranges --><!-- /lvr:param seg2.context-protected-ranges -->
- 原声 / BGM / ambience 策略：<!-- lvr:param seg2.bgm-ambience --><!-- /lvr:param seg2.bgm-ambience -->
- 每条源音轨完整取段及 audio review_refs（含 J/L-cut 扩展）：<!-- lvr:param seg2.audio-review-refs-j-l-cut --><!-- /lvr:param seg2.audio-review-refs-j-l-cut -->
- 独立声音的完整 utterance、成片放置、track 级截句例外 / 政策原因（如有）：<!-- lvr:param seg2.utterance-track --><!-- /lvr:param seg2.utterance-track -->
- 文字意图（如有）：<!-- lvr:param seg2.copy-intent --><!-- /lvr:param seg2.copy-intent -->
- 预计时长：<!-- lvr:param seg2.duration --><!-- /lvr:param seg2.duration -->
- transition / time cue：<!-- lvr:param seg2.transition-time-cue --><!-- /lvr:param seg2.transition-time-cue -->

> 按需要继续增加。
<!-- /lvr:container plan.segments -->
## Execute Step 0 · Selected Range Verification

> D2 可跨模型交付。正式 Execute 先只精校入选片段 + handles；按需精听 / 小窗口 ASR，补齐 selected boundary 的精确连续性值与 reviews，升级为 supported。语义冲突返回 D2，不自行换段。最终 source in/out 写入 timeline；机器授权在 Step 0 后按最终取段准备 / 确认。

- Step 0 待核片段 / boundary IDs：
- `d2_selection_snapshot` 已写入 timeline 草稿：yes / no
- 允许的边界校准范围：
- 原声 / speaker / 断句 / J-L cut 风险：
- 精校完成状态：pending / completed

| event ID | D2 planned in/out | snapshotted safe windows | Step 0 verified in/out | delta / reason | within D2 allowance |
|---|---|---|---|---|---|
|  |  |  |  |  | yes / no |

> `within D2 allowance=no` 时停止，不确认授权、不渲染；返回 D2 / 人工确认并更新 snapshot 后再继续。

## 逐段执行坐标与画面处理

| event ID / 顺序 | unit / source ID | source in/out ms | speed / crop / scale / 画面位置 | assembly 预计帧 / event anchor | 本段文字 / 声音 / 转场引用 |
|---|---|---|---|---|---|
<!-- lvr:param plan.coordinates.rows -->
|  |  |  |  |  |  |
<!-- /lvr:param plan.coordinates.rows -->

## 逐条文字事件

| text ID / 用途 | 逐字全文 / 明确断行 | anchor event ID | local in/out frames | style ID（reference） | 进入 / 退出动效与帧数 | 实际阅读停留 / 保护的重点 |
|---|---|---|---|---|---|---|
<!-- lvr:param plan.text-events.rows -->
|  |  |  |  |  |  |  |
<!-- /lvr:param plan.text-events.rows -->

## 音轨与接点

| track ID / narrative role | source / asset ID | source in/out ms | event anchor / local frames 或显式 output 坐标 | gain dB / speed / fade ms | review refs / 同步 / 完整对白保护 |
|---|---|---|---|---|---|
<!-- lvr:param plan.audio-joins.tracks -->
|  |  |  |  |  |  |
<!-- /lvr:param plan.audio-joins.tracks -->

| 前后 event ID | cut / fade / card 等 | overlap 或独立 card 帧数 | 接续理由 / 保护范围 |
|---|---|---|---|
<!-- lvr:param plan.audio-joins.joins -->
|  |  |  |  |
<!-- /lvr:param plan.audio-joins.joins -->

## 时长与节奏分配

- 总时长目标：<!-- lvr:param plan.duration.duration-target --><!-- /lvr:param plan.duration.duration-target -->
- 各段预算：<!-- lvr:param plan.duration.segment-budgets --><!-- /lvr:param plan.duration.segment-budgets -->
- 必须保留的完整动作 / 对白：<!-- lvr:param plan.duration.protected-actions-dialogue --><!-- /lvr:param plan.duration.protected-actions-dialogue -->

## 执行边界

- 可替换素材：<!-- lvr:param plan.constraints.replaceable-assets --><!-- /lvr:param plan.constraints.replaceable-assets -->
- 可调整顺序 / 时长：<!-- lvr:param plan.constraints.sequence-duration-permissions --><!-- /lvr:param plan.constraints.sequence-duration-permissions -->
- Execute 不得改变：<!-- lvr:param plan.constraints.execute --><!-- /lvr:param plan.constraints.execute -->

## Evidence check

- pending / contradicted 节点：<!-- lvr:param plan.evidence.pending-contradicted --><!-- /lvr:param plan.evidence.pending-contradicted -->
- counterevidence 已处理：<!-- lvr:param plan.evidence.counterevidence --><!-- /lvr:param plan.evidence.counterevidence -->
- 可进入 Execute：<!-- lvr:param plan.evidence.execute -->yes / no<!-- /lvr:param plan.evidence.execute -->

## 同包制作参考与 QA

- execution_reference_ref：<!-- lvr:param plan.production-qa.execution-reference-ref -->execution-reference.md<!-- /lvr:param plan.production-qa.execution-reference-ref -->
- execution_reference_asset_refs：<!-- lvr:param plan.production-qa.execution-reference-asset-refs -->实际采用的 selected mockup / executable proof / 其他风格样本；缺少图片时写 [] 并说明待补项。<!-- /lvr:param plan.production-qa.execution-reference-asset-refs -->
- visual_gate_status / visual_mockup_ref / visual_proof_ref / visual_proof_refs：<!-- lvr:param plan.production-qa.visual-gate-status-visual-mockup-ref-visual -->见 project.json；单 Proof 兼容字段仍用 visual_proof_ref，多代表性 Proof 用 visual_proof_refs 列全量；采用视觉设计时 proof_confirmed 才可进入正式 Execute。<!-- /lvr:param plan.production-qa.visual-gate-status-visual-mockup-ref-visual -->
- 具体文字 / 画面 / 声音 / 转场规则、Toolchain Continuity 与资产入口：<!-- lvr:param plan.production-qa.toolchain-continuity -->见同包 reference。<!-- /lvr:param plan.production-qa.toolchain-continuity -->
- Reference Application Rules：<!-- lvr:param plan.production-qa.reference-application-rules -->样本提炼为全片规则，不要求每个字幕 / 镜头单独配对。<!-- /lvr:param plan.production-qa.reference-application-rules -->
- QA：<!-- lvr:param plan.production-qa.qa -->原内容 / 技术 / 听看项 + ReferenceCompliance，未实看保持 not_tested。<!-- /lvr:param plan.production-qa.qa -->
- exceptions 与下游处理：<!-- lvr:param plan.production-qa.exceptions --><!-- /lvr:param plan.production-qa.exceptions -->

## 机器可读执行授权

- execution_authorization_ref：<!-- lvr:param plan.authorization.execution-authorization-ref -->execution-authorization.json<!-- /lvr:param plan.authorization.execution-authorization-ref -->
- authorization_id / version：<!-- lvr:param plan.authorization.authorization-id-version --><!-- /lvr:param plan.authorization.authorization-id-version -->
- confirmed_by：<!-- lvr:param plan.authorization.confirmed-by --><!-- /lvr:param plan.authorization.confirmed-by -->
- selected_events / sequence：<!-- lvr:param plan.authorization.selected-events-sequence --><!-- /lvr:param plan.authorization.selected-events-sequence -->
- allowed_units / allowed_boundaries：<!-- lvr:param plan.authorization.allowed-units-allowed-boundaries --><!-- /lvr:param plan.authorization.allowed-units-allowed-boundaries -->
- allowed_adjustments（逐 event）：<!-- lvr:param plan.authorization.allowed-adjustments-event --><!-- /lvr:param plan.authorization.allowed-adjustments-event -->
- event_specs / audio_specs / text_specs / transitions：<!-- lvr:param plan.authorization.event-specs-audio-specs-text-specs-transitions --><!-- /lvr:param plan.authorization.event-specs-audio-specs-text-specs-transitions -->
- source_bindings / evidence_digest / Direct 文档指纹：<!-- lvr:param plan.authorization.source-bindings-evidence-digest-direct --><!-- /lvr:param plan.authorization.source-bindings-evidence-digest-direct -->
- execution_reference_digest / execution_reference_asset_digests：<!-- lvr:param plan.authorization.execution-reference-digest-execution-reference-asset-digests --><!-- /lvr:param plan.authorization.execution-reference-digest-execution-reference-asset-digests -->
- preserve_dialogue / 删句例外 / dialogue_policy_reason（明确改变政策时）：<!-- lvr:param plan.authorization.preserve-dialogue-dialogue-policy-reason --><!-- /lvr:param plan.authorization.preserve-dialogue-dialogue-policy-reason -->

先用 prepare_execution_authorization.py 生成 draft，再根据本轮已确认决定核对并记录；草稿不能自动升为 confirmed。发生实际证据变化须回查，发生方案变化须按已有用户授权重新裁决，不能仅重算指纹掩盖变化。详见 references/execution-integrity.md。

## 阶段内关口与续接

按 `references/workflow-control.md` 恢复 project.json 中的关口与已有确认。交接前运行 `workflow_control.py handoff`，保留声音策略、Mockup、Proof、两次 Direct 和后续核验的当前状态、确认来源、缺口及下一步；不要因换会话而重置或默认关闭。
