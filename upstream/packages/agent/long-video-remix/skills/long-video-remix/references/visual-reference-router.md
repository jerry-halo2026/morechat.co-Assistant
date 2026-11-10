# Visual Reference Router · 公开方法版

Direct 2 的 V0 → V7 视觉执行入口。先读取 [Visual Direction Atlas](../visual-reference/visual-reference-package-v2.4.3/references/visual-direction-atlas.md)、[图文关系](../visual-reference/visual-reference-package-v2.4.3/references/scene-text-grammar.md) 和 [文字时序](../visual-reference/visual-reference-package-v2.4.3/references/timing-grammar.md)，用 V1 的画面事实判断注意力、文字角色、空间关系与强调尺度。V2 用当前项目证据校准方向，V3 先写 Art Direction，再定参数。

| 当前问题 | 方法 |
|---|---|
| 镜长、切点、镜内运动、文字与对象 | [剧情剪辑方法](../visual-reference/visual-reference-package-v2.4.3/references/editing-grammar.md) |
| 双人同框、关系观察、长文案和原声字幕 | [人物关系观察](../visual-reference/visual-reference-package-v2.4.3/references/cp-relationship-visual-application.md) |
| 动效机制、参数和工程选择 | [实现机制](../visual-reference/visual-reference-package-v2.4.3/references/motion-implementation-map.md) |
| 视觉阶段文件、检查命令和交接 | [V0–V7 执行规程](../visual-reference/visual-reference-package-v2.4.3/references/visual-design-procedure.md) |

## 1. 单一事实源

新项目在 `project.json#visual_pipeline.visual_stage_dir` 指定视觉目录，默认 `visual/`：

`V0 登记/范围 → V1 视觉问题 + 方向初判 → V2 参考选择/方向校准 → V3 全局/候选/逐镜头方向深化 + Art Direction → V4 Mockup + QA → V5 证据化评审 → V6 用户决定 → V7 参数锁定`

职责边界：

- **Style System**：审美底线与判断原则；
- **Visual Methods**：解决视觉问题和 production method；
- **视觉方向与剪辑方法**：提供方向判断、图文关系、时序和实现机制。
- **V0–V7**：当前项目真正的设计、验证范围和用户确认；
- **Implementation Lock**：把 V7 编译到可执行 Blender / FFmpeg 元素与参数；
- **Proof / QA**：验证当前实现是否忠实于 V6/V7 与 Implementation Lock。

不得再维护一套与 V0–V7 并行、可能冲突的 Reference Selection。

## 2. 渐进式 Direct 2

