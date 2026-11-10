# Execution Reference

> 与 execution-plan.md 一起构成 Direct 2 的 Execution Package。填写实际确定参数；任务未使用的层写 not_applicable 及原因。参考样本通常一两个，全片复用同一套规则。

## 版本、规格与确认

- 项目 / reference 版本：<!-- lvr:param reference.version.project-version --><!-- /lvr:param reference.version.project-version -->
- execution-plan.md / Narrative Direction：<!-- lvr:param reference.version.execution-plan-md-narrative-direction --><!-- /lvr:param reference.version.execution-plan-md-narrative-direction -->
- 输出 width × height / fps：<!-- lvr:param reference.version.width-height-fps --><!-- /lvr:param reference.version.width-height-fps -->
- reference 状态与已有确认来源：<!-- lvr:param reference.version.confirmation-status --><!-- /lvr:param reference.version.confirmation-status -->
- 原片关键帧清单 / 图片入口：<!-- lvr:param reference.version.source-keyframes --><!-- /lvr:param reference.version.source-keyframes -->
- selected Aesthetic Mockup（project.visual_mockup_ref；未确认写 null）：<!-- lvr:param reference.version.selected-aesthetic-mockup-project-visual-mockup-ref --><!-- /lvr:param reference.version.selected-aesthetic-mockup-project-visual-mockup-ref -->
- Implementation Lock（project.visual_pipeline.implementation_lock_ref；Mockup 确认后必须把构造参数写入）：<!-- lvr:param reference.version.implementation-lock-project-visual-pipeline-implementation-lock --><!-- /lvr:param reference.version.implementation-lock-project-visual-pipeline-implementation-lock -->
- Executable Proof Frame(s)（首个用 project.visual_proof_ref；多 Proof 时 project.visual_proof_refs 列全量；未确认写 null / []）：<!-- lvr:param reference.version.executable-proof-frame-s-project-visual-proof --><!-- /lvr:param reference.version.executable-proof-frame-s-project-visual-proof -->
- visual_gate_status：<!-- lvr:param reference.version.visual-gate-status -->not_started / mockup_confirmed / awaiting_proof / proof_confirmed / not_applicable<!-- /lvr:param reference.version.visual-gate-status -->
- execution_reference_asset_refs：<!-- lvr:param reference.version.execution-reference-asset-refs -->selected mockup、proof、`capability-map.json`（proof_confirmed 时三者都必须纳入）及其他资源：<!-- /lvr:param reference.version.execution-reference-asset-refs -->

## Visual Reproducibility Gate

> Aesthetic Mockup 负责选审美；Executable Proof 负责证明最终 Execute 的真实工具链可以复现。两步可在不同模型 / 会话中完成。模型连续性不要求，工具链连续性要求。

- mockup 基于的真实 keyframe / source timestamp：<!-- lvr:param reference.visual-reproducibility-gate.mockup-keyframe-source-timestamp --><!-- /lvr:param reference.visual-reproducibility-gate.mockup-keyframe-source-timestamp -->
- selected mockup 文件 / 确认来源：<!-- lvr:param reference.visual-reproducibility-gate.selected-mockup-decision --><!-- /lvr:param reference.visual-reproducibility-gate.selected-mockup-decision -->
- inherited execution toolchain（来自 execution-handoff / capability-map）：<!-- lvr:param reference.visual-reproducibility-gate.inherited-execution-toolchain-execution-handoff-capability-map --><!-- /lvr:param reference.visual-reproducibility-gate.inherited-execution-toolchain-execution-handoff-capability-map -->
- proof 实际使用的 actual_tool / 版本：<!-- lvr:param reference.visual-reproducibility-gate.proof-actual-tool --><!-- /lvr:param reference.visual-reproducibility-gate.proof-actual-tool -->
- renderer / layout entrypoint：<!-- lvr:param reference.visual-reproducibility-gate.renderer-layout-entrypoint --><!-- /lvr:param reference.visual-reproducibility-gate.renderer-layout-entrypoint -->
- proof 使用的字体 / 布局源文件 / 资源：<!-- lvr:param reference.visual-reproducibility-gate.proof --><!-- /lvr:param reference.visual-reproducibility-gate.proof -->
- current Implementation Lock / SHA-256：<!-- lvr:param reference.visual-reproducibility-gate.current-implementation-lock-sha-256 --><!-- /lvr:param reference.visual-reproducibility-gate.current-implementation-lock-sha-256 -->
- final Execute toolchain / entrypoint：<!-- lvr:param reference.visual-reproducibility-gate.final-execute-toolchain-entrypoint --><!-- /lvr:param reference.visual-reproducibility-gate.final-execute-toolchain-entrypoint -->
- toolchain continuity：<!-- lvr:param reference.visual-reproducibility-gate.toolchain-continuity -->same / changed（changed 时说明 capability-map 与最终 Execute 如何同步更新；同步前 Gate 不得 confirmed）<!-- /lvr:param reference.visual-reproducibility-gate.toolchain-continuity -->
- proof frame 文件 / 确认来源：<!-- lvr:param reference.visual-reproducibility-gate.proof-frame --><!-- /lvr:param reference.visual-reproducibility-gate.proof-frame -->
- Gate 尚未关闭时的缺口与下一步：<!-- lvr:param reference.visual-reproducibility-gate.gate --><!-- /lvr:param reference.visual-reproducibility-gate.gate -->

