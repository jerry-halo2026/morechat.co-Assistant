# Detail Structure → Director 2 Handoff

> E 阶段交付。接收方无需安装原 Skill，即可凭本文件与随附证据形成 Execution Package。本文件不替代 Detail 表，也不提前生成最终剪辑方案。模板空白须填入实际信息；未知项明确标注并带异常原因。

## 当前状态与文件清单

- 项目 / 产物版本：
- 当前已完成范围 / coverage 缺口：
- 实际随附文件与可读取位置（包括图片）：
- 尚未包含的资源与取得方式：
- exceptions 文件及影响 / 下游处理：

## 本轮 Scope Lock

- 当前阶段 / current stage：Detail → Director 2
- 可修改 / editable：
- 不可修改 / locked：
- 已否决 / rejected：

## 已确认叙事背景

- Narrative Direction 文件与确认来源：
- 核心主题 / 内容目标：
- 情绪路径 / 人物关系（事实、解读分列）：
- 必须保护的原话、画面、动作与表达重点：
- 已确认禁改项：

## 所选素材与证据

| segment / unit ID | source ID / 版本 / time_mapping | 源区间 ms | 叙事用途及状态 | evidence refs / reviews | context / protected ranges | edit boundary / safe windows | 缺口 / 反证 |
|---|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |  |

原音轨完整核听范围、问答 / 动作的最短完整范围及切点风险：

### Question Closure Ledger

所有 `answer_status=contradicted` 或 `unresolved` 的 Detail 问题逐行列出；没有时保留表头。标题可附中文说明，但须包含 "Question Closure Ledger" 或“问题闭环”字样，validator 只读取这个标题下的表格。每个 question_id 只列一次，plan_node_id 与实际关联节点一致（多个节点用分号分隔）。`处理方式` 写具体下游动作（不能只写 resolved）；入选成片的节点带 `contradicted` 问题时，`confirmed_by` 必须是作出该决定的人。

| question_id | status | plan_node_id | 处理方式 | confirmed_by |
|---|---|---|---|---|

## 原片关键帧

- keyframe-references.json：
- 单独保存、实际随包附带的原片关键帧图片与 source timestamp：
- 每张图对应的素材节点 / narrative role：
- 提取失败或定位不确定项（status / reason / impact / downstream_handling）：

## Toolchain Continuity

> 来源是现有 `capability-map.json`；这里只摘录与本条后续有关的映射，不另建工具链配置。模型 / 会话可以变化，但 Visual Proof 与最终 Execute 必须继续使用同一套实际可访问的执行能力。

- capability-map.json / 版本或入口：
- Broad / Detail 实际使用的分析 capability → actual_tool：
- 最终 Execute 可继续访问的 render / layout / text / image capability → actual_tool：
- 已验证版本 / entrypoint / 输入限制：
- 可用字体、布局源文件、渲染代码与其他必要资源入口：
- unavailable / unverified 能力及下游影响：

## 下游任务：生成完整 Execution Package

采用视觉制作流程时，D2 另交制作方法（叙事作用→视觉问题→视觉重点→原画条件→处理依据→参数/失败情形）；已有方案可由 Visual Methods 校正深化，没有成熟方案时按 Router + 完整方法库 / fallback 提出可制作候选后再选定 Project Method。完整 `composition-plan.json` 要覆盖最终需要的 Blender production windows，但前置验证只对 `proof_composition_ids` 交代表性 Blender 工程、可访问资源、含接点两侧的动态 demo、技术 receipt 和逐项实看 review；composition 数量不等于 demo 数量。方法与当前代表性工程/demo 均需真实确认，其余 composition 只有在 `proof_covered_by` 指向当前 Proof 且 mode / Lock elements / methods / join 风险均被机器判定覆盖时，才在最终授权后一次性正式生产。确认后按当前 manifest 回到既有 FFmpeg 流程，并完成原 QA 与 CompositionCompliance / MotionContinuity / DeliveryTechnical。缺项随包传递，不能以以后再反馈代替本轮 Gate。详细规范与入口是 [视觉制作](../references/visual-production.md)。