同一项目已确认方法的局部修订遵守 [方法保持合同](workflow-control.md#方法保持与叙事参数补丁)。Narrative 文件更新不自动重开风格探索，也不触发默认换字形、图文关系或动效结构；确实改变方法时回原 D2 对应决策。

V0 先设 `design_scope.mode`：

- `explore_new`：新的视觉语言或明显存在未知设计风险；V3 必须做 **2–3 个**候选。
- `reuse_confirmed`：已有明确、已确认的设计语言，只需适配当前素材；允许 **1–3 个**候选，单案合法。**不能只写 `basis`**：必须在 `reuse_evidence` 绑定此前真实 `V6 confirmed + V7 lock + confirmed artifact` 的文件与 SHA。`material_changes` 若包含图文关系、动效语言或几何策略变化，必须改走 `explore_new`。
- `simple_text`：简单文字处理、不值得完整比稿；允许 **1–3 个**候选，单案合法，并说明简化依据。

V3 再设 `validation_scope`：

- `full`：每个登记关键帧都在 V4 做 Mockup；适合镜头差异大、关键帧少或每帧都有独立风险。
- `representative_first`：先选择能覆盖不同版式的代表性关键帧做比稿。其余帧在 `deferred_keyframes` 记录 `covered_by / difficulty / risk_tags / reason`。普通镜头可以沿用已验证规则；长文字、多人、复杂背景、窄净区、字幕冲突、运动主体等 `difficult` 镜头在 V7 前必须补**实际成图**，不重新比稿但要重新做适配 QA。

因此，“8 个关键帧 × 2–3 个方案 = 16–24 张 Mockup”**不是默认要求**。代表性验证不是少做证据，而是把证据集中在会改变设计选择的风险点。

执行时每一步完成后运行：

```bash
python3 -I visual-reference/visual-reference-package-v2.4.3/scripts/check_visual_stage.py PROJECT/visual \
  --package visual-reference/visual-reference-package-v2.4.3
```

只做 `NEXT_ALLOWED` 指向的一步。V5 后停给用户；V6 记录同一次真实 Mockup 决定，不新增审批次数。

## 3. V2 Reference 与 `no_ref_needed`

公开版的参考目录初始为空。逐项覆盖 V1 的问题：在 `no_ref_needed` 说明当前源帧、文案和验证计划如何支持方向校准，`selections` 保持空。对应的 V3 `ref_trace` 与 V7、Implementation Lock 的 `reference_trace` 同样保持空。新风格进入 V5 后用当前项目的代表性同源 A/B 验证。

如另行配置有权使用的参考目录，仍按结构卡逐项核对画面与文案条件。只有满足所需条件的构图、层级、落位或运动原则可以迁移。当前项目的设计、证据和决定继续在 V0–V7 绑定。

## 4. Art Direction 与代表性扩展

V3 每个候选仍须先写 Art Direction，再写参数：

- `art_direction_thesis`；
- `composition_grammar`；
- `shot_dependency`；
- `failure_condition`。

`explore_new` 的多个候选仍需有实质差异，但差异可以来自**叙事观看逻辑**（注意力顺序、文字角色、空间关系、timing、强调预算）或形式结构；相同画幅/字体下，只要观看逻辑真实不同即可成立，不为通过比稿硬改文字方向或画幅。`reuse_confirmed/simple_text` 的单候选不为了凑数制造假差异。

V7 在 `representative_first` 模式下可以加入未在 V4 出现的正式元素，但代表帧通过只证明“设计语法成立”，不证明所有镜头适配成立。每个扩展元素必须：

- 用 `validation_basis` 指向一个实际做过 Mockup 的代表关键帧；
- 用 `adaptation` 说明如何从已验证规则适配到当前镜头；
- 文案、角色和其他事实仍来自 V0 / 已确认设计；
- `rect` 必须在 V7 `canvas` 内；
- 被标记为 `difficult` 的 deferred keyframe 必须在 `expansion_checks` 绑定真实渲染图 + SHA，并复核字号、对比度、保护区距离、字幕带和等比缩放。

不能把“代表性验证”理解成选一个最容易的镜头，然后无证据扩展全片。普通镜头无需重新比稿，困难镜头必须看实际成图。

## 5. V5 Review：保留有用证据，按需增加成本

默认硬证据：

- **代表性同源 A/B**：公开版没有预置已测参考豁免项。新风格 `explore_new` 需要在当前项目的真实素材上对比 baseline 与 candidate。
- **范围保持代表性**：选择能代表本轮主要设计风险的关键帧。已提供的 A/B 仍须逐项核验。
- **A/B 证据绑定**：精确绑定同一源帧 file+SHA、所属 unit 完整文案 id 集合与实际画布。文件相同或解码后像素相同只能记 no_visible_change，不能作为提升证据；同图候选须 rejected 或回 V4。动态时序仍由 Dynamic Proof 验证。
- **small-screen board：保留**，用于直接检查实际观看尺寸下的层级和可读性；
- **do-not-transfer checks：保留**，防止把参考中不可迁移的部分带进方案；
- **实际展示 artifact + SHA：保留**。

条件式工具：

- **blur/squint board**：当问题确实涉及视觉重心、明暗块、第一眼层级时使用；否则 `review_scope.blur_squint.status=not_needed` 并说明原因。
- **blind-map**：只在真实独立盲审时生成；没有盲审就不为形式完整生成映射。
- 独立 reviewer 默认 optional；如果实际使用，response 必须绑定当前 blind-map / board / V4 source。

这些都是机械证据，不是“高级感自动评分”。

## 6. 设计链失效：语义变化，不是文件字节变化

视觉模板使用 `inputs_design_sha256`。它对 JSON 的设计/证据 payload 做 canonical fingerprint：空白、键序、说明性备注等记录变化不会让后续阶段全部作废；真实设计输入变化仍会使相关后序失效。

**仍按原始内容 SHA 强绑定的对象不放松**：源素材、关键帧、实际 Mockup、small-screen/blur board、用户实际看到的 artifact、Proof、工程凭据和正式执行产物。

历史 v2.3.6 case 若只有 `inputs_sha256`，checker 继续按旧 byte-chain 严格验证，不把历史记录静默改写成新语义。

需要刷新当前项目的设计链时：

```bash
python3 -I visual-reference/visual-reference-package-v2.4.3/scripts/refresh_visual_chain.py PROJECT/visual
```

## 7. V7 → Implementation Lock：机械重复由程序同步

V3、V7、Implementation Lock 各自职责仍保留，但不要求重复手抄相同字段。

```bash
python3 scripts/sync_visual_stage.py PROJECT --target v7
python3 scripts/sync_visual_stage.py PROJECT --target implementation-lock
# 或 --target all
```

同步器负责：

- V3 chosen candidate → V7 `style`；
- 当前 design-chain fingerprints；
- V7 / V6 → `visual_stage_binding`、`confirmed_mockups`；
- V7 reference trace → Implementation Lock 的 stage-trace scaffold。

同步器**不会臆造**真实 `target_element_ids`、execution `parameter_paths`、`proof_checks` 或 `do_not_copy_checks`；这些仍需按实际执行工程填写并可解析。

链路为：

`V2 reference selection → V3 chosen ref_trace → V6 confirmed artifacts → V7 reference_trace → Implementation Lock executable parameters → Proof ReferenceCompliance → Final QA`

## 8. Mockup / Proof 复用边界

Aesthetic Mockup 仍不自动等于 Executable Proof。默认情况下，同文件或同内容的 Mockup/Proof 会被拦截。

只有 Mockup 已由最终实际工程工具链生成，并且项目显式声明：

- `visual_proof_reuse.mode = reuse_engineered_mockup`；
- 精确绑定 mockup / proof ref；
- 给出具体 reuse reason；
- `engineering_evidence_refs` 非空，文件真实存在并已列入 `execution_reference_asset_refs`；

才允许静态 Proof 复用同一内容。

这只消除重复静态出图。**连续 Dynamic Demo、运动/节拍/转场验证、执行 readback/receipt 与最终 QA 不因此跳过。**

## 9. Visual Methods 的职责

新项目 `visual-methods.json` 只记录当前 production method（PM001…）、事件范围、工具参数、失败模式与 Demo 检查，可用 `visual_stage_problem_refs` 回指 V1。