## Production Lock

> Production Proof Lock 通过后，本节与当前 Proof / Composition / Visual Methods / Delivery Spec 一起进入机器指纹。Execute 只允许替换本轮已授权内容和 safe adaptation；不得重新选择字体层级、版式区域、crop 逻辑、颜色关系、运动方法或最终渲染工具链。任何锁定项变化只使受影响的 Proof / Composition / Production Lock 失效，不重做无关 Structure。

- Blender / 合成实际工具与 entrypoint：<!-- lvr:param reference.production-lock.blender-entrypoint --><!-- /lvr:param reference.production-lock.blender-entrypoint -->
- FFmpeg 最终交付 entrypoint（默认 `scripts/finish_ffmpeg.py`；如不同须在 capability-map 与本节同时声明）：<!-- lvr:param reference.production-lock.ffmpeg-entrypoint-scripts-finish-ffmpeg-py-capability --><!-- /lvr:param reference.production-lock.ffmpeg-entrypoint-scripts-finish-ffmpeg-py-capability -->
- 采用的 composition ID / method ID：<!-- lvr:param reference.production-lock.composition-id-method-id --><!-- /lvr:param reference.production-lock.composition-id-method-id -->
- Implementation Lock / selected Mockup SHA-256 / selected REF trace：<!-- lvr:param reference.production-lock.implementation-lock-selected-mockup-sha-256-selected --><!-- /lvr:param reference.production-lock.implementation-lock-selected-mockup-sha-256-selected -->
- 字体与字体文件 / fallback：<!-- lvr:param reference.production-lock.fallback --><!-- /lvr:param reference.production-lock.fallback -->
- 文字层级与最小可见字形规则：<!-- lvr:param reference.production-lock.text-hierarchy-glyph-floor -->引用 `project.text_policy`；<!-- /lvr:param reference.production-lock.text-hierarchy-glyph-floor -->
- 版式区域 / crop / fit / frame / border / layer order：<!-- lvr:param reference.production-lock.crop-fit-frame-border-layer-order --><!-- /lvr:param reference.production-lock.crop-fit-frame-border-layer-order -->
- 颜色角色与强调关系：<!-- lvr:param reference.production-lock.color-emphasis --><!-- /lvr:param reference.production-lock.color-emphasis -->
- 运动方法 / 曲线 / 允许的安全适配：<!-- lvr:param reference.production-lock.motion-safe-adaptation --><!-- /lvr:param reference.production-lock.motion-safe-adaptation -->
- FFmpeg / ASS / filter 实现策略及不可替换项：<!-- lvr:param reference.production-lock.ffmpeg-ass-filter --><!-- /lvr:param reference.production-lock.ffmpeg-ass-filter -->
- 当前 `delivery-spec.json`：<!-- lvr:param reference.production-lock.delivery-spec-json --><!-- /lvr:param reference.production-lock.delivery-spec-json -->
- 允许 Execute 调整：<!-- lvr:param reference.production-lock.execute-adjustable -->仅 D2 snapshot / safe windows / 本节明确列出的 adaptation；<!-- /lvr:param reference.production-lock.execute-adjustable -->
- 禁止 Execute 自行调整：<!-- lvr:param reference.production-lock.execute-locked -->未列入允许项的风格、工具链、字体、布局、声音政策与旁白政策。<!-- /lvr:param reference.production-lock.execute-locked -->