Director 2 基于以上已核实素材和 Narrative Direction 决定最终呈现；保留两次 Direct 的职责，不重做已确认主线，不把未核实项当成事实。素材不足只补对应缺口；主线冲突说明证据并返回 Direct 1。

请一次交付以下内容，已明确的规则填具体参数，不将必要判断留到 Execute：

1. **Editorial Execution Plan / execution-plan.md**：最终素材取舍、顺序、逐段 planned source range + boundary ref、允许 Execute Step 0 校准的 safe windows / handles、速度 / 画面处理、保护范围、时长预算、文字 / 原声 / 接点处理。D2 不必在外部环境把最终帧级 in/out 做死。
2. **Visual / Text Reference / execution-reference.md**：字体及可用资源、字号与单位、字重 / 颜色、位置 / 对齐、换行 / 行数、描边 / 背景、阅读停留、动效；明确输出分辨率、原片裁切 / 缩放和文字与画面的关系。
3. **Audio Specification**：每条原声 / 环境音 / BGM / 旁白的政策、源取段、成片放置、增益、速度、淡化、完整对白保护；没有配乐需求时不默认添加。
4. **Transition Specification**：每个接点采用什么及帧数；黑场 / card / hold 若增时，要计入事件与总长。
5. **Visual Reproducibility Gate（强制但可跨模型完成）**：先用随附真实关键帧、实际文字和目标输出画幅制作一两个 Aesthetic Mockup，由人选择审美方向；随后可在同一或其他模型 / 会话中，使用上方 Toolchain Continuity 中最终 Execute 可访问的同一实际工具链重建 Executable Proof Frame，并把 renderer / layout entry、字体、资源与关键参数写入 execution-reference。mockup 确认后可先标 `awaiting_proof` 继续准备其他内容，但 proof 未确认前不得进入正式 Execute。若当前工具链做不到已选 mockup，调整 mockup 或正式更新 capability-map / 最终 Execute 路径后重做 proof，不能用下游不可用的工具冒充 proof。
6. **Asset / Constraints**：可读素材、证据、关键帧、字体和参考资源；允许调整、禁改项、status / reason / impact / downstream_handling。封面等仅在本任务要求时提供，其余记 not_applicable。
7. **QA Criteria**：内容、保护范围、时间、文字可读性、音轨 / 接点与 Reference Compliance（成片与 mockup 风格匹配即可，不要求逐帧或逐像素对应）。静态检查和真实播放分开，未实看写 not_tested。
8. **Execute Step 0 + 机器授权**：正式剪辑先只精校 D2 已选片段及 handles；subtitle + waveform / signals 优先，ASR 仅按需小窗口使用。补齐 selected boundary 的最终音画边界 / reviews 并升为 supported；语义冲突返回 D2。随后用最终 ranges 准备 / 确认 execution-authorization.json。selected mockup、proof 与 reference 继续进入既有指纹。

时间继续以 source_id + source ms 定位，文字 / 音轨放置优先使用 event anchor + local frames；正式成片坐标按现有时间轴编译对账。异常可以随包继续推进可做部分，但不能豁免证据、完整对白、Edit Boundary、源许可或正式渲染条件。

## Execute 接手入口

接收 Source Clips + Detail Structure + execution-plan + execution-reference + Constraints。先执行 Selected Range Verification，再按已确认方案制作；边界可在 D2 允许范围内校准，但不重新选择核心主题、片段或风格。资源 / 参数有缺口时先明确处理，不补造确认结果。

## 阶段内关口与续接

按 `references/workflow-control.md` 恢复 project.json 中的关口与已有确认。交接前运行 `workflow_control.py handoff`，保留声音策略、Mockup、Proof、两次 Direct 和后续核验的当前状态、确认来源、缺口及下一步；不要因换会话而重置或默认关闭。