## Visual Methods 与 Visual V0–V7 锁定规则

Visual Methods 只提供 production method / fallback，不把外部案例当当前素材证据。采用视觉设计时，以 `project.visual_pipeline.visual_stage_dir` 下的 V0–V7 为视觉设计事实源：V2 用当前项目证据覆盖视觉问题，V3 先 Art Direction 后参数，V4/V5 做 Mockup 与 evidence-bound review，V6 只记录用户真实选择及实际展示 artifact hash，V7 锁定设计。`visual-methods.json` 不再复制 Reference Selection，只可用 `visual_stage_problem_refs` 回指 V1 问题。

| mockup ID / 实际图片 / 原片 frame_id | style / layout ID、文字层级与画面关系 | 全片应用范围与规则 | 未提供项与原因 |
|---|---|---|---|
<!-- lvr:param reference.visual-methods-visual-v0-v7.mockup-application -->
|  |  |  |  |
<!-- /lvr:param reference.visual-methods-visual-v0-v7.mockup-application -->

### V7 → Implementation Trace

> 新项目的每条 V7 `reference_trace` 必须在 `implementation-lock.json#reference_trace` 有且只有一条桥接：`stage_trace` 精确保留 `structure_card / transfer / element / parameter_path`，再映射到当前执行层的 `method_id / ref_id / target_element_ids / parameter_paths`。`visual_stage_binding` 必须绑定当前 V7 bytes，`confirmed_mockups` 必须精确等于 V6 选中候选的全部实际 artifact。只停在 V7、不落执行参数不算实现。

| V7 structure card / transfer / element / parameter | method / REF | confirmed mockup(s) | target element IDs | concrete Implementation Lock parameter paths | Proof checks / do-not-copy checks |
|---|---|---|---|---|---|
<!-- lvr:param reference.visual-methods-visual-v0-v7.implementation-trace -->
|  |  |  |  |  |  |
<!-- /lvr:param reference.visual-methods-visual-v0-v7.implementation-trace -->

Visual Gate 规则见本 Skill 的 `references/execution-package.md`：一两个 Aesthetic Mockup 只选审美方向；选中后必须由最终 Execute 可访问的同一实际工具链重建 Executable Proof。proof_confirmed 后才把该视觉方案视为可执行。原图独立保留，缺图标待补。

- proof 与正式 Execute 共用的字体（含授权说明；商用注意授权）/ 布局生成入口（布局源文件或渲染代码 / 方法）及资源：<!-- lvr:param reference.visual-methods-visual-v0-v7.proof-execute --><!-- /lvr:param reference.visual-methods-visual-v0-v7.proof-execute -->
- 仅作说明的箭头 / 标签，与实际进入视频的元素及计划引用：<!-- lvr:param reference.visual-methods-visual-v0-v7.annotation-usage --><!-- /lvr:param reference.visual-methods-visual-v0-v7.annotation-usage -->

## 画面规则

### 制作方法与动态验证（schema 1.9）

- visual-methods.json：<!-- lvr:param reference.visual.visual-methods-json -->visual_problem / Project Method（PMxxx）/ library_refs（M01–M14）/ fallback_refs（F01–F09）/ 必要候选比较 / 叙事作用 / 视觉重点 / 原画条件 / 处理选择及理由 / 参数 / 失败情形 / demo 检查点：<!-- /lvr:param reference.visual.visual-methods-json -->
- implementation-lock.json：<!-- lvr:param reference.visual.implementation-lock-json -->visual_stage_binding / confirmed_mockups、renderer / element / event scope / crop / rect / font / color / z-order / motion 等直接执行参数，以及每条 V7 reference trace 的执行桥接：<!-- /lvr:param reference.visual.implementation-lock-json -->
- method 的当前确认来源与适用范围：<!-- lvr:param reference.visual.method --><!-- /lvr:param reference.visual.method -->
- composition-plan.json：<!-- lvr:param reference.visual.composition-plan-json -->图层 / 父子关系 / 曲线 / 帧区间 / 前后接点设计：<!-- /lvr:param reference.visual.composition-plan-json -->
- 实际 .blend、依赖资源、连续 demo（包含接点两侧及相关声音）：<!-- lvr:param reference.visual.blend-demo --><!-- /lvr:param reference.visual.blend-demo -->
- Blender 原生 readback、技术 receipt、逐项 review：<!-- lvr:param reference.visual.blender-readback-receipt-review --><!-- /lvr:param reference.visual.blender-readback-receipt-review -->
- proof / composition 的实际展示与当前确认来源：<!-- lvr:param reference.visual.proof-composition --><!-- /lvr:param reference.visual.proof-composition -->
- delivery-spec.json、FFmpeg 回接窗口、成片 QA 与可调范围：<!-- lvr:param reference.visual.delivery-spec-json-ffmpeg-qa --><!-- /lvr:param reference.visual.delivery-spec-json-ffmpeg-qa -->
- 未实现或未观看项及受影响 Gate：<!-- lvr:param reference.visual.gate --><!-- /lvr:param reference.visual.gate -->

实现与检查按 [视觉制作](../references/visual-production.md)；模板空白不表示通过。

- 原片保留方式 / crop / scale / 位置（精确参数）：<!-- lvr:param reference.visual.crop-scale --><!-- /lvr:param reference.visual.crop-scale -->
- 人物、动作、硬字幕需避让的范围 / 安全边距：<!-- lvr:param reference.visual.protected-regions --><!-- /lvr:param reference.visual.protected-regions -->
- 色彩与效果处理：<!-- lvr:param reference.visual.color-effects --><!-- /lvr:param reference.visual.color-effects -->
- 情绪强化方式及允许使用的范围：<!-- lvr:param reference.visual.emotion-treatment --><!-- /lvr:param reference.visual.emotion-treatment -->
- 相片页 / 录像框等已采用版式：<!-- lvr:param reference.visual.adopted-layout -->layout ID、图片置入框 x/y/w/h、crop / fit、边框 / 圆角 / 间距、图层顺序与符号参数（尺寸单位与坐标原点须明确；未采用写 not_applicable）：<!-- /lvr:param reference.visual.adopted-layout -->
- 禁止的处理：<!-- lvr:param reference.visual.forbidden-treatment --><!-- /lvr:param reference.visual.forbidden-treatment -->

## 文字样式

| style ID / 文字用途 | 字体文件或可用字体名 / 确定替代 | 字号 / 单位 / 字重 | 颜色 / 描边 / 阴影 / 背景 | 位置 / 坐标基准 / 对齐 / 边距 | 行数 / 换行 / 字距 / 行距 | 进入 / 退出动效及 ms 或帧数 | 阅读停留规则 |
|---|---|---|---|---|---|---|---|
<!-- lvr:param reference.text-style.styles -->
|  |  |  |  |  |  |  |  |
<!-- /lvr:param reference.text-style.styles -->

实际文字全文、断行及逐条出现 / 消失事件锚点放在 execution-plan.md，并引用 style ID。不要只交“字幕大一些”或“适当停留”。字重是否可用、字号采用 px / pt / 相对高度必须明确；参数绑定本版输出规格。v1.4.1 新运行契约还要求 timeline 的每条文字写 `text_role / glyph_height_px / canvas_height_px / stable_hold_frames`；ready 前按 `project.text_policy` 检查最小实际字形高度、创作者文字最大行数、阅读速度和最低稳定停留。放不下时先减字 / 延长 / 改布局，不允许在 Execute 中静默缩小到政策下限以下。

## 声音与转场

- 原声 / 环境音 / BGM / 旁白政策和禁止项：<!-- lvr:param reference.audio-transitions.bgm --><!-- /lvr:param reference.audio-transitions.bgm -->
- `project.voiceover_policy`：<!-- lvr:param reference.audio-transitions.project-voiceover-policy -->默认未明确允许即禁止新增旁白；若采用旁白，写清 allowed=true、叙事作用、与原对白关系及本节 ref。<!-- /lvr:param reference.audio-transitions.project-voiceover-policy -->
- 每条音轨的源 / 取段 / 放置 / 增益 / 速度 / fade / review refs：<!-- lvr:param reference.audio-transitions.fade-review-refs -->见 execution-plan.md 的明确记录。<!-- /lvr:param reference.audio-transitions.fade-review-refs -->
- 每个接点的类型 / overlap 或 card 帧数：<!-- lvr:param reference.audio-transitions.overlap-card -->见 execution-plan.md 的接点表。<!-- /lvr:param reference.audio-transitions.overlap-card -->
- 重要停顿、动作 / 回应、对白尾部的保护规则：<!-- lvr:param reference.audio-transitions.protected-audio-actions --><!-- /lvr:param reference.audio-transitions.protected-audio-actions -->

## 素材与允许调整

| asset ID / 文件 | 用途 / 来源与版本 | available / unavailable / partial / uncertain | reason / impact / downstream_handling |
|---|---|---|---|
<!-- lvr:param reference.assets-permissions.assets -->
|  |  |  |  |
<!-- /lvr:param reference.assets-permissions.assets -->

- 字体和参考图片在执行环境的实际入口：<!-- lvr:param reference.assets-permissions.font-reference-assets --><!-- /lvr:param reference.assets-permissions.font-reference-assets -->
- 可调整项（与原机器授权的 allowed_adjustments 一致）：<!-- lvr:param reference.assets-permissions.allowed-adjustments --><!-- /lvr:param reference.assets-permissions.allowed-adjustments -->
- 不得调整项：<!-- lvr:param reference.assets-permissions.locked-values --><!-- /lvr:param reference.assets-permissions.locked-values -->
- 封面规格 / 全文 / 源图 / 排版（仅本任务要求时）：<!-- lvr:param reference.assets-permissions.cover-spec --><!-- /lvr:param reference.assets-permissions.cover-spec -->

## QA 判据

- 全片文字层级、位置、字号 / 颜色、画面占比是否符合上述规则：<!-- lvr:param reference.qa.text-rule-compliance --><!-- /lvr:param reference.qa.text-rule-compliance -->
- 正常速度阅读时间、遮挡 / 裁切和手机检查：<!-- lvr:param reference.qa.readability-mobile --><!-- /lvr:param reference.qa.readability-mobile -->
- 情绪强调、动效 / 转场与 reference 是否一致：<!-- lvr:param reference.qa.emotion-motion-compliance --><!-- /lvr:param reference.qa.emotion-motion-compliance -->
- 成片风格对照：<!-- lvr:param reference.qa.style-comparison -->同一版式的成片截图与 executable proof 的对照入口及结论；selected mockup 只辅助审美核对（风格匹配即可）：<!-- /lvr:param reference.qa.style-comparison -->
- 原声、保护范围与音轨参数是否实现：<!-- lvr:param reference.qa.audio-compliance --><!-- /lvr:param reference.qa.audio-compliance -->
- 实际导出 / reference 对照尚未完成的项：<!-- lvr:param reference.qa.pending-export-comparison --><!-- /lvr:param reference.qa.pending-export-comparison -->

在原 qa.json checks 中登记 ReferenceCompliance；没有实际观看记 not_tested。具体参数变更同步计划、机器授权与受影响时间轴 / 缓存，不在 Execute 中另行定义风格。

## 阶段内关口与续接

按 `references/workflow-control.md` 恢复 project.json 中的关口与已有确认。交接前运行 `workflow_control.py handoff`，保留声音策略、Mockup、Proof、两次 Direct 和后续核验的当前状态、确认来源、缺口及下一步；不要因换会话而重置或默认关闭。
