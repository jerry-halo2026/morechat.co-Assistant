# Long Video Remix v1.5.1-public-methodology-clean · Chat Project Reference

> 插件在当前回合不可读取时，使用以下同版规程续接。需要抽帧、渲染或机器校验时，先核对当前环境的实际能力与项目文件。

## FILE: `SKILL.md`

---
name: long-video-remix
description: 从三到五小时或多集影视、活动视频中建立可回查的画面与原声索引，先输出正式的文字化 Structured Observation Layer 与 Content Map；由人工或独立 Director 确定 Narrative Direction 后回原素材做定向高密度核验，再由 Director 基于 Detail 证据形成 Execution Package（执行计划与制作参考），最后落实为可执行剪辑时间轴、渲染清单与成片核查。用于长视频结构化、九宫格分析、逐抽样帧记录、定向精查、同集重组、跨场景主题混剪、剪辑执行稿、分层渲染、成片返工、导出核查及跨模型交接；不把两次创意决策作为默认自动职责。 AI video editing Agent Skill for long-video-to-shorts, highlight extraction, remix planning, traceable source indexing, Visual Methods, Blender motion composition, FFmpeg execution and QA. Both directing decisions remain with a human or Director.
---

# 长视频结构化与混剪执行

工作流、视觉方法与合成工程 v1.5.1-public-methodology-clean · 2026年11月7日

先将视频、图像、对白与上下文转成有来源、可检索、可回查的**紧凑结构化工作层**，供人工、Director 或其他 Skill 使用。创意确认后，只对命中区域回原素材高密度核验，再编译执行。

整体工作分为三个功能层，但 Direct 在完整工作流里出现两次：

- **Structure**：Broad 建立正式文字化结构；Direct 1 确定主线后，Detail 回原片定向取证。
- **Direct**：人或独立 Director 两次决策：Direct 1 定 Narrative Direction / Spine；Detail 补证后，Direct 2 定 Execution Package（Editorial Execution Plan + 制作参考）。
- **Execute**：将 Direct 2 已确认方案与已核实素材编译为时间轴、渲染清单、粗剪 / 成片及 QA。

标准路径是：

```text
Source
  ↓
Broad Structure
  ↓
Structured Observation Layer
(frame-observations + action-node-candidates + structure-questions + scene/segment observations)
  ↓
Content Map + emotional / relationship cues
  ↓
Direct 1 — Narrative Direction
“到底讲什么？” → Narrative Spine + candidate regions + questions to verify
  ↓
Detail Structure
“围绕这条主线，把证据看清楚”
  ↺ 证据不足 / 主线不成立时返回 Direct 1 调整
  ↓
Direct 2 — Execution Package
“这些证据最终怎么讲？” → confirmed execution plan + execution reference
  ↓
Execute
  ↓
Render / QA
```

抽帧负责发现，连续音画负责核实，完整片段负责剪辑。允许改变叙述顺序和集中呈现分散线索；保留原话含义、真实指向、必要因果和动作完整性。

## 执行边界

- 以本轮明确要求 > 已确认方案 > 指定素材 > 默认值执行。各 Direct / handoff 用四行 **Scope Lock**（阶段、可改、禁改、已否决）承接当前状态；不另建历史状态文件。
- **每个大阶段结束必须生成 handoff。** `workflow_control.py handoff` 更新 `handoff.md`；前向 `advance` 只接受当前阶段最新 handoff。跨模型 / 机器的 manifest 与源重绑定规则见 [workflow-control](references/workflow-control.md)；Detail 另交 `execution-handoff.md`。非新增 Gate。
- 先核查工具并映射到 `capability-map.json`（含 actual_tool + entrypoint）；未实际调用不写已完成。Visual Proof 可换模型 / 会话，但必须沿用最终 Execute 可访问的执行工具链：**模型可换，工具链不可漂。** proof capability 的 output_mapping 必须指向当前 proof；schema 1.7 新项目缺 Visual Gate 字段、proof 或可复现工具入口时不得正式 Execute。
- 默认以角色和剧情为对象。公开活动只描述可见行为和观看感受，不由混剪推断真人私下关系、性取向或心理。
- 不凭抽样帧补出未见动作，不凭转写补出未听台词，不把用户摘要或工具标签改写为亲眼观察。
- **Broad Structure 不因已有 brief 过早缩窄覆盖。** brief 可以帮助标注重点，但第一轮仍要保留整体内容面、coverage 和 unknowns。
- **Structure 有最低信息地板。** `frame-observations.csv`、动作节点候选、结构化问答 / 未验证项，以及进入第二轮后的 `detail-intervals.csv` / `speaker-adjudications.csv` 是基础工作层，不得用 overview、Content Map、最终文案或剪辑结论替代。某字段没有可见信息时保留原字段及允许的 `unknown` / `not_applicable` 等值，不能留空；无法满足的字段或产物另外声明 status / reason / impact / downstream_handling，继续可做部分，不补造、不豁免精确执行门槛。详见 [异常与执行包契约](references/execution-package.md)。
- **时间标签是全流程的证据主键。** Structure 中一律以 `source_id + source_ms / source_range` 为 canonical 定位；`display_timecode` 只是人读显示，九宫格序号、ASR 自带时间、代理文件时间和成片时间都不能替代源时间。任何抽帧、硬字幕、ASR、原声核听、动作节点、Detail observation、unit 都必须保留或能无歧义映射回同一源时间；Execute 再由 source time 通过 event anchor 编译到 assembly / output frame。源版本或 time mapping 变化时，所有精确下游坐标必须失效重核。本地原片优先用 `scripts/extract_frames.py`；MCP / 代理等用经短段校验的适配器，均保留实测时间与源绑定。
- **未观察到不等于没有发生。** 4fps 是动作候选的局部加密起点，不是“没有发生”的充分证据。否定性结论必须先限定明确 source-time 范围，再按事实类型核验：视觉动作 / 物件缺席需连续视频覆盖完整机会窗口，某句话未说需连续原声覆盖声明区间，或存在能直接排除该事实的可靠反证；否则只记录 `not_observed_in_sample` / `unknown`。
- **证据冲突按事实类型裁决，不设一条机械总排名。** 视觉动作以连续原画为主；实际台词以清晰原声核听与可靠官方硬字幕相互校验；说话人 / 对象结合口型、连续原声、人物关系与字幕信号。ASR 尤其在方言 / 强口音下默认只作 locator，未经回听或硬字幕核对不得升级为台词事实；冲突必须显式保留。
- **先记录基础事实，再做派生判断。** 画面事实、动作、硬字幕、原声要点、与前帧变化、背景、情绪线索、主题判定、confidence / 证据依据、问题与未验证项必须保留；意象标签、情绪解释、叙事功能和剪辑价值只能建立在这些基础记录之上。
- **第一次 Direct 的 Narrative Direction 是创意意图，不等于素材已经证明。** Detail Structure 必须围绕其 narrative spine、candidate regions 和 verification questions 重新回到相关原片核对。
- 如果第二轮证据与 narrative direction 冲突，报告冲突、替代素材和缺口；默认返回 Direct 1 调整主线，不通过剪辑技巧强行证明原方案。
- **D2 在 Detail 后完成。** 按 [Visual Reference](references/visual-reference-router.md) 与正式规程走 V0→V7：先 V1 事实与方向初判，再用当前项目证据完成 V2 校准、V3 Art Direction。新风格才多案；复用、代表帧、困难镜头成图及新风格的代表性同源 A/B按规程核验。V7 再进 Implementation Lock。
- **Proof 必须最小充分。** 被其他 Proof 覆盖即阻断，等价留前者；素材级例外须显式 `additional_proof_exception` 并展示证据。native_blend 复用要求同 scene/dependencies；最终 CompositionCompliance 每段须有 pass/finding，含 join 再写 join_finding。
- 同一集优先；同一事件、对白指向和关系阶段优先级高于服装相似。跨集须有明确主题联系，并让观众辨认时空变化。
- 删段不删句，删重复不删因果。必要问答、否定、条件、迟疑、回应和动作后果共同决定最短保留范围。
- 默认不改写原声、不拼接词语制造新对白、不借用异场反应冒充即时回应。明确要求架空或恶搞时另行约定，不沿用剧情准确混剪的事实标签。
- 不强制每条五至八段或四十五至六十秒。未给时长时先提出由证据支持的时长，再试剪；不为达到配额拆碎互动。
- 不新增审批阶段；采用视觉设计时，实际工具链 proof 未确认前不得正式 Execute。

- **局部修订继承方法。** 具名参数用 `adapt`；改文案、素材或段落先用 `revise` 声明范围，再由原 plan 确认实际 diff。范围外阻断，方法变化另走原 D2 决策，见 [方法保持](references/workflow-control.md#方法保持与叙事参数补丁)。

## 开始工作

1. 读取 [工作流程](references/workflow.md) 和 [数据契约](references/data-contracts.md)，建立任务目录与 `project.json`。
2. 读取 [MCP 适配](references/mcp-adapter.md)，发现真实能力、记录映射并完成小范围探测。只使用获授权的素材访问与处理范围。
3. 每轮续接先按 [关口与续接控制](references/workflow-control.md) 恢复项目：新制作管线首次 `visual_pipeline.py init`，以后 `workflow_control.py status`；读不到状态就说明缺口。沿用有效确认，主动提示 pending/stale，不因换模型重扫或清空关口。
4. 如果当前任务只要求 Structure，可在 Structured Observation Layer + Content Map 完成后正式交付，不必进入 Direct 或 Execute。
5. 如果要继续混剪，先读取已有 Narrative Direction；没有时，把 Broad Structure 的正式结构化表单、scene / segment observations、Content Map、情绪 / 关系线索和 usable bounds 交给用户或独立研究 / 编导环境，结合外部资料与人工判断形成第一次 Direct 输出。Detail Structure 完成后，固定交付真实关键帧与 `execution-handoff.md`，在 handoff 内写入下游 Execution Package 的完整要求，再交给可位于其他环境的 Director 2。
6. 从当前可验证阶段开始，按下面的顺序推进。缺少某种观察能力时降级输出，并明确标签。

## 工作顺序

| 阶段 | 执行动作 | 产物 | 进入下一步的条件 |
|---|---|---|---|
| A 素材登记 | 确认版本、时长、时间基准、字幕匹配、能力与配置 | project、sources、capability-map | 能把后续证据定位回原素材；否则只做准备 |
| B Broad Structure | 全时段粗扫画面和台词；逐张记录已分析抽样帧的完整基础观察；保留帧尾、原声要点、主题判定与 confidence；标记相邻帧变化、意象、动作节点候选，并对候选开 4fps 局部窗口；记录问题回答与未验证项；登记可用素材物理边界并增量落盘 / 更新 coverage | frames、frame-observations、action-node-candidates、structure-questions、transcript、coverage、usable source bounds | 基础观察层完整且可识别覆盖与缺口；源时间映射稳定；人工 / Director 不必重新从九宫格猜内容 |
| C Structured Working Layer + Content Map | 在逐抽样帧表之上形成 scene / segment 观察、source-order overview、情绪 / 关系线索和跨场景 Content Map；这些都是 Broad Structure 的正式文字化结构输出，不是用 Content Map 替代表单 | frame-observations、action-node-candidates、structure-questions、scenes / segment observations、overview、content-map、emotional / relationship cues、handoff.md | 形成足够完整且可下钻回 frame observation 的素材面；若 deliverable=content_map 可在此正式交付 |
| D1 Direct — Narrative Direction | 人 / Director 读取正式结构化表单 + Content Map + 外部研究，抽选“到底讲什么”：核心命题、Narrative Spine、candidate regions、需要 Detail 验证的问题和禁改项 | brief、narrative-direction、external research refs、narrative mapping、handoff.md | 主线已人工确认到足以指导定向深挖；不要求已有精确切点 |
| E Detail Structure | 围绕目标问题核实到最小充分证据即 STOP；字幕 / signals 优先，ASR 只查关键歧义；未入选候选可交 partial 保守边界 | detail-intervals、deep-observations、speaker-adjudications、edit-boundaries、units、reviews、protected_ranges、keyframe-references、execution-handoff、handoff.md | 核心节点足以供 D2 选择；主线不成立退回 D1 |
| D2 Direct — Execution Package | 基于 Detail handoff 定最终选段与讲法；给 planned range / boundary ref 和允许的边界校准范围；把 planned range + safe windows 写入 timeline 的 d2_selection_snapshot；mockup→proof 可跨模型完成 | execution-plan、execution-reference（mockup + proof + 执行入口）、selected units、final narrative mapping、handoff.md | 方案确认；采用视觉设计时 Visual Gate=proof_confirmed |
| F Execute | **Step 0 只精校 D2 已选片段**：读取选段及 handles，按需精听 / 定向 ASR，校准真实音画 in/out、停顿 / 尾音 / 反应并把 selected boundary 升为 supported；语义冲突或校准超出 D2 snapshot 时返回 D2，不能换段。随后完成授权、timeline、预算、渲染与 QA | timeline（含 verified bounds / boundary refs）、transitions、render-manifest、edit-plan、rough-cut、handoff.md | schema 1.8+ 入选 boundary 必须 supported；当前 reviews / 对白 / source-time、Visual Gate 与授权均通过；预算守恒，再继续音画实看 |
| G QA & Handoff | 逐接点及全片复核，做 EVA 和 Reference Compliance，保存问题与缓存版本 | render-audit、接点图表、qa、handoff.md | 技术检查与人工观看分别记录，不以成功日志代替验收 |

## Structure 的两种密度

### 第一轮：Broad Structure

目标是**扩大覆盖并建立可回查的文字化结构层**。表单与分片段观察是基础；Content Map、情绪 / 关系大意是导航，不能替代表单或为预定选题补造证明。

- 全时段建立基础画面与台词覆盖；
- 对每张**已实际分析的抽样帧**按数据契约建立一行完整基础观察，含**原声要点及核听状态**、`change_from_previous`、**topic_judgment、confidence、confidence_basis**、interpretations 与 unknowns；
- `change_from_previous` 只写相邻**已分析抽样帧**之间实际可见的变化，不把中间未观察过程补成完整动作；第一张可写 `not_applicable`；
- 出现明显动作变化、视线 / 站位变化、物件交接、进入 / 离开等候选节点时，登记 `action-node-candidates.csv`，同时保留候选起止帧、最小有效单元候选、口型 / 说话线索与关系转折信号，围绕候选点建立默认 **4fps** 的局部高密度窗口；若因源帧率、工具限制或连续播放更合适而偏离 4fps，必须记录 `sampling_exception_reason`；
- 对理解场景或候选价值有实质影响的问题，登记 `structure-questions.csv`：保留问题、回答、回答状态、证据引用、未验证项和下一步核查；未回答的问题保持 `unresolved`，不能被 overview 或最终结论吞掉；
- 同时保留机器可追溯的 `frames.jsonl` 与人可读的 `frame-observations.csv`；后续创意阶段优先消费这些结构化表，而不是反复加载原始九宫格；
- 场景、人物、事件、关系变化和无声互动都保留入口；
- 形成 source-order overview 和跨场景 Content Map；
- Broad Structure 的正式交付包称为 **Structured Observation Layer**：`frame-observations.csv` + `action-node-candidates.csv` + `structure-questions.csv` + scene / segment 观察 + `overview.md`；`content-map.md`、情绪 / 关系线索和 usable bounds 是建立在这套文字化结构数据之上的导航层。第一次 Director 必须优先消费这套表单，而不是只读一份总结；
- 明确抽样、字幕 / ASR、连续音画核实三种 coverage 的差别；
- Broad 阶段发现片头卡、黑场、硬切尾、缺帧 / 缺音等物理边界时，在 `sources.json` 中登记 `usable_ranges` / `downstream_constraints`，并在 Content Map / handoff 显式传给 Direct，不能让编导对不存在的可用时长做承诺；
- 高成本长任务采用 **incremental output + resume + coverage accounting**：按已完成区间持续落盘基础表和 coverage；任务中断后从缺口继续，不因 agent / 工具静默结束而重扫已经完成且版本一致的多模态区间；
- 不把未处理区域悄悄排除。

### 第二轮：Detail Structure

目标是**只把已确认方案命中的节点重新压回原片证据**，把高成本观察集中在真正需要的区域。

- 先建立 `detail-intervals.csv`：写清精查区间、为什么进入精查、前情、当前背景、后续、内容摘要、目标问题（稳定 question ID）与主题关联；
- 按 [Detail 证据获取](references/detail-evidence.md) 取证：目标问题、最小完整单元、Edit Boundary、反证四项闭合后 **STOP DETAIL**；证据不足才升级密度，细动作不凭缩略图定案；
- 建立 `deep-observations.csv`，按数据契约填写全部字段；
- 写清这一核心区域**实际发生了什么**，并补充 setting_context、narrative_context、before_state、after_state；
- 从台词命中扩展到完整问答、动作链和必要前后文。声音默认 **字幕原话 + signals / 波形停顿优先**；只在原话、speaker / addressee 或叙事判断存在关键歧义时局部回听 / ASR。ASR 不要求覆盖整个 Detail 区间，也不是 Detail complete 条件；冲突和核听状态继续记录；
- facts、interpretations、unknowns 分开；每个核心观察保留 `topic_judgment`、`confidence` 与 `confidence_basis`，主题判定必须落到该帧 / 节点承担的具体叙事作用，不能只写抽象标签；检查反证、误读风险和时空关系；
- 形成 context_ranges、protected_ranges 与 Edit Boundary。Detail 对候选先给足以选择的保守 safe windows / handles；若最终声音尾部或逐帧切点尚无必要精校，可把 boundary 留为 `partial`，不为未入选候选做最终态精听。D2 真正选中后由 Execute Step 0 精校并升为 `supported`；字幕 / ASR 时间不得直接当最终切点；
- 被否决 / 未解决的目标问题列入 handoff 的 Question Closure Ledger；入选节点不得带 `unresolved`，带 `contradicted` 须有人工 `confirmed_by`；
- 如果 Narrative Direction 不成立，把具体问题返回 Direct 1，而不是直接替用户重写核心创意；如果证据成立，则随 Detail 固定交付 `keyframe-references.json`、可用真实图片和 `execution-handoff.md`；handoff 直接携带完整 Execution Package 要求。Director 2 再形成计划与制作参考，经确认后进入 Execute。关键帧失败要声明异常并继续，不能由生成图片冒充素材。

## 决策时读取

- 抽帧密度、批次、Content Map、第二轮定向回查和恢复：读取 [工作流程](references/workflow.md)；E 阶段取证、切点与问题闭环另读 [Detail 证据获取](references/detail-evidence.md)。
- 时间码、记录字段、Structured Observation Layer / Content Map / 两次 Direct 与时间轴关系：读取 [数据契约](references/data-contracts.md)。
- 换模型或 MCP、能力缺失、调用失败：读取 [MCP 适配](references/mcp-adapter.md)。
- D2 方法、Blender 工程、动态验证与 FFmpeg 回接：读取 [视觉制作](references/visual-production.md)。新模板 schema 1.9 的方法/合成确认、成片 QA 均由入口检查；不通过降 schema 或删除 policy 规避。
- 在已确认 Narrative Direction / execution plan 下保住完整对白、连续性与正确重组关系：读取 [重组与剪辑规则](references/montage-rules.md)。
- 首次出片或返工：读取 [渲染与工程检查](references/render-engineering.md)，按文字校准、时间轴编译、分层渲染、解码实测、全接点检查顺序执行。
- 交付前、移交另一模型：读取 [检查与交接](references/qa-handoff.md)。
- Structure 异常、Detail 交接与 Direct 2 完整输出：读取 [异常与执行包契约](references/execution-package.md)；视觉方案 / 兜底按 [Style System](references/style-system.md) → [Visual Router](references/visual-methods/index.md) → 命中完整方法 / fallback。少量 reference 锁整体风格，不要求逐项配对。
- 准备 Direct 2 执行记录、进入正式编译或接入渲染器：读取 [执行完整性契约](references/execution-integrity.md)，将采用证据与源版本绑定，明确 adopted_utterance_refs 和源音轨 review_refs；逐源音轨核对白保护及完整取段核听，包括卡片、未关联与异源仅音频。关联视频时另核同步；独立声音按成片放置核完整对白、政策原因及 track 级例外。continuity_type 不关闭保留对白政策；指纹计算不等于实际观察或人工确认。
- 续接、跨主体/模型、阶段内确认、依赖动作与交付：读取 [关口与续接控制](references/workflow-control.md)，沿用原阶段与审批边界。
- 每次改版或重新封装后：读取 [核心能力回归检查](references/regression-checklist.md) 与 [Structure 能力对照矩阵](references/structure-regression-matrix.md)，确认 Board/Broad / Detail / Direct / Execute 主线和基础信息层没有被弱化。

复制 `assets/` 中对应模板建立配置与各表：`project-template.json`、`frame-observation`、`action-node-candidate`（4fps 局部窗口）、`structure-question`、`detail-interval`、`deep-observation`、`speaker-adjudication`（本轮没有歧义也保留带表头的文件）与 `timeline-template.json`。Direct 用 `brief`、`narrative-direction`、`execution-plan` 模板（`editorial-plan` 为兼容模板，也可接入用户已有编导文档）；Detail 交接用 `keyframe-reference` 与 `execution-handoff`；Direct 2 另用 `execution-reference`；异常按 `structure-exception` 模板逐项保存为 JSONL；效率测量用 `benchmark-template.md`。

依赖动作前运行 `scripts/workflow_control.py guard 项目目录 --action 动作`；新模板默认启用，声音策略、Mockup、Proof 和两次 Direct 的缺项/失效会主动列出，授权草稿与正式渲染入口继续强制检查。再运行 `scripts/validate_project.py 项目目录` 核查证据。不具备 Python 时按同表静态检查并标未运行，不声称宿主已强制拦截。

进入实际渲染时，用 `scripts/compile_render_manifest.py 项目目录` 编译成片坐标与缓存键，再按 [渲染与工程检查](references/render-engineering.md) 使用 `scripts/audit_render.py` 实测导出并生成接点对照表。前者需要 Python；后者需要 Python 和 FFmpeg，拼图额外需要 Pillow。缺少能力就列明未验证项，不填通过。

## 每次工作结束

阶段结束与交接统一按 [workflow-control](references/workflow-control.md) 的 Next-Step Delivery Contract：生成当前 `handoff.md`，保留源版本 / `time_mapping` / 关键 source time 与已编译坐标；partial handoff 不算执行许可。接收方先恢复状态。同一项目保留稳定 ID，修订不得让旧引用悄悄指向不同素材。

---

## FILE: `references/workflow-control.md`

# 阶段内关口与续接控制

本规范把确认与核验要求集中为可检查的工程记录。A–G、两次 Direct、正式 CSV 表头不变；新制作项目使用 schema 1.9，含方法与合成确认，详见 [视觉制作](visual-production.md)。音乐确认仍属于 D2，不另造阶段。

## 1. 大块交接，块内主动提醒

| 大块 | 原阶段 | 默认交接点 | 块内已有要求 |
|---|---|---|---|
| Broad Structure | A–C | 正式观察层 + Content Map → Direct 1 | 来源、时间基准、覆盖与信息地板 |
| Direct 1 | D1 | 已确认 Narrative Direction → Detail | 核心命题、待核问题、范围与禁改项 |
| Detail Structure | E | 证据包 + 原片关键帧 + handoff → Direct 2 | 问题闭环、最小充分证据、反证、边界与异常 |
| Direct 2 | D2 | 完整 Execution Package → Execute | 音乐/音轨策略、Mockup、方法、Blender 工程与动态验证、Executable Proof、最终计划 |
| Execute | F | 实际成片 → QA | Step 0、最终范围授权、编译/渲染检查 |
| QA & Handoff | G | 已核验交付 | 实际播放、EVA、ReferenceCompliance 与未完成项 |

阶段内的确认在当前块处理；不要求每个小关口开新对话。用户主动跨模型、跨会话处理 Mockup 或 Proof 时，可交接未完成进度，但不能把 partial handoff 当作已满足 Execute 条件。

### 阶段出口的 Next-Step Delivery Contract

每个大块完成后，**必须先生成面向下一块的可独立交付 `handoff.md`，再前向 advance**。这是阶段出口文件约束，不新增用户审批 Gate，也不改变原阶段顺序。handoff 必须至少包含：当前大阶段与 Scope Lock、有效确认与 pending/stale 项、下一步、实际随附文件 manifest（路径 + SHA-256 + bytes）、`project.json` 状态快照 digest、以及 `sources.json` 中可用于跨机器重绑定的 `source_id / source_signature（或版本）/ time_mapping / locator`。

Detail 仍额外交专用 `execution-handoff.md`；总 `handoff.md` 负责把整个项目状态与随附文件清单交给下一主体。换机器时旧绝对路径只作 locator；接收方须按 source signature / time mapping 重新绑定源媒体，不能因为路径变化重建已确认状态，也不能仅凭旧路径继续精确执行。

`workflow_control.py handoff` 会把 `last_handoff` 写入 `project.json.workflow_control`。当前阶段的项目文件或随附产物在 handoff 后变化时，旧 handoff 自动视为过期；重新运行 `handoff` 后才能前向 `advance`。回退到较早阶段仍按原 `--reason` 规则，不要求先生成面向后续的 handoff。

## 2. 每轮续接循环

对同一长视频项目的“继续”“可以”“改这里”、确认或补充材料，先恢复项目，不依赖用户重新提示“还有哪个 Gate”。

1. 核对当前可用的插件/技能版本、项目目录或已交付的 `project.json`、四行 Scope Lock；读不到时说明具体缺口，不猜测阶段。
2. 具备 Python 时，采用新制作管线首次运行 `visual_pipeline.py init`（初始化关口并采用 schema 1.9）；旧管线只补续接控制用 `workflow_control.py init`，以后运行 `status`。不重扫素材、不自动确认旧决定；有效确认引用既有记录，不重复决定。
3. 按本轮反馈修改最小范围，重新计算受影响关口。已确认且输入未变的事项继续沿用。确认记录仍在，但状态可能因文件、音轨策略、视觉规则、选段快照或工具链变化变为 `stale`。
4. 到达依赖动作前运行对应 `guard`；关口未闭合时，主动展示具体方案/图片、现有确认来源或待确认项。无关工作可继续，例如音乐未确认时仍可整理文字；Mockup 未确认时不能直接去做 Proof。
5. 每个大阶段完成、交付、换主体、换对话、换模型或换机器前，运行 `handoff`，把本轮结果、未完成关口、实际随附文件 manifest 与源媒体重绑定信息一起带走。前向 `advance` 前当前阶段 handoff 必须存在且未因文件变化失效；接收方重读记录再推进，不能因一句“继续”清空待确认项。

内部每轮检查；对用户只在状态变化、需其决定、尝试受阻动作或交接时展开说明。普通修订不反复贴整张关口表，也不重复询问有效确认。用户说“可以”时，先对应上一轮已实际展示的具体方案及请求范围，再记录；不把它扩成之后所有环节的通用授权。

## 3. 工程状态与确认依据

唯一的机器状态放在现有 `project.json.workflow_control`。`handoff.md` 中的 Workflow Checkpoints 表由脚本生成，只是可读快照。不要另建 current-state、visual-style 或 music-gate 状态文件。

状态为 `pending`、`stale`、`satisfied`、`not_applicable`。确认记录保存真实决策者、既有确认文件/分节、原话摘录及当时输入指纹。脚本不会生成用户原话，不会自己确认，也不能认证记录中的人名或判断素材真伪。

声音策略写在 `workflow_control.audio_choice`：

```json
{
  "mode": "no_music",
  "description": "沿用本轮已确认的原声处理方案，不另加配乐；具体取段与参数见原计划。",
  "ref": "execution-plan.md#音轨与接点"
}
```

模式可用 `original_only`、`original_with_music`、`replace_music`、`no_music`、`silent`、`custom`；模式只是索引，实际方案及其原文引用都必须明确，不能只填“已确认”。`audio_policy` 仍按原契约填写。

`visual_spec_refs` 指向实际已展示的视觉规则，可用 `execution-reference.md#画面规则`、`execution-reference.md#文字样式`。优先分节绑定，避免改声音说明时使无关视觉确认失效；采用整份文件时，该文件任意变化都会重开相应确认。

Mockup 绑定真实样稿、视觉规则与输出规格；Mockup 确认后还必须生成 `implementation-lock.json`，把 renderer / element / crop / rect / font / color / motion 等直接执行参数，以及每个 selected REF 的 application trace 写死。Proof 另绑定真实 Proof、连续 demo 和实际可执行工具链。计划绑定 D2 选段快照、计划原文、文字及输出规格；原模板中的 Execute Step 0 记录区单独处理，允许范围内的精校记录不等于改写 D2 内容选择。实际越界仍由原 snapshot/boundary 校验拦截。

当视觉设计不适用时，沿用原 `visual_gate_status=not_applicable` 并明确 `visual_not_applicable_reason`。这不是遗失样稿时的豁免方式。

## 4. 命令与触发点

以下命令从技能目录执行；项目与技能安装目录分开。

```sh
python scripts/workflow_control.py init /path/to/project
python scripts/workflow_control.py status /path/to/project
python scripts/workflow_control.py guard /path/to/project --action make_proof
python scripts/workflow_control.py guard /path/to/project --action execute_handoff
python scripts/workflow_control.py guard /path/to/project --action authorize
python scripts/workflow_control.py guard /path/to/project --action render
python scripts/workflow_control.py handoff /path/to/project --output handoff.md
```

`guard` 在受阻时返回非零退出码，并输出关口、原因和下一步。其他动作包括 `broad_handoff`、`start_detail`、`detail_handoff`、`make_mockup`、`process_audio`、`qa_start`、`deliver_complete`。`advance --to D1/E/D2/F/G` 仅跨到相邻大块，并检查前一块出口；返回前块须 `--reason` 说明具体冲突。

新管线另有 `build_composition`：方向、Detail、声音、Mockup 和 method 确认后可做限定动态预览；`method` 校验视觉方案与当前 Implementation Lock 的绑定。`composition` 只绑定 `proof_composition_ids` 最小充分集合的实际工程、连续 demo 和已完成 review，且 renderer / element IDs 与 Implementation Lock 一致；其余 production composition 只在 plan 中冻结，最终授权后再一次性渲染，不要求逐段预先 demo。默认交互仍收敛为两个确认束：**D2 Design Lock** 可同轮登记 `audio + mockup + method`（完整 plan 已展示时可一并登记），**Production Proof Lock** 同轮登记 `proof + composition`（plan 尚未确认或已因 Demo 修改时一并登记）。确认束不是新 Gate；脚本仍逐项保存 digest / stale 状态。

对已经真实确认的事项登记来源，例如：

```sh
python scripts/workflow_control.py confirm /path/to/project --gates audio --actor user --confirmation-ref 'execution-plan.md#用户确认' --quote '保留原声，不加配乐。'
```

Mockup / Proof / Composition 属于**必须绑定实际展示文件**的视觉确认。登记时追加 `--shown-ref`，例如：

```sh
python scripts/workflow_control.py confirm /path/to/project --gates mockup method --actor user --confirmation-ref decisions.md --quote '当前 Mockup 的真实确认原文' --shown-ref mockup/current.png
python scripts/workflow_control.py confirm /path/to/project --gates proof composition --actor user --confirmation-ref decisions.md --quote '当前 Proof/Demo 的真实确认原文' --shown-ref compositions/C01/current-proof.png compositions/C01/current-demo.mp4
```

如果没有这些 artifact bindings，仅一句后续执行命令（例如“渲染视频”“继续”）不能补签未展示的 Mockup / Proof / Composition。

该句必须是实际已有原话且存在于指定文件；示例不是当前项目的用户确认。人或用户明确授权的 Director 才能作相应决定，模型/脚本不能自行填名代签。一次已展示且被明确同意的组合方案，可以一条真实确认记录对应多个关口；不将未展示的样稿、未生成的 Proof 一并确认。

## 5. 已接入的强制检查

项目使用 `workflow_control.schema_version=1.3` 与 `execution_policy.workflow_gate_control=required_v4`。运行 `workflow_control.py init` 初始化控制记录。准备授权草稿前，`prepare_execution_authorization.py` 检查声音、样稿、Proof、D2 与 Step 0。进入 `ready_for_render` 时，`validate_project.py` 检查所有执行前关口。

结构化状态和文件存在仅是第一层检查；真正跨大块或运行依赖动作还会复用原校验器，不能靠把 completed/confirmed 字段改成 true 绕开证据规则。

最终交付前，`qa` 关口还要求原 QA 项的实际记录、`final_playback_verified=true`、ReferenceCompliance 及无阻断问题。`workflow_control.render_output_ref` 指向真实输出文件；`qa.json.artifact_sha256` 绑定当前文件，成片变更后旧 QA 不算当前验收。渲染输出路径应在编译前登记，实际文件在渲染后核查。

## 5A. 视觉制作、确认与锁定

- **V0–V7 记录视觉设计链。** `make_mockup` 前 `reference_routing` 要求 V0–V2 checker PASS；V0 `design_scope` 控制探索强度：`reuse_confirmed` 必须绑定此前真实 V6/V7/confirmed-artifact，且图文关系、动效语言或几何策略变化必须回到 `explore_new`。V3 可先验证代表性关键帧；新风格 V5 必须提供同素材/同文案/同画幅 baseline vs candidate A/B；small-screen + do-not-transfer 保留，blur/blind 条件式。V6 绑定同一次真实 Mockup 选择及 shown-artifact hash；V7 锁定方案，所有 rect 必须在 canvas 内，并对长文字、多人、复杂背景等 difficult deferred 镜头要求实际成图与 QA。V2 全 `no_ref_needed` 时不强造 trace。进入 Proof 前，有 reference trace 的项目仍必须桥接到 Implementation Lock 的真实 element IDs 与可解析 parameter paths。
- **Implementation Lock 是 Mockup 的机器构造合同。** 它锁 renderer / entrypoint、元素、source role、crop / rect / font / color / z-order / motion 和 safe adaptation；composition plan 必须绑定同一 lock 与 `implementation_element_ids`，不能在 Execute 中把 `native_blend` 改成 `layers` 近似实现。
- **视觉确认必须绑定 shown artifacts。** `workflow_control.py confirm` 对 mockup / proof / composition 保存当前展示文件的 hash；后续一句“渲染视频 / 继续”不会自动补齐未展示 Gate。
- **Production Lock 是代表性 Proof + 全量 Composition Plan 的实现冻结。** Production Proof Lock 只要求 `proof_composition_ids` 中各代表性 Proof 已有真实工程 / demo / review；同时冻结完整 `composition-plan.json`、`implementation-lock.json`、Reference application chain、`execution-reference.md#Production Lock`、Visual Spec、Proof toolchain、Visual Methods、`delivery-spec.json`、`text_policy` / `voiceover_policy`。非 proof composition 的正式 scene / video 在最终授权后生成，不属于 Production Lock 的前置 demo。 但每个 deferred composition 必须先由 `proof_covered_by` 指向 `proof_composition_ids` 中某个 Proof，并通过 mode / Lock elements / methods / join 风险的机器覆盖校验。Execute 前重新计算设计输入；不同即 stale。

- **文字与旁白进入机器 Policy。** ready 前实际检查 glyph height / canvas ratio、creator text 行数、阅读速度 / stable hold；旁白轨只有 `voiceover_policy.allowed=true` 且 ref / description 明确时才允许。
- 这些检查只能约束经本技能官方入口消费的项目文件和 renderer；绕开入口的任意外部程序仍不受自动控制。


## 5B. 最小充分 Proof 覆盖

- `proof_composition_ids` 是一个非空、**最小充分**集合：同一实现族通常只选一个 Proof。任一 Proof 若被其他 Proof 按 mode、Lock elements、methods、join（native_blend 再加 native scene/dependencies）机械覆盖，Runtime 直接判为冗余；完全等价时保留列表靠前者。不要用多 Proof 重新制造“每段 Demo”。
- 只有机器无法从实现元数据识别的素材级风险，才可用显式 `additional_proof_exception` 增加一个原本会被判冗余的 Proof；必须写 reason + evidence_refs，且 evidence 会进入 shown-artifact 确认绑定。
- 每个 deferred composition 无论是否声明 `proof_scope_policy`，都必须写 `proof_covered_by` / `proof_coverage_reason`；Runtime 机械核对 mode、Implementation Lock elements、methods、join，以及 native_blend 的 native_scene_ref / native_dependency_refs。自由文本理由不能覆盖机械不一致。
- 最终 `CompositionCompliance` 不只点名窗口：每个 composition window 都必须有独立 `status: pass` + `finding`；含 join 的段另有 `join_finding`。四个身份字段仍与 render-manifest 精确绑定。validator 的具体错误必须透传到 QA Gate reason，便于直接定位哪一段填错。

## 6. Chat 的能力边界与降级

安装插件、插件对本轮可用、实际读入技能、执行工具可用是不同状态。`@` 是显式选用，不是每轮“解锁”；自动匹配也不等于每条消息强制执行。不能宣称普通网页 Chat 已被本插件的生命周期钩子拦截。

当前会话能读取文件但不能运行 Python 时，按同一关口表核查，随既有项目/交接记录保留确认依据，并明确这是模型静态检查、未执行脚本。文件也读不到时，只处理已知文字、指出需要重新选择插件或补齐哪份状态；不编造已恢复进度。不把本插件的普通提示写成宿主平台强制保证。

若某轮平台完全没有向模型提供插件与项目记录，插件本身无法在那一轮自行运行自检。跨会话采用显式 `@` 并带上最新 handoff；同一会话的续接由上述循环恢复，不要求用户每轮手工排查关口。

## 7. 插件未加载回合的项目托底

普通 Chat 的某一轮未挂载插件时，上述插件内循环也可能没有机会执行。长期项目应把插件根目录 `PROJECT_INSTRUCTIONS.txt` 的内容一次性追加到实际项目说明，再把 `CHAT_PROJECT_REFERENCE.md` 放入项目文件；仅把这两个文件留在 ZIP 中不会自动生效。项目说明负责持续提供关键要求，项目文件提供可读依据，检查脚本负责已接入入口的强制校验。三者不是同一层。

项目说明不新增平台能力：无法自动把缺失插件挂进每一轮，也不能强制执行模型未调用的脚本。无项目的普通 Chat，目前没有已核实的“插件逐轮永久绑定”开关，不以修改 default_prompt 冒充这一能力。必要时显式 @ 用来恢复插件工具；项目托底继续保留已知状态与关口。


## 方法保持与叙事参数补丁



同一项目的局部修订以最新确认的 Narrative、当前有效 Execution Plan 与已经确认的方法为输入。默认继承当前项目值；Skill 的初始默认值不覆盖已确认项目。先列参数补丁，再执行修改。叙事变化不自动解除方法锁，不重新挑字体、版式、图文关系、运动结构、声音策略或工具链。

方法合同继续放在 `visual-methods.json` 与 `implementation-lock.json`，由现有 `method` 确认建立。`safe_adaptation.allowed` 使用具名、带类型和数值上下限/字符串长度上限的 slot；`parameter_bindings` 把一个参数写入源映射到现有其他文件的精确字段。实际数值须一致，不能只登记相同 element ID。目标可声明固定 `format`，只支持一个 `{value}` 占位符，用于同步含参数值的说明；模板自身保持锁定，不能执行表达式。未声明字段及动效 easing、renderer、父子结构、字体资源、源/单元身份等保持固定。空 allowed 表示没有自动适配权限，旧版文字描述只作说明。

slot 的 `artifact` 支持 `visual-methods / implementation-lock / composition-plan / timeline / execution-plan / execution-reference`。JSON path 使用 `/methods/@method_id=PM001/parameters/scale_end` 一类稳定 ID，不使用数组下标、通配符或模糊匹配。Markdown 的可变文字必须在唯一的显式块中；块外文字、标点、空白保持原样：

```text
<!-- lvr:param T03.copy -->已确认文字<!-- /lvr:param T03.copy -->
```

对应 locator 为 `{"artifact":"execution-plan","path":"block:T03.copy"}`。没有块、块重复、目标缺失或绑定不一致时阻断，不扩大到整段重写。不默认把所有 parameters 字段视为可改；可调项须在本项目的方法决定中明确。

`workflow_control.method_preservation` 只登记一份当前 `method-baseline.json` 的指纹及最近一次补丁摘要。基线由 method 确认生成；plan 确认后同时覆盖两份执行 Markdown 和 timeline。基线保存上述文本/JSON，不复制媒体，不建立历史树。其方法指纹绑定原真实方法确认，不能靠改 baseline SHA 或普通 confirm 刷新来消除越界。回退 Plan 或重新 init 均不重置它。

更新 Narrative 后，准备一个本轮补丁 JSON（项目数据，不是额外安装文件）：

```json
{
  "schema_version": "1.0",
  "base_sha256": "<status 中 method_preservation.baseline.sha256>",
  "narrative_sha256": "<当前 Narrative 文件原始字节 SHA-256>",
  "instruction_ref": "decisions.md#本轮修改",
  "quote": "<该分节中实际已有的本轮指令原文>",
  "changes": [{
    "slot": "push_scale_end",
    "old": 1.08,
    "value": 1.10,
    "narrative_basis": "<当前 Narrative 中对应的原文>"
  }]
}
```

参数示例不是当前项目指令。每条补丁精确登记原值、新值和叙事依据，不额外添加字段。字段选择仍须忠实于真实指令；程序检查原文存在、版本、类型、范围、绑定与差异，不自动理解叙事或认证指令来源身份。

```sh
python scripts/workflow_control.py adapt PROJECT --patch PROJECT/requested-parameter-patch.json
```

工具仅写这些 slot 及其已声明绑定，验证固定方法未变，再推进当前基线。真正受影响的 composition 使用确定性的新输出文件名，既有工程和视频保留；不相关 composition 的输入指纹不因其他元素参数变化而失效。已验证 review 的文件内容及其实际输入作用域都未变时保留原审阅记录，不改写旧 findings；当前整体 Production Lock 与成片 QA 仍须按实际版本闭合。共享元素必须覆盖所有使用它的 composition 映射，不能漏改另一段。只存在时间轴上的最终文字改变，不自动重渲染未消费该文字的合成。

V0–V7 已按原规程完成新内容确认后，现有 `sync_visual_stage.py` 可同步新的 V6/V7 artifact 身份；它检查 V7 的固定视觉语法与执行方法未变，只更新可计算的图片/文件绑定，不重新选择方法，也不把尚未应用的 Narrative 标为已落实。字体、布局语法或运动结构确实改变时仍返回原 D2 方法决策。

合法补丁不代替创意确认、V0–V7、Step 0、执行授权或实际观看。方法合同未变时 method 确认保留；方向、选段、Proof、Production Lock、最终授权和成片 QA 按当前真实输入重算。参数超出允许区间、素材证据不成立或适配无法满足阅读/保护规则时，报告具体冲突并返回原有对应决策；已确认执行包的非参数内容修订使用下节 revise。

若指令明确只修改叙事表述、保留全部执行参数，可用空 changes，并写 `unchanged_execution_reason`；该理由必须逐字存在于 quote 中，不能由模型补造“不用修改”。无依据的空补丁不通过。 原 Step 0 校准仍可在已有 d2_selection_snapshot 窗口和许可内调整源端点，同步 locked 原声音轨并确定性更新帧坐标/预算；不允许借此改源身份、文字、增益或快照。Step 0 的 pending/completed 状态记录可更新，其余正文仍冻结。若校准影响已生成的 Proof，可用同一空参数补丁登记已获授权的技术更新，理由引用原 Step 0 指令，工具为受影响合成生成新输出名；Narrative 无需为了技术精校另改一版。

已有已确认项目先运行 init 补控制字段，再运行 `workflow_control.py adopt-method PROJECT`。只接受原 method 确认与当前旧版输入指纹仍完全一致的项目；已有 receipt 仅在旧输入、实际文件指纹和新片段输入投影都一致时接续，不能把变更后的工程当作未变。其他确认按原真实来源与已展示 artifact 重新绑定，无需因此重渲染未变工程。无法验证旧确认时，先恢复原有效文件，不能直接以当前文件覆盖基线。

确实需要改变方法时，先在干净状态返回 D2，使用下节 kind=method 的 revise 声明精确范围，再修改。现有 confirm 使用 `--gates method plan --method-change --base-sha256 <父基线> --diff-sha256 <实际差异>`，并绑定本次真实、不同于旧批准语句的方法变更决定。未开启范围的 method-change 不再接受。V0–V7、A/B 与 shown-artifact 规则继续生效。

补丁中断后所有依赖动作阻断。运行 `workflow_control.py recover-adaptation PROJECT`：已完整提交的事务只清理残留标记；未提交事务恢复补丁前原始字节。若文件或项目状态被另一任务独立修改，拒绝覆盖并报告冲突。基线与原确认、项目一起交接；不把运行时基线或旧输出积累到 Skill 安装包。


## 有范围的内容修订

已有具名参数继续用 adapt；未预设的文案、素材替换、剪短、顺序或段落增删用 revise。只在 D2 对已经 plan 确认的执行包开启一条 open_revision，位置仍为 workflow_control.method_preservation。执行资产必须与基线逐字节一致，Narrative 可以已经更新。原 Step 0 技术更新先通过 adapt 登记，再开范围。修改发生前声明；不能扩大、替换进行中的范围，不能先改后补。

范围由模型依据本轮真实指令起草。用户在原 plan 决定时看范围与实际 diff，不新增一次范围审批。示例（替换某合成的一张图片，保留视觉语法）：

```json
{
  "schema_version": "1.0",
  "kind": "content",
  "base_sha256": "<当前基线 SHA>",
  "narrative_sha256": "<当前 Narrative 原始字节 SHA>",
  "instruction_ref": "decisions.md#本轮修改",
  "quote": "<该位置实际已有的本轮指令>",
  "scope": [{
    "artifact": "composition-plan",
    "path": "/compositions/@composition_id=C01/layers/@layer_id=panel-a/asset_ref",
    "op": "replace"
  }]
}
```

```sh
python scripts/workflow_control.py revise PROJECT --scope PROJECT/revision-request.json
# 然后仅修改所列字段；其余继承当前项目值
python scripts/workflow_control.py revise PROJECT
python scripts/workflow_control.py confirm PROJECT --gates plan --actor ACTUAL_DECISION_MAKER --confirmation-ref decisions.md#本轮确认 --quote '实际已有的确认原文' --diff-sha256 ACTUALLY_DISPLAYED_DIFF_SHA
```

quote 示例不能当用户批准。开启修订时 `instruction_ref` 必须指向明确 Markdown 分节（`file.md#分节`）；修订专用指纹忽略该分节末尾空白，因此在后面另起确认分节不会让已展示 diff 失效，但全局 `artifact_bytes` 与其他 Gate 的分节指纹规则不变。关闭修订时 `confirmation_ref` 同样必须带 `#分节`，且不得复用修改指令分节或上一次 plan / method 的确认分节；整份文件引用不能用于关闭修订。相同的短确认文字（例如再次说“可以”）只有写在新的真实确认分节时才可作为新决定，引用旧确认分节会被拒。修改指令本身仍不能充当批准。报告逐条列 before、after、artifact、稳定 ID / path、op，以及 in_scope / derived / out_of_scope。存在越界即 LINEAGE_VIOLATION；不以方法变更吞掉内容漂移。status 也显示当前差异，指令、Narrative、受控文件或本轮范围变动后必须重新核对；旧 diff 的确认不能用于新内容。程序只核对精确范围和证据指纹，不判断指令语义、发言者身份或审美。

JSON 只用 event_id、text_id、track_id、composition_id、method_id、layer_id、join_id、key_id 等稳定 ID，禁止数组下标与通配符。replace 指向明确字段，开启时即拒绝对象或实体集合（如 /text_tracks），不要先开粗范围再尝试修改；add/remove 指向明确实体（例如 /compositions/@composition_id=C02）；重排使用 /events/$order 等精确位置及 op=reorder。ID 改名须明确 remove/add。没有稳定 ID 的非实体列表可按明确列表字段修改，报告完整 before/after。输出文件名只能由程序派生。

两份 Markdown 的普通字段用 `block:ID` 范围；执行计划的段落结构使用 stable Segment identity，不按任意标题或整段容器放开。新草稿将可变正文值置于唯一的 lvr:param 块，标题、字段标签和静态说明在块外；模板已带基础标记。建议每条文案独立块，如 TXT001.copy，不将整个计划套进单块。旧计划先开 kind=markup，仅声明待添加 block / container 标记的 op=add；移除新增标记后必须与旧正文逐字节相同，不得同时改字。经原 plan 确认迁移后，再用 kind=content 修改具体 block。

`execution-plan` 的 `container:plan.segments` 只作为结构边界，不再作为内容修订的宽权限。新增或删除段落必须逐项声明，例如 `segment:seg3` + `op=add`、`segment:seg1` + `op=remove`；没有声明的 Segment 既不能删也不能加，因而“删 seg1、换号加 seg9”会明确暴露为两条变化。`### Segment N` 后允许跟说明文字，例如 `### Segment 3 · 结尾余味`；说明文字属于该既有 Segment 的冻结结构，未单独授权不得改。**Segment 编号是身份，不是显示顺序**：在 Segment 1 与 2 之间插入新段时使用新的身份（如 Segment 3），允许显示为 1、3、2，不得为了顺序美观重排旧编号。标题写法不符合 `### Segment N` / `### Segment N · 说明` 时直接报 `invalid Segment heading format`，而不是伪装成其他段落越界。一级、二级标题仍必须在容器外。旧计划可先用 kind=markup 添加容器标记；模板 ID 采用 seg1.duration 等语义化名称，不自动改写已确认项目的旧编号 ID。

派生项只包括可精确计算的绑定同步、受影响合成新输出名、源区间/顺序变化后的 assembly 帧坐标及守恒预算。工具可填入这些值；手填值既不等于旧值也不等于精确结果时阻断。不是所有时间变化都自动派生：动效重排、阅读停留、音轨/文字取段、接点类型和 D2 snapshot 变化必须分别列范围，并继续接受原完整对白、素材证据、阅读政策及授权检查。复用底层 timeline_math，不扩大 Step 0 窗口。

方法指纹与实例输入分离：普通图片/视频素材、文案、事件范围、片段长度不定义新方法；renderer、mode、字体、原生工程依赖、元素/父子结构、变换与 easing 等保持锁定。确认基线保存一份已批准的合成语法 catalog，增删复用同一语法的实例不改变方法；新语法使用 kind=method 和原 method+plan 决定。safe_adaptation 的类型/限值与绑定合同仍执行，不因 revise 自动放宽。

实例内容仍进入各合成 job_input。增删复用同一语法的实例时，工具还派生同步其实际参数绑定目标，避免下一轮 adapt 漏掉新实例。开启修订时核对并封存可复用 receipt / review 的实际作用域，提交时只为受影响合成换新输出名，旧工程、视频、审阅原文保留；共享输入发生变化时所有真实消费者失效。整体 Production Lock、执行授权和最终 QA 按真实输入重算，plan 确认不代表已具备执行证据。

open_revision 存在时，编译、Proof 生产、渲染、授权和 QA 执行均阻断，不能交错运行 adapt 或机械视觉同步。提交复用原 .applying 事务恢复；中断时 recover-adaptation 恢复提交前的进行中状态，或收尾已经完整提交的状态。未改动的范围可用 revise --cancel 取消；有改动须先恢复受控文件，取消不丢弃他人的编辑。运行项目继续只有一个当前基线和最近摘要，不建版本树、不复制媒体、不新增永久状态文件。

### 修订来源与 Segment 身份保护

新修订的 `instruction_ref` 与关闭时的 `confirmation_ref` 都必须绑定 Markdown 分节。修订指令仅在本地 revision 指纹层忽略末尾空白，保证后续另起批准分节不会改变已展示 diff；其他 Gate 的 artifact 指纹不变。关闭时拒绝整文件引用、原指令分节和旧 plan / method 确认分节。出处按实际文件和解析到的标题位置比对，等价路径和标题锚点指向同一分节。

段落结构不再接受 `container:plan.segments replace` 作为宽范围；新增/删除必须逐个使用 `segment:segN add/remove`。解析器接受 `### Segment N · 说明`，并把 N 视为身份而非顺序；已有标题说明和静态结构继续冻结，非法标题直接给出格式错误。

### 修订预览的静态校验

revise 开启时保存现有 validate_project 非渲染校验的错误清单。每次预览以当前实际资产和程序计算的派生 JSON 值运行同一校验器，报告 baseline_errors、errors、new_errors、resolved_errors；按错误多重集合比较，仅新增错误阻止关闭修订，既有待办继续显示。校验不要求渲染或当前授权；正式执行入口仍运行原完整 guard，没有新增可关闭 guard 的项目字段或 CLI 开关。

剪短后受保护意义区间被删、音轨/文字越过事件或成片范围，均须在预览中解决。修订保持进行中，基线与确认不推进。校验输入文件的指纹也进入本轮 diff；提交前再次核对，不能用旧检查结果接受后来变动的证据。

合法 adapt 不再额外重开已满足的 plan：工具仅对起步时 satisfied 的计划继承其真实 actor、confirmation_ref、quote，用 adaptation.parent_input_digest 与 patch_sha256 绑定确定的参数补丁，并更新派生输入指纹。没有有效 plan 时不创建或修复批准；方向、Proof、Production Lock、授权和 QA 仍按实际输入失效。非参数修订继续必须展示 diff，再由独立的新真实 plan 确认关闭。


## Proof 成本与显式豁免

Proof 的职责是验证代表性实现风险，不是提前制作正式成片。`composition-plan.json` 使用 `proof_scope_policy=representative_risk_based_v2` 时，`proof_composition_ids` 对应作业必须标记 `delivery_role=proof_only`，不会进入最终 render manifest；其余作业标记 `delivery_role=delivery`。动态 Proof 默认限制在约 3 秒，只有存在机器覆盖关系无法表达的连续动态风险时，才允许通过 `full_length_proof_exception` 扩大。

用户明确要求跳过 Proof 时使用 `workflow_control.py waive-proof`，状态写为 `visual_gate_status=proof_waived`，并保存真实决策人、确认文件、逐字 quote 和理由。该状态只豁免代表性 Proof 的生成与人工审阅，不得写成 `proof_confirmed`，也不得补造 playback/review 记录；Method、Plan、Production Lock、Selected Ranges、Execution Authorization、正式渲染与最终 QA 仍然必须通过。

---

## FILE: `references/workflow.md`

# 工作流程

## 总体路径

本流程不是单向的“结构化 → 自动选题 → 剪辑”。标准路径是：

```text
A 素材登记
  ↓
B Broad Structure：全量粗覆盖
  ↓
C Structured Working Layer + Content Map
  ↓
D1 Direct：Narrative Direction（人 / Director 确定叙事主线）
  ↓
E Detail Structure：围绕主线回原片做高密度补查
  ↺ 证据不足 / 主线不成立时返回 D1
  ↓
D2 Direct：Editorial Execution Plan（基于核实证据形成最终执行方案）
  ↓
F Execute：时间轴与渲染
  ↓
G QA & Handoff
```

第一次 Structure 追求**广度 + 紧凑表示**：正式产出逐抽样帧 / 分片段观察表、动作节点、Q&A、scene / overview 等文字化结构数据，并在其上形成 Content Map；第一次 Direct 只负责确定 Narrative Direction。第二次 Structure 追求**与已确认 Narrative Direction 相关的证据深度**；Detail 完成后必须再次回到 Director 形成 Editorial Execution Plan，之后才进入 Execute。不要在第一轮为某个主题过早押题，也不要把第二轮证据直接当成最终剪辑方案。

Structure 字段无法取得时，保留原 schema 并明确异常后继续可做部分；E 随证据交付关键帧和独立 handoff，D2 输出完整 Execution Package。具体字段与样式参考规则见 [异常与执行包契约](execution-package.md)，不增加阶段。

## 任务与默认值

接收视频文件或授权地址、已有九宫格、字幕、转写和分析文档。优先复用已完成工作，但先核对它们对应的源视频版本与时间轴。用户只提供九宫格时可以建画面索引，不能据此交付已核实的对白剪辑。

配置必须写明：素材范围、目标人物（如有）、已知目标或开放 Structure、是否限同集、成片比例和时长、原声与配乐要求、已有底稿、交付目标、可用工具。未知项写 null；对不影响前期建档的缺项先继续工作。无指定时，以同集为优先、保留原声、只用必要解释文字；时长和比例不擅自写成用户已确认要求。

`deliverable=content_map` 时，默认目标是完成 A—C，并正式交付 Structured Observation Layer + Content Map，而不是只交一份摘要。`deliverable=detailed_plan` 或更后续产物时，进入 E 前必须取得第一次 Direct 的 Narrative Direction；E 完成后，进入 F 前必须取得第二次 Direct 的 Editorial Execution Plan。两者都可以来自用户或独立研究 / 编导环境。

已有 brief 可以在 Broad Structure 阶段作为重点标记，但不得让第一轮覆盖只剩关键词检索。Structure 的价值之一就是扩大人的可见范围，并把昂贵的多模态上下文压成可反复复用的表格 / 文本层，让后续 Direct 不被最初假设锁死，也不必在每次创意讨论时重复读取原视频。

默认不主动渲染。只有明确要求或任务已包含试剪时才调用渲染；下载、上传、付费和访问私有资源均受当前环境授权约束。不得发布、发给他人或覆盖源视频。

## A 素材登记

为每个源文件建立 source_id，记录文件位置、可取得的版本标识或哈希、时长、流起点、分辨率、帧率信息、是否可变帧率、音轨和字幕。拿不到元数据时标记未知，不从文件名推断集数或版本。

项目时间基准采用原文件从首个展示时刻起算的非负毫秒；保留容器原始 PTS 与项目时间的映射。合集切出单集、代理文件、音轨分块都记录原片偏移。若转换并非线性偏移，保存完整映射，不能直接套加法。

### 时间标签稳定性（全流程硬约束）

`source_id + source timestamp/range` 是 Structure 的 canonical time tag。九宫格格号、抽样序号、ASR 自带时间、代理文件时间、字幕文件时间和 `display_timecode` 都只是派生定位，不得成为新的事实主键。画面、硬字幕、ASR、原声核听、动作节点、问题、Detail observation、unit 必须能无歧义回到同一源时间。

进入 Execute 后才新增 assembly / output frame 坐标，并通过 `anchor_event_id + local_*_frame` 或明确 output 坐标与源时间建立映射；不得反过来用成片时间覆盖源证据时间。源版本、代理偏移或 `time_mapping` 改变时，所有依赖精确时间的字幕、音轨、切点、缓存和 QA 锚点必须失效重核。

字幕先抽查开头、中段、末段与原声的对应。不同版本可能出现片头长度差、删减或累计漂移；只有验证为恒定偏移时才能整体平移。候选段字幕必须局部复核。无法听音时只能记“未核对”。

## B Broad Structure：全片概览

画面和台词分别扫描，再按同一时间轴合并。不要只按台词关键词找候选，否则会漏掉等待、递东西、回望等无声互动。

下表是第一轮可调试的参数，不是质量保证或平台限制。

| 参数 | 起始建议 | 调整条件 |
|---|---|---|
| 分析批次 | 以场景为主，必要时每五至十分钟分批 | 依据图片数、分辨率、上下文和服务时长限制缩小 |
| 批次边缘 | 先取前后各十五至三十秒辅助语境 | 一轮对话仍跨界时继续扩展到事件边界 |
| 概览抽帧 | 镜头代表帧加长镜头约五至十秒补帧 | 快动作、遮挡、无声互动或不确定处增加 |
| 第二轮精查抽帧 | 按内容定密度（0.5 / 1 / 4fps） | 见 [Detail 证据获取](detail-evidence.md)；切点用逐帧条 |
| 动作节点局部窗口 | 默认 4fps | 用于 Broad / Deep 中发现的动作、视线、站位、物件交接等变化节点；偏离 4fps 必须记录原因 |

九宫格是展示方式，不等于分析时间单位。按已验证能力抽帧，每格保留 frame_id、source_id 与实测取帧时间；从左至右、从上至下按时间排序。跨场景清楚标记。保留原分辨率单帧；文字或表情看不清就读取单帧或放大，不能凭缩略图补写。

**否定性事实的举证门槛：**稀疏抽样只证明“这一张没有看到”，不证明“整个机会窗口没有发生”；**4fps 也只是局部加密观察的起点，不是区间级否定结论的充分证据。**任何 `没有开门 / 没有说这句话 / 没有出现该物件` 等 negative claim 必须先限定明确的 source-time 观察范围，再按事实类型完成核验：视觉动作 / 物件是否出现，需连续视频 review 覆盖整个机会窗口或有能直接排除该事实的可靠反证；某句话是否说过，需连续原声 review 覆盖所声明区间或有直接、可回查的反证。密集抽帧可以触发进一步核验、缩小窗口或支持“该采样点未观察到”，但不能单独证明整个区间内没有发生。条件不足时只写 `not_observed_in_sample` / `unknown`，不能进入 facts。

每张已分析抽样帧都要留下两层记录：

1. `frames.jsonl`：机器可追溯证据，保留 frame_id、真实时间、image_ref、facts、unknowns；
2. `frame-observations.csv`：面向人工 / Director / 其他 Skill 的**基础结构化观察表**。每个已分析 sampled frame 一行。除定位外，至少覆盖 frame_id / frame_name、timestamp_ms / frame_end_ms、characters、visual_facts、visible_action_state、observed_emotional_cues、expression_gaze、spatial_relationship、setting_background、key_objects、motif_tags、visible_text、**original_audio_keypoint / audio_verification_status**、nearby_dialogue_refs、content_description、change_from_previous、**topic_judgment、confidence、confidence_basis**、action_node_candidate_ids、speaker_adjudication_refs、interpretations、unknowns。可复制 `assets/frame-observation-template.csv`。

这张表不是九宫格的重复说明，而是把“每一张已看过的抽样帧里真正有什么”变成人可浏览的基础层。**基础层不得被 overview、Content Map、最终文案或剪辑建议替代。** `visual_facts`、`visible_action_state`、`motif_tags`、`visible_text`、`original_audio_keypoint`、`audio_verification_status`、`change_from_previous`、`content_description`、`topic_judgment`、`confidence`、`confidence_basis`、`unknowns` 必须有显式值；没有内容时写 `none` / `unknown` / `not_applicable`，不能留空。相邻帧间的动作只能作为待核实假设。请求“逐帧文档”时说明这里是逐抽样帧记录，并列抽样规则，不声称看过每个视频帧。

`frame_end_ms` 用于保留该观察帧 / 观察切片的尾边界；能取得真实帧时按真实帧时长记录，只有静态抽样点时按提取工具给出的观察边界记录并在 coverage 说明。`original_audio_keypoint` 记录该帧附近真正可归属的原声要点；没有核听就写 `not_verified`，不能把字幕文本冒充原声。`topic_judgment` 必须落到该帧 / 节点为什么值得后续检索或承担什么叙事功能，不能只写“甜”“虐”“高光”等空标签；`confidence` 必须和 `confidence_basis` 同时写，例如 `high(frame_evidence)` / `medium(subtitle_only)`。

`change_from_previous` 只比较相邻**已分析抽样帧**：人物进入 / 离开、视线变化、站位变化、物件状态变化、字幕变化、镜头 / 光线明显变化等都可记录，但不能据此补写中间动作过程。`motif_tags` 用于低成本导航重复意象 / 行为 / 空间线索，例如“门 / 离开”“回望”“等待”“共同物件”；它只是索引标签，不等于已经确认象征意义。

### 动作节点候选与 4fps 局部窗口

Broad Structure 或 Detail Structure 发现明显动作变化候选时，写入 `action-node-candidates.csv`（可复制 `assets/action-node-candidate-template.csv`）。每个候选至少记录 trigger_frame_id、候选起止帧、center_timestamp_ms、trigger_reason、change_signal、window_start_ms / window_end_ms、sampling_fps、最小有效单元候选、口型 / 说话线索、关系转折信号、topic_judgment、confidence / confidence_basis、evidence_refs、verification_status 与 unknowns。

默认在候选节点附近使用 **4fps** 局部窗口（0.25 秒采样间隔）观察动作起点、过程、回应与结束；对真正影响切点、口型或关系转折的节点，允许进一步细化到约 **0.1–0.5 秒颗粒**，但必须由连续画面或更密采样支持；窗口长度按事件完整性决定，不强制固定秒数。源帧率不足、工具限制或连续播放更适合时可以偏离 4fps，但必须写 `sampling_exception_reason`。动作候选是“值得加密观察”的导航，不自动升级为已验证动作链。

### 结构化问题回答与未验证项

凡是会影响场景理解、Content Map、Narrative Direction（或 legacy rough plan）或剪辑意义的问题，都写入 `structure-questions.csv`（可复制 `assets/structure-question-template.csv`），至少保留 question、answer、answer_status、evidence_refs、unverified_items、next_check。answer_status 使用 `supported / partial / unresolved / contradicted / not_applicable`。没有证据时保持 unresolved，不允许用最终总结把问题吞掉。

机器检测的镜头切换先作为技术边界。同一轮正反打通常仍属于一个场景；闪白、运镜和灯光变化可能需要人工复核。保留检测原结果及调整结果，不用算法切点直接决定叙事单元。

coverage 分别记录画面抽样、字幕或转写、连续音画复核的时间区间与状态。全时段完成抽样不等于全时段实看。任何未处理、失败或低清区域都保持可见；特别记录片头片尾是否有正片内容。

Broad Structure 的完成条件不是“已经知道该剪什么”，而是：素材主要时间范围已经建立基础索引，场景和对白可以回查，coverage 与 unknowns 清楚；`frame-observations.csv` 与 `frames.jsonl` 一一对应；动作节点候选文件与结构化问题表已生成（没有候选 / 问题时也保留带表头的空表）；基础字段没有被摘要或 Content Map 替代。基础层实际完成后才记 complete；字段 / 产物无法取得时保留结构、报告异常与 coverage 缺口，再继续可做的整理、草案和交接，不能为完成状态补造观察。

### 可用素材边界与长任务 checkpoint

Broad 扫描发现片头 / 片尾卡、黑场、硬切尾、缺失音轨、代理缺段或其他物理边界时，不只在 overview 里提一句：在对应 `sources.json` 条目登记 `usable_ranges` 与 `downstream_constraints`，明确哪些源时间真正可用于后续设计。Content Map 和 handoff 必须把会限制下游分段时长、结论段、J/L-cut 或音频处理的边界传给 Direct。

长时间抽帧、分析、转写和并行任务采用 checkpoint 纪律：基础产物增量落盘，`coverage.json` 同步记录已完成 / 未完成区间；任务中断后按版本、区间和输出完整性从缺口续跑。子任务或 agent 静默结束后先核对落盘数量与 coverage，不因为“没有最终回复”就重做已经可靠完成的部分。具体每多少项落盘、使用什么脚本语言由环境决定，不写死。

## C Structured Working Layer + Content Map：正式文字化结构输出

C 阶段不是把 B 阶段表格“总结掉”，而是把 Broad Structure 的文字化结构数据整理成 Director 可以直接工作的正式交付包：逐抽样帧观察表、动作节点候选、结构化 Q&A、scene / segment 级观察、source-order overview，以及在其上形成的 Content Map、情绪 / 关系线索和 usable bounds。

先写场景事实：人物、地点、可确认的剧情时间、进入时的状态、动作与对白、离开时的状态。再写解读与候选价值。场景可以覆盖多个不连续镜头；交叉叙事需记录多个源区间，不假装它们是一个连续事件。

将跨批次同一对话合并。用 source_id、区间和证据 ID 去重；不要因重叠读取把同一个动作算成发生两次。

`overview.md` 保留 source-order 导航：事件顺序、关系变化、重复线索、未确认事项，每一项链接 scene_id。它不能替代台词原文、`frames.jsonl`、`frame-observations.csv` 和场景卡。Content Map 中的重要线索应能继续下钻回 scene，再下钻到具体 frame / utterance / review，而不是只剩摘要。

同时生成 `content-map.md`。它面向后续人工 / Director，不按源时间顺序机械罗列，而是在不丢证据链接的前提下提供可横向浏览的素材面，例如：

- 人物 / 关系及其变化节点；
- 重要事件和重复出现的行为；
- 可检索对白主题和原声位置；
- 无声互动、物件、空间和动作线索；
- 前后呼应、潜在对照、尚未确认的关联；
- 每项对应 scene_id / source range / evidence refs；
- coverage 缺口和 unknowns。

Content Map 可以提示“这里可能值得继续看”，但不把这种提示写成已经确认的编导结论。

建立初步 unit。每个 unit 必须是同一源文件中的连续区间；若跨源或不连续，拆成多个 unit 并用 scene_id 或后续 plan_id 关联。第一轮 unit 可以较粗，记录可取范围和回查语境范围；`protected_ranges` 可以等待第二轮核验后补齐。unit 没有固定秒数。

如果 `deliverable=content_map`，A—C 完成后就是合法终点。交付时明确哪些内容来自抽样、字幕 / ASR 或连续音画实看，不为了进入后续流程强行生成创意主线。

## D1 Direct：Narrative Direction — 先决定“到底讲什么”

第一次 Direct 是创意层的第一次决策，默认在仓库之外的独立研究 / 编导工作区完成。它消费的是 **Structured Observation Layer + Content Map**：正式表格、scene / segment observations、overview、情绪 / 关系线索、usable bounds，并可叠加行业 / 主题研究、平台语境、参考案例与人工经验。

第一次 Direct 的输出重点不是精确剪法，而是：

- 核心命题 / 观看关系；
- Narrative Spine；
- candidate regions / scenes；
- 每个 spine node 的大致功能；
- 需要 Detail Structure 回原片裁决的问题；
- 已确认的人工判断、禁改项和允许调整范围。

可使用 `assets/narrative-direction-template.md`。已有 rough editorial plan 也可作为兼容输入，但进入 E 前要明确哪些内容属于 Narrative Direction，哪些只是尚未被素材证明的假设。第一次 Direct 不要求精确时间码；已有时间码只作 locator。

把 Narrative Direction 映射到 Content Map：每个 narrative node 链接已有 scene / unit / evidence；没有对应项的节点登记为 evidence gap。不要为了让主线看起来完整而把弱证据升级为事实。

如果用户明确授权本 Skill 辅助 brainstorming，可以给出基于 Content Map 的建议，但要与外部研究、人工判断和后续执行记录分开。默认情况下，不自行替代人的主线判断。

## E Detail Structure：带着 Narrative Direction 回原片

这是第二轮 Structure。它只对 Narrative Direction 命中的区域重新消费高密度多模态信息，目标是把第一次 Director 的主线问题变成完整、可回查的证据包；它本身还不是最终执行方案。

### Detail 区间卡：先把精查对象说清楚

在任何高密度抽帧或连续播放前，先生成 `detail-intervals.csv`（可复制 `assets/detail-interval-template.csv`）。每个核心区间必须写清：为什么进入精查、前情、当前场景 / 关系背景、后续、这段实际内容的粗摘要、要回答的问题、与当前主题 / plan node 的关系、证据与 unknowns。

**区间卡不是脚本文案。** 它的作用是让后续 Detail Structure 知道“从哪里看、为什么看、要裁决什么”，避免直接拿 Narrative Direction / legacy rough plan 的目标倒推原片。前情 / 背景 / 后续不清时写 `unknown`，不能省略。

对 Narrative Direction 中每个节点重新回到原素材，不仅复用第一轮摘要。第二轮的顺序是**先重新把核心区域看完整，再决定怎么剪**：

- 优先从 Broad 已知事件边界与目标问题的最小必要语境开始；边界未知时前后各五至十五秒起步，仅在指代、条件、动作因果或反证仍不清楚时扩到完整事件，必要时追溯前后场景或前集；
- 读图、升级与切点方法见 [Detail 证据获取](detail-evidence.md)；动作起止、反应链、停顿和声音关系用逐帧条、连续播放或等价能力确认；
- 建立 `deep-observations.csv`（字段与枚举见 [数据契约](data-contracts.md)）：把 visual facts / action chain、setting 与 narrative context、可观察情绪线索与谨慎解释、内容说明、字幕 / 原声状态、speaker adjudication、before / after、问题 / 反证 / unknowns、topic judgment / confidence 和 plan node 分开记录；计划功能不能反向污染事实。
- 声音默认 **subtitle + signals / waveform first**：已有可靠字幕先用于语义定位，signals / 有声区间用于找停顿与回听点；只有会改变当前叙事判断的原话、speaker / addressee、重叠说话或字幕冲突才做局部原声核听 / 定向 ASR。Detail 不等待整段 ASR，也不以全量转写作为完成条件；
- **证据冲突不使用机械总排名。** 视觉动作优先连续原画；“实际说了什么”由清晰原声核听与可靠官方硬字幕相互校验；speaker / addressee 结合口型、连续原声、可见人物关系与字幕信号。ASR 是定位和候选证据，方言 / 强口音默认 `locator_only`，未经核听或硬字幕核对不得写进台词 facts。任何冲突保留在 `subtitle_asr_conflicts` / `speaker-adjudications.csv`，不能选择一个方便 plan 的版本后删除冲突；
- 第二轮同样遵守 negative evidence rule：没有在抽样里出现的动作只能算 `not_observed`；4fps 或更密抽样仍不能单独证明区间级“没有发生”。视觉否定结论要覆盖完整机会窗口的连续视频，语音否定结论要覆盖声明区间的连续原声，或存在可直接排除该事实的可靠反证。
- 检查 Narrative Direction 可能忽略的反证、玩笑语境、时间差、关系阶段和异场反应；
- 在上述内容理解完成后，再把第一轮粗 unit 收敛为可剪 unit，确认 context_ranges、protected_ranges、isolated_use_risk 和 verification；
- **建立 Edit Boundary / Continuity Layer**：对候选先给足以供 D2 选择的内容范围、保守 preferred in/out、safe windows、must-keep ranges、handles 与 cut risk。若最终音频尾部或逐帧切点尚无必要精校，可保留 `boundary_status=partial`、相关精确值写 `unknown`；未入选候选不为完整度做最终态精听。字幕 / ASR 时间只作线索；
- **STOP DETAIL**：目标问题已裁决、最小完整互动 / 动作单元已找到、Edit Boundary 可用、足以改变结论的反证与必要前后文已检查后，停止继续加密读取。不得为“保险”或填满字段重复取证；仍 unresolved 时记录具体 next_check，不无限扩查。
- 为接续关系准备连续性、比较、倒叙、章节变化等依据。

记录审阅者身份或能力来源、时间范围和结果。只有文件实际被读取不等于被看懂；音频抽取成功也不等于原声已核听。不能处理音频或连续视频时，请有能力的工具或用户核查；同时继续可做的索引和草案。

### E 的关键帧与跨模型 handoff

随 Detail 固定交付 `keyframe-references.json`、真实原图与 `execution-handoff.md`，参见 [执行包契约](execution-package.md)。图片只作素材视觉依据；失败时声明异常并继续可做部分。handoff 携带已确认主题、源区间、证据 / 保护范围、文件入口、下游 Execution Package 要求，并引用 `capability-map.json` 中实际使用的分析工具与最终 Execute 可访问的执行工具映射。接收模型无需安装本 Skill 即可继续；此处不替 D2 作视觉决定。

### 何时返回 Direct 1

以下情况不要直接进入 Execute：

- Narrative Direction 的关键节点在原片中没有足够证据；
- 原台词含有被计划忽略的否定、条件或玩笑语境；
- 计划把不同事件误当成同一问答或即时反应；
- 某个段落功能需要的素材不存在，只能靠强解释文案弥补；
- 新发现的前后文会改变核心表达。

此时输出具体 evidence gap、冲突证据和可替代素材，返回 D 调整。允许多次 D ↔ E 循环。不要因为已经投入精查成本就强行保留原计划。

## D2 Direct：Execution Package — 再决定“最终怎么讲”

E 阶段完成后，不直接进入 Execute。以独立 handoff 把 `detail-intervals.csv`、`deep-observations.csv`、speaker adjudications、verified units、context / protected ranges、counterevidence、evidence gaps、source-time refs 和真实关键帧交回 Director；直接附上后续执行包的必需组成，不能依赖同一环境的 Skill 上下文。

第二次 Direct 基于**已经核实的材料能力**形成完整 Execution Package，其中 Editorial Execution Plan 至少明确：

- 最终选择 / 排除的 verified units，并为采用片段给出 **planned selected range + boundary ref**；D2 可授权 Execute 仅在该 boundary 的 safe windows / handles 内做边界校准，不能借此换段或改叙事；
- 段落顺序与每段 narrative function；
- 必须完整保留的对白、动作、反应与 protected ranges；
- 原声 / BGM / ambience / 文字的处理策略；
- 总时长与各段分配；
- 转场 / 时空提示等执行意图；
- 可替换范围、允许执行层调整的边界、不得改变的核心表达。

按 [执行包契约](execution-package.md) 先用真实关键帧做 **Aesthetic Mockup** 选审美，再由最终 Execute 可访问的实际工具链生成 **Executable Proof Frame**。两步可跨模型 / 会话；`capability-map.json` 是工具来源，proof 与正式 Execute 必须沿用同一执行能力、入口和资源。做不到时 Gate 保持 open：调整 mockup，或正式更新 capability-map / reference 后重做 proof。

逐条文字与锚点写入计划。采用视觉设计时，`visual_gate_status` 可停在 `mockup_confirmed / awaiting_proof`，但只有 `proof_confirmed`（或 `not_applicable`）才进入 F Execute。其余 ready_for_render 门槛不变：Broad / Content Map / Detail 完成、两次 Direct confirmed、文档存在、render_authorized=true；每个入选 source event 仍须绑定实际采用的 Deep observation 与 edit boundary，默认切点落在 safe windows 并覆盖 must-keep ranges，越界须显式 override + 理由 + review refs。

## F Execute：执行与粗剪

输入为 Source Clips + Detail Structure + execution-plan + execution-reference + Constraints；Execute 只落实已确认方案。采用视觉设计时，Visual Gate 必须 `proof_confirmed`，并沿用 proof 的工具链、entrypoint 与资源，不再看 mockup 自由发挥。

### Execute Step 0 — Selected Range Verification

D2 可在另一模型 / 会话完成，锁定采用片段、planned range、boundary ref 与允许校准范围，并把 planned range + 当时 safe windows 写入 timeline 的 `d2_selection_snapshot`。回到实际执行环境后，仅读取**入选 range + handles**：subtitle + waveform / signals 先定位，按需精听 / 小窗口 ASR，校准 video/audio in/out、句尾、关键停顿、尾音 / 反应和必要 J/L-cut；补齐同一 boundary 的精确值与 review evidence，并升为 `supported`。schema 1.8+ 入选 boundary 未 supported 不得 `ready_for_render`；Step 0 超出 snapshot 允许范围时停止并返回确认，不由 Execute 自行扩张。

Step 0 只能校准边界；若原话、主动方或上下文与 D2 选择冲突，返回 D2，不自行换段。精校后再按最终取段准备 / 确认 execution-authorization。

随后读取“渲染与工程检查”，完成 **duration budget ledger**：源片段按目标 fps 使用**累计时长统一量化**确定 assembly 边界，不允许每段各自四舍五入后再相加；validator 与 compiler 必须共用同一套累计量化与 overlap 计算。再以累计量化后的事件帧数求和，减去相邻 transition overlap，得到预计成片帧数；黑场卡 / freeze / hold 等真正新增时间必须作为事件计入，普通覆盖式文字停留不单独加时。若文字阅读时间放不进现有画面，必须在结构层显式延长事件、加 card / hold、减字或调整别处预算，不能把文字时长重复加到总长。预算未对平不得标记 ready_for_render。

随后按反馈类型先判断失效范围，再动文件：纯文字层反馈只重烧文字层；声音策略改变失效音频 + final；切点 / 段长 / 转场改变重新编译 timeline 并使所有依赖坐标的下游失效；核心主线 / 段落功能变化退回 Direct，并只重做受影响的 Detail Structure。

音频处理前先标记它在该段的 **narrative_role**（例如 dialogue_information / ambience_continuity / emotional_music / rhythm_cue / intentional_silence），再决定 preserve / isolate / attenuate / replace / remove；不能把“信息”只理解成对白。

再用锚点和对照帧校准文字，按实际叠化帧数编译 render-manifest；所有成片文字、音轨放置、封面定位和接点核查使用此版本成片坐标。分开保存视频单元、无字底片、混音和文字烧录产物，便于局部返工。

先生成 edit-plan，再编译 timeline。详细稿包含成片参数、主线、源素材取舍、逐段画面、原声、创作者文字、字号位置、转场、封面、禁止项和待验证项。画面、声音、文字按 D2 执行包的各层规格落实，同一主句可跨原片正反打保留；若执行稿还缺必要参数，指出缺口并回 D2 补定，不擅自补写风格或表达。

粗剪先保留必要原声及最少的场景提示，验证结构，再按执行包中已确认的策略处理配乐和包装。按照转场逐个观看接点，再正常速度看全片。原片音乐无法干净衔接时优先换切点、加长段落或接受明确场景切换；不假设淡化即可解决所有音乐断裂。

用户只要执行稿时，交付 detailed_plan；未生成粗剪则 rough_cut_verified=false。用户要成片而当前没有渲染能力时，交付能够直接执行的计划与明确缺口，不谎称已剪好。

每次导出先完整解码实测帧数和展示时长，再做全片低电平扫描，并从该成片自动生成全部接点对照图。技术错误先修复；近静音和接点图进入实际核听、播放，不能用截图代替动态检查。

## G QA、保存与恢复

在原 EVA 中增加 Reference Compliance：对照少量已确认样本与全片规则，检查文字层级、位置、画面关系、强调方式和风格漂移；不检查逐镜头配对数量。静态规则检查和真实导出观看分开记录，未实看保持 not_tested。

每批成功后保存结果和 coverage；长任务把“已完成区间 / 未完成区间 / 最近可靠 checkpoint / 可恢复入口”一起保存；**每个大阶段结束必须生成面向下一阶段的 `handoff.md`，并把 `project.json`、阶段产物、文件 SHA-256 manifest 与源媒体重绑定信息一起交付。** 只有聊天总结、临时路径或上一模型记忆不算可续接交付。Detail 另保留专用 `execution-handoff.md`。缓存键由源文件版本、处理区间、参数、工具及模型版本组成。换源版本或 time mapping 时重新核对时间标签并失效精确下游坐标；换机器只改变 locator 时先按 source signature / time mapping 重绑定，不重建已确认状态；调整 Broad Structure 抽样密度只重做受影响区间；Direct 调整通常复用第一轮 Content Map 与已验证证据，不重扫全片。

如果 Narrative Direction 改动只影响局部节点，优先只重做对应的 Detail Structure 区域。只有新的方向依赖此前完全未覆盖或低可信区域，才扩展相应 Structure 范围。

切点或片段长度变化，强制失效对应片段及下游缓存；不能只看同名文件是否存在。将片段 manifest、渲染参数及实际时长纳入缓存判定。纯文字改动可复用无字底片和已确认音轨；卡片或转场时长变化则须重新编译并更新所有下游位置。

下一模型先读 handoff、project、capability-map、sources、coverage、Structured Observation Layer、content-map、Narrative Direction 与 Editorial Execution Plan，再按需读取相关 scene / unit / review / evidence。不得仅凭前一模型的 overview、Narrative Direction 或 execution plan 把未看部分写成已验证。

## 执行完整性接入

沿用 A—G 与两次 Direct。Detail 的实际观察记录与 edit boundary 追加源版本、时间映射指纹；单位 verification 与采用 reviews / utterances 保留同样绑定。Direct 2 锁定采用事件、顺序、unit / boundary、音轨、文字、转场及允许的边界校准；Execute Step 0 精校入选范围后再按最终取段确认 authorization，正式编译继续检查证据与对白。

授权不增加固定审批关卡：当前用户已经确认且包含执行时，据该授权继续工作；缺证据时补实际观察，机器记录不能代替观察。按 [执行完整性契约](execution-integrity.md) 创建字段，并在外部渲染前运行 check_render_authorization.py。

---

## FILE: `references/data-contracts.md`

# 数据契约

目录：文件清单、共同约定、证据记录、场景与片段、Content Map 与外部 Direct、计划映射、剪辑时间轴、静态校验。

## 文件清单

按阶段创建需要的文件。还没到某阶段时允许文件不存在，不用空文件冒充已处理。每个项目放在独立目录。

| 文件 | 格式与用途 |
|---|---|
| project.json | 对象；任务范围、约束、参数、交付目标、版本 |
| capability-map.json | 对象；顶层 `schema_version` + `capabilities` 数组，映射内部能力和真实工具 |
| sources.json | 数组；源文件、版本、时长、时间映射 |
| frames.jsonl | 每行一个抽样帧证据记录；包含图片定位和机器可追溯 facts / unknowns。`extract_frames.py` 在输出目录另写同名索引，`source_ms` 为实测时间戳 |
| frame-observations.csv | Broad Structure 的人可读逐抽样帧基础观察表；供人工 / Director / 其他 Skill 浏览 |
| action-node-candidates.csv | Broad / Detail Structure 的动作变化候选；记录 4fps 局部窗口、触发原因与核验状态 |
| structure-questions.csv | Structure 阶段的问题—回答—证据—confidence—未验证项工作表 |
| detail-intervals.csv | Detail Structure 的精查区间卡；保留进入原因、前情、当前背景、后续、目标问题 |
| speaker-adjudications.csv | 说话人 / 对象的帧级裁决记录；口型、画面、硬字幕、ASR、原声与 confidence 分列 |
| transcript.jsonl | 每行一条字幕或转写；保留核听状态 |
| scenes.jsonl | 每行一个事件或场景；链接多个源区间 |
| units.jsonl | 每行一个可用的连续片段及其保护范围 |
| reviews.jsonl | 每行一次实际观察的区间、模态、结果与审阅者 |
| deep-observations.csv | Detail Structure 的核心区域高密度观察表；包含完整画面、内容、背景、前后状态、原声、反证及 plan 关系 |
| edit-boundaries.csv | Detail Structure 的可剪边界 / 连续性表；把内容范围、真实音频尾部、动作 / 反应收束与 safe in/out windows 分开记录，并为 Direct 2 / Execute 提供强约束切点 |
| structure-exceptions.jsonl | 无法满足的 Structure 字段 / 产物声明；status、reason、impact、downstream_handling 与原字段分开保存 |
| keyframe-references.json | Detail 的真实关键帧清单与可读图片入口；source time、素材节点、用途和异常 |
| execution-handoff.md | E 阶段独立交接；主题、Scope Lock、证据、保护范围、关键帧、capability-map 中相关工具链及下游完整 Execution Package 要求 |
| visual/V0-intake.json … V7-lock.json | 采用视觉设计的项目的视觉设计事实源；V0 `design_scope` 决定探索/复用/简单文字强度，`reuse_confirmed` 必须绑定此前真实 V6/V7/confirmed-artifact，图文关系/动效语言/几何策略变化则回 `explore_new`；V3 可做 full 或 representative-first 验证，deferred 镜头区分 standard/difficult；当前模板用 design fingerprint 区分真实设计变化与格式/备注变化；没有 measured 同条件 XR/MR 时 `explore_new` 的 V5 必须有同素材 baseline vs candidate A/B，small-screen 必需、blur/blind 条件式；V7 rect 必须在 canvas 内且 difficult deferred 镜头必须有实际成图 QA；`no_ref_needed` 可闭环到 V7。 |
| visual-methods.json | schema 1.0；D2 的 Project Method。采用视觉设计的项目只记录 production method 与可选 `visual_stage_problem_refs`，不再重复保存 Reference Selection；旧项目的 `visual_reference_status / visual_reference_refs / viewed_reference_assets` 仅作兼容读取。 |
| implementation-lock.json | 采用视觉设计的项目承接 V7，而不重新做视觉选择：`sync_visual_stage.py` 可机械同步 `visual_stage_binding`、`confirmed_mockups` 和 stage-trace scaffold，减少重复手填；真实 `target_element_ids / parameter_paths / proof_checks / do_not_copy_checks` 仍必须按工程明确。V2 全 `no_ref_needed` 时 trace 可为空。 |
| composition-plan.json | schema 1.0；完整 Blender production windows、图层/关联/曲线、事件范围、接点，以及 `proof_scope_policy` / `proof_composition_ids`；Proof 集合必须最小充分，任一被其他 Proof 机械覆盖的 Proof 默认判冗余，完全等价时保留靠前者；素材级例外用显式 `additional_proof_exception` + shown evidence；每个 deferred composition 必须有 `proof_covered_by` / `proof_coverage_reason`，native_blend 还要求与 Proof 同 native scene/dependencies；composition 数量不等于前置 demo 数量 |
| compositions/… | `proof_composition_ids` 交实际 .blend、visual / demo MP4、proof PNG、render receipt、原生 readback 和逐项 review；其余 production composition 在最终授权后只交正式 .blend、visual、render receipt、readback；新版本使用新路径 |
| delivery-spec.json / delivery-receipt.json | schema 1.0；FFmpeg clean-video / mix / 字幕 / 输出规格，以及真实最终输出字节和技术检查 |
| execution-reference.md | D2 的制作参考；Visual Gate、Toolchain Continuity、具体样式、声音 / 转场规则、少量 reference 的应用规则、资源与 QA |
| coverage.json | 数组；按素材、区间、模态记录覆盖状态 |
| overview.md | 带 scene_id 的 source-order 全片导航，不替代证据 |
| content-map.md | 第一轮 Structure 的横向内容地图；链接 scene / evidence / coverage，供人或 Director 做创意判断 |
| brief.md | 可选输入；主题、核心表达、范围、重点和禁改项，可来自用户或外部 Direct |
| narrative-direction.md | 第一次 Direct 的 Narrative Direction；记录核心命题、Narrative Spine、candidate regions、verification questions 与禁改项 |
| execution-authorization.json | D2 已确认决策的机器授权记录；schema 1.8+ 在 Execute Step 0 精校最终采用范围后准备 / 确认，保存顺序、处理、证据与决策指纹；draft 不能授权渲染 |
| execution-plan.md | 第二次 Direct 的 Editorial Execution Plan；基于 Detail 证据确认最终取舍、顺序、声音 / 文字策略、时长与执行边界 |
| editorial-plan.md | 兼容旧项目的合并式 / legacy Direct 计划；新项目优先拆分为 narrative-direction + execution-plan |
| candidates.json | 兼容性结构；记录 editorial plan 的映射分支、证据、片段顺序、反例和状态，不要求由本 Skill 自动生成 |
| timeline.json | 对象；主视频轨、音轨、文字轨、输出参数 |
| transitions.json | 数组；每个相邻主视频段落的接续关系 |
| render-manifest.json | 对象；编译后的成片帧轴、接点、轨道坐标、分层缓存键 |
| render-audit.json | 对象；真实导出文件的完整解码计数、时长、近静音及接点图表记录 |
| edit-plan.md | 人可读执行稿，与时间轴保持一致 |
| qa.json | 对象；每项检查、证据、问题及待验证事项 |
| handoff.md | 每个大阶段面向下一步的自包含交付：当前阶段 / Scope Lock、确认与 pending/stale、下一步、实际文件 manifest + SHA-256、project 状态 digest、源媒体跨机器重绑定信息 |
| jobs.jsonl | 工具调用、缓存键、状态、产物与可重试错误 |

## 共同约定

- 各类文件的 schema 分开管理：`project.json` 新项目使用 `schema_version=1.9`（旧 1.8 保持兼容）；`timeline.json` 使用 `schema_version=1.4`；`render-manifest.json` 使用 `schema_version=1.4`；`execution-authorization.json` 使用 `schema_version=1.0`。证据 JSONL / CSV 按本文件字段契约管理，不把 project / timeline / manifest 的版本号混用。原有 1.0 / 1.1 证据记录保留，不为升级重写内容。UTF-8；JSONL 每行独立合法 JSON；未知值用 null，不用猜测值占位。
- source_id、frame_id、utterance_id、scene_id、unit_id、candidate_id、event_id、review_id 各自全项目唯一；一旦被引用不重新编号。
- 所有源区间使用整数 start_ms、end_ms，左闭右开，即包含开始、不包含结束。必须满足 0 ≤ start_ms < end_ms ≤ source.duration_ms。单帧用 timestamp_ms，必须小于 duration_ms。
- **运行控制。** `project.text_policy` 和 `voiceover_policy` 属于可执行约束。`workflow_control.production_spec_refs` 与 `production_lock` 保存在同一个项目状态文件。
- **`source_id + source ms/range` 是全流程证据层的 canonical time tag。** `display_timecode`、九宫格位置、抽样序号、字幕 / ASR 文件时间和代理时间只是派生信息；若使用代理、分轨或外部字幕，必须通过 `source.time_mapping` 映射回 canonical source time。进入 Execute 后新增 assembly / output frame，但不得覆盖源时间。任何引用如果只有“第几秒”却没有 source_id 或坐标空间，不视为稳定定位。
- 原始文件发生内容变化时建立新 source_id；原版本 ID 保留。只移动位置可更新 locator，保持 source_id 不变。
- evidence_refs 使用带类型的引用，例如 frame:F001、utterance:T001、review:R001。外部前情使用 context_refs，记录来源与核实状态，不伪造本项目证据 ID。
- facts、interpretations、unknowns 分开。facts 中也保留证据来源，区分模型实际观察、用户提供和上游工具输出。
- 第一轮 Broad Structure 与第二轮 Detail Structure 使用同一套稳定 source / scene / unit / evidence ID；第二轮补密时优先更新 verification、context_ranges、protected_ranges 和 review_refs，不复制一个看似全新的平行素材库。
- `frame-observations.csv`、`action-node-candidates.csv`、`structure-questions.csv`、`deep-observations.csv`、`content-map.md`、`brief.md`、`editorial-plan.md` 都是人可读工作层，不替代 JSON / JSONL 原始证据。任何创意判断进入 Execute 前仍须链接回 frame / utterance / scene / unit / review / source range。
- 不把取样帧序号当成源视频帧号。display_timecode 只用于阅读，机器使用毫秒或输出帧号。


## 输出异常、关键帧与执行包补充

原 CSV 表头与类型锁定；字段无法取得时使用原契约允许的未知表示，并在 `structure-exceptions.jsonl` 保存异常，继续可做的索引 / 草案 / 交接，不虚构、删字段或把未完成阶段标成 complete。E 固定提供 keyframe 清单和自包含 handoff；D2 提供 execution-plan + execution-reference。详见 [异常与执行包契约](execution-package.md) 及其可复制模板。

project 增加 `handoff_ref`（默认 `handoff.md`），并保留可选 `structure_exceptions_ref`、`keyframe_references_ref`、`execution_handoff_ref`、`execution_reference_ref`、`execution_reference_asset_refs` 与 `execution_package_policy`。`workflow_control.last_handoff` 记录当前阶段 handoff 的 state digest 与文件 SHA-256；它是阶段出口交付记录，不是新 Gate。v1.2.2 的 project schema 1.7 继续只使用 `visual_gate_status`、`visual_mockup_ref`、`visual_proof_ref` 三个轻量 Visual Gate 字段；v1.4.4 在多代表性 Proof 时另用可选 `visual_proof_refs` 列出全部 Proof，`visual_proof_ref` 继续指向首个兼容 Proof，不新增状态文件或 visual-style schema。schema 1.7 时必须使用 `execution_package_policy=plan_and_reference`，且三个字段必须存在；ready 时状态必须为 `proof_confirmed` 或 `not_applicable`。`proof_confirmed` 还要求 mockup 与每个代表性 proof 都是不同且内容不相同的真实文件；所有 Proof 与 `capability-map.json` 一起进入 `execution_reference_asset_refs`。每个代表性 Proof 都必须有 available capability 记录真实 `actual_tool` 与 `entrypoint`，且其 `output_mapping` 实际指向该 Proof；单 Proof 时仍兼容 `visual_proof_ref`。schema 1.6 旧项目保留 v1.2.0/1.2.1 兼容行为。Detail complete 须有清单 / handoff；正式 ready 须有 reference 文档和已列出的资源。关键帧缺失有明确异常仍可继续。采用未核实证据的原门槛不变。

完整执行包确认继续使用 reference 文档 / 实际样本指纹；selected mockup、proof 与执行入口写入 reference / asset refs 后，变更会使旧确认失效。只有状态、结构、文件与指纹经过机器检查；proof 是否真的由声明的同一执行工具链产生、视觉是否符合审美，仍按契约人工 / 模型审阅。

## 结构化工作层与上下文成本

Structure 的目标之一，是把视频 / 图像 / 原声等高成本多模态输入转换成 **compact structured representation**。`frames.jsonl`、`frame-observations.csv`、`action-node-candidates.csv`、`structure-questions.csv`、scene / segment observations 与 overview 共同构成第一轮正式的 **Structured Observation Layer**；`content-map.md` 与情绪 / 关系线索建立在这层文字化结构数据之上。第一次 Direct 优先消费这些表单和文本，而不是反复重新加载原始视频或九宫格。

这是一种有损压缩式的工作表示，但不是证据替代：所有关键记录必须保留时间码和 evidence refs，确保需要时可以重新下钻到原素材。第二轮 Detail Structure 只对 editorial / script plan 命中的区域恢复更高密度多模态上下文。这样可以减少重复上下文和不必要的高密度观察，但不承诺固定比例的 token 或算力节省。

## 素材和证据记录

sources 每条必填 `source_id`、`locator`、`version`、`duration_ms`、`time_mapping`。version 可以是可核查版本标识或哈希；未知为 null，并阻止复用旧缓存到精确剪辑。`time_mapping` 即使为原文件直读也写 `{"type":"identity"}`，代理 / 合集切分 / 非线性转换则保存可复核映射。其他字段包括 episode、width、height、fps_num、fps_den、frame_rate_mode、audio_streams、subtitle_source。

Broad Structure 完成时，每个 source 还应有 `usable_ranges`（可用源时间区间；完整可用也显式写全长区间）与 `downstream_constraints`。片头 / 片尾卡、黑场、缺音、代理缺段等会限制后续设计的边界必须写入这里，并由 Content Map / handoff 传给 Direct；不能只留在某次分析文字里。

frame 必填 frame_id、source_id、timestamp_ms、image_ref、facts、unknowns。建议补充 sheet_id、cell_index、visible_text、observation_origin。cell_index 为一至九，不参与时间计算。frame 只描述该时点看见的状态。

`frame-observations.csv` 是同一批抽样帧的**人可读基础结构化层**，不是另起一套证据 ID。每行必须对应一个已实际分析的 sampled frame；Broad Structure 标记 complete 时，其 frame_id 集合应与 `frames.jsonl` 一致。字段至少包括：`source_id`、`episode`、`timestamp_ms`、`display_timecode`、`frame_id`、`sheet_id`、`cell_index`、`scene_id`、`characters`、`visual_facts`、`visible_action_state`、`observed_emotional_cues`、`emotional_interpretation`、`expression_gaze`、`spatial_relationship`、`setting_background`、`key_objects`、`motif_tags`、`visible_text`、`nearby_dialogue_refs`、`content_description`、`change_from_previous`、`action_node_candidate_ids`、`interpretations`、`unknowns`、`evidence_ref`、`image_ref`、`coverage_status`。

其中 `visual_facts` / `content_description` 不得把相邻抽样帧之间未实际观察到的动作补齐；**稀疏抽样中的“没看到”不能写成“没有发生”，4fps 或更密抽样本身也不能证明整个区间内没有发生。**否定性事实必须先声明明确的 source-time 观察范围，再按事实类型核验：视觉动作 / 物件缺席需连续视频 review 覆盖完整机会窗口，语音缺席需连续原声 review 覆盖声明区间，或存在能直接排除该事实的可靠反证；否则写 `not_observed_in_sample` / `unknown`。`change_from_previous` 只能描述相邻已分析抽样帧的可见差异；`motif_tags` 是导航标签而非已确认象征；`observed_emotional_cues` 只写可观察线索，`emotional_interpretation` 与事实分列。`visual_facts`、`visible_action_state`、`motif_tags`、`visible_text`、`original_audio_keypoint`、`audio_verification_status`、`change_from_previous`、`content_description`、`topic_judgment`、`confidence`、`confidence_basis`、`unknowns` 不允许空白；没有内容时显式写 `none` / `unknown` / `not_applicable`。这里的“逐帧”始终指逐**已分析抽样帧**。

`action-node-candidates.csv` 每行一个动作 / 视线 / 站位 / 物件状态等变化候选，至少包含 `candidate_id`、`stage`、`source_id`、`scene_id`、`trigger_frame_id`、`center_timestamp_ms`、`trigger_reason`、`change_signal`、`window_start_ms`、`window_end_ms`、`sampling_fps`、`evidence_refs`、`verification_status`、`unknowns`、`review_refs`。默认 `sampling_fps=4`；偏离时必须填写 `sampling_exception_reason`。候选窗口只是局部加密观察机制，不等于动作已经被连续音画验证。

`structure-questions.csv` 用于保留 Structure 中真正影响理解的问题，不允许只把未确定内容散落在总结里。至少包含 `question_id`、`stage`、`source_id`、`scene_id`、`frame_refs`、`plan_node_id`、`question`、`answer`、`answer_status`、`evidence_refs`、`unverified_items`、`next_check`、`review_refs`。`answer_status` 只用 `supported`、`partial`、`unresolved`、`contradicted`、`not_applicable`。未解决问题必须继续可见。

utterance 必填 utterance_id、source_id、start_ms、end_ms、text、origin、audio_verified。origin 为 subtitle、asr、manual 或 user；audio_verified 默认为 false。其他字段包括 speaker、addressee、language、translation、unclear_words、review_refs、`asr_role`。未知说话人保持 null，不能按画面中出现的人直接指定。

ASR 默认是定位 / 候选证据，不天然等于台词事实。方言、强口音或已知高误识率段落应标 `asr_role=locator_only`；要把台词写进 facts，需要可回查的原声核听或可靠硬字幕支持。硬字幕与原声冲突时不机械规定“字幕永远赢”或“原声永远赢”，而是记录 conflict，并按要裁决的事实类型与源可靠性回原片处理。

review 必填 review_id、source_id、start_ms、end_ms、modalities、reviewer、result、evidence_locator。modalities 是实际处理的 video、audio、frames 或 text 列表；reviewer 说明来自模型、工具或用户。保留能复核的工具输出、人工确认记录或音画位置。只有提取音轨的日志不算 audio 审阅。

coverage 每条包含 source_id、start_ms、end_ms、modality、method、status、evidence_file、reason。modality 为 visual_sample、transcript 或 av_review；status 为 complete、partial、failed、pending、excluded。complete 只指该模态在该区间按所列方法处理完成。excluded 必须有理由。覆盖率按区间并集计算，不把批次重叠重复计入；不能把 visual_sample 的完成率叫作完整观看率。

## 场景和片段

scene 包含 scene_id、source_ranges、characters、location、story_time、facts、interpretations、unknowns、before_state、after_state、evidence_refs、context_refs。source_ranges 是若干 source_id/start_ms/end_ms 对象，允许交叉叙事。story_time 不确定时写 null。

unit 包含以下字段。一个 unit 只能对应一个源文件中的连续区间。

```json
{
  "unit_id": "U001",
  "scene_id": "S001",
  "source_id": "SRC001",
  "start_ms": 120000,
  "end_ms": 145000,
  "context_ranges": [{"source_id":"SRC001","start_ms":100000,"end_ms":170000}],
  "protected_ranges": [{"start_ms":122000,"end_ms":142000,"reason":"完整问答与动作回应"}],
  "summary": "示例占位，须据实际素材填写",
  "utterance_ids": ["T001"],
  "evidence_refs": ["utterance:T001"],
  "visual_state": {"costume":null,"props":null,"position":null,"lighting":null},
  "relationship_stage": null,
  "audio_state": {"speech":true,"music":null,"ambience":null},
  "isolated_use_risk": "缺少前一问时指代不清",
  "verification": {"audio":"pending","visual":"pending","context":"pending","review_refs":[]},
  "unknowns": ["尚未回看连续音画"]
}
```

verification 的 audio、visual、context 使用 pending、reviewed、not_applicable。not_applicable 在 not_applicable_reasons 对象中按对应字段说明原因，例如已确认源文件完全没有音轨。仅仅没有对白不等于音频不需检查。reviewed 必须有 review_refs，值为 reviews.jsonl 中真实存在的 review_id；不能仅靠摘要设置。连续画面核查使用 video 模态，仅有 frames 不能标记 visual=reviewed。核查区间合计应覆盖实际选用的片段。protected_ranges 可以在探索期暂为空，精查后入选执行稿时必须有明确保护范围，或在 protection_note 写明为何整段无可保护的对白、动作且经复核。

## Edit Boundary / Continuity Layer

Detail Structure 在“理解完整”之后还必须回答一个独立问题：**如果这段进入 D2，怎样的范围足以保住声音、动作、反应与语义？** `edit-boundaries.csv` 是正式基础产物，不得由 execution plan 自由文字代替。Detail 可以先交 selection-ready 的保守边界；字幕结束、ASR end、某个抽样帧不再见到动作，都不等于最终切点。

每行至少包含：`boundary_id`、`detail_interval_id`、`plan_node_id`、`source_id`、`unit_id`、`observation_refs`、`continuity_type`、`content_start_ms/end_ms`、`audio_start_ms/end_ms/tail_end_ms`、`action_start_ms/end_ms/reaction_or_settle_end_ms`、`preferred_in_ms/out_ms`、`safe_in_start_ms/end_ms`、`safe_out_start_ms/end_ms`、`must_keep_ranges`、`left_handle_ms/right_handle_ms`、`boundary_reason`、`cut_risk`、`evidence_refs`、`confidence`、`boundary_status`。没有某类连续性时显式写 `not_applicable`，不能留空。

`continuity_type` 使用 `dialogue`、`action`、`reaction`、`music`、`scene`、`mixed`。`boundary_status=partial` 表示已具备供 D2 选择的保守 envelope：content、preferred / safe windows、must-keep 与 handles 仍要明确，但尚无必要精校的 audio / action 精确起止可写 `unknown`。只有 `supported` 才表示这些适用的连续性边界已经通过实际连续音画补齐。对于 supported 的 dialogue / music / mixed，safe-in 必须结束在需保留音频表达开始前，safe-out 必须开始在真实尾音 / 衰减结束后；action / reaction / mixed 同理保护动作与 settle。`must_keep_ranges` 使用 `start-end;start-end` source-ms 表达。

Direct 2 选择素材时必须引用 `boundary_id`，把 source in/out 视为 planned range，并声明 Execute 可否在该 boundary 的 safe windows / handles 内校准。schema 1.8+ 的 source event 还保存轻量 `d2_selection_snapshot`：`edit_boundary_ref`、planned in/out、当时四个 safe-window 端点和 `allowed_adjustments`。Step 0 只能在这份快照内校准；safe windows 被扩大、boundary 被替换，或最终取段超出允许的 trim / handle 范围时，停止并返回确认。到 `ready_for_render` 时，所有入选 boundary 必须已升为 `supported`；未入选的 partial boundary 不要求补全。最终 `source_in_ms/out_ms` 仍须覆盖 must-keep ranges。若故意做非自然切法，沿用 `boundary_override + review refs + overrides`；unit 的 `protected_ranges` 仍不可被自动绕过。

## Detail Structure 的结构化观察

`deep-observations.csv` 用于第二轮定向高密度 Structure。它不是剪辑表的替代品，也不能只记录“可用 / 不可用”。当某个区域已经被 Narrative Direction（或 legacy rough plan）选为核心回查对象时，应先把它做成更完整的内容档案，再收敛为 unit 和切点。

推荐每行对应一个高密度观察时点或连续观察区间，字段至少包括：

- 定位：`observation_id`、`detail_interval_id`、`plan_node_id`、`source_id`、`episode`、`start_ms`、`end_ms`、`display_range`、`scene_id`、`unit_id`、`representative_frame_refs`、`frame_observation_refs`；
- 画面：`visual_facts`、`shot_composition`、`action_chain`、`key_visual_changes`、`observed_emotional_cues`、`emotional_interpretation`、`expression_gaze`、`spatial_relationship`、`motif_tags`；
- 背景：`setting_context`、`narrative_context`；
- 内容：`content_description`、`hard_subtitle_notes`、`original_audio_keypoints`、`audio_verification_status`、`subtitle_asr_conflicts`、`dialogue_audio`、`speaker_adjudication_refs`、`before_state`、`after_state`；
- 判断：`question_refs`、`topic_judgment`、`confidence`、`confidence_basis`、`interpretations`、`unknowns`、`unverified_items`、`evidence_status`、`counterevidence`；
- 执行衔接：`context_ranges`、`protected_ranges`、`min_effective_unit_candidate`、`isolated_use_risk`、`review_refs`、`narrative_function`、`edit_note`。

字段含义：

- `detail_interval_id` 必须能回到 `detail-intervals.csv`，确保高密度观察不会脱离进入精查时的前情 / 当前背景 / 后续和目标问题；
- `original_audio_keypoints` 只写已真实核听或明确标为未核听的原声要点；`hard_subtitle_notes` / ASR 不得冒充原声；字幕、ASR 与原声不一致时写入 `subtitle_asr_conflicts`；
- `topic_judgment` 写该帧 / 节点在当前候选主题中的具体叙事作用；`confidence` 和 `confidence_basis` 必须同时存在，说明判断来自帧证、连续画面、已核听原声、字幕 / ASR 或组合证据；
- `visual_facts` 写这一时段实际看到的画面；人物、站位 / 朝向、动作、表情 / 视线、人物间距离、物件、景别 / 构图与明显画面变化尽量具体；
- `key_visual_changes` 记录核心区间内已经观察到的动作 / 视线 / 站位 / 物件变化；必要时链接 `action-node-candidates.csv` 的 4fps 局部窗口；
- `observed_emotional_cues` 只写可观察的表情、视线、语气、停顿、身体状态；`emotional_interpretation` 才写谨慎情绪解释，不推断隐藏心理；
- `content_description` 回答“这一小段实际发生了什么”，不只抄对白；
- `setting_context` 写地点、时间、环境、空间状态等场景背景；
- `narrative_context` 写它在完整事件中的位置、前一事件和后续关系；
- `dialogue_audio` 写已核听的原声信息，并明确 speaker / addressee / tone / pause / ambience / music / audio_verified；
- `before_state` / `after_state` 用于保住动作与因果，不等同心理推断；
- `plan_node_id` / `narrative_function` 只说明为什么要回查这一段，不得用计划目标倒推事实；
- `evidence_status` 可用 pending、supported、contradicted、partial；关键节点若为 contradicted 或仍 pending，不进入 ready_for_render。

第二轮可以在第一轮相同 frame_id / scene_id 上补充更密的新 frame / review，也可以对连续区间形成新的 observation_id；不要为了“更细”而复制一套与第一轮断开的素材库。

## Detail 区间卡与说话人裁决

`detail-intervals.csv` 每行对应一个进入 Detail Structure 的核心区间。至少包含：`detail_interval_id`、`plan_node_id`、`source_id`、`start_ms`、`end_ms`、`entry_reason`、`preceding_context`、`current_background`、`following_context`、`content_summary`、`target_questions`、`topic_relevance`、`evidence_refs`、`unknowns`。前情 / 背景 / 后续不清时写 `unknown`，不能省略。`target_questions` 写分号分隔的稳定 `question_id`（无则 `none`），每个都须存在于 `structure-questions.csv` 并被本区间至少一条 `deep-observations.question_refs` 回指；`contradicted / unresolved` 的目标问题列入 handoff 的 Question Closure Ledger（见 [Detail 证据获取](detail-evidence.md)）。

`speaker-adjudications.csv` 用于说话人 / 对象歧义的帧级裁决。至少包含：`adjudication_id`、`stage`、`source_id`、`utterance_id`、区间、`frame_window_refs`、`lip_movement_observation`、`visible_speaker_candidate`、`addressee_candidate`、`audio_speaker_candidate`、`hard_subtitle_signal`、`asr_signal`、`asr_role`、`evidence_resolution_rule`、`subtitle_audio_conflict`、`decision`、`decision_basis`、`confidence`、`evidence_refs`、`unknowns`。只有字幕或只有画面时不得假装完成裁决；ASR 在方言 / 强口音场景默认 `locator_only_until_verified`。

## Content Map 与两次外部 Direct

`overview.md` 和 `content-map.md` 作用不同：

- `overview.md` 按源时间顺序帮助恢复“原片发生了什么”；
- `content-map.md` 横向组织人物、关系变化、重复行为、对白主题、无声互动、物件 / 空间线索、潜在前后呼应与 unknowns，帮助人或 Director 看见“素材里都有什么可以继续想”。

它们都建立在正式的 Structured Observation Layer 之上，不能反向替代 `frame-observations.csv`、动作节点、Q&A 或 scene / segment 观察。Content Map 中每个可操作条目应尽量带 `scene_id`，必要时补 source range / evidence refs / coverage 状态；情绪大意只作为 `observed cues / trajectory` 的导航性汇总，与心理解释分开。

### Direct 1：Narrative Direction

`narrative-direction.md` 是第一次 Director 的输出，说明“到底讲什么”，至少覆盖：`thesis` / 核心命题、`narrative_spine`、candidate regions / scene refs、各节点功能、verification questions、human decisions、external research refs、constraints / do-not-change。它不要求精确到帧，也不因写得详细就自动升级为素材事实。

Detail Structure 把 Narrative Direction 的每个核心节点映射回已有 Content Map 与原片。建议维护 narrative mapping，至少包含：`plan_node_id`、`function`、`scene_refs`、`unit_refs`、`evidence_refs`、`evidence_status`、`gaps`、`counterevidence`、`allowed_adjustment`。

### Direct 2：Execution Package（含 Editorial Execution Plan）

`execution-plan.md` 在 Detail Structure 完成后生成，说明“这些已核实材料最终怎么讲”。至少引用 selected verified units / protected ranges，并明确 final order、narrative function、required context、audio treatment、text intent、duration allocation、transition intent、allowed substitutions、execution boundaries 和 do-not-change。

若 evidence_status 仍为 pending / contradicted，不得把对应节点当成可确认执行事实；主线级冲突退回 Direct 1，执行取舍问题留在 Direct 2。Execute 接收 Source Clips、Detail、execution-plan、execution-reference 和 Constraints；只把确认后的包落实为 timeline / render manifest，不在技术层自行补定叙事或风格。reference 用一两个样本锁定全片规则，不逐项映射所有视觉动作。

`brief.md` 可作为两次 Direct 的共同背景输入。`editorial-plan.md` 保留为旧项目或需要合并式文档时的兼容格式，新项目优先使用 `narrative-direction.md` + `execution-plan.md`，第二次 Direct 同时交付 `execution-reference.md`。

## 计划映射与 candidates 兼容结构

`candidates.json` 保留用于兼容既有项目和多分支 Narrative Direction / legacy rough plan。candidate 不再意味着“必须由本 Skill 自动想出的创意主线”；它可以是用户 / Director 提供的 editorial plan 分支，也可以是明确授权 brainstorming 时产生的草案。

candidate 建议包含 candidate_id、origin、thesis、experience、mode、unit_order、roles、claims、counterevidence、unknowns、status。`origin` 可使用 user、director、brainstorming、legacy_auto 等值。mode 为 contrast、payoff、behavior_change 或 perspective；必要时可用自定义值并解释。

claims 每条至少含 text、evidence_refs、status。status 为 supported、interpretation 或 pending；有证据并不自动等于某种心理动机得到证明。counterevidence 记录可能改变主线的上下文；尚未查找时写 pending，不留空后声称不存在。

candidate.status 为 provisional、ready_for_plan 或 rejected。ready_for_plan 表示 Narrative Direction / legacy rough plan 对应的核心素材已经完成 Detail Structure、语境和反证已经检查，不表示粗剪通过。补充 estimated_duration_ms、scope_changes、reorder_reason 和 selected 字段方便执行。

## Execute 前的时长预算

`timeline.duration_budget` 用帧而不是浮点秒做对账，至少含 `sum_event_frames`、`sum_transition_overlap_frames`、`computed_output_frames`、`target_max_frames`、`status`、`adjustment_note`。计算规则：`computed_output_frames = Σ event frames − Σ transition overlap frames`。黑场卡、freeze / hold 等真正增加播放时间的内容必须成为 event 后再计入；覆盖在既有画面上的 text track 不单独加时。若文字阅读时间放不进当前视觉窗口，先修改 event / card / hold 或内容长度，再重新对账。

有明确总时长上限时，ready_for_render 前必须 `computed_output_frames ≤ target_max_frames`；超出时先按既定压缩规则裁决并在 `adjustment_note` 记录调整，不能一边执行一边让预算漂移。无明确上限也要完成对账，可用 `status=checked_no_limit`。

## 剪辑时间轴

### 时间轴量化与 ready_for_render 机械门槛

`timeline.json` 的输入坐标空间是 `assembly`，但 source event 的 assembly 边界不得由每一段独立四舍五入得到。先按 source duration / speed 计算精确帧时长，再对**累计边界**统一量化；card 使用明确整数帧时长。相邻 transition overlap 再从这套累计量化结果映射到 output 坐标。静态校验与编译器必须调用同一套计算规则，因此 text / audio 轨也按最终 output 总帧数检查，不能只拿未扣 overlap 的 assembly 末帧做上界。

当 `timeline.status=ready_for_render` 时，除了时间轴本身合法，还必须满足：Broad Structure + Content Map 完成、Detail Structure 完成、`narrative_direction_status=confirmed`、`execution_plan_status=confirmed`、两份 Direct 文档存在且非空、`render_authorized=true`；schema 1.8+ 还要求每个入选 source event 的 edit boundary 已在 Execute Step 0 精校为 `supported`。每个被选中的 source event 必须显式给出 `deep_observation_refs`，引用本次实际采用的 `observation_id`；这些 observation 必须与 event 的 `source_id` 一致、其 source-time 区间合并后完整覆盖本次实际采用的 source range，且 `evidence_status` 只能是 `supported / partial`。同一 unit 中未被本次 event 引用的 pending / contradicted observation 继续保留为证据记录，但不阻断本次执行。这些检查不替代原片真伪核验，只阻止“阶段没完成或采用证据映射不清却进入 Execute”。

`source.time_mapping` 是精确时间定位的一部分，不只是输入摘要。任何 source 的 `version` 或 `time_mapping` 改变，所有依赖该 source 的 unit / clean-video / audio / final cache key 都必须变化；旧精确切点缓存不得继续标记为可复用。


timeline 顶层包括 schema_version、project_id、candidate_id、status、coordinate_space、fps_num、fps_den、width、height、events、audio_tracks、text_tracks。status 为 draft 或 ready_for_render。未确定输出规格时保持 draft，未知数字为 null。`timeline.json` 1.4 使用 `coordinate_space=assembly` 保存未扣除叠化的编排计划；实际成片坐标由 `render-manifest.json` 1.4 提供。无叠化时两者可能重合，仍应在出片前完成编译，避免下游混用。

主视频 events 按 out_in_frame 排序，左闭右开，从零开始无缺口、无重叠。每条包含 event_id、kind、out_in_frame、out_out_frame、function。kind=source 时还需 source_id、unit_id、source_in_ms、source_out_ms、speed；进入 `ready_for_render` 时还必须有非空 `deep_observation_refs`，以及明确的 `edit_boundary_ref`。默认切点必须落在该 boundary 的 safe-in / safe-out windows 并覆盖 must-keep ranges；只有显式 `boundary_override=true`、原 reason/review refs 和 v1.0.3 具体 `overrides` 全部有效才允许故意越界。默认 speed=1。kind=card 时记录 card_text 或 card_asset，不借用伪造的 source_id。

每段源素材的精确播放时长先进入同一条累计时间轴，再统一量化到目标 fps；输入 `assembly` 边界必须与这套累计量化结果一致，不能把每段各自四舍五入后的帧长直接相加。单段量化误差可以存在，但只能由累计边界分配，不能逐段累积。精剪仍需按真实解码结果核对。源可变帧率不影响输出采用确定帧率，但必须记录源到输出的映射。

audio_tracks 每条含 track_id、kind、source_id 或 asset_ref、source_in_ms、source_out_ms、out_in_frame、out_out_frame、gain_db、fade_in_ms、fade_out_ms、sync_event_id、reason，并补 `narrative_role` 与 `treatment_reason`。kind 区分 original、music、voiceover、ambience；v1.4.1 中 voiceover 默认未声明即禁止，只有 `project.voiceover_policy.allowed=true` 且 description / ref 明确时才允许进入执行；`narrative_role` 可用 `dialogue_information`、`ambience_continuity`、`emotional_music`、`rhythm_cue`、`intentional_silence`、`other`。先说明声音在叙事中承担什么，再决定 preserve / isolate / attenuate / replace / remove，不能把“信息”窄化成对白。明确是否保留原声；异步 J/L-cut 要说明语义与同步范围，不能把音轨默认等同主视频切点。未知增益和淡化写 null，核听后确定。编译输入优先使用 anchor_event_id、local_in_frame、local_out_frame，编译器据实际段起点生成 out_in_frame/out_out_frame；对确实跨段的绝对定位须显式 coordinate_space=output，并在结构变动后重核。

text_tracks 每条含 text_id、kind、text、out_in_frame、out_out_frame、position、font、font_size_px、color、motion、evidence_refs。kind 区分原声字幕、解释、场景提示。解释不得伪装原话。v1.4.1 current pipeline 另要求显式 `text_role=original_subtitle / creator_text / chapter_card`、`glyph_height_px`、`canvas_height_px`、`stable_hold_frames`；ready 前按 `project.text_policy` 对实际字形高度比例、creator text 行数与阅读时间做硬检查。像素规格未定时保持 draft，不以待定值进入 ready。

文字轨也使用 anchor_event_id/local_in_frame/local_out_frame 编译。补充 stable_hold_frames、fade_in_frames、fade_out_frames、glyph_height_px、font_unit、font_size_value、anchor_reference，记录阅读时间和字号校准。fade_in+stable_hold+fade_out 不得超过显示范围；章节卡延长会修改事件长度，不能只修改文字轨。原音不许含音乐等要求写入 project.audio_policy，音频修复必须遵守。

转场使用 transitions 中独立记录；timeline 中各段保持未扣叠化的顺序区间。transition 新增 effect=hard_cut/xfade 与 overlap_frames；硬切为0，叠化为正整数。编译后各段在 render-manifest 中允许按明确的 overlap_frames 相邻重叠，并生成每个接点的成片开始、结束帧。须核查源边界和 protected_ranges；不能把两个片段的完整长度相加后又偷偷扣除叠化时间。双时间轴、量化方法及所有下游坐标更新规则见“渲染与工程检查”。

transition 必填 from_event、to_event、relation、reason、omitted_context、audio_method、time_cue、risk、review_status。relation 使用重组规则规定的五个值。review_status 为 pending 或 reviewed；有几个接点就检查几个，不能只抽查一个代表全部。

render-manifest 顶层记录 coordinate_space=output、fps_num/fps_den、total_frames、duration_seconds、events、joins、audio_tracks、text_tracks、cache_keys、warnings、input_digest。event 同时保留源取段与最终输出帧号；joins 包含 start_frame/end_frame，硬切两者相同。封面从成片选取时引用此坐标；从源片选取时仍记录 source_id 与源时间，不混称同一坐标。

cache_keys 分开标识视频单元、无字合成、音频混音和文字成片层。`cache_reusable_by_layer` 必须按各层真实依赖判断：视频 source 的版本 / time_mapping 未知只影响依赖它的视频层；音频 source 的版本 / time_mapping 或外部 `asset_version` 未知时，`mix_audio` 与 `final` 不得标为可复用，但已知版本且不依赖该音频的视频单元 / clean-video 仍可保持可复用。章节卡的 `card_text` 及其文字渲染参数属于 final 文字合成依赖：仅修改卡片文案、字号、字体、颜色、位置、动效等时必须改变 final cache key，但不应无故使 clean-video 或 audio cache 失效。顶层 `cache_reusable` 为向后兼容的 final 聚合标志。render-audit 记录 file_sha256 与 manifest_sha256，以确认审查的是同一个版本。expected_quiet_ranges 使用成片 start_frame/end_frame 与 reason，供人工解释有意静默；未提供理由不能自动豁免。

人可读执行稿表头统一为：成片时间及帧号｜原素材及时间码｜画面与动作｜原声及音轨｜屏幕文字｜字号位置｜接续与注意事项。另附素材取舍表、完整文字清单、封面选帧和 EVA。

## 执行绑定补充

Project 1.6、timeline / render-manifest 1.4 增加采用证据版本、Direct 2 机器授权、许可取段与独立原声连续性。详见 [执行完整性契约](execution-integrity.md)，该补充是 ready_for_render 的必需条件；原六套 Structure 表和两次 Direct 的职责保持。旧项目可继续做 Structure / draft，但进入正式执行须补真实绑定与确认，不能将旧 evidence 自动盖成当前版本。

正式执行要求每个 source event 显式列出 adopted_utterance_refs，每条 source_id 音轨独立列出 review_refs。实际取段内已知对白和明确采用的对白均先验证来源、版本与完整音频核查；continuity_type 不能关闭 preserve_dialogue。源音轨全范围（含 J/L-cut 扩展）须由当前有效 audio reviews 的区间并集覆盖，并纳入采用证据指纹。已确认的不保留对白政策须附 event.dialogue_policy_reason；具体删句 / 截尾仍使用有效创作例外。完整规则和未实现边界见执行完整性契约。

检查器逐 source_id 音轨推导已知对白，视频关联不决定检查资格。卡片、未关联和异源仅音频均核对整句当前证据、核听、保留政策与可听覆盖；音轨独有 utterance 及其 review 进入 evidence_digest。独立轨可选 adopted_utterance_refs；不保留政策的具体原因写 track.dialogue_policy_reason，截句例外写 track.overrides，target_id 为 track_id。视频原声仍沿用 event 级同步与例外。没有新增正式 CSV 列、创意阶段或 schema 版本；完整适用关系见执行完整性契约第3节。

## 静态校验

随附脚本检查 sources、frames、transcript、reviews、units、timeline 的核心 ID、源范围、保护区间、帧时长，以及 transitions 的相邻引用。ready_for_render 还检查核查记录的存在及音视频区间覆盖。它不会证明核查记录所写事实真实、说话人正确、剧情因果成立、实际音画流畅或字幕准确。JSON 合法也不等于数据契约所有语义要求得到满足。

运行 `python3 scripts/validate_project.py 项目目录`；缺失后续阶段文件列为 skipped，不得把输出 status=pass 解释为项目已完成。进入 ready_for_render 前仍须按检查与交接规范人工或模型复核全部相关字段。

---

## FILE: `references/detail-evidence.md`

# Detail 证据获取：时间标签、读图、切点与问题闭环

只在 E（Directed Deep / Detail Structure）阶段读取。本文件规定**怎样取证**，不改变 Detail 要交付的字段与验证项；字段契约仍见 [data-contracts.md](data-contracts.md)。

## 1. 时间标签：在帧产生时实测写入

- 本地原片且 identity 映射时，抽帧优先用 `scripts/extract_frames.py`。标签是 ffmpeg 实测的 pts，不是"起点 + 序号 × 间隔"。文件名为 `source_id_源毫秒.jpg`，同目录 `frames.jsonl` 记录 `source_ms`、`label_method=measured_pts` 与 source 绑定。
- 之后只引用这些标签，不再换算。拼图格子、Broad 名义时间、字幕时间都只是线索。
- 该脚本只接受本地文件和 `time_mapping.type=identity`；MCP / 远程、代理 / 偏移或缺少本地工具时，按 [MCP 适配](mcp-adapter.md) 校验短段，保留实测媒体时间、canonical source time 与源绑定，不为调用脚本改写既有映射。
- 进入 Detail 时核对一次 source 版本与 time mapping；它们不变就沿用已有标签，变了则旧标签与切点全部失效重做。

```sh
python3 scripts/extract_frames.py PROJECT SRC001 1200000-1260000 --mode signals
python3 scripts/extract_frames.py PROJECT SRC001 1200000-1260000 --mode frames --fps 1
python3 scripts/extract_frames.py PROJECT SRC001 1216200-1216800 --mode strip
```

## 2. 读图：全覆盖、按内容定密度、每个时间点只读一次

先读文字：Broad 逐帧观察、动作候选、**已有可靠字幕原话**、已有转写和目标问题。再对整个 DI 运行 `--mode signals`，得到画面变化、硬切与有声 / 静音候选。声音默认走 **subtitle + signals / waveform first**：先用已有字幕确定语义候选，用有声区间 / 停顿定位回听点；只有某个词、speaker / addressee、重叠说话或字幕冲突会改变当前判断时，才对该小窗口原声回听或定向 ASR。不要等待整个 DI 的 ASR 才继续 Detail。

按时段分配密度，每个时段只生成并阅读一种密度，不叠加多层：

| 时段 | 密度 |
|---|---|
| 前后语境 | 0.5fps |
| 核心范围中静止或只在说话的部分 | 1fps（下限） |
| 变化时段、Broad 动作候选、目标问题时间窗 | 4fps |

另有必读全分辨率单帧：关键事实的决定性时刻、说话人 / 对象裁决的口型时刻、切点附近，以及缩略图看不清的文字。

升级按事实类型，不按"再加密一层"：

- 细动作、物件交接、谁对谁做：4fps，再读决定性时刻单帧；仍有歧义看连续视频。
- 表情、视线、反应：读单帧，不靠更密的缩略图。
- 说话人 / 对象：原声、硬字幕与口型单帧综合；ASR 只作定位。
- "没有发生"：必须看覆盖完整机会窗口的连续视频或连续原声。

**细动作不凭缩略图下结论**：肯定或否定一个手部 / 物件动作，至少要读决定性时刻的全分辨率单帧。

单一事实的停止条件：证据已达该事实类型标准；或连续视频 / 原声仍无法确定，则写 `unresolved` 与具体缺口。达到标准后不再升级密度；节点级停止按第 3 节。

## 3. 先裁决目标问题，再做最小充分 Detail

进入 DI 后先回答 `target_questions` 中会改变后续理解的问题，立即更新 `structure-questions.csv`。Detail 的目标不是提高素材理解覆盖率，而是用最低成本关闭 Direct 1 的具体问题；不要因为“也许还能发现更多”自动扩大精查。

每个 plan node 满足以下四项后停止继续加密读取：

1. 会改变叙事判断的目标问题已得到 `supported / contradicted` 结论；若连续视频 / 原声仍无法确定，则明确 `unresolved + next_check`，不继续无限加密。
2. 已找到能保持原意的最小完整互动 / 动作单元，主动方、条件、回应和结果不因截短而改变。
3. 若该节点可能进入 D2，已建立足以供选段的 Edit Boundary、safe windows、handles 与 must-keep ranges；最终音频尾部 / 逐帧切点尚无必要精校时可标 `partial`。
4. 已检查足以改变当前结论的反证和必要前后文。

四项闭合即 **STOP DETAIL**。同一证据可同时关闭多个字段和问题；不得为了字段“更满”、画面“更多”或保险性重复阅读而继续取证。`contradicted` 不取消其余必要验证，也不改变 D1 / D2 的职责。

## 4. 边界分两层：Detail 先夹住，入选后再精校

Detail 的任务是让 D2 **能可靠选择片段**，不是把所有候选都做到最终帧级。先用已有观察、字幕、signals 和必要连续播放建立保守的 `preferred in/out`、safe windows、must-keep ranges 与左右 handles。若这一候选尚未被 D2 采用，且精确尾音 / 逐帧切点不会改变“能否使用”的判断，可把 `boundary_status=partial`，未知的 audio / action 精确值写 `unknown`；不要为了候选完整度做整段 ASR 或逐帧精修。

只有以下情况在 Detail 就升级为 `supported`：精确边界本身会改变 D1 结论、没有精听就无法判断素材是否可用，或当前短段核验成本已经很低。方法仍是“先夹住，再读取决定性逐帧条 / 连续音画”，字幕或 ASR end 不能直接当自然切点。

D2 选中片段后，**Execute Step 0 — Selected Range Verification** 只读取 `selected range + handles`：

1. 用实际原声与连续画面核对 D2 选择，不重扫整个 Detail 区间；
2. 字幕和 waveform / signals 先定位，ASR 只在精确原话、speaker、重叠说话或最终字幕确有需要时对小窗口运行；
3. 校准 video/audio in/out、句首句尾、关键停顿、尾音 / 笑声 / 反应和必要 J/L-cut；
4. 把同一 boundary 的精确值、`evidence_refs` / reviews 与 `boundary_status=supported` 补齐，再生成最终 timeline / 授权；
5. 如果精听发现台词含义、主动方或上下文与 D2 选择冲突，停止并返回 D2。Step 0 可以校准边界，不能自行换素材或重写叙事。

schema 1.8+ 的 `ready_for_render` 只接受入选 boundary=`supported`；未入选的 partial boundary 可以继续保留，不要求补成最终态。

## 5. 被否决 / 未解决的问题：handoff 里一张表闭环

问题一律用唯一、稳定的 `question_id`，由 `detail-intervals.target_questions` → `structure-questions.csv` → `deep-observations.question_refs` 串联；每个目标问题至少被本 DI 一条观察回指，明确声明的来源、区间和节点须与实际关联一致。

任何实际关联到 Detail 的 `contradicted` / `unresolved` 问题都列入 `execution-handoff.md` 的 **Question Closure Ledger**（节点与实际关联一致，多个节点用分号分隔；标题须含 Question Closure Ledger 或“问题闭环”）：

| question_id | status | plan_node_id | 处理方式 | confirmed_by |
|---|---|---|---|---|

这是唯一的闭环记录。`unresolved` 还要在问题表写出具体缺口与 `next_check`。进入 `ready_for_render` 时，入选节点不能带 `unresolved` 问题；带 `contradicted` 问题须有具体处理方式和人工 `confirmed_by`。validator 会检查这些条件。

## 6. 执行方式

- 密集读图保持单一上下文，不拆给子代理；脚本、lint、文件生成可以并行。每完成一个 DI 即落盘。
- Detail 文件一出现，`validate_project.py` 就做结构检查（表头、ID、范围、引用、枚举），不必等到 E 完成。
- 用 `assets/benchmark-template.md` 记录读图、返工与写入耗时；声音额外记录 full-interval ASR 是否被避免、实际定向核听 / ASR 秒数，防止候选范围越长成本越高。

---

## FILE: `references/execution-package.md`

# Structure 异常、Detail 交接与 Execution Package

本契约补充现有 B / E / D2 / F / G，不新增阶段。原有 CSV 表头、证据、时间标签、Edit Boundary、对白保护、机器授权和渲染检查继续适用。

## 1. 输出契约与异常继续

First / Broad Structure 与 Detail Structure 的必需文件、字段和类型保持锁定。字段无法取得时，保留字段：CSV 文本使用原契约允许的 `unknown` / `not_applicable`，JSON 的未知数值使用 `null`；枚举保持原有取值。`none` 只表示已核实没有相应内容，不能表示工具失败。不得把所有字段改成 status 对象，也不得为填满字段补造人物、台词、时间、观察或核验。

在 `structure-exceptions.jsonl` 中另行记录无法满足的字段或产物；有异常时必须交付此文件，无异常时可以不创建。每行包含：

| 字段 | 固定要求 |
|---|---|
| exception_id | 稳定、唯一 ID |
| stage | B / C / E；对应原阶段，不新增阶段 |
| artifact | 受影响的项目文件名 |
| record_id | 既有行 ID；整文件异常用 `null` |
| field | 受影响字段；整文件异常用 `*` |
| status | `unavailable` / `uncertain` / `partial` |
| reason | 实际无法取得或无法确认的原因 |
| impact | `low` / `medium` / `high` |
| downstream_handling | 可继续什么、不能据此确认什么、需要怎样补查 |

模板见 `assets/structure-exception-template.json`；仅在实际发生异常后填写，不把模板示例当成观察。

输出异常后继续索引、整理、草案和交接，不因一个非核心字段或关键帧失败停住整个流程。无法观察的记录不得伪装成“已分析帧”；缺失区间仍进入 coverage。若没有实际观察行，保留规定表头，并在异常和 coverage 中报告缺口；不能用虚构行补数量。数值、ID 或源时间无法可靠获得时保留未知状态，不宣称该记录符合精确执行契约。

阶段未实际完成时保留 partial / pending；异常声明不等于将阶段改成 complete，也不豁免静态错误。核心素材不可用、文件损坏或时间轴无法解析时，暂停依赖它的动作并交付已完成部分；其他可独立完成的工作继续。采用证据不足或主线冲突仍按原规则回 D1 / E；进入正式渲染仍须通过全部既有门槛。

## 阶段出口交付文件

除本文件下文规定的 Detail / D2 专用产物外，每个大阶段完成都必须生成/更新根项目 `handoff.md`，使下一模型、会话或机器在没有当前聊天上下文时仍可继续。handoff 至少携带当前阶段 / Scope Lock、确认与 pending/stale、下一步、实际随附文件 manifest（路径 + SHA-256 + bytes）、project 状态 digest，以及 source signature / time mapping / locator。`project.json` 与 handoff 必须随包；机器更换后源 locator 允许变化，但先按 source signature + time mapping 重绑定。前向阶段切换前 handoff 必须对应当前阶段且未因产物变化过期。该要求不增加创意审批 Gate。

## 2. Detail 的真实关键帧

E 阶段固定交付 `keyframe-references.json` 及单独保存的核心关键帧原图（如 `keyframes/<frame_id>.png`）。原图与清单、handoff 一起交给 D2；不能只给九宫格、缩略图或接收方打不开的临时路径。通常选 1–3 张足以展示重要素材节点的真实画面，不追求配额，不给每个镜头抽一张。它们是事实层的视觉依据；字幕、动效与视觉规则由 D2 决定。

文件为数组，每条保留以下字段：`frame_id`、`source_id`、`timestamp_ms`、`image_ref`、`source_segment`（unit ID）、`narrative_role`、`notes`、`status`、`reason`、`impact`、`downstream_handling`。`timestamp_ms` 是 canonical source time，图片保留原片内容；不得生成或修饰一幅画面充当原片证据。相同关键帧继续使用既有 frame_id，另附对应 source 版本 / time_mapping 与 evidence refs 供回查。

`status` 使用 `available` / `unavailable` / `uncertain` / `partial`。available 必须对应实际可打开的图片和可靠源时间。图片提取失败时 `image_ref=null`，保留已知定位，写原因、影响与下游处理，并同步异常声明；源时间也不可靠时 `timestamp_ms=null`。若没有可定位的候选帧，交付空数组并声明产物级异常，不编造 K1 或图片路径。模板见 `assets/keyframe-reference-template.json`，模板不是已提取图片。

## 3. Detail → 外部 Director 2 的交接

Detail 不替 Director 生成最终方案，但交付必须在没有安装本 Skill 的环境中也能独立阅读。使用 `assets/execution-handoff-template.md` 生成 `execution-handoff.md`，与证据表、关键帧清单、实际图片及必要源素材入口一起交付；这个包是 E 阶段产物，不是额外步骤。

交接至少包含：

1. Narrative Context：已确认主题、内容目标、情绪路径、人物关系、必须保护的原话 / 画面与禁改项，引用既有 Narrative Direction，不新写成事实。
2. Selected Clip Structure：segment / unit ID、source ID / 版本 / 时间映射、源区间、叙事用途、采用证据、context / protected ranges、edit boundary 与未验证项。
3. Keyframe References：清单、可访问图片、源时间、素材节点与用途；无法提供图片的异常随包携带。
4. Next Stage Requirements：**直接写入**下节要求的 Execution Package 组成、完成标准和边界。不能只写“按 Skill 继续”，也不能只给接收者无法读取的安装目录链接。
5. 文件清单与资源可达性：附带什么、还缺什么、源素材如何访问；确认传出的图片 / 证据文件实际包含在交接中。此前日志只作来源，不改写为下一模型的亲眼观察。

外部 Director 优先复用此包，按缺口局部回查；不因换模型重扫全片，不重做已确认的 D1。

## 4. Director 2 的 Execution Package

按 Visual Methods 选择制作方案或备选方法。参见 [制作方法、Blender 工程与动态验证](visual-production.md)：模型先说明每个关键处理的叙事作用、视觉问题、视觉重点、原画判断、选择依据、参数及失败情形；已有方案用 Visual Methods 校正，没有成熟方案时必须通过 Router → 完整方法 / fallback 提出可制作候选；工程与真实连续 demo 在正式 Execute 前确认，但采用**代表性风险验证**：默认仅 `proof_composition_ids` 生成工程 / Dynamic Demo / Proof / readback / receipt / review，不能把计划中的每个 Blender production window 都变成前置 demo。完整 `composition-plan.json` 仍在 Production Lock 时冻结；其余 composition 在最终授权后按已锁定实现一次性正式渲染。没有执行能力时明确缺口并保持 Gate pending。

D2 保留 Editorial Execution Plan，交付升级为 **Execution Package**。最小组成是 `execution-plan.md` + `execution-reference.md` + 采用素材 / Detail 证据与关键帧入口。`execution-authorization.json` 仍用于正式执行；若 D2 位于外部模型 / 会话，可先交确认的创意决定与允许校准范围，待 Execute Step 0 得到最终 source in/out 后再准备 / 确认机器授权。允许引用既有文件，无需复制素材库。

| 组成 | 执行前写清的内容 |
|---|---|
| Editorial Execution Plan | 最终取舍、顺序、逐段 **planned source range + boundary ref**、速度 / 画面处理、保护范围、总长与各段预算；允许 Execute Step 0 在 safe windows / handles 内校准什么；实际文字、音轨、转场及其余允许调整 |
| Visual Treatment Reference | 基于真实关键帧的实际 mockup 及全片规则；按目标输出画幅展示原片裁切 / 缩放、画面占比、文字与人物 / 原字幕关系，以及本次采用的相片页 / 录像框等版式 |
| Text Treatment Rules | 各类文字的字体 / 可用字体文件或确定替代、尺寸及单位、字重、颜色、描边 / 背景、位置 / 对齐、行数 / 换行、动效与阅读时间；绑定输出分辨率 |
| Audio Treatment Rules | 原声 / 环境音 / BGM / 旁白的采用政策；每条音轨取段、源与成片锚点、增益、速度、淡化及完整对白保护；不默认加 BGM |
| Transition Rules | 具体接点使用 cut / fade / black card 等什么处理及帧数；真正增时的卡片 / hold 计入事件和预算 |
| Reference Application Rules | 用一两个代表性风格参考锁定文字层级、位置、画面关系、情绪强调和视觉密度；按相同规则扩展到全片 |
| Asset / Constraint Mapping | 素材、字体、关键帧、mockup、布局生成入口及必要资源的文件入口；禁改项、可调整项、缺失项及降级处理 |
| QA Criteria | 内容 / 保护范围、实际文字与阅读时间、音轨 / 接点及 Reference Compliance 的判据；未经播放的项不得填通过 |

使用 `assets/execution-plan-template.md` 和 `assets/execution-reference-template.md`。参考文档是执行规格，不只是“简洁 / 有情绪 / 字体大一点”等意图；逐条文字与素材时间放在计划，重复使用的样式放在 reference，二者相互引用。没有某层时写 not_applicable 及原因，不为满足标题额外制作。

保留 event anchor + local frame 的坐标表达；预计成片坐标只能标为计划值，正式 output frame 由现有编译器给出并对账。不能把 source time 当成成片时间。

本节是 mockup / Visual Gate 规则的唯一完整出处，模板与其他文档只保留字段或摘要。

### Selected Range Verification：Execute 的第 0 步

D2 的 selected range 是**内容选择**，不是强迫外部 Director 在没有最终执行工具的环境里给出帧级终值。回到实际 Execute 环境后，只对 D2 已采用的片段及其 handles 做精校：连续音画优先，subtitle + waveform / signals 用于定位，ASR 仅在精确原话、speaker、重叠说话或最终字幕需要时对小窗口运行。

Step 0 复用现有 `edit-boundaries.csv`、`reviews.jsonl`、`transcript.jsonl` 和 timeline，不新增 audio closure 文件或阶段。它需要：

- 校准最终 video / audio in/out、句首句尾、关键停顿、尾音 / 笑声 / 反应及必要 J/L-cut；
- 对入选 boundary 补齐适用的 audio / action 精确值、review evidence，并把 `boundary_status` 从 `partial` 升为 `supported`；
- 对真正采用的 utterance 才要求当前原声核听 / audio review；完整 ASR 不是默认动作；
- D2 先把 planned range、boundary ref、当时 safe windows 与允许调整写进 timeline 的 `d2_selection_snapshot`。Step 0 只在这份快照内做技术性边界校准；越界、扩大 safe windows、换 boundary，或发现原话含义、主动方、上下文 / 素材身份冲突时停止并返回 D2，不自行换段。

schema 1.8+ 的 `ready_for_render` 将 selected boundary=`supported` 作为硬门槛；未入选的 partial boundary 可继续保留。Step 0 后再按最终 ranges 准备 / 确认 execution authorization，从而同时保留跨模型 D2 的创意锁定和实际执行环境的精确切点。

### Runtime Contract

Direct 2 在制作 Mockup 前先关闭 `reference_routing`。公开版新项目中，这一 Gate 的事实源是 `visual/V0→V2`：V0/V1 必须完成，V2 逐项在 `no_ref_needed` 说明如何用当前素材校准方向。V0 `design_scope` 决定探索强度：只有 `explore_new` 强制 2–3 套候选；`reuse_confirmed` 单案必须绑定此前真实 V6/V7/confirmed-artifact，且图文关系、动效语言、几何策略变化时必须回 `explore_new`；`simple_text` 可单案。V3 可选择 `representative_first`，先验证覆盖不同版式与困难条件的关键帧，选定后再扩展；standard deferred 镜头可沿用，difficult deferred 镜头必须在 V7 以前产生实际成图并通过尺寸/画布/字号/对比度/保护区 QA。公开版 `explore_new` 的 V5 必须做同素材、同文案、同画幅且声音不变的 baseline vs candidate A/B；small-screen + do-not-transfer 保留，blur/squint 与 blind-map 条件式。V6 可复用现有 Mockup Gate 的同一次真实决定，不增加审批次数；V7 冻结参数，所有 rect 必须位于 canvas 内。

V7 之后、进入 Proof 前必须完成 `implementation-lock.json`。该文件把已确认视觉方案编译成机器可消费的构造合同：`visual_stage_binding` 绑定当前 V7 bytes + chosen candidate，`confirmed_mockups` 精确绑定 V6 选中候选的全部实际 artifact；renderer / entrypoint、element ID、event scope、crop / rect / font / color / z-order / motion 等仍是现有执行参数。V7 每条 `structure_card + transfer + element + parameter_path` 必须逐条桥接到 Implementation Lock 的真实 `target_element_ids` / 可解析 `parameter_paths`，否则 `method` / `build_composition` 保持 blocked。

`composition-plan.json` 必须显式绑定同一 `implementation_lock_ref`，每个 composition 还要列 `implementation_element_ids`；`proof_composition_ids` 只选最小充分的代表性风险验证集合（通常一个）。任一 Proof 若可被其他 Proof 按 mode、Implementation Lock elements、methods、join（native_blend 再含 native scene/dependencies）机械覆盖，会被判为冗余；完全等价时保留列表靠前者；只有机器无法表达的素材级风险可用显式 `additional_proof_exception` + shown evidence 例外。非 proof composition 必须用 `proof_covered_by` / `proof_coverage_reason` 指向某个代表性 Proof；不要求提前生成 demo / proof / review；`native_blend` / `layers` 的 renderer 必须和这些锁定元素一致。若 Mockup 锁定 `native_blend`，Execute 不能为了方便改成 layers 后声称“效果类似”；实现不了就返回 D2。Production Proof Lock 通过时再形成 `workflow_control.production_lock`，把当前 Implementation Lock、Reference application chain、Proof / Composition、`execution-reference.md#Production Lock`、delivery spec、文字与旁白 policy 一起冻结。

### Visual Reproducibility Gate

原片关键帧证明“画面有什么”，保持原图独立。Visual Gate 分两步，但**不新增工作流阶段**：

1. **Aesthetic Mockup**：D2 基于真实关键帧、实际采用文字和目标输出画幅制作一两个可打开的视觉方案，用于选择“我们想长成什么样”。这一层可以使用图像生成模型或其他审美探索工具；确认后把选中的文件写入 `project.visual_mockup_ref`，状态可记 `mockup_confirmed` / `awaiting_proof`。它只是审美意图，不证明可执行。
2. **Executable Proof Frame**：随后用**最终 Execute 真正可访问的同一实际执行工具链**，严格消费当前 `implementation-lock.json` 重建 proof + continuous demo。proof 可以在另一个模型、会话或执行环境补完；模型连续性不要求，工具链与 Implementation Lock 连续性要求。确认后把第一个代表性 Proof 保持在兼容字段 `project.visual_proof_ref`；多 Proof 时同时记录 `project.visual_proof_refs` 全量列表，状态设为 `proof_confirmed`。 如果 Mockup 本身已经由最终工程工具链生成，允许通过 `project.visual_proof_reuse={mode: reuse_engineered_mockup, ...}` 让静态 Proof 复用同一内容，但必须绑定实际 `engineering_evidence_refs` 且这些文件属于 `execution_reference_asset_refs`；没有工程凭据仍阻断。该复用不取消 continuous Dynamic Demo、执行 readback/receipt 或 QA。

Visual Gate 可以在 `mockup_confirmed` / `awaiting_proof` 状态继续完成文案、计划、音轨和其他 Execution Package 内容，但采用视觉设计的任务**不得在 proof 确认前进入正式 Execute / ready_for_render**。完全不需要额外视觉设计时明确设 `visual_gate_status=not_applicable`。

Toolchain Continuity 直接复用项目已有 `capability-map.json`，可从 `assets/capability-map-template.json` 建立，不另建 visual-style 或 toolchain 文件。Detail handoff 必须把与执行有关的 capability / actual_tool 带下来；D2 在 `execution-reference.md` 记录 inherited execution toolchain、proof 实际使用的 tool / entrypoint 与 final Execute toolchain。proof 的核心实现能力、字体 / 资源和布局入口必须是最终 Execute 可访问的同一套。若现有工具链无法实现已选 mockup，Gate 保持 open：要么调整 mockup，要么正式更新 capability-map、execution-reference 和最终 Execute 路径后重做 proof；不能临时用一个下游不可用的工具做漂亮图再当 proof。

在 `execution-reference.md` 将 selected mockup / proof、原片 frame_id、style / layout ID 与适用范围绑定。交付字体文件或确认可用的字体及明确替代（商用发布时注意字体授权：不少商用字库不允许再分发或未经授权商用，打包或烧录前确认，必要时改用开源字体）、字号 / 字重、断行 / 字距 / 行距、颜色、描边 / 阴影、坐标 / 对齐和边距；采用特殊版式时再写图片置入矩形 x/y/w/h、crop / fit、边框 / 圆角 / 间距、图层顺序与符号参数。尺寸绑定输出画幅，位置注明坐标原点与单位；时间仍在计划中绑定 event anchor + local frames。

selected mockup、proof、`implementation-lock.json` 都加入 `execution_reference_asset_refs`，因此样稿、proof、Reference application trace 或执行资源变化会沿用既有 Direct 2 指纹失效机制。proof 确认后 Execute **不得重新解释 aesthetic mockup**：只替换实际内容并执行 Implementation Lock 已声明的安全适配；字体层级、基本区域、框体、颜色关系、crop 逻辑、renderer、运动方法和素材角色都不能重新设计。

真实关键帧或出图能力缺失时，明确 mockup / proof 尚待补齐及原因，先交可做部分；不生成替代画面冒充原片。缺口随包传递，依赖该视觉的制作前必须关闭 Gate。

**不要求每个字幕、镜头或主要视觉动作逐项映射一个 reference；逐镜头内容与时间仍写入计划。** 一两个样本用于提炼 Design Rules 并保持全片一致。

## 5. 与原工程入口的衔接

新项目的 project 设置 `execution_package_policy="plan_and_reference"`，并保存 `structure_exceptions_ref`、`keyframe_references_ref`、`execution_handoff_ref`、`execution_reference_ref` 和 `execution_reference_asset_refs`。v1.2.2 只新增三个轻量 Visual Gate 字段：`visual_gate_status`、`visual_mockup_ref`、`visual_proof_ref`；不新增 current-state、visual-style 或 music gate 文件。project schema 在 v1.2.3 升到 1.8：继续强制 Visual Gate，并要求正式渲染前完成 selected-range verification；timeline / authorization schema 与正式 CSV 不变。

`visual_gate_status` 允许 `not_started`、`mockup_confirmed`、`awaiting_proof`、`proof_confirmed`、`not_applicable`。schema 1.7+ 新项目必须使用 `execution_package_policy=plan_and_reference`，且三个 Visual Gate 字段必须存在；Detail complete 时须有关键帧清单和独立 handoff。schema 1.8+ 允许候选 edit boundary 在 Detail 以 `partial` 交付，但 `ready_for_render` 时每个入选 boundary 必须经 Execute Step 0 升为 `supported`。ready_for_render 仍须有非空 reference 文档及实际参考资源，并要求 Visual Gate=`proof_confirmed` 或 `not_applicable`。`proof_confirmed` 时 selected mockup、executable proof、`implementation-lock.json` 与 `capability-map.json` 都列入 `execution_reference_asset_refs`；Implementation Lock 必须绑定当前 Mockup bytes，且每个 selected REF 都必须有可解析的 application trace。schema 1.6 旧项目保持原兼容行为；schema 1.7 项目继续沿用 v1.2.2 的 boundary 行为，只有 schema 1.8+ 才要求入选 boundary 在正式渲染前完成 Step 0 并升为 `supported`。

准备 draft 时继续追加 `execution_reference_digest` 和 `execution_reference_asset_digests`。mockup、proof 与 reference 都进入既有指纹；它们改变会使既有 Direct 2 确认和旧渲染入口失效。机器只检查状态、文件、指纹与入口声明是否齐全；proof 是否真的由所声明的同一工具链生成、视觉是否好看，仍须由负责确认 Gate 的人 / 模型审阅。新机制不自动确认草稿，也不改对白保护、源许可、时间轴算法或缓存边界。

未得到的事实通过异常声明携带，不能靠重新计算指纹变成有效证据。

## 6. Reference Compliance

在现有 G / EVA 中增加 `ReferenceCompliance` 检查：全片是否遵守已确认的文字层级、位置、字号 / 颜色、画面关系、情绪强调、动效 / 转场及禁止事项。对照一两个样本和全片规则，不逐镜头核配对数量。声音另按既有 Audio 检查和本次音轨规范复核。

QA 从成片中截取与 executable proof 同一版式的代表画面（不要求逐帧对应），直接对照 selected mockup + executable proof + Implementation Lock。`ReferenceCompliance` 必须记录当前 selected REF IDs、mockup / proof / implementation-lock 的 SHA-256 与证据路径，核对 source role、crop、版式比例、字体层级、颜色角色、运动方法和不可照搬项。`r1=r2`、像素 diff=0 或“包含 mint / violet / 三张图”只能证明可复现或元素存在，**不能**证明 Design Fidelity。

qa 每项仍用原字段 name、status、method、evidence、finding、action。静态规则检查与实际导出观看分开；没有真实导出或没有实际对照查看时写 not_tested，参考图提取成功和脚本成功都不等于全片风格通过。

---

## FILE: `references/execution-integrity.md`

# 执行完整性契约

目录：证据绑定、Direct 2 机器授权、声音连续性、源范围、创作例外和正式编译。

保留 Broad → Structured Observation Layer / Content Map → Direct 1 → Detail → Direct 2 → Execute → QA。这里只把现有证据与已确认决定接入实际执行，不新增创意阶段。

## 1. 证据绑定

实际审阅或观察时保存两个 SHA-256 指纹，算法见 `scripts/execution_integrity.py`：

- `source_signature`：canonical JSON 的 source_id、version、duration_ms；locator 移动不改变素材身份。
- `time_mapping_digest`：canonical JSON 的完整 source.time_mapping。

进入 ready_for_render 时，这两个字段必须存在于实际采用的 Deep observation、edit boundary、review、unit.verification、utterance、source event 和源音轨。Deep 与 boundary 的 CSV 只追加上述字段；原有列和职责保留。尚未采用的 pending / contradicted observations 不会因同属一个 unit 而阻断当前事件。

每个 source event 增加：

```json
{
  "event_id": "E001",
  "source_id": "SRC001",
  "source_signature": "<本次实际核实版本的指纹>",
  "time_mapping_digest": "<本次实际核实映射的指纹>",
  "deep_observation_refs": ["DO001"],
  "adopted_observation_refs": ["DO001"],
  "edit_boundary_ref": "EB001",
  "adopted_boundary_ref": "EB001",
  "evidence_status": "supported",
  "source_constraint_ref": "source:SRC001"
}
```

新旧引用字段须一致。观察区间覆盖实际取段；status 为 supported / partial。review 仅在 result 为 reviewed / pass / passed，reviewer 与 evidence_locator 具体非空、模态与区间覆盖适配且指纹一致时计入成功核查。

`python3 scripts/execution_integrity.py PROJECT` 只计算源、映射、约束、采用证据与授权记录指纹。它不观察视频、不签署确认，也不更新任何旧记录。源版本或映射变化后先重核采用证据；仅把旧行的指纹改成新值不构成重新核实。

## 2. Direct 2 机器授权

`execution-plan.md` 保留编导表达；完整执行包同时包含 `execution-reference.md` 与实际采用的少量风格样本。`execution-authorization.json` 保存同一已确认包的可检查范围。Project 增加 `execution_authorization_ref` 和 `execution_authorization_digest`。后者是完整授权对象 canonical JSON 的 SHA-256。

| 字段 | 作用 |
|---|---|
| authorization_id、version、project_id、project_version | 稳定确认记录与对应项目版本 |
| status=confirmed、confirmed_by | 当前用户 / Director 已确认决定的记录；draft 不允许正式编译 |
| execution_plan_digest、narrative_direction_digest | 两份 Direct 文件的原始字节 SHA-256；改动使旧确认失效 |
| execution_reference_digest、execution_reference_asset_digests | 已声明 reference 文档与实际样本的字节指纹；改动使旧确认失效，未声明的新字段不改变旧项目授权 |

> schema 1.7+ 继续执行 Visual Gate；schema 1.8+ 还要求 ready_for_render 的每个入选 edit boundary 已在 Execute Step 0 升为 `supported`。D2 若位于外部模型，timeline 草稿先保存 `d2_selection_snapshot`（planned in/out、boundary、safe windows、允许调整）；Step 0 只能在该快照内校准，越界即停并返回确认。最终 authorization 在 Step 0 得到真实 source in/out 后准备 / 确认，并把 snapshot 与最终 event 一起锁进 event spec。proof_confirmed 仍要求 mockup / proof / capability-map 进入既有 asset digest。
| selected_events、sequence | 所有 event ID 的有序列表，包括 card；与 timeline 必须一致 |
| allowed_units、allowed_boundaries | 可采用的明确 unit / boundary ID 列表 |
| event_specs | 逐 event 已确认字段快照；assembly/output 坐标由编译推导，card 时长另存 card_duration_frames |
| allowed_adjustments | 逐 event 的列表：默认 []，可明确允许 trim_inside_safe_window / add_transition_handle |
| audio_specs、text_specs、transitions | 已确认的音轨、文字和接续；Execute 不得自行替换 |
| output、audio_policy | 已确认输出规格、声音要求 |
| source_bindings | 采用源的 source_signature、time_mapping_digest、source_constraint_digest |
| evidence_digest | 采用 observation / boundary / unit / utterance / review 的 canonical 快照指纹，含每条源音轨独有的 utterance 及其 review |

使用 `prepare_execution_authorization.py PROJECT` 从当前方案准备 draft。schema 1.8+ 若 D2 交付时 selected range 尚待执行环境精校，先保持 timeline draft；Execute Step 0 完成后再用最终范围生成 authorization draft。脚本不会确认，也不会刷新 evidence；已有同名 draft 不会被覆盖。人工 / Director 对照已确认方案核对取舍、顺序、处理和例外，在授权范围内补 authorization_id、confirmed_by、status 并保存正式文件；不要把 draft 自动升为 confirmed。随后计算授权指纹并写入 project。

`allowed_adjustments` 不允许变更 source、unit、boundary、采用证据、速度、叙事功能或其他字段。safe trim 只能缩短既定范围，add_transition_handle 可在已核实 safe windows 内扩展；两者均不能越过源许可或保护区间。原声 locked 轨可以随已允许的安全裁剪调整源端点和 local frame，其余处理仍须一致。文字 / 接续变化按既有授权重新裁决并更新对应确认记录。改变取段后须按累计量化更新 locked 音轨、文字显示范围和 duration_budget；编译器不会自动替方案改写这些依赖字段。

机器记录将用户已有授权具体化，不增加固定确认关卡。名字、状态和指纹可以检查一致性，不能证明填表者身份或自然语言意图真实；实际决定来自本轮用户 / Director 指令。

## 3. 声音连续性

对白约束由实际采用的 utterance、unit.audio_state.speech=true 或 dialogue / mixed boundary 触发，continuity_type 只说明主要连续性，不能关闭保留对白政策。每个 ready source event 明确写 `adopted_utterance_refs`；检查对象还包括同源 transcript 中与实际视频取段或任一采用源音轨相交的对白，不由待验证的 audio_start_ms—audio_tail_end_ms 筛掉。逐源音轨推导不依赖 audio_source_refs 或 sync_event_id，卡片声音、未关联音轨及异源仅音频同样检查。取段外且未明确采用的对白不强行加入成片。

每条应检查的 utterance 先核对引用、来源、当前版本、audio_verified=true 及覆盖整句的有效 audio review，再核对保护范围与可听音轨。缩小自报保护范围、漏列第二句、清空采用列表均不能跳过这些检查。

使用现有 CSV 的 `dialogue_required_range`，按 `start-end;start-end` 源毫秒格式覆盖 audio_start_ms 至 audio_tail_end_ms 及采用的完整 utterance。event 增加：

```json
{
  "adopted_utterance_refs": ["T001"],
  "audio_boundary": {"required_start_ms": 1300, "required_end_ms": 5800},
  "dialogue_required_range": "1300-5800",
  "sync_mode": "locked",
  "audio_source_refs": ["A001"]
}
```

每个采用的源音轨保留 source_signature、time_mapping_digest、source_constraint_ref，并确定 speed（默认 1）、gain_db、fade_in_ms、fade_out_ms、treatment，以及独立的 `review_refs`（reviews.jsonl 中的 review ID 数组，如 ["R001", "R002"]）。与视频同步时另明确 sync_event_id、sync_mode。成功的同源、当前版本 audio reviews 按半开区间并集合并，必须覆盖完整 source_in_ms—source_out_ms；相邻覆盖可合并，1ms 缺口也不放行。音轨采用的 utterance、其专属 review 及音轨全范围 review 同时进入 evidence_digest，改动后原确认失效，重新编译仍须检查当前证据资格。外部 asset_ref 音轨沿用原契约，本补丁只加强 source_id 音轨。

对白采用 kind=original、narrative_role=dialogue_information，treatment=preserve / isolate。保护某源对白时，不能用另一源或 music 冒充；另一源完整且核实的对白可作为独立音轨采用。muted 或 gain_db≤−80 会被当作实际静音阻断。无效处理或错位的轨道不计入保护范围的可听覆盖。具体可听性仍由最终核听判断。

源音频时长 / speed 与最终 output frame 时长的差最多一输出帧；音画映射在对应源时间处允许最多一帧量化误差。淡音区间不能覆盖保护对白；被采用轨的淡音后源区间并集须覆盖完整 required range。

- locked：源音轨位于对应 event 的 output 区间内，并保持源时间同步。
- J_cut：音轨开始早于对应视频 event，保持源时间映射；需要明确 audio_transition override。
- L_cut：音轨继续到对应视频 event 之后，同样需要 audio_transition override。

J/L-cut 可跨 card / 邻接 event，但不能跨出最终成片总范围。audio_transition 说明已审阅的接续决定，不能替代新增源音频区间的完整核听。创作删句或截尾必须针对被改变的整句 / 保护区间提供有效 audio_required_range override，分别检查声明范围与实际可听范围；普通 boundary override 不自动豁免音轨，也不能把未核听区间升级为已核实。unit.protected_ranges 的意义保护仍不可被该 override 自动取消。

独立源对白按以下适用关系处理，不需要新增视频事件或正式表：

| 音轨关系 | 保留及例外归属 | 同步要求 |
|---|---|---|
| 出现在同源 source event 的 audio_source_refs | 沿用该 event 的完整对白 / boundary 覆盖、原因和例外；逐轨仍检查 utterance 证据 | 保留既有 sync_event_id、locked / J_cut / L_cut 与源时间映射检查 |
| 卡片声音、未列入同源 event 的音轨、异源仅音频 | track 负责完整 utterance 的可听覆盖、政策原因及 audio_required_range 例外 | 按源取段、speed 与最终 output 位置对账，允许异步；anchor_event_id 只锚定位置，不证明口型同步 |

独立轨可选写 adopted_utterance_refs（唯一 ID 数组），明确采用取段外对白时也接受完整检查；实际取段内已知对白自动加入，漏列或 [] 不能免检。每句须由同源、同 speed 且源时间到成片时间映射一致（最多一帧量化差）的有效保留轨覆盖；可跨卡片接续同一句，不能拿另一成片位置的一次完整播放来掩盖本次截句。淡音后的源区间并集用于覆盖计算。独立截句例外放在 track.overrides，target_id 为 track_id，audio_required_range 的 target_range 覆盖受影响整句，核听与确认要求同第5节。已关联 event 的创作决定不要求再复制一份 track 例外。

若本轮明确改为 `audio_policy.preserve_dialogue=false`，对应 event 或独立对白 track 必须有具体 `dialogue_policy_reason` 并进入 Direct 2 快照；此时允许已确认的无对白处理。已采用对白的证据和源音轨完整核听仍须有效。没有对白时使用已核实的无语音元数据及适配 review，不凭改标签宣布不适用。

## 4. 实际源范围

Project.source_scope 是明确允许采用的 source ID 列表。每个 source 的 usable_ranges 必须覆盖最终视频和源音轨采用范围，按半开区间并集合并；存在 allowed_scope 时也须落在其并集内。context 回查不因此扩大成片范围。

可机器处理的 downstream_constraints 对象支持 `type=exclude_range` / `allowed_range`，使用 start_ms / end_ms 或 ranges 数组。未知 typed 规则拒绝正式执行；自由文字约束仍由用户 / Director 核对。

source_constraint_digest 覆盖 source_scope、usable_ranges、allowed_scope 和 downstream_constraints。确认后修改约束，使原 Direct 2 源绑定失效。

## 5. 具体创作例外

event / track / transition 的 `overrides` 必须是对象数组。字段如下：

```json
{
  "override_id": "OV001",
  "target_id": "E001",
  "type": "creative_exception",
  "target_range": {"source_id": "SRC001", "start_ms": 5600, "end_ms": 6200},
  "violated_rule": "safe_out_window",
  "evidence_ref": ["review:R001"],
  "reason": "尾部采用突然结束的处理",
  "creative_decision": "本轮 Direct 2 明确采用该截尾",
  "approved_by": "<对应 confirmed_by 的实际决策者>"
}
```

规则限 safe_in_window、safe_out_window、boundary_must_keep、audio_required_range、audio_transition、protected_overlap。target_id 对 event 为 event ID，对独立音轨为 track ID（audio_required_range），对 transition 为 `E001->E002`；target_range 必须覆盖实际受影响的源区间。evidence_ref 必须解析到同源、当前版本、成功且覆盖相应区间 / 模态的 review。approved_by 与 Direct 2 确认记录一致，override 内容须在其快照中。none / unknown / 空依据及无关 review 均不能放行。

普通越界仍保留原 boundary_override、boundary_override_reason、boundary_override_review_refs，新增具体 overrides 提供真正放行依据。叠化覆盖保护画面时，用 transition.overrides 的 protected_overlap，不能只填 overlap_protection_review 自由字符串。

## 6. 正式编译与入口检查

```sh
python3 scripts/validate_project.py PROJECT
python3 scripts/compile_render_manifest.py PROJECT
python3 scripts/check_render_authorization.py PROJECT PROJECT/render-manifest.json
```

正式清单包含 render_allowed=true、eligibility=validated_for_render、timeline_status、render_authorized、authorization digest、input_digest、manifest_digest。渲染适配器应在实际消费前调用最后一步，防止编译后 evidence / plan 改动或清单被改写。外部渲染器须接入此入口；不能声称已经控制绕过入口的任意第三方渲染器。

规划草稿用 `compile_render_manifest.py PROJECT --planning`，清单携带 render_allowed=false / eligibility=planning_only。规划编译不授权渲染。所有模式的 playback_verified 保持 false；原 render audit、全部接点检查与最终听看继续执行。

---

## FILE: `references/visual-production.md`

# Visual Methods、Blender 合成与动态验证

目录：职责与交付、方法决策、合成规格、Gate 顺序、实际命令、FFmpeg 回接、QA 与返工、能力和边界。

## 职责与交付

沿用 A → B → C → D1 → E → D2 → F → G，不另造创作阶段。新增交付是 D2 内的方法和动态验证，以及 F 内的局部合成回接。保留音乐形式、Mockup、静态 Proof、完整执行包、入选范围和最终授权的原确认。

| 工作 | 交付 | 完成判据 |
|---|---|---|
| 模型提出制作方法 | `visual-methods.json` + `implementation-lock.json`，在 execution-reference 中解释选择 | 叙事作用 → 视觉问题 → 视觉重点 → 原画条件 → 候选 / 处理选择 → 参数 → 失败情形 → demo 验证点；已选 REF 必须落到 Implementation Lock 的真实元素 / 参数；用户确认当前选择 |
| Blender 制作合成计划 | `composition-plan.json`、必要资源与每个最终 production window 的明确规格 | 全片需要的 Blender 段全部进入计划；但计划段数不等于预先 Demo 数量，非代表性段在最终授权后一次性正式生产 |
| 代表性 Blender Proof 工程 | `proof_composition_ids` 对应的实际 `.blend`、原生状态 readback | 用最小充分窗口验证图层、关联、运动曲线及前后镜头接点；实现不支持时保留缺口，不简化成别的效果 |
| 代表性动态验证 | 同一 Proof 工程渲染的连续 `*-demo.mp4`、静态 proof、技术 receipt、逐项 review | 正常速度看完整进入、运动、退出及接点两侧，听相关声音；问题已修改，用户确认当前代表性工程和 demo |
| 回到既有 FFmpeg 流程 | 当前 manifest、clean-video、已确认 mix、delivery-spec、最终 MP4 和 delivery receipt | 用明确输出帧区间接回已验证合成段；不改其余镜头，不增添音乐，不重复扣除转场时长 |
| 成片 QA | 原 qa、render-audit、ReferenceCompliance，加 CompositionCompliance / MotionContinuity / DeliveryTechnical | 同一版成片的真实观看和技术检查均闭合；导出成功不代替审美或内容验收 |

代表性 Mockup / Proof 仍只做**最小充分验证**。`proof_composition_ids` 按关键处理与接点风险选择一个最小充分的代表性 Blender composition 集合；**composition 数量不等于 demo 数量**。多个生产段若复用同一已锁定实现方法，可由其中一个 proof 覆盖，不得因为计划里有 C01/C02/C03/C04 就在 Execute 前把四段全部预渲染成 demo。只有出现 materially distinct、尚未验证的实现风险时，才回 D2 调整代表性 proof 范围。

**覆盖不是自由文本声明。** 每个非 proof composition 必须显式写 `proof_covered_by`（且值属于 `proof_composition_ids`）与非空 `proof_coverage_reason`。Runtime 使用同一 `composition_covers()` 规则机械要求：目标段与所指 Proof 的 `mode` 相同；目标 `implementation_element_ids` 是 Proof 的子集；目标 `method_ids` 是 Proof 的子集；目标若包含 join，则所指 Proof 也必须实际包含 join；`native_blend` 还必须复用完全相同的 `native_scene_ref` 与 `native_dependency_refs`，只允许窗口位置不同。任一条件不成立即阻断并返回 D2。`proof_scope_policy` 缺省也不能省略覆盖关系。

**Proof 集合自身也必须最小充分。** `proof_composition_ids` 中每个 Proof 都与任一其他 Proof 按上述机器维度比较：只要被另一个 Proof 机械覆盖，默认视为冗余并阻断，要求改为 production composition + `proof_covered_by`；两个 Proof 完全等价时只保留列表靠前者。只有素材遮挡、具体画面读性等机器元数据无法表达、但确实需要额外动态验证的情况，才允许在该 Proof 写 `additional_proof_exception={kind: material_specific_unmodeled_risk, reason, evidence_refs}`；`evidence_refs` 必须是真实文件，并会进入 Proof / Composition 确认的 shown-artifact 绑定，不能静默追加 Proof。

## 方法决策：Visual Methods 是知识底座与兜底，不是新流程

从 `assets/visual-methods-template.json` 填写本片实际 Project Method。每条绑定 event IDs 和 Detail 证据。交付简短选择依据，不写无依据的心理事实。不把“对视”固定映射成放大：先看原画是否已足够、是否需要保留双方反应和视线关系，再决定保持、停留、裁切、移动或合成。

D2 先判断**当前视觉问题**。已有具体方案时，用 [Style System](style-system.md) 和 [Visual Router](visual-methods/index.md) 校正、深化；公开版新项目采用视觉设计时，在进入 Mockup 前按 [Visual Reference Router](visual-reference-router.md) 完成 `visual/V0→V3`：V0 登记真实 keyframe / copy，V1 先测量问题并在参考选择前做 `direction_hypothesis`，V2 用当前项目源帧、文案和验证计划校准方向，V3 用 `direction_read` 深化全局基调，并让 candidate / per-shot 承接具体观看逻辑，再写 Art Direction、最后定参数；出现以下任一情况时，Visual Methods 承担 production-method 兜底职责：

- 方案只有“高级 / 电影感 / 综艺感 / 克制 / 大字 / 放大 / 加字幕”等抽象词；
- 方案是常见默认处理，却解释不了为什么适合当前真实关键帧；
- 人物、动作、原字幕、构图或画幅使原方案无法落地；
- 用户要求更强视觉完成度，而现有方案没有足够具体的制作路径。

此时先用 Router 定位问题，**继续读取 `method-library.md` 中命中方法的完整条目**；需要稳妥替代或当前素材限制较强时读取 `fallback-recipes.md`。形成 1–3 个可制作候选（简单问题允许一个），说明各自画面 / 文字 / 色彩 / 运动 / 声音处理、工具需求与风险，再选择推荐方案。方法库提供组织方法，不替代当前项目的素材证据。

项目 `method_id` 与知识库 ID 分开：新项目使用 `PM001 / PM002...`；M01–M14 记录在 `library_refs`，F01–F09 记录在 `fallback_refs`。`candidate_treatments` 可记录候选比较。

**视觉验证范围。** `explore_new` 需要 2–3 个候选和代表性同源 A/B。`reuse_confirmed` 可单案，需绑定已有真实确认；图文关系、动效语言或几何策略变化时回 `explore_new`。`simple_text` 可单案。V2 逐项填写 `no_ref_needed`，无外部参考时不填写迁移 trace。V3 可先验证不同版式的代表帧，普通 deferred 镜头沿用已选方案，困难镜头须在 V7 前有实际成图与画布、字号、对比度、保护区 QA。保留 small-screen，按需启用 blur/squint 与盲审。V6 绑定用户决定与展示文件，V7 锁定可执行设计。Dynamic Demo 与 Proof 继续验证当前实现。

`parameters` 写本片的具体起止、幅度、速度或版式参数；`failure_modes` 至少写本次实质风险，`demo_checks` 写能观察的验收点。未确认的方法在 D2 组合选择；已确认方法在 Narrative 修订中持续保留，仅适配具名参数，改变方法使用原 D2 显式决策。外部参考只是候选依据，不决定统一外观。完整接入规则见 [Visual Methods Application](visual-methods/application.md)。

## 合成规格

V5 评审后停给用户；V6 confirmed + V7 PASS 后，复制 `assets/implementation-lock-template.json`，把 V6-confirmed Mockup 与 V7 reference trace 编译成实际 renderer、元素和参数；再复制 `assets/composition-plan-template.json`。`composition-plan.json.implementation_lock_ref` 必须等于 `project.visual_pipeline.implementation_lock_ref`，每个 composition 的 `implementation_element_ids` 必须指向该锁里的真实元素。profile 必须与 project.output 完全相同。所有区间是 **零起点、左闭右开输出帧**；Blender 内部一开始的帧号由适配器转换，不能再偏移一次。

- `anchor_event_id + local_start_frame + frame_count` 指定合成结果在正式 manifest 中替换的输出窗口。`local_start_frame` 是相对该 event **编译后起点**的偏移，不是源时间；完整窗口可以跨多个已选 event。
- `event_ids` 列出窗口涉及的实际事件，`method_ids` 绑定采用方法。
- `joins` 写每个关键接点的局部帧号、前后覆盖帧数、前后 event、cut_intent、outgoing_state、incoming_state、motion_handoff。硬切、顺势切和重叠按叙事选择；不默认加叠化或结尾停顿。
- `preview_audio_ref` 只要求在 `proof_composition_ids` 上提供，指向该代表性验证窗口的实际已对齐原声 / 已确认 mix。确实只需无声演示时明确 `silent_demo=true` 与 `silent_reason`；AudioContinuity 审阅记录说明适用范围，不默认加 BGM。非 proof production composition 不需要为了预审另做 preview audio。
- 对 `proof_composition_ids`，`scene_ref / video_ref / demo_ref / proof_ref / receipt_ref / readback_ref / review_ref` 是七个不同文件；每次改版使用新版本路径，保留旧文件。其余 production composition 在 Execute 后只要求正式 `scene_ref / video_ref / receipt_ref / readback_ref`；不要求提前生成 demo / proof / review。
- `proof_composition_ids` 选择**最小充分的代表性风险验证集合**；通常只有一个。任一 Proof 若被其他 Proof 机械覆盖会被判为冗余；完全等价时保留列表靠前者；真正互不覆盖的实现风险才直接增加 Proof。只有机器无法表达的素材级风险可使用显式 `additional_proof_exception`，且必须绑定展示证据。每个代表性 proof 渲染成功后，脚本只登记该段的 proof 与 measured capability，状态为 awaiting_proof，绝不自动确认；非 proof composition 默认延后到 Execute，在最终授权后按 Production Lock 一次性渲染。

### 两种实现方式

**layers：随包固定 2D 适配器。** `layers` 按从底到顶排序，支持 image、video、color、text；每层有唯一 layer_id、kind、start_frame、end_frame。图像 / 视频使用 asset_ref，fit 为 cover / contain / native；视频先通过现有 FFmpeg 规范化到相同 FPS，source_in_frame 是规范化输入的零起点帧。原声独立处理。

位置 x/y 是相对画布中心的像素位移，x 向右、y 向上；scale 为统一缩放比例，rotation 为角度，opacity 为 0..1。每层 transform 为起点；keyframes 为 `{frame, values, easing}` 列表，values 可含上述字段。easing 使用 linear / smoothstep / ease_in / ease_out / hold，作用于到达该关键帧的区间。最后状态保持，不自动复位。固定适配器将计算值写入原生关键帧，并回读实际帧值。

`groups` 是命名的 transform / keyframes 对象，layer.parent 可引用；组也可引用父组。统一缩放、位移、旋转、透明度按父子关系组合；检测缺失和循环。关联层随组一起运动，避免框体与内容漂移。当前适配器使用中心锚点，不支持任意锚点、非统一缩放、透视或声明外的效果。

**native_blend：已有原生合成工程。** 通过已核实的 Blender MCP 或 Blender Python 做复杂蒙版、跟踪、节点合成或其它视觉处理；登记 native_scene_ref、native_start_frame 和所有 native_dependency_refs，再用同一适配器渲染、检查和交付。原生工程不得依赖未声明的外部素材 / 字体。一个 deferred native_blend 只有在 `native_scene_ref` 与 `native_dependency_refs` 都和所指 Proof 完全一致时才算复用同一工程；换 `.blend` 或依赖集合即视为新实现，必须回 D2 或新增真正不同的 Proof。不同时间窗口可通过 `native_start_frame` 表达。MCP 调用成功不等于镜头衔接合格。

**Renderer 不能在 Execute 中替换。** Implementation Lock 中某个元素若写 `renderer=blender_native_blend`，对应 composition 必须保持 `mode=native_blend`；若写 `renderer=blender_layers`，才可走 layers。因为“看起来近似”而从 native_blend 改成 layers，或把复杂版式降级成白字 / flat card，均直接 BLOCK 并返回 D2。

Blender / MCP 缺失时，按原 mcp-adapter 发现、准备免费后端并 smoke test；无法取得则交付已完成方案、缺口和续接入口，保留 Gate pending。随包不包含 Blender 程序、第三方 MCP 或未验证的服务地址。直接 CLI 可执行时不强制安装 MCP。

## Gate 顺序：机器状态不变，默认收敛成两次用户决策

内部仍保留 `audio / mockup / method / proof / composition / plan` 等可独立 stale 的状态，这些确认使用现有的 schema 1.9。为了减少交互冗余，默认把已实际展示的项目组合成两个 confirmation bundle；一次真实确认可以登记多个明确展示的 Gate，未展示项不能顺带确认。

### A. D2 Design Lock

> `reference_routing` 对新项目等价于 V0–V2 checker PASS；候选数和 Mockup 覆盖由 `design_scope / validation_scope` 决定，复用必须有真实既有确认链。公开版的新风格在 V5 做代表性同源 A/B；代表性扩展中的困难镜头在 V7 追加实际成图 QA。V6 复用现有 Mockup 选择，V7 + `implementation-lock.json` 是进入 Proof 的机器前置验证。视觉阶段不增加额外用户确认次数。

1. 完成原 D1 / Detail；D2 明确声音、审美方向与视觉问题。
2. 形成 Mockup + Project Method。已有成熟方案时 Visual Methods 用于校正；没有成熟方案时先走 Router → 完整 Method / Fallback → 候选比较。选中 Mockup 后，立即把其实现编译进 `implementation-lock.json`；不得把“看图再实现”留给 Execute。
3. 同一轮展示时，可一次确认 `audio + mockup + method`；如果完整 execution plan 此时已经真实完成并展示，也可同时确认 `plan`。这只是确认束，不是新 Gate。
4. `build_composition` 仍只在方向、Detail、声音、Mockup、method 均有效后制作 **`proof_composition_ids` 的限定窗口工程和预览**，不授予整片渲染权限。其余 planned compositions 此时保持未渲染；不能为了“先看看”逐段生成 demo。

### B. Production Proof Lock

> 本锁除 `proof + composition` 确认外，同时冻结 `implementation-lock.json`、REF application trace、`execution-reference.md#Production Lock`、实际工具链、方法/工程、delivery spec 与文字/旁白 policy。下游输入变化只使受影响锁 stale。

5. 实看代表性 `proof_composition_ids` 同一工程的动态 demo 并填写 review：NarrativeFocus、Layout、MotionCurve、JoinContinuity、Timing、AudioContinuity、ReferenceCompliance；未观察项保留 not_tested，问题存在时保留 blocking_issues。
6. 展示当前工程 / demo / 静态 proof / 问题处理后，一次确认 `proof + composition`；确认记录必须绑定当前实际展示的 proof / demo 文件 hash。若没有 shown-artifact binding，仅一句“渲染视频 / 继续 / 可以渲染”不能补签未展示的 Proof / Composition。若 `plan` 尚未在 Design Lock 确认或 Demo 导致计划发生实际变化，则本轮同时展示并确认当前 `plan`。
7. Execute Step 0 只在既有 D2 快照和 safe windows 内定帧；源取段、事件时长或处理参数改变会使相关工程 / demo 及受影响确认失效，先重做对应验证。
8. 最终授权后，先对**非 proof production compositions** 按已冻结的 Implementation Lock / composition plan 一次性执行 `render_blender_composition.py --purpose production`；这一步只生成正式 scene / visual / readback / receipt，不再生成 demo / proof / review。随后编译 manifest，既有 FFmpeg 渲染器生成 clean-video / mix；由 finish_ffmpeg 接回全部合成窗口。技术输出仍为 rendered_not_reviewed。
9. 完成原 G / EVA 与成片检查，最后 guard deliver_complete；未观看成片或 QA 未闭合，不交付为“最终完成”。

Visual Methods 的 failure signals / validation points 直接映射到现有 Demo Review 和最终 QA，**不新增 VisualMethodsCompliance**。

schema 1.9 新项目必须保留 visual_pipeline 与 workflow_control。删除对象、删掉 policy 或把字段设为 not_applicable 不会豁免 Gate。旧 schema 项目保持原检查；要采用本版制作流程，显式 init，承接原观察和叙事，不重新扫描，不导入 / 编造旧确认。没有复杂合成需求时，可继续原项目规范；本版新管线不自动取消 Blender 步骤。

## 实际命令

在独立项目复制并填写 `visual-methods`、`implementation-lock`、`composition-plan` 等模板，先设置输出规格和事件，再运行：

```sh
python scripts/visual_pipeline.py init PROJECT
python scripts/workflow_control.py status PROJECT
python scripts/workflow_control.py guard PROJECT --action build_composition
# 先把真实会话确认以原文和来源保存在项目中；以下不提供示例同意文本。
python scripts/workflow_control.py confirm PROJECT --gates audio mockup method --actor user --confirmation-ref decisions.md --quote "实际已有、且同轮明确覆盖这些项目的确认原文" --shown-ref path/to/current-mockup.png
python scripts/render_blender_composition.py PROJECT --composition C01 --purpose proof --blender /absolute/path/to/blender
# 实看 demo，填写生成的 review，并引用用户对当前版本的真实决定。
python scripts/workflow_control.py confirm PROJECT --gates proof composition plan --actor user --confirmation-ref decisions.md --quote "实际已有、且同轮明确覆盖这些项目的确认原文" --shown-ref path/to/current-proof.png path/to/current-demo.mp4
python scripts/workflow_control.py guard PROJECT --action execute_handoff
```

保留已有 direction / audio / mockup / plan 的确认命令和原 Step 0 / authorization。一个真实决定可在同轮覆盖多个明确展示的项目，不重复询问，也不把一般继续指令当作具体版本已获同意。状态为 stale / pending 时主动说明当前文件、缺口、下一步；换对话 / 模型时交接整个工程和关口表。

## FFmpeg 回接

复制 delivery-spec，声明现有渲染器按 **当前授权 manifest** 实际生成的 base_video_ref、mixed_audio_ref、可选 ASS 字幕及字体、output_ref。提前把 workflow_control.render_output_ref 设为同一路径。base video 和 mix 是授权后的生成层，不能先把它们作为 pre-render 指纹输入制造循环；最终 receipt 会绑定其实际字节。

```sh
python scripts/prepare_execution_authorization.py PROJECT
# 按原流程确认最终 execution-authorization，不由命令代签。
# 最终授权后，仅对 composition-plan 中不属于 proof_composition_ids 的 production 段执行一次正式 Blender 渲染：
python scripts/render_blender_composition.py PROJECT --composition C02 --purpose production --blender /absolute/path/to/blender
# C03/C04 同理；不存在时不运行。proof_composition_ids 中各 Proof 已有有效正式 video 时直接复用，不重复渲染。
python scripts/compile_render_manifest.py PROJECT
python scripts/check_render_authorization.py PROJECT PROJECT/render-manifest.json
# 既有 FFmpeg renderer 消费上述 manifest，生成规范化 clean-video 和已确认 mix。
python scripts/finish_ffmpeg.py PROJECT
python scripts/audit_render.py --help
python scripts/workflow_control.py guard PROJECT --action qa_start
# 正常速度听看当前整片，完成原 QA / ReferenceCompliance 与既有 生产检查；Visual Methods 不增加独立 QA 项。
python scripts/workflow_control.py guard PROJECT --action deliver_complete
```

finish_ffmpeg 只接回互不重叠的全画幅合成窗口，原声来自已确认 mix；本版输出 H.264 / yuv420p / AAC，适用于 SDR。不会从任意 timeline 重新发明剪辑器。外部 clean-video 的内容是否真的符合计划仍由原 QA / 源证据对照验收；媒体元数据只能验证规格。透明叠层、HDR、复杂重叠等需另经能力验证，不静默套用。

## QA、返工与能力边界

- demo 审阅绑定 scene、demo 和实际渲染输入摘要；工程、资源、曲线、取段或声音改变后必须重新验证对应结果。未变的独立合成文件保留，不要求重建整片。
- final qa.json 沿用原结构，保留 final_playback_verified、artifact_sha256、project_id 和 blocking_issues；新增 CompositionCompliance、MotionContinuity、DeliveryTechnical，三项均须 pass。CompositionCompliance 的 `composition_windows` 必须逐项列出 render-manifest 的 composition_id、start/end frame、production video SHA-256，并为**每一段**填写 `status: pass` 与非空 `finding`；该段声明了 join 时还必须有非空 `join_finding`。允许这些结论字段存在，但四个身份字段必须与 manifest 精确一致；manifest 与所有 composition video 均纳入 evidence。所有 pass 要有实际 evidence；原有检查的 not_applicable 须说明理由。
- **方法保持与参数一致性：** 现有 method 决策建立固定方法与允许适配项；同 element ID 下更换 easing、运动结构或未声明参数会被基线 guard 阻断。已声明 parameter_bindings 的实际值须一致；Narrative 更新仅通过受限 slot 补丁同步。未映射参数保持固定，native_blend 工程及当前 V0–V7 / Proof 的观看要求继续适用。操作见 [方法保持与叙事参数补丁](workflow-control.md#方法保持与叙事参数补丁)。
- `.blend`、render receipt、readback、动态视频和 review 一起交接；仅交 MP4 无法继续修改工程，仅交 .blend 无法证明已经实现。
- 随包脚本可以阻止经其连接入口执行的缺项、过期输入和未确认动作；它不能验证一份会话摘录是否确为用户所说，也不能限制绕过入口的任意外部程序。模型和接手人必须诚实保留来源，不能生成同意语句或把未看结果填 pass。
- 标准静态脚本保持 Python 3.9+；新增 CLI 需 FFmpeg / ffprobe，Blender worker 使用 Blender 自带 Python。实际运行版本和测试证据写入发布 QA，不由文档宣称跨平台均已验证。

---

## FILE: `references/style-system.md`

# Long Video Remix｜Style System & Visual Calibration

版本：1.3.1-integrated\
文档类型：风格规范与视觉校准指南\
适用范围：知识可被全流程引用；Broad / Direct 1 只保留素材条件与表达语气，正式 Visual Method 选择在 Direct 2 完成\
建议路径：`references/style-system.md`；Visual Router：`references/visual-methods/index.md`

------------------------------------------------------------------------

## 1. 文档目的

本文件用于帮助 AI
在视频剪辑、字幕文案、字体排版、色彩、动效、声音和画面组织中，形成稳定而灵活的审美判断。

目标不是让所有视频长得一样，而是建立一套共同的审美底线，使不同类型的作品既能保持当代、准确、有设计意识的完成度，又能根据内容需要呈现不同的表达方式。

本规范重点解决以下问题：

-   将"高级感""电影感""综艺感""有质感"等模糊词语，转化为可以执行和检验的设计判断。
-   避免把风格误解为特效、滤镜、字体或配色的简单堆叠。
-   为情感表达、综艺表达等常见方向提供可理解的参考案例。
-   在正式批量执行前，通过关键帧 Mockup 与动态 Demo
    验证风格是否真正成立。
-   让 AI 学习案例背后的判断逻辑，而不是机械复制案例中的表面形式。

## 2. 最重要的原则：参考案例不是固定模板

**本文件中的示例用于解释判断方式，不代表所有项目都必须采用示例中的做法。**

示例中的文案、字体方向、色彩、构图、字幕位置、动效和节奏都只是特定情境下的可能方案。不得因为某个示例被列入本文件，就在其他项目中自动复用。

每次创作都必须结合当前任务重新判断：

1.  用户本轮明确提出的要求是什么？
2.  已确认的项目决策、指定底稿和已有交付物有哪些？
3.  原始素材实际提供了什么画面、声音、动作和叙事证据？
4.  这条视频希望观众理解什么、感受到什么，或者因为什么而发笑？
5.  哪种视觉与剪辑处理最能服务这个目标？

当示例与用户要求、已确认的项目决策或实际素材不一致时，以当前有效要求和真实素材为准。不得为了符合示例而扭曲叙事、添加素材中不存在的信息，或擅自改变已确认的剪辑决定。

**应当迁移的是判断逻辑，不是具体答案。**

情感表达可通过反应镜头与停顿呈现关系变化。轻松表达可以让文字和节奏凸显已经在素材里成立的反差。

如果当前内容不适合本文件列出的模式，应当提出更匹配的表达方案，而不是强行套用。

------------------------------------------------------------------------

## 3. 统一审美底线

### 3.1 核心定位

整体视觉语言应当具有以下特征：

-   **当代**：避免无意识沿用过时的视觉包装习惯。
-   **准确**：每个镜头、文字和设计元素都服务于明确的叙事或表达目的。
-   **有层级**：观众能迅速识别什么是重点，什么是辅助信息。
-   **有节奏**：画面、文字、声音和停顿之间存在组织，而不是持续争夺注意力。
-   **有设计意识**：字体、构图、色彩、留白和动效之间相互协调。
-   **有弹性**：可以克制，也可以鲜明；可以安静，也可以活跃。风格选择取决于内容，不取决于固定模板。

质感来自准确的选择、协调的关系和有意识的取舍，不来自效果数量。

### 3.2 当代感不等于极简

当代感不等于黑白灰、不等于细字体、不等于大量留白，也不等于去掉所有特效。

鲜艳的色彩、强烈的字重、复杂的画面、快速的动画，都可能是正确选择；前提是它们有明确的内容理由，并且在比例、层级、时机和整体关系上成立。

反过来，极简设计也可能空洞、老套或缺乏表达。不能只因为一种设计"干净"，就默认它更高级。

### 3.3 质感不等于电影滤镜

不得将"电影感"自动理解为：

-   复古胶片、泛黄、暗角、强颗粒或光晕；
-   无理由地压暗画面、降低饱和度或添加蓝橙色调；
-   自动慢动作、长时间淡入淡出或刻意模仿旧电影；
-   大量使用居中标题、装饰线条或海报式文字；
-   用视觉效果代替镜头选择、节奏和叙事判断。

上述手法并非一律禁止。如果素材、时代背景、叙事主题或用户明确要求支持这些选择，可以有意识地使用；但不得把它们作为"有质感"的默认答案。

### 3.4 视觉设计必须有功能

在决定是否加入任何设计元素前，先问：

-   它帮助观众看到了什么、理解了什么，或者感受到了什么？
-   它与当前画面、人物、台词和情绪有什么关系？
-   如果删除它，信息、情绪或节奏是否会受到实质影响？
-   它是否抢走了原本应该属于人物、动作或关键台词的注意力？

如果无法说明其功能，默认不添加。这里的"默认不添加"是一项判断原则，不是禁止创意；当设计本身就是表达目标时，应当说明它为何成立。

------------------------------------------------------------------------

## 3.5 从审美底线到具体视觉方向

Style System 只回答“什么不应被默认做俗、什么是共同审美底线”。对于 Direct 2 的真人画面 + 创作者文字，不应从本文件直接跳到字体/颜色。先使用 **Visual Direction Atlas**：先判断注意力所有者、文字角色、图文空间关系、字体语气、动态关系和强调预算，再用当前项目画面和文案校准，最后在 V3 落成 Art Direction。这样“情感/综艺”不再是直接套版的风格名，而只是更上层的内容语气。

## 4. 从风格词到可执行决策

AI
不应只输出"高级、电影感、克制、活泼、年轻化"等形容词。每个风格判断都应继续落到具体决策上。

建议采用以下顺序：

**内容意图 → 叙事功能 → 表达策略 → 视觉与剪辑决策 → 样片验证 → 修订**

### 4.1 内容意图

先明确本条视频的核心任务，例如：

-   让观众意识到人物关系发生了变化；
-   让一个反应或潜台词被观众发现；
-   通过连续冲突建立情绪递进；
-   用反差或误解制造笑点；
-   让一段台词更容易理解和记住；
-   建立某种氛围、人物印象或叙事悬念。

不要在目标尚未明确时，先决定字体、滤镜或动画。

### 4.2 叙事功能

明确镜头、字幕或设计承担什么功能，例如：

-   提供信息；
-   建立预期；
-   暴露反应；
-   强化反差；
-   延迟揭示；
-   转移注意力；
-   留下余韵；
-   帮助观众理解复杂信息。

同一个视觉处理在不同功能下可能产生相反效果。长停顿可以制造情绪，也可能拖慢笑点；大字可以强调重点，也可能破坏人物画面。

### 4.3 执行参数

在明确功能后，再决定实际做法，包括但不限于：

-   镜头选择、顺序和停留时间；
-   字幕文案、句长、分行和出现时机；
-   字体、字号、字重、字距和行距；
-   字幕位置、画面安全区与人物避让；
-   主色、强调色、明暗关系和对比度；
-   动画方式、速度、缓动、持续时间和退出方式；
-   原声、环境声、音乐和静默的关系；
-   画面调色、裁切、构图与转场。

不能在没有依据时，把这些参数固定成所有项目共用的数值。

------------------------------------------------------------------------

## 5. 表达模式

情感表达与综艺表达是常见模式，不是唯一模式，也不是必须二选一的封闭分类。

每条视频可以确定一个主模式，并在局部采用其他表达方式。混合使用必须有叙事理由，而不是为了丰富视觉效果而随意切换。如果当前项目更适合纪实、信息型、悬疑型、实验型或其他方向，应根据目标建立相应策略。

### 5.1 Emotional｜情感表达

#### 核心目标

让观众通过人物动作、目光、反应、声音、镜头关系和信息释放，逐步感受到人物关系或情绪的变化。

#### 主要判断

**镜头** - 优先寻找能表现人物关系变化的动作、目光、反应和细节。 -
不只保留台词信息，也判断台词前后发生了什么。 -
不凭空制造素材中没有的情绪或关系结论。 -
不是每个镜头都需要慢放或特写；景别变化应服务于信息和情绪。

**节奏** - 重要镜头可以留出理解和感受的时间。 -
停顿必须承载信息、期待、反应或余韵，而不是单纯拖长时长。 -
情绪递进可以来自镜头次序、反应延迟、信息反差，不必依赖音乐逐渐增强。 -
如果快速剪辑更能体现人物慌乱、关系拉扯或情绪失控，就不应为了"情感向"而刻意放慢。

**文案** - 可以有文学性，但避免空泛抒情、过度解释和替观众宣布情绪。 -
优先表达画面尚未直接说出的关系、潜台词或反差。 -
不重复画面已经清楚传达的信息，除非重复本身承担节奏或修辞功能。 -
文案应当符合人物、场景、语境和平台表达方式。

**字体与排版** - 先考虑画面构图、人物位置、文字长度和阅读速度。 -
字体气质应与内容相符，而不是默认选择极细、衬线、手写或复古字体。 -
留白、字重、对齐和位置应服务于观看体验。 -
不要为了"高级"牺牲可读性，也不要为了醒目而遮挡人物的重要表情。

**色彩与效果** - 优先尊重原始素材的光线、肤色和整体色彩关系。 -
需要调整时，说明它如何支持情绪或统一画面。 -
光晕、颗粒、模糊、慢动作等效果只有在具体内容支持时才使用。

**声音** - 判断原声、环境声、停顿、音乐分别承担什么作用。 -
音乐不是情绪的自动补丁。某些场景中，原声或静默可能更有效。 -
任何"加音乐""去音乐"或声音改动都必须服从用户明确要求和项目已确认决定。

按动作、反应和镜头顺序核实关系是否发生变化，再决定要保留的停顿与前后对照。已有画面足够时，可以省去解释文字。

### 5.2 Variety｜综艺表达

#### 核心目标

通过信息铺垫、反应、节拍、反差、误解、重复或文字机锋，让观众在准确的时机理解笑点或感受到趣味。

#### 主要判断

**镜头** - 找到铺垫、触发点、反应和结果之间的关系。 -
优先保留能让笑点成立的表情、停顿或动作。 -
不为追求快节奏而切掉必要的信息，也不为了显得热闹而频繁切镜。 -
有时最有趣的镜头是没有台词的反应镜头。

**节奏** - 先建立观众的预期，再判断何时揭示、打断或反转。 -
文字、动作、切镜和声音效果应当共同服务于节拍。 -
有效的停顿也可以是综艺节奏的一部分。 -
不要求每一句台词都配音效、每次切镜都配动画。

**文案** - 优先寻找观察、反差、误读、反讽和简洁的重新定义。 -
字幕可以评论局面，但不应只是重复台词，也不应过度解释笑点。 -
语言要有明确的对象、语境和节奏；"搞笑""抽象""有梗"不是文案本身。 -
不要为了追求网络感，机械添加流行语、谐音梗或夸张语气。

**字体与排版** - 可以比情感表达更鲜明、更具动势，但必须有清晰层级。 -
强调色、字重、位置和动效应突出关键笑点，而不是每句话都争夺注意力。 -
字体的个性要与文案语气和素材氛围相符。 -
可读性、人物避让和视觉秩序仍然是基本要求。

**声音与动效** - 音效、动画或节奏变化应当强化铺垫、反应或包袱。 -
如果效果比笑点更醒目，就需要重新判断。 -
不将综艺风自动等同于弹跳字、震屏、贴纸、拟声词或连续音效。 -
若用户要求保留原声、不加 BGM 或限制某些画面，必须遵守。

先找出观众预期真正改变的一拍，再用切点、停顿或一句观察文案强调它。文案应补充画面已经支持的观察。

## 6. 识别过时或廉价的视觉语言

"土""俗""过时"不能只作为结论。AI
应当指出具体问题发生在哪里，以及为什么它削弱了作品。

### 6.1 常见风险信号

以下是风险信号，不是绝对禁令：

-   **效果堆叠**：描边、阴影、发光、渐变、颗粒、贴纸同时出现，却没有明确主次。
-   **层级失控**：标题、正文、装饰字和强调字都很抢眼，观众不知道先看哪里。
-   **模板感过强**：无论素材、情绪和平台如何变化，都使用同一套字体、配色和动画。
-   **形式先行**：先选特效、字体或滤镜，再勉强解释它与内容的关系。
-   **文案用力过猛**：把人物的情绪直接说尽，反复使用空泛形容词，或者用网络流行语代替具体观察。
-   **动态缺少节制**：文字不断弹出、放大、摇晃或闪烁，导致观众无法聚焦内容。
-   **时代语法错位**：使用某种过度熟悉的旧式包装方式，却没有与当下素材、内容语气或用户目标建立关系。
-   **画面被设计破坏**：文字遮挡人物表情、关键动作或重要信息；裁切和装饰打断原有构图。
-   **静态成立、动态失败**：单帧看起来精致，但字幕出现时机、运动速度或持续时间与剪辑节奏冲突。

### 6.2 发现问题后的修正顺序

不要一发现问题就换字体或增加效果。建议依次检查：

1.  这个元素是否真的有必要？
2.  内容重点和视觉层级是否明确？
3.  位置、比例、字重、间距和时机是否合适？
4.  是否需要减少元素、降低动效强度或重新组织信息？
5.  只有在上述问题解决后，再判断是否需要更换字体、色彩或视觉方案。

"去掉不必要的东西"常常比"再加一个更漂亮的效果"更有效，但不能把删减当成唯一的审美方法。

------------------------------------------------------------------------

## 7. 风格参考案例的使用规则

用于风格校准的参考，都应帮助 AI
解释"为什么这样做"，而不仅仅展示"最后做成什么样"。

### 7.1 案例应包含的信息

条件允许时，每个案例包含：

-   **情境**：素材和任务是什么；
-   **目标**：观众应该理解、感受或注意到什么；
-   **关键证据**：哪些真实画面、动作、台词或声音支撑这一目标；
-   **决策过程**：为什么选择这样的镜头组织、文案、字体或动效；
-   **成立原因**：哪些选择真正发挥了作用；
-   **失败风险**：如果照搬到其他场景，可能在哪些地方失效；
-   **可迁移原则**：哪些判断可以借鉴，哪些具体参数不能直接复制。

### 7.2 不要把参考案例变成隐性模板

AI 在使用案例时，必须明确区分：

-   **可迁移原则**：例如用反应镜头呈现人物关系，用节拍控制笑点揭示。
-   **情境性选择**：例如某一帧采用的字体、颜色、位置、动画或具体文案。
-   **不可直接外推的结论**：例如"情感向必须慢""综艺向必须用大字""高级感必须留白"。

当新项目与案例相似时，也只能将案例作为候选思路。仍然需要根据新素材重新验证，不能默认复用。

### 7.3 多案例之间不一致时怎么办

不同案例可能给出不同甚至相反的做法，例如一个案例使用静态小字，另一个使用醒目的动态文字。这并不代表规则矛盾。

AI
应当识别两者的目标、内容条件和表达功能，再判断当前项目更接近哪一种情况。如果条件不同，就不应强行统一成一种形式。

------------------------------------------------------------------------

## 8. Visual Methods｜Direct 2 的方案生成与兜底

本文件是 **Direct 2 的视觉判断知识底座**，不是第二套制作流程。Mockup、Blender Composition、Proof、Dynamic Demo、确认、Execute 与 QA 全部继续由 [visual-production.md](visual-production.md) 管理。这里负责的是：当 Director 已有想法时校正和深化；当 Director 没有成熟视觉方案时，主动提出可制作的候选方案并兜底。

### 8.1 什么时候必须调用 Visual Methods

出现以下任一情况，不应直接把抽象形容词送入 Mockup：

- 方案仍停留在“高级、电影感、综艺感、克制、大字、放大、加字幕”等词，没有明确观看问题与制作处理；
- 已有方案只是常见默认处理，无法解释为什么适合当前真实画面；
- 真实关键帧、原字幕、人物位置或动作范围使原方案无法落地；
- 当前内容需要更鲜明的视觉表达，但 Director 尚未形成足够具体的构图、文字、运动或色彩策略；
- 用户明确要求更有质感、更当代、更有综艺感或更强视觉完成度，而现有方案不能说明如何实现。

先读 [Visual Router](visual-methods/index.md)，再按命中项读取 [完整方法库](visual-methods/method-library.md)；需要稳妥替代或当前素材限制较强时再读 [兜底组合](visual-methods/fallback-recipes.md)。**按需加载不等于删减知识：命中的方法必须读取完整条目，不能只凭索引的一行摘要猜执行。**

### 8.2 兜底输出必须具体到可比较方案

当 Visual Methods 承担兜底职责时，Direct 2 至少形成：

1. 当前视觉问题：观众应该先看见什么，现在被什么干扰或没有被充分表达；
2. 当前证据与画面条件：真实关键帧、人物 / 动作 / 原字幕 / 空间 / 光线及输出画幅；
3. 方法依据：命中的 M01–M14、必要的 F01–F09，以及这些方法为什么适合当前问题；
4. **1–3 个真正可制作的候选方案**：说明画面、文字、色彩、运动、声音分别怎么处理；
5. 推荐方案与取舍：为什么选它，另外方案在哪些条件下更合适或为什么当前不选；
6. 工具可执行性：Blender / FFmpeg / 当前字体与资源能否按现有 capability-map 实现；
7. 失败信号与 Dynamic Demo 需要重点看的项目。

简单问题可以只有一个明确方案；如果已有方案已经具体、证据充分且可执行，不为了形式强制凑三个。

### 8.3 Project Method 与 Library Method 分开

Visual Methods 的 `M01–M14` 是**知识库方法 ID**；项目 `visual-methods.json` 中的 `method_id` 是当前视频的实际制作方法实例。新模板使用 `PM001 / PM002...`，并通过 `library_refs` / `fallback_refs` 记录参考来源，避免把“本项目方法 1”与“知识库 M01”混为一谈。旧项目继续允许原有 method ID，不要求迁移。

------------------------------------------------------------------------

## 9. 与 工作流的衔接

Visual Methods 只在需要的地方介入，不把视觉设计提前扩散到整个流程。

### Broad Structure

只记录真实可见的视觉条件：人物与物件位置、动作范围、构图、硬字幕、光线、色彩和可用空间。**不在 Broad 阶段选择 M01–M14，也不提前设计包装。**

### Direct 1

只决定叙事方向及必要的整体表达语气，例如情绪型、轻综艺、混合或其他方向。可以提出“哪些节点应克制 / 强调”的意图，但不要求在此锁定字体、颜色、运动曲线或 Visual Method。

### Detail Structure

提供真实关键帧、连续动作 / 原声、人物与原字幕位置、必要前后状态和执行边界，让 Direct 2 有可靠画面条件。Detail 不替 Director 做视觉方法选择。

### Direct 2

先形成内容与视觉问题判断。已有成熟方案时用本系统校正、深化和检查；没有成熟方案时按第 8 节触发 Visual Router / Method Library / Fallback，提出候选并形成 Project Method。随后进入 Mockup → Blender Composition → Proof + Dynamic Demo。

### Execute / QA

只执行已确认的 Project Method 与工程，不在 Execute 重新选视觉风格。Visual Methods **不新增 VisualMethodsCompliance 或独立 QA 层**；方法的 failure signals / validation points 映射到现有 NarrativeFocus、Layout、MotionCurve、JoinContinuity、Timing、AudioContinuity、ReferenceCompliance 及最终 Visual / Rhythm / ReferenceCompliance 等检查。

------------------------------------------------------------------------

## 10. 风格质量判断与返工触发

以下判断保留为 Direct 2 / Demo Review 的质量标准，不新增 Gate：

- 视觉选择是否服务当前表达目标，而不是只增加效果数量；
- 观众是否能快速识别人物、动作、原话或本段真正的视觉重点；
- 文字是否增加观察 / 信息价值，并在真实播放中可读、不遮挡关键内容；
- 字体、色彩、构图与运动是否有明确功能，不是从参考案例机械复制；
- 方案是否已经从形容词落到真实文案、位置、尺度、时间、运动和资源入口；
- Dynamic Demo 是否证明静态方案在进入、运动、退出及接点两侧仍成立；
- 是否存在更简单但同样有效的处理；复杂度本身不算质量；
- 是否遵守用户明确要求、已确认决定、素材事实与当前工具能力。

仅使用某种字体、低饱和、留白、电影颗粒、综艺大字、复杂动画或某个参考案例，都不能单独证明“有质感”。出现遮挡关键信息、歪曲素材、运动破坏节奏、最终效果偏离已确认方案，或**方案仍只有形容词而没有可制作说明**时，应先返回 Direct 2 / 当前 Production Proof 修订，不把问题推给 Execute。

------------------------------------------------------------------------

## 11. AI 的输出要求

当任务需要进行风格设计或风格校准时，输出应尽量包含以下内容。具体详略根据任务规模决定，不要求每个小任务都重复输出整份报告。

1.  **表达目标**：这条视频想让观众理解、感受或注意到什么。
2.  **主要模式**：情感、综艺、混合或其他更合适的方向，并说明理由。
3.  **视觉问题与设计逻辑**：观众应该先看见什么，当前画面哪里需要被组织；镜头、字幕、字体、色彩、动效和声音分别承担什么功能。
4.  **关键执行选择 / 候选比较**：列出真正影响效果的具体决定；当现有方案不足以制作时，调用 Visual Methods 提出可比较的候选并说明推荐理由。
5.  **参考案例的使用方式**：说明借鉴的是哪一项判断原则，不把示例直接当作模板。
6.  **验证方式**：需要检查哪些关键帧和动态节点。
7.  **风险与待确认项**：明确哪些结论基于素材、哪些是设计提案、哪些仍需用户确认。

对于简单任务，可以简化为几条清晰的执行说明；对于完整视频项目，应与当前工作流的交付要求保持一致。

## 12. 给 AI 的最终指令

在进行任何风格设计时，遵守以下原则：

-   先理解内容，再决定风格；先确定表达功能，再决定视觉形式。
-   不把"高级感""电影感""综艺感"等形容词当成完整方案。
-   不默认使用某种字体、配色、滤镜、动画、音乐或节奏。
-   根据当前素材重新判断风格和表达强度。
-   不为了追求风格而扭曲素材、叙事、人物关系或用户意图。
-   不把当代感等同于极简，也不把鲜明等同于俗气。
-   不以效果数量、技术复杂度或与参考案例的相似程度判断质量。
-   说明关键设计选择的理由，并通过真实关键帧和动态效果验证。
-   在用户明确要求、已确认决定、素材事实与参考示例之间发生冲突时，优先遵守当前有效要求和真实素材。
-   当现有案例无法解释当前场景时，应独立分析并提出新的方案，而不是强行归类。
-   当方案仍是抽象形容词、常见默认处理或无法适配真实关键帧时，必须调用 Visual Router / 完整方法库 / 必要兜底组合，形成可制作候选后再进入 Mockup。

**最终目标不是让 AI
记住一套固定的"好看公式"，而是让它能够根据不同内容，做出有依据、可解释、可验证的剪辑与视觉选择。**

---

## FILE: `references/visual-methods/index.md`

# 视觉方法：按当前问题调用

本模块继承 [style-system.md](../style-system.md) 的原则：迁移判断逻辑，根据素材重新选择。它提供起点和分析工具；不要求每条视频采用相同字体、色彩、密度、节奏或布局。


## 读取策略：瘦加载，不瘦知识

默认先读本页做路由；命中某个方法后，**继续读取 method-library.md 中该方法的完整条目**。索引只负责导航，不能替代完整方法的适用条件、组合约束、失败信号、修正和当前视频验证。需要稳妥替代、Director 暂无成熟方案、或真实素材使首选方案无法落地时，再读取对应 Fallback。

Visual Methods 有两种职责：已有方案时用于校正 / 深化；没有成熟方案时用于**主动提出可制作候选并兜底**。如果当前 Method Decision 仍只有“高级、克制、综艺感、大字、放大、加字幕”等抽象描述，不视为视觉方案已经完成。

## 制作边界

实际画面来自当前项目视频。可根据叙事与真实画面，组织镜头、调整字幕、重新裁切、放大细节、局部变速、安排原声以及制作必要的文字和图形。外部视觉案例提供搭配与组织方法，不提供待拼入视频的第三方图像。

方法选择属于现有编导职责。Broad Structure 继续保留整体素材覆盖和基础观察；Direct 1 决定叙事方向；Detail 回查素材；Direct 2 决定处理与具体参数；Execute 实现既有方案。本模块不增加创意决策主体或审批阶段。

剧情剪辑节奏、字与人物/物件的关系和 CP 观察文字，另从 [Visual Reference Router](../visual-reference-router.md) 读取 完整方法。本页仍负责 production method，不重复维护参考选择。

## 问题导航

| 当前问题 | 优先方法 | 可用兜底 |
|---|---|---|
| 人物、标题或字幕互相抢重点 | M01 / M03 / M06 | F01 / F02 / F07 |
| 想让关系或状态变化被发现 | M02 / M08 | F01 / F03 |
| 想鲜明而有情绪，避免自动极简 | M03 / M05 / M11 | F02 |
| 信息较多，阅读顺序混乱 | M04 / M05 / M08 | F05 / F07 |
| 想让文字参与物件或空间 | M07 / M09 | F04 |
| 评论不够有趣或出现得不对 | M12 / M01 | F06 |
| 多人对白、姓名与角色区分 | M06 / M11 / M05 | F07 |
| 任务、规则或线索难以跟踪 | M10 / M04 | F08 |
| 想放大、裁切、慢放或加速 | M13 / M14 / M01 | F09 |

完整内容见[方法库](method-library.md)和[兜底组合](fallback-recipes.md)。ID 用于检索和说明，不是必须写满的额外制作表单。项目中的实际制作方法使用 `PM001...` 等 Project Method ID；这里的 M01–M14 只作为 `library_refs`，避免 ID 混淆。

## 调用顺序

先用一句话说明观众需要看见什么，再引用当前证据，选择能解释问题的方法。可以先从一个主要组合起步，再按需要补充；不以使用规则的数量衡量完成度。

方法间出现矛盾时，按当前有效要求、已确认决定、真实素材与观看任务判断。比如“大标题”与“人物优先”可以通过位置和时间分工；若仍冲突，优先保护本段核心信息。

## 项目偏好与完成度

配色是项目可设置的偏好，不设全局禁用色或固定色板。沿用当前 brief、品牌规范及已确认决定，在既有执行参考中记录主调方向、希望避免的颜色、强调色职责和例外范围。已有明确偏好时直接承接，不另建必填配置文件或重复询问。

未指定配色时，结合素材、内容语气、人物与文字的对比提出候选；冷暖、中性、高饱和或低饱和都可有合理用途。具体选择以当前项目为准，不从来源案例推出所有项目共用的禁令。

原片中的肤色、现场光线和环境色与新增包装色分别判断。鲜明、密集、复杂或克制的设计均可成立，判断重点是层级、功能、可读性与节奏。

## 证据范围

来源索引中的20条分析支持构图、层级、颜色关系、字形及组件组织的静态观察；不自动支持动画曲线、运动速度、镜头持续时间或声音效果的结论。M12、M14及其他动态建议来自风格规范和方法推演，须在当前视频中核验。来源分析与当前项目的方案确认分别记录，不以来源收录代替制作验证。

---

## FILE: `references/visual-methods/application.md`

# 将 Visual Methods 接入 Execution Package

这是 Direct 2 的设计知识层，不新增阶段、状态文件、确认 Gate 或 QA 层。完整生产顺序、Blender Composition、Proof、Dynamic Demo 与 FFmpeg 回接统一以 [visual-production.md](../visual-production.md) 为准。

## 从视觉问题到 Project Method

1. 从已确认 Narrative Direction 与 Detail 证据说明本段叙事功能，绑定 source_id、源时间、真实关键帧与必要上下文。
2. 用 [Visual Router](index.md) 判断当前问题；命中方法后读取 [完整方法库](method-library.md)，需要替代 / 兜底时读取 [fallback-recipes.md](fallback-recipes.md)。
3. 同一项目已确认的方法按 [方法保持合同](../workflow-control.md#方法保持与叙事参数补丁) 继承，只用具名参数补丁适配 Narrative；方法未确认时，Methods 用于校正和深化；没有成熟方案、方案过于普通或无法适配真实画面时，形成 1–3 个可制作候选，说明取舍并推荐一个。
4. 公开版新项目采用视觉设计时，参考研究和候选设计统一交给 [Visual Reference Router](../visual-reference-router.md) 的 V0–V7：V2 按问题说明如何用当前素材校准方向，V3 先 Art Direction 后参数。Visual Methods 不再另选参考，只负责把确认后的视觉问题/方案转成可生产的方法。
5. 把当前视频实际采用的 production method 写成 `visual-methods.json`；`method_id` 使用 PM001...，通用知识来源写在 `library_refs` / `fallback_refs`，需要时用 `visual_stage_problem_refs` 指向 V1 问题。参考来源、迁移原则和候选比较留在 V2/V3，不重复抄到 methods。
6. 真实参数继续进入 execution-reference、visual-methods、composition-plan 与 timeline；Mockup / Composition / Proof / Dynamic Demo / Gate 由视觉制作流程执行。

## 具体参数写到哪里

| 处理 | 当前执行包中写清 |
|---|---|
| 字幕与标题 | 实际文字、类别、字体与可用入口、字号单位、字重、换行、位置、安全区、图层、色彩、进出场和阅读窗口 |
| 裁切与缩放 | 源尺寸、输出画幅、crop / fit、起止框、锚点、主体运动范围、时间窗口、缓动与关键证据避让 |
| 变速或停顿 | 源区间、速度及变化方式、原声处理、动作和对白保护、输出时长及 source → output 映射 |
| 自制图形或空间文字 | 内容用途、语义对象、形状或组件、跟踪与遮挡方式、图层、可复现入口及失效处理 |
| 色彩 | 包装与原片处理的分工、正文与强调色角色、对比、肤色及场景光线保护 |

具体数值由本次画幅、素材和验证决定；方法库不提供所有项目共用的固定字号、固定坐标、固定倍速或固定时长。

## Project Method 推荐记录

以下字段不增加新项目文件，直接进入 `visual-methods.json` / execution-reference：

- `visual_problem`：当前观看问题与目标；
- `library_refs`：采用的 M01–M14；
- `fallback_refs`：采用的 F01–F09，可为空；
- `visual_stage_problem_refs`：采用视觉设计时可选，回指 V1 中由该 production method 负责实现的问题；
- Reference Selection / structure-card conditions / transfer / do-not-transfer：留在 V2；
- Art Direction / candidate comparison / per-shot composition grammar / shot dependency：留在 V3；
- `visual_reference_status / visual_reference_refs / viewed_reference_assets / candidate_treatments`：供兼容读取。采用视觉设计时以 V0–V7 为事实源；
- `selected_treatment` / `selection_reason`：当前采用方案与为什么；
- `parameters`：本次真实画幅和素材下的参数；
- `failure_modes` / `demo_checks`：失败信号与 Dynamic Demo 检查点。

这些字段帮助 Direct 2 形成可执行方案，但**不把方法库本身当成素材证据**。事实仍来自当前项目 Detail / source-time 证据；外部案例只能提供组织方法。

## 质量与兜底

如果 Direct 2 输出仍只是“更高级 / 更电影 / 更综艺 / 字大一点 / 放大人物”，或没有说明真实画面条件、候选取舍与可执行参数，就继续调用 Visual Methods，不进入 Mockup。

若当前方法库没有合适答案，可以按 [research-extension.md](research-extension.md) 扩展研究；无法联网时继续使用完整方法库与兜底组合。最终是否成立仍由当前真实关键帧、动态 Demo 和现有 QA 验证。

---

## FILE: `references/visual-methods/method-library.md`

# 视觉方法库

本库将静态视觉分析与原始风格规范归纳为14条方法。按当前素材的表达目标选择和组合，具体参数须在当前视频中验证。

先读[方法入口](index.md)，需要起步方案时读[兜底组合](fallback-recipes.md)。

<a id="m01"></a>

## M01｜观看重点与人物避让

**适用条件**：表情、视线、动作或人物之间的位置关系是当前段落的主要信息。

**搭配逻辑**：先决定观众要先发现的内容，再安排标题和辅助信息；强调可以来自尺寸、位置、明暗和出现时机的组合。

**执行选择**：

- 标出实际连续画面中的脸、手势、关键物件、原有字幕及其运动范围。
- 给新文字选择干扰较低的区域；大标题可以使用，但需给关键表情和动作保留可见路径。
- 背景复杂时，先比较移动文字、改变局部明暗或添加简单承载底的效果，再决定是否需要改变镜头裁切。

**组合约束**：标题强度与人物特写可以共存；当两者同时争夺注意力时，用位置或时间分工。保留空间深度，避免把每帧都压成同一种海报。

**失效信号**：第一眼看不到关键反应；文字只在静帧避开人物，播放时却横穿脸或手。

**修正办法**：先重排位置和时机，再调字号、字重与承载底；必要时减少本次文字信息。

**当前视频验证**：在动作开始、最大位移和结束位置检查，并连续播放文字进出场。

<a id="m02"></a>

## M02｜用空间与状态的呼应表达关系

**适用条件**：当前素材已提供可比较的人物、空间、状态或前后变化。

**搭配逻辑**：距离、景别、视线方向、空场和位置呼应能让观众发现联系；关系解释仍须由本项目证据支持。

**执行选择**：

- 先写出要比较的具体信息，再选顺接、交叉剪辑、并置或分屏。
- 分屏会缩小表情；表情细微或双画面负担过高时改为先后呈现。
- 用构图和节奏建立联系后，再判断评论文字是否补充了新信息。

**组合约束**：双画面、高密度文字与快速运动会增加并行阅读负担，需确定先看哪一侧或分时揭示。

**失效信号**：观众需要先猜谁与谁有关；分屏隐去了关键反应；视觉隐喻被写成了人物心理事实。

**修正办法**：恢复必要上下文，扩大关键画面或改用连续镜头；删去证据不足的关系结论。

**当前视频验证**：核对双方素材的时空与关系阶段，再按真实播放尺寸检查面部和观看顺序。

<a id="m03"></a>

## M03｜强标题与情绪画面的共存

**适用条件**：本段需要主题、章节或一句关键表达，且标题本身承担叙事功能。

**搭配逻辑**：情绪表达可以鲜明；标题尺度、字重、色彩和人物轮廓之间建立有意识的强弱关系。

**执行选择**：

- 区分标题与原话字幕，先写出实际使用的短文案。
- 根据人物位置和阅读时长比较不同标题尺度及断行；不照搬参考中的字形和排列。
- 用一种主要方式建立标题重心，再决定是否需要其他强调；多种强效果同时出现需各有用途。

**组合约束**：高饱和文字可与复杂画面搭配，但需要稳定的对比、清晰的轮廓和足够的阅读窗口。

**失效信号**：标题遮住情绪节点；文字读完之前已经切走；标题与对白同时需要精读。

**修正办法**：缩短文案、调整标题出现窗口或分开阅读任务，再调字重和颜色。

**当前视频验证**：用当前真实标题和完整句子观看；海报中的静态标题不提供视频持续时间依据。

<a id="m04"></a>

## M04｜信息层级、对齐与跨镜头一致性

**适用条件**：需要同时传达主题、背景、姓名、时间或其他辅助信息。

**搭配逻辑**：用尺度差、分组、对齐和重复的组件关系建立阅读顺序；密度由信息任务决定。

**执行选择**：

- 区分主信息、必要辅助信息与可省略装饰，给各层确定功能。
- 以当前画幅和长短文本推导版心、对齐与边距；长中文必须重新测量。
- 将相同信息保持在稳定层级，按镜头遮挡允许位置适配；制作网格和测量标记不进入成片。

**组合约束**：密集信息与小字、快速切镜组合前，先确认阅读时间；印刷版式只支持层级研究。

**失效信号**：每一行都像主标题；换镜头后相同信息跳到无规律的位置；屏幕变成杂志正文。

**修正办法**：明确一条阅读路径，分组或分时呈现，减少同时出现的辅助层。

**当前视频验证**：检查短文本、最长文本和复杂背景，分别核对安全区、实际尺寸和连续阅读。

<a id="m05"></a>

## M05｜颜色按角色搭配

**适用条件**：需要让文字、组件或局部视觉处理形成统一的识别与强调。

**搭配逻辑**：先分配背景、正文、识别和强调的颜色职责，再选择具体颜色；颜色数量和饱和度服从观看主次。

**执行选择**：

- 保留当前视频的肤色和现场光线；包装色与原片调色分别判断。
- 先读取当前项目已确认的主调方向、避免色、强调色和品牌约束；未指定时，根据素材、内容语气与可读性提出候选，不预设全局禁用色。
- 角色识别同时保留姓名或形态线索，避免仅靠颜色辨认；在亮暗背景上分别测读。

**组合约束**：两种强色可以并置，但需确定承载、强调或识别的分工。冷暖、饱和度与例外范围按当前项目决定，不将某个案例的配色扩展为全局规则。

**失效信号**：每层都在用强调色；肤色被统一滤镜改变；同一角色的颜色无理由变化。

**修正办法**：恢复颜色职责，降低次要层的竞争；必要时使用中性承载底，而不是强行重调全画面。

**当前视频验证**：在当前视频的明亮、暗部和高纹理画面上检查；不以色卡单独判定搭配成立。

<a id="m06"></a>

## M06｜对白、姓名与评论的字幕分工

**适用条件**：多人对话、角色识别或正文与评论需要同时存在。

**搭配逻辑**：正文保持稳定阅读，姓名承担识别，评论补充观察；不同功能通过结构和时机分工。

**执行选择**：

- 先保证实际对白准确完整，再建立姓名与正文的层级关系。
- 角色色服务识别，正文对比和行距保持稳定；设计时覆盖短姓名、长姓名及长句。
- 样式对照板里的多条字幕是备选展示，实际播放按当前对话组织，避免机械叠放。

**组合约束**：原有硬字幕存在时先处理空间冲突；评论字幕不与核心对白长期争夺同一个阅读区域。

**失效信号**：观众分不清哪句是原话；姓名抢过正文；长句溢出或遮住动作。

**修正办法**：明确标识原话与评论，重排断行或显示窗口；承载底和位置按真实画面适配。

**当前视频验证**：用真实最长句、换人处和双人同框测试，并实际播放检查停留与退出。

<a id="m07"></a>

## M07｜文字与叙事物件的空间结合

**适用条件**：当前素材中的某件物品或空间表面确实承担线索、记忆或章节功能。

**搭配逻辑**：文字可以参与空间关系，透视、遮挡、焦点和光线共同决定它是否自然。

**执行选择**：

- 从当前视频里选有叙事作用的物件，说明文字依附它的理由。
- 需要空间贴合时记录跟踪、透视和遮挡方法；无法稳定实现时改为邻接标注。
- 新文字的内容与身份保持清楚，避免把设计新增内容误呈为原片固有事实。

**组合约束**：材质、景深和空间贴字需共同可读；物体快速运动时，不强求表面贴合。

**失效信号**：文字在物体上漂移；关键字落入虚焦；新标注让人误以为原片已有该文字。

**修正办法**：简化贴合方式，改为旁置标题或单独章节；保留真实物件信息。

**当前视频验证**：在当前连续镜头中检查遮挡、跟踪、光照与焦点；静帧本身不证明跟踪可用。

<a id="m08"></a>

## M08｜密度、空场与景别的对照

**适用条件**：段落之间需要区分关注点，或观众需要从高密度信息转向细节、反应和余韵。

**搭配逻辑**：通过信息密度、景别和文字尺度的变化组织注意力；空场也要有具体内容用途。

**执行选择**：

- 明确空场让观众等待、理解或发现什么，再决定它是否需要保留。
- 细节画面和较宽画面可以形成对照；文字量随观看任务调整。
- 用真实反应、环境声或必要的停顿支撑节奏，不按印刷跨页推断镜头时长。

**组合约束**：低密度不要求低饱和或细字；密集画面也可以保持清晰层级。

**失效信号**：停留没有新信息；空场只是为了显得高级；重要对白后没有足够的理解时间。

**修正办法**：重新定位停顿功能，缩短无效等待或恢复必要反应；改变信息释放次序。

**当前视频验证**：连看前后段落并听原声，判断对照是否帮助理解，而非只看单帧是否干净。

<a id="m09"></a>

## M09｜材质与细节作为有依据的意象

**适用条件**：真实素材、已确认主题或自制图形支持某种材质、细节和重复意象。

**搭配逻辑**：轮廓、反射、局部裁切和明暗可组织观看；材质的作用需要与当前内容建立联系。

**执行选择**：

- 优先使用当前视频已有的相关细节、光线和物件，说明与主题的联系。
- 需要自制抽象图形时，将其标为设计层，不作为原片事实；可用性取决于实际制作工具。
- 分别决定全景、局部和空场的作用，不默认添加透明流体、胶片颗粒或泛光。

**组合约束**：强材质和强文字叠加前，需确定观看重心；没有文字的参考不能证明字幕方案。

**失效信号**：材质比人物故事更醒目；效果只起滤镜作用；静态漂亮但运动塑料感明显。

**修正办法**：回到原片细节或降低材质强度，减少无叙事用途的图层。

**当前视频验证**：用当前素材检查意象联系，并以连续动态检查高光、形变和文字可读性。

<a id="m10"></a>

## M10｜任务与线索图形的语义一致

**适用条件**：素材存在任务、推理、线索、规则或有证据的状态变化。

**搭配逻辑**：符号、空间切分、人物尺度与标题使用同一套语义，让设计帮助观众跟踪内容。

**执行选择**：

- 逐个说明标记、框体、连线或数字对应的具体信息，使用本项目自制几何与文字。
- 按内容主次分配前后层次和颜色角色；保留当前人物、动作及线索的可见范围。
- 背景设定服从任务，不为了套某个包装而添加谍战、游戏或数学设定。

**组合约束**：高密度图形可以使用，但符号含义和观看顺序需稳定；无任务依据时不用这一组合。

**失效信号**：箭头、问号和公式没有信息对象；图形虚构了原片没有的联系；包装遮住真正线索。

**修正办法**：删掉无指向符号，恢复线索与证据的对应；必要时只保留文字说明。

**当前视频验证**：让每个图形回指当前素材的明确内容节点，并播放检查信息揭示顺序。

<a id="m11"></a>

## M11｜字形节奏与语言适配

**适用条件**：标题或短词需要明确语气，或字体风格与阅读之间出现矛盾。

**搭配逻辑**：笔画、粗细、字距、字外留白和断行共同形成语气；不同语言的结构必须重新判断。

**执行选择**：

- 使用当前可用字体与实际中文内容排版，比较字面大小、字重和字间关系。
- 短词标题与长句字幕分别验证；标题中的个性字形不自动扩展成整套正文。
- 替换字体时重新测量文本边界和断行，不能只更换字体名称。

**组合约束**：个性笔画、强色和复杂运动可分工使用；识读困难时先恢复字形轮廓和间距。

**失效信号**：照搬其他语言连笔结构；长句挤成一团；字体替换造成布局溢出。

**修正办法**：改用当前可用的清楚字形，保留真正有作用的尺度和节奏关系。

**当前视频验证**：分别查看短词、长句、数字和姓名，在最终尺寸与连续播放中测读。

<a id="m12"></a>

## M12｜评论字幕与笑点的出现时机

**适用条件**：真实对话已提供铺垫、触发、反应或反转，评论能增加新的观察。

**搭配逻辑**：先确定笑点的信息结构，再让文字、切镜和声音在合适时机揭示；静态参考不提供节拍证据。

**执行选择**：

- 标出观众何时获得铺垫、何时看到触发与反应，绑定已核实源区间。
- 评论可以静态出现，也可以使用简短动效；时机比动效数量更先决定。
- 让评论与原话身份明确，保留使包袱成立的必要停顿与回应。

**组合约束**：评论、音效与放大若同时工作，需确定主要强调；不默认加入音乐或额外声音。

**失效信号**：文字提前说出结果；每句都有强调而失去节拍；音效盖过关键原话。

**修正办法**：延后或删除评论，恢复原声与必要反应，先用切镜和出现时机建立笑点。

**当前视频验证**：连听连看铺垫至结果，比较有无评论的理解效果；所有时机由当前视频核验。

<a id="m13"></a>

## M13｜裁切与缩放引导注意力

**适用条件**：同一原画面内有值得强调的表情、动作或物件，且裁切不会损害必要关系。

**搭配逻辑**：先确定需要放大的具体信息，再决定静态裁切、切到近景或连续缩放；画面变化应让信息更清楚。

**执行选择**：

- 保留原画和处理版对照，检查双人关系、手势、原有字幕与空间指向。
- 根据原始分辨率、目标画幅和主体运动推导裁切范围；按整段运动路径设置跟随。
- 连续缩放只是候选，记录起止框、锚点、时间窗口与缓动；必要时使用固定裁切。

**组合约束**：裁切、动字和变速同时出现时，避免多个重点彼此冲突；不为了填满画面切掉必要证据。

**失效信号**：主体出框；画质明显不足；只剩单人特写而丢失互动；缩放与情绪节拍不符。

**修正办法**：减小裁切、恢复更宽画面或改为原生近景；取消无效的连续缩放。

**当前视频验证**：检查开始、峰值、结束及中间运动；静态来源只支持构图分析，缩放曲线仍须实测。

<a id="m14"></a>

## M14｜局部变速与停顿的表达功能

**适用条件**：当前已核实动作、反应或段落节奏存在具体强调需求，且已确认方案允许处理。

**搭配逻辑**：速度服务于观众需要发现的信息；情感表达可以快，综艺反应也可以停留。

**执行选择**：

- 先看原速，写出变速要让观众多看到什么或更快理解什么。
- 根据动作完整性、源帧率与目标节拍确定局部速度和窗口；不预设通用倍速。
- 记录源区间到输出的时间映射，按原方案处理声音；不默认静音、变声或截短对白。

**组合约束**：变速会改变阅读和声音节奏；叠加动字或缩放前，先确认各自功能及总时长预算。

**失效信号**：动作被拖成无信息等待；插帧变形；原声失真；句子、回应或因果关系被破坏。

**修正办法**：恢复原速或缩短处理窗口，调整切镜与字幕时机；证据或方案冲突按既有流程返回相应阶段。

**当前视频验证**：按原速与候选版比较完整音画，核对动作、对白、阅读时间及源时间回查。

**分析来源与范围**：[原始风格规范](../style-system.md)；动态方案由当前视频核验，不来自静帧运动证据。

---

## FILE: `references/visual-methods/fallback-recipes.md`

# 条件化兜底组合

9组方案为没有新参考、无法联网或需要快速起步时提供候选。它们不是固定模板，也不表示已经通过当前项目审美验证。按素材和叙事选择，具体数值在Direct 2落实；不合适时允许退出或重新组合。

完整判断逻辑见[方法库](method-library.md)。字体等依赖复用[常规资源说明](resources.md)，不为每组方案重复提醒。

<a id="f01"></a>

## F01｜人物关系与真实反应主导

**什么时候用**：人物动作、视线或回应已足以承载关系变化，主要任务是让观众发现。

**起步搭配**：以真实互动和必要上下文为主；正文字幕稳定；有必要时用低干扰位置的短评论补充观察；色彩优先延续原画。

**如何适配**：根据反应强弱决定景别与停留，必要时可快速剪辑；评论尺度、位置和色彩由当前画面推导。

**避免**：把情绪直接宣布成事实；固定慢放、白字、细字体或长淡入。

**不成立时**：画面信息不足时补查上下文；不靠字幕替素材证明关系。

**怎样验证**：连续查看互动及回应，确认先看到人，再理解文字，且解释有证据。

**组合方法**：[M01](method-library.md#m01)、[M02](method-library.md#m02)、[M08](method-library.md#m08)

<a id="f02"></a>

## F02｜鲜明标题的情绪表达

**什么时候用**：主题或章节需要被明确说出，同时希望保留人物情绪与视觉张力。

**起步搭配**：用实际短标题建立主次；选择有职责的强色与清楚字形；人物表情、视线和关键动作留有观看位置。

**如何适配**：比较标题尺度、断行、位置及出现时机；强字与高饱和均为可选，不固定某个色对。

**避免**：沿用海报的完整构图；把标题、对白与评论同时做成最高等级。

**不成立时**：人物信息被压制时先调整时间与位置；仍冲突则转F01，保留需要的章节信息。

**怎样验证**：以真实标题在连续镜头里试读，检查能否在窗口内读完并看到关键反应。

**组合方法**：[M01](method-library.md#m01)、[M03](method-library.md#m03)、[M05](method-library.md#m05)、[M11](method-library.md#m11)

<a id="f03"></a>

## F03｜空间与状态的对照

**什么时候用**：存在有证据的两种状态、两个空间或前后变化，比较本身承担叙事作用。

**起步搭配**：先使用连续镜头建立对应关系；需要同时比较时才并置或分屏；辅助文字解释比较维度。

**如何适配**：根据脸部大小、动作和信息量决定比例、顺序与是否分屏；可用位置呼应而不复制原参考版式。

**避免**：为了形式整齐拼接不同时空，造成同时发生或即时回应的错觉。

**不成立时**：并行阅读困难时回到先后呈现，保留明确的时空提示。

**怎样验证**：核对关系与时空，再检查缩小后的表情、阅读顺序与信息是否完整。

**组合方法**：[M02](method-library.md#m02)、[M04](method-library.md#m04)、[M08](method-library.md#m08)

<a id="f04"></a>

## F04｜物件与局部细节承载主题

**什么时候用**：当前视频中的物件、材质或环境细节与已确认主题存在联系。

**起步搭配**：用原片细节与人物画面构成呼应；文字可邻接物件或有条件地参与空间；局部颜色服务主题。

**如何适配**：按运动与工具能力决定跟踪、贴字或固定标注；细节停留由信息功能决定。

**避免**：下载其他项目的材质或图像补入；无依据加入梦境、记忆或人物心理结论。

**不成立时**：物件没有叙事作用或贴合不稳时，恢复人物画面与普通标题，不保留装饰性意象。

**怎样验证**：检查与主题的联系、文字身份、透视遮挡及连续运动。

**组合方法**：[M07](method-library.md#m07)、[M08](method-library.md#m08)、[M09](method-library.md#m09)

<a id="f05"></a>

## F05｜编辑式信息层级

**什么时候用**：需要解释背景、概括段落或组织较多事实信息。

**起步搭配**：用主标题引导，必要辅助信息分组；图像承担证据或情境；通过尺度与对齐建立阅读顺序。

**如何适配**：按实际文本长度和画幅决定是否拆页、分时揭示或保留较高密度；强调色仅承担明确职责。

**避免**：把杂志小字密度、跨页布局或制作辅助线直接搬到视频。

**不成立时**：阅读超载时优先分组和分时，精简辅助信息；不只是无限缩小字号。

**怎样验证**：检查最长文本、复杂背景与实际停留，连续观看是否一次获得主信息。

**组合方法**：[M03](method-library.md#m03)、[M04](method-library.md#m04)、[M05](method-library.md#m05)、[M08](method-library.md#m08)

<a id="f06"></a>

## F06｜观察式综艺评论

**什么时候用**：素材已存在铺垫、转折与反应，一句观察能增加趣味。

**起步搭配**：正文字幕稳定，评论集中在真实转折处；用字重、位置、颜色或简短运动中的合适手段强调。

**如何适配**：根据原声与反应确定进入、停留和退出；静态文字也可成立，画面缩放仅在有用途时加入。

**避免**：提前揭示包袱；每句套梗；连续音效掩盖原话。

**不成立时**：评论没有新增观察时删除，保留真实反应与切镜节拍。

**怎样验证**：从铺垫连看至结果，比对有无评论；保证原话、观察与玩笑的身份清楚。

**组合方法**：[M01](method-library.md#m01)、[M05](method-library.md#m05)、[M12](method-library.md#m12)

<a id="f07"></a>

## F07｜稳定对白与角色识别

**什么时候用**：人物多、换人频繁或需要统一姓名与正文字幕。

**起步搭配**：正文结构保持稳定，姓名承担识别，角色色与姓名共同工作；在不同背景上维持清晰对比。

**如何适配**：按真实姓名和长短对白确定宽度、换行和位置；字幕条样式可以丰富，但正文阅读必须连续。

**避免**：把样式对照板的多条字幕堆成实际播出画面；用颜色替代姓名信息。

**不成立时**：承载底遮挡内容时调整位置、尺寸或简化轮廓；角色身份明确时减少重复标签。

**怎样验证**：检查换人、长句、双人同框和原有硬字幕，并播放检查阅读与避让。

**组合方法**：[M04](method-library.md#m04)、[M05](method-library.md#m05)、[M06](method-library.md#m06)、[M11](method-library.md#m11)

<a id="f08"></a>

## F08｜任务与线索的图形组织

**什么时候用**：当前内容确有任务、规则、线索或进度需要帮助观众跟踪。

**起步搭配**：用当前视频配合自制文字与几何标记；符号一一对应真实内容，主次、层次与颜色角色统一。

**如何适配**：依据任务复杂度决定静态提示、分步揭示或空间分区；图形形态从当前信息推导。

**避免**：套入参考项目的谍战或游戏设定；用装饰公式、箭头制造不存在的推理。

**不成立时**：没有明确语义或制作能力不足时，改用简洁的文字步骤与原片。

**怎样验证**：逐个回查标记对应的素材节点，连续检查揭示顺序与关键证据可见性。

**组合方法**：[M04](method-library.md#m04)、[M05](method-library.md#m05)、[M10](method-library.md#m10)

<a id="f09"></a>

## F09｜动作或反应的局部强调

**什么时候用**：同一原画面内已有关键动作或反应，常速观看时重点不易被发现。

**起步搭配**：先比较原速原画、固定裁切与原生近景；必要时试局部缩放或变速，保留动作与声音的完整性。

**如何适配**：由主体运动、源分辨率、帧率、对白和节拍决定框体、速度、曲线及窗口，并回写时间映射。

**避免**：把放大和慢放当作情绪公式；为处理效果丢失另一人物、关键物件或完整对白。

**不成立时**：画质、声音或关系受损时恢复原速宽画面，通过镜头顺序或字幕时机引导。

**怎样验证**：比较完整音画和处理前后信息量，检查出框、插帧、声画及总长预算。

**组合方法**：[M01](method-library.md#m01)、[M13](method-library.md#m13)、[M14](method-library.md#m14)

---

## FILE: `references/visual-reference-router.md`

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

---

## FILE: `visual-reference/visual-reference-package-v2.4.3/references/visual-design-procedure.md`

# 视觉方案执行规程 · Visual Design Procedure v2.3.6 base + progressive integration

适用：Direct 2 的视觉阶段，从“D1 / Detail / D2 文案已登记”到 Implementation Lock。
范围：creator text、台词引用、开场 / 片尾 / 封面文字等所有压在原片上的视觉元素。

每一步形成对应 JSON，运行检查脚本确认。脚本会重新测量画面、核对引用和哈希。依照 `NEXT_ALLOWED` 进入下一步。


先读 [Visual Direction Atlas](visual-direction-atlas.md)、[图文关系](scene-text-grammar.md) 与 [文字时序](timing-grammar.md)，在 V1 形成 `direction_hypothesis`。V2 用当前项目证据校准，V3 再深化方向。V5 核查实际展示证据，V6 记录用户选择。独立评审按项目条件启用。

---

## 铁律（执行模型必须遵守）

1. **按 V0 → V7 顺序，一次只做一步。** 每步产出对应 JSON（模板在 `templates/visual-stage/`），然后运行：
   `python3 -I scripts/check_visual_stage.py <项目视觉目录>`
   只做检查结果里 `NEXT_ALLOWED` 指向的那一步。
2. **声称某一步完成时，回复里必须贴出检查脚本对这一步的输出行。**
3. **不知道就写 `unknown` 并停下来问，不编造。** 测量值会被重测，偏差超过 10 即失败。
4. **文字只能来自 V0 登记的文案。** 需要改文案，回到 D2 改 V0。
5. **参考图只能通过结构卡迁移，并且逐条核对条件。** 每个迁移项只在它所需的条件全部满足时可用；可测量的条件按 V1 区域实测值核对；没有“部分满足”。
6. **V3 先写 Art Direction，再写参数。** 说不清这版设计怎样参与叙事、依赖本镜头什么、在什么情况下失效，就不要往下定字体颜色。
7. **V5 之后必须停下，把比较结果交给用户。** V6 只能由用户原话确认。
8. **真实设计输入变化才使相关后序失效。** 当前模板使用 `inputs_design_sha256` 做 canonical design fingerprint；空白、键序、说明性备注等记录变化只产生记录差异，不重做设计。源素材、Mockup、展示 artifact、Proof 等实际文件仍按内容 SHA 强绑定。历史 case 的 `inputs_sha256` 继续保持旧 byte-chain。

---

## 步骤总表

| 步骤 | 必须产出 | 过关条件（脚本检查） | 停止条件 |
|---|---|---|---|
| **V0 登记** | `V0-intake.json` | 源绑定齐全；文案逐句登记并标 `act` / `say`；关键帧必须是完整源帧，裁切图列入 `blocked_keyframes` | 文案未登记、没有完整源帧 |
| **V1 视觉问题** | `V1-visual-problems.json` | 每个关键帧都有：等比几何、保护区、字幕带、实测区域、1–3 个问题，问题引用区域或保护区 | 无法测量的画面 |
| **V2 校准方向** | `V2-reference-selection.json` | 用 `no_ref_needed` 逐项说明如何以当前项目证据校准 V1 的问题；如自行配置参考，逐项核对结构卡条件 | 问题未覆盖 |
| **V1 方向初判** | `V1-visual-problems.json#direction_hypothesis` | 画面问题测完后、选参考前，先判断全局与逐镜头的注意力所有者、文字角色、空间关系、timing、强调预算；不得引用 REF/XR/MR | — |
| **V2 方向校准** | `V2-reference-selection.json#direction_context` | 与 V1 初判一致，并说明需校准的具体问题 | — |
| **V3 候选方案** | `V3-candidates.json` | `direction_read` 深化全局基调；每个 candidate 有 `direction_strategy`，每个 per-shot 有 `direction_use`，允许同一视频前后使用不同观看逻辑；再进入 Art Direction 与参数。`explore_new` 为 2–3 个方案；`reuse_confirmed/simple_text` 可 1–3 个 | — |
| **V4 Mockup + QA** | `V4-mockups.json` + 图片 | `full` 时覆盖全部关键帧；`representative_first` 时只覆盖 V3 登记的代表关键帧。均须等比，字高、对比度、避让、字幕带达标 | — |
| **V5 设计评审** | `V5-design-review.json` + 比较页 | 主观设计论证（不自动判美）+ do-not-transfer；small-screen 必须；blur/squint 按问题启用；blind-map 只在真实盲审时生成；展示 artifact 路径+SHA；字幕缩到底线以下必须否决 | **必须停下等用户** |
| **V6 用户决定** | `V6-user-decision.json` | `confirmed` 必须附用户原话 + 实际确认 artifact SHA；若 V0 文案 working，还要逐字 copy confirmation | `pending` 或 `revise` |
| **V7 锁定参数** | `V7-lock.json` | `style` 与 V3 选定方案一致；V4 已验证元素直接锁定；代表性验证下新增正式元素必须写 `validation_basis` + `adaptation`；有进出时间和动态；有参考时 `reference_trace` 可解析，无参考路径保持空 | — |

---

## 各步要点

### V0 登记
- 只登记，不设计。`act` = 动作 / 结果 / 结论，`say` = 说法 / 引用 / 信息。
- 用 `design_scope.mode` 决定验证强度：`explore_new` 才强制多方案；`simple_text` 可单案。`reuse_confirmed` 也可单案，但必须用 `reuse_evidence` 绑定此前真实 V6/V7/confirmed artifact；只写 `basis` 不够。图文关系、动效语言或几何策略有实质变化时必须回 `explore_new`。
- 文案未经用户逐句确认时写 `copy_status: working`。
- 放大过的证据裁切不是完整源帧，列入 `blocked_keyframes`。

### V1 视觉问题
- 先测量，再下结论。区域坐标用源片像素，亮度用 0–255 灰度。
- 问题写“画面里什么东西造成了什么限制”，不写“需要高级感”。
- V2 要用的可测条件（平、亮、暗、细节少、竖向结构）都要在这里先测出对应区域。

### V2 校准方向
- 从当前源帧、已登记文案和 V1 的区域测量出发，写明需校准的方向。
- 公开版默认用 `no_ref_needed` 逐项覆盖 V1 问题，`selections` 留空。V3/V7 的参考 trace 同样留空。
- 结构卡的**每个条件**都要判定：`met`、`not_met`，或（仅限卡上标明可创造的条件）`created_by_design` 并写清用什么手段、代价是什么。
- 判定 `met` 的可测条件必须写 `zone`，脚本会用该区域的实测值核对。
- 看状态：**已入库**可以借原则和数值；**原则可用**只借原则（比如“词贴细节、无框”），不借参考的字高、距离；**待确认**没有可用的卡，不能直接选。

### V3 候选方案（先 Direction Read，再 Art Direction，最后参数）

**先不要选字体。** 打开 `visual-reference/visual-reference-package-v2.4.3/references/visual-direction-atlas.md`、`scene-text-grammar.md`、`timing-grammar.md`，完成 V3 的 `direction_read`：

- `attention_owner / attention_sequence`：这一刻先看人物、动作、关系还是文字；
- `text_role`：观察、关系注解、细节标注、反差第二声部、情绪余韵、punchline 或章节；
- `spatial_relation`：邻接、关系轴、负空间、表面绑定、对重、夺权或独立字段；
- `typography_voice`：中性观察、温和编辑、干式机锋、轻俏、强断言；
- `motion_relation`：事实同步、reaction 后补、随语义形成、余韵、切镜定义或声音绑定；
- `emphasis_budget`：low / medium / high，并说明本段最需要避免的模板化做法。

Atlas 是知识底稿，不是自动分类器，也不新增 PASS/FAIL Gate；它的作用是避免“先找空白、再挑字体”的现场发明式 Art Direction。

然后按 V0 `design_scope` 决定候选数量，再用 `validation_scope` 决定是 `full` 还是 `representative_first`。代表性路径必须说明代表帧覆盖什么，并把 deferred keyframe 标成 `standard` 或 `difficult`；长文字、多人、复杂背景、窄净区、字幕冲突、运动主体等困难镜头必须记录 risk_tags。代表帧负责选方案，困难镜头负责验证适配，两者不能混为一谈。

V1 初判、V2 校准、V3 全局 `direction_read` 完成后，每个候选先写 `direction_strategy`，每个镜头写 `direction_use`，再写下面四项及 `dimensions`、`style`：

1. **`art_direction_thesis`**：一句话说清这版设计怎样参与这条视频的叙事。必须引用至少一句 V0 文案（`copy_refs`）和一个 V1 画面元素（`image_refs`）。
   - 动作观察和对白引用可以分别贴近所指对象，用空间与字重明确各自的作用。
2. **`composition_grammar`**（每个镜头）：主视觉是谁、文字形成什么形状、利用哪块负空间、哪条线是视觉轴、阅读顺序（必须同时包含文字和画面元素）、视觉重心在哪。
3. **`shot_dependency`**（每个镜头）：这个设计依赖本镜头的哪些元素；换到别的镜头会怎样。说不出依赖什么，就可能是模板。
4. **`failure_condition`**：什么情况下这套设计不成立；能量化的写成区域阈值。

另外：`explore_new` 多候选的实质差异可以来自 5 个形式结构维度，也可以来自注意力顺序、文字角色、空间关系、timing、强调预算及逐镜头方向。**不要求为了凑“两个形式维度”硬改画幅或文字方向。**单候选的 `reuse_confirmed/simple_text` 不为凑数制造假差异。`style` 写可执行参数；有 selection 时 `ref_trace` 写到迁移项 id（如 `T1`），全 `no_ref_needed` 时保持空。

### V4 Mockup + QA
- 只能用真实关键帧，等比缩放，不生成替代人物或场景。
- 可用 `scripts/caption_place.py` 或项目渲染器。按当前样稿填写 QA 字段，烧录字幕字高填实测值。

### v2.3.6 Evidence-bound Art Direction 工具链

- V3 前可运行 `art_direction_brief.py`：只把 V0/V1/V2 的事实压成 brief，不替你设计。
- V4 完成后运行 `make_review_board.py`：默认只生成 480px small-screen board；确有视觉重心/明暗块问题时加 `--blur`；实际要做独立盲审时才加 `--blind` 生成随机 blind-map。
- 再运行 `design_quality_audit.py`：只查模板复用、镜头依赖和小屏证据，不给“高级感自动分”。
- 只有真实独立评审时，reviewer 才看盲化 board / mockup，并用 `finalize_independent_review.py` 绑定当前 blind-map。
- V5 Gate 必查 small-screen、do-not-transfer checks 和展示 artifact 的真实 SHA；blur/blind 只在启用时检查。
- 独立盲审默认 optional；如果使用，评审文件必须绑定当前 blind-map / board SHA。代码只能验证“绑定”和 reviewer 的独立性声明，不能证明 reviewer 真正独立。
- `quality_claim=not_automated`：V5 PASS 只表示证据链机械完整，不等于自动认证“高级感”。
- 有动态方案时用 `make_motion_state_board.py` 做 before / enter / hold / exit 四态板；静态高级不代表运动后仍成立。

### V5 设计评审
- `explore_new` 需做代表性同源 A/B。公开版没有预置已测参考豁免项。
- A/B 绑定同一源帧 SHA、所属 unit 的完整文案与实际画布。同文件或解码像素相同只能记为 `no_visible_change`。动态时序由 Proof 验证。
- 8 个问题仍保留作为**设计论证提示**：画面是否兑现论点 / 第一眼主次 / 图文融合 / 字体 / 颜色 / 叙事细节 / 去装饰测试 / 模板风险。它们不是机器审美 Gate，缺失只 warning。
- `do_not_transfer_checks` 是硬检查；允许如实写 `fail`，但该候选必须列入 `rejected`，或回 V4 修改后重做 V5。
- small-screen board 必须和当前 V4 file+SHA 形成证据链；blur/squint 只有 `review_scope.blur_squint.status=used` 时要求，`not_needed` 必须写理由。
- blind-map 只在实际 independent review 时存在。独立 review 只有在 policy=required 时必须；optional 时可 `not_used`。使用时必须绑定当前 blind-map/board SHA，并记录 reviewer id/type/origin/independence 声明。
- 做比较页交给用户，然后停下。

### V6 用户决定
- 用户说“好很多”不等于选定方案；没有明确选择就保持 `pending`。

### V7 锁定参数
- 锁定阶段不改设计；要改设计，回到 V3。
- `representative_first` 下，未在 V4 出现的正式元素必须绑定一个实际验证过的 `validation_basis`，并写 `adaptation`；`rect` 必须落在 canvas 内。被 V3 标为 `difficult` 的 deferred keyframe 还必须在 `expansion_checks` 绑定真实成图 + SHA，并复核字号、对比度、保护区距离、字幕带；普通 deferred 镜头无需重新比稿。
- V7 style / design-chain 建议由宿主 `scripts/sync_visual_stage.py` 机械同步，避免和 V3 重复手填。
- 记录文字进出时间、动态参数与其对应的当前画面或声音证据。

---

## 剧情剪辑方法（可选，不加 Gate）

- **字与画面：**见 [剧情剪辑方法](editing-grammar.md)。按单人、双人、动作与文字角色分别判断落位。
- **文字时序：**以切点、动作可辨认时刻、对白或阅读时长为依据，按角色处理。
- **剪辑节奏：**保留动作和叙事所需的镜长。混源调色在当前素材上做同源比较。
- **CP 应用：**双人同框、关系观察文字、中文长句与结尾文字见 [CP 关系观察型视觉应用补充](cp-relationship-visual-application.md)。
- **序列计划：**`templates/sequence/S0-sequence-plan.json` 可选，不新增检查门；音乐与卡拍仍服从项目 audio policy。
- **参考片分析：**`scripts/analyze_clip.py` 可选；输出是测量辅助，不是自动剪辑评分。

## 常见偏离与拦截方式

以下为常见偏离及检查对应的回退条件。

| 偏离 | 拦截 |
|---|---|
| 跳过问题定义和选参考，直接出方案 | 后续文件存在而前序缺失 → FAIL |
| 新风格探索只做一个方案 | `explore_new` 候选数 < 2；`reuse_confirmed/simple_text` 单案合法 |
| 几个方案只是换颜色 | 结构维度差异 < 2 |
| 自己改写文案 | 元素文字不在 V0 |
| 编造测量值 | 重测偏差 > 10 |
| 事后改了真实设计输入 | design fingerprint 不符；空白/备注等记录变化不触发设计失效 |
| 所需条件不满足还迁移该项 | 迁移项的 requires 未全部满足 |
| 迁移结构卡里没有的东西（符号化） | 迁移项 id 不在卡上 |
| 用“部分满足”蒙混条件 | status 只能是 met / not_met / created_by_design |
| 声称条件满足，但指定区域的实测值不达标 | 按区域实测值核对阈值 |
| 依赖“由设计创造”的条件，却没用对应几何 | 方案几何不在 creatable_by 里 |
| Art Direction 论点空泛，不引用文案和画面 | thesis 过短或没有 copy_refs / image_refs |
| 说不出依赖本镜头什么（模板） | shot_dependency 为空或引用别的镜头 |
| 阅读顺序只排文字，不排画面 | reading_order 必须含画面元素 |
| 替用户确认方案 | `confirmed` 无用户原话 |
| 烧录字幕被缩到底线以下的方案没被处理 | V5 未否决 |

---

## 文件位置

- 模板：`templates/visual-stage/V0-intake.json` … `V7-lock.json`
- 检查脚本：`scripts/check_visual_stage.py`
- 可配置参考目录：`manifests/reference-structure-cards.json`、`manifests/external-references.json`
- 截帧测量：`scripts/measure_frame.py`（单帧）
- 可选字幕落位测量：`scripts/caption_place.py`

---

## FILE: `references/montage-rules.md`

# 重组与剪辑规则

## 方案映射与素材范围

本文件主要服务于已有 brief / rough editorial plan 的素材映射与执行。把画面中已经存在但分散的关联组织出来，但不能为了匹配 plan 强行制造关系。每条只保留一个主要观看体验，例如心动、会心一笑、踏实、释然或带劲。

下表中的十一类情感索引保留为 **Direct 层可选参考**：只有用户明确让本 Skill 辅助 brainstorming 时才使用；默认执行流程不靠它自行决定选题。它们是检索提示，不是要求素材服从的结论。

| 同时成立的愿望 | 优先观察的证据 |
|---|---|
| 被看懂与保有体面 | 不张扬的帮助、保留选择权 |
| 强烈吸引与自主靠近 | 停顿之后由对方主动回应 |
| 各自生活与持续被惦记 | 不在场时仍影响对方选择 |
| 保留独特性与形成共同语言 | 暗号起点、复现和变化 |
| 尽情发光与得到真心喝彩 | 具体而热烈的回应 |
| 认真竞争与关系依然稳固 | 真正较量、胜负后的欣赏 |
| 可以依靠与也值得被依靠 | 不同场景中交换主导权 |
| 去更远处与仍为彼此留位置 | 支持出发、安排联结 |
| 潜力被看见与成长由自己决定 | 记住愿望、支持自主尝试 |
| 自由表达与心意被准确接收 | 付出线索和准确回应 |
| 允许小失误与一起做好下一次 | 表达偏好、实际调整和反馈 |

优先使用同一事件，其次同集的相关事件，再考虑相邻集或跨集主题。判断顺序是语义与因果、关系阶段、时空可辨识性、动作连续性、服装道具和声音衔接。漂亮的接点不能抵消错误因果。

## 四种重组方式

rough plan 可以采用下列一种或多种结构关系。Detail Structure 负责检查这些关系是否真的得到原素材支持；若不成立，返回 Direct 调整，不用剪辑手法硬做。


| 方式 | 段落组织 | 核对重点 |
|---|---|---|
| 前后反差 | 表态、后续选择、实际行动 | 原表态是否有条件或玩笑语境；行动是否针对同一件事 |
| 铺垫兑现 | 线索出现、暂时搁置、后续回收 | 是否真是同一物件、约定或主题，而非外观相似 |
| 行为变化 | 两次或多次完整互动的比较 | 比较维度一致，关系阶段明确，每次回应都完整 |
| 视角对照 | 一方知道的事情、另一方可见的表现 | 不把角色未知的信息写成其行为动机 |

可把结果提前作为钩子，但让观众辨认倒叙。可并列不同事件，但不伪装成同一次问答。同一集内部调序同样可能改变意思，不能因为服装统一就省略核对。

## 完整片段的边界

片段由意义决定，不按一秒、三秒或固定镜头数切分。最短完整范围至少满足：人物和指代可理解；一句话的否定、条件与转折保留；必要回应存在；动作的发起、发展和后果可见。

“我不会帮你，如果你还是这样”不能只保留“我不会帮你”再接帮助场面制造反差。“不是不想去，是今天走不开”也不能截成“不想去”。完整句有时仍不足以保持原意，前一问、下一句或现场玩笑反应可能同样必须保留。

为 unit 标明 protected_ranges。选入该 unit 后，剪辑区间必须包含所有保护区间；若确需改变保护范围，先重新回看并更新依据，不能仅为压时长删除保护标记。

优先连续保留动作链。若原片已有正反打，通常沿用；“一段完整素材”不要求固定机位。不要为每个分析点另切一个镜头。

## 相邻段落如何接

每个接点选择以下一种关系，并写明依据：

- continuous：同一事件连续推进，源区间和声画变化支持连续性。
- ellipsis：省略同一事件中不影响理解的部分；保留省略内容记录，检查道具、站位和语气。
- comparison：比较不同事件；允许场景变化，必要时标注此前、后来或集数。
- flashback：时间回退；用清楚且克制的提示建立倒叙。
- chapter_change：转入新场景或新阶段；给观众重新定位的时间。

接点还要写：为什么放在一起、被省略的内容、声音接法、是否需要时间或地点提示、可能的误读。无法解释接续关系时，先改结构或删除弱段落。

异场笑容、点头或沉默不能借作某句台词的即时反应。J-cut 或 L-cut 可帮助衔接，但不能让另一时空的台词或声音冒充当前事件。不能把有台词的画面随意静音来制造“默默接受”。

## 画面与声音

主场景承担主要情绪与交流，辅助片段只承担必要的铺垫、对比或兑现。允许多个完整事件共同组成主线，不规定主场景必须占某个比例。

原声句首、落句、重要呼吸和回应保留。音量差先核实并调整；不可凭文字稿判断听感。原片音乐或环境声跳变时，按换切点、保留较长原段、明确转场的顺序处理；轻淡化仅用于听过后确实改善的接点。

动作爆发和同场对话优先连续原片或正常硬切。叠化只在必要且不损伤台词、动作时使用，不以闪白、抖动或复杂特效掩盖错误结构。

## 文字与封面

原声字幕与创作者解释分区。创作者解释原则上每次不超过两行；同一段意义可以跨多个镜头保持，不随正反打换位置。不挡脸、手和关键道具。文字停留以正常播放可读为准。

成片比例与分辨率确定后再给像素坐标、字号和安全区。未确定时使用相对位置并标为待定；不直接把横屏字号套进竖屏。实机可读性优先，放不下先减字或延长，不先缩小字体。

封面必须给出选帧 source_id 与时间码、主字、可选栏目角标。标题和封面承诺必须由成片兑现。不要预设每条都使用古诗词；用户选择该栏目时，保留完整诗句、必要解释和出处，教学页停留由阅读量决定。

## 文字尺寸的量化校准

先确定画布、最终裁切、文字作用和渲染器，再定字号。不能把不同软件的 38pt、48pt 与 FFmpeg 的像素字号直接比较；名义字号也不等于汉字实际可见高度。

1. 优先选用本项目中用户已认可的文字作为锚点；其次选原素材中清楚可读的字幕。保存锚点原帧、分辨率和文字实际字形高度 h。最终画面高度为 H 时，以 h/原帧高度×H 换算到当前画布；有裁切或缩放时按真实变换重新测量。
2. 按功能调整锚点：原声字幕可从锚点的 1.0—1.2 倍试起，创作者主句 1.2—1.5 倍，章节卡 1.5—1.9 倍。这是候选范围，不是已验证的设计标准；还需检查布局、最长行、遮挡和手机观看。
3. 没有合适锚点时，用实际字形高度占画面高度的比例做第一轮：原声字幕约 4.5%—6%，主句约 5.5%—7%，章节卡约 7%—9%。**项目把三个区间的下沿（4.5% / 5.5% / 7%）作为默认机器可读性 floor 写入 `project.text_policy`，这是本版基于现有规范新增的硬化默认值，不声称是历史项目曾确认过的旧数字。** 项目有明确已确认字号 / 锚点时，以项目值更新 policy，并使 Production Lock 重新计算。不能把小字原片字幕当上限。
4. 用实际字体和最长文案渲染三档对照帧，记录 renderer_font_parameter、font_size_value、font_unit、font_file、glyph_height_px、canvas_height_px、line_width_px。选择能读清且不遮挡关键动作的一档；已有用户明确字号反馈时直接落实，无需再设审批关卡。
5. 用户要求“增加10pt”时，在原编辑器的同一字号单位下增加10；迁移渲染器时按渲染后字形高度复核，不能随意把10pt改成10px。修改后检查两行占高、行距和安全区，不只改一个数字。

## 文字停留的起始档位

以下以短中文文案为调试起点，来自项目实践，尚非跨项目验证结论。stable_hold 指文字完全显现、位置不动的可读时间，淡入和淡出另计。完整诗句、解释或较长原声字幕按实际阅读量延长。

| 文案类型 | stable_hold 起点 | 调整规则 |
|---|---|---|
| 短单行 | 3.0—3.5秒 | 同时看人物动作时取较长值 |
| 双行 | 3.5—4.5秒 | 长句按字数继续延长 |
| 三行 | 4.5—5.0秒 | 原则上先减字或拆表达；三行是例外 |
| 结论句或完整诗句 | 4.5—5.0秒 | 解释和出处不能挤占主句阅读时间 |
| 黑场章节卡文字 | 至少3.0秒 | 总时长另加淡入淡出 |

辅助校验：stable_hold 不短于“显示字符数÷4.5”的秒数，并与上表取较大值；它只是阅读负担的初始估计，最终仍按正常播放实看调整。复杂句、陌生词、诗句训释适当放慢。默认淡出可从0.5—0.6秒试起。不要把总显示3秒减去淡入淡出后，仍宣称有3秒阅读时间。

## 黑场章节卡

跨集、跨时段或情绪阶段变化，且单靠画面不能让观众定位时，优先试用纯黑底的简短章节卡承载 chapter_change。它是有条件的首选，不是每个接点的默认转场，也不是零风险手段；过多会打断情绪。

卡片用一句具体提示说明变化，不插入无关片名、剧集logo或装饰性片头。在部分项目中，片名卡可能显得突兀，黑场过渡更合适；这类判断属于项目经验，不推广成所有片名卡都无效。

无字黑场或极短视觉停顿可从总时长2.5—3.5秒试起；有字卡片必须同时满足稳定可读时间。例如淡入0.2秒、stable_hold 3.0秒、淡出0.5秒，卡片总长至少3.7秒，不能同时套用2.8秒总长。需要延长卡片时，重算后续画面、文字和音频位置。

章节卡作为独立 card 事件计入时长。章节文字放独立文字轨，便于返工；声音是否延续、渐弱或留空按情境决定，不能自动把黑场做成静音。

## 压缩顺序

先删重复解释，再删已经证明过的反应或重复例子，再整段删次要对白，再缩短非必要无声停顿和装饰。核心片段仍放不下时提出合理时长或减少论点，不拆碎必要问答。

---

## FILE: `references/render-engineering.md`

# 渲染与工程检查

目录：适用范围、双时间轴、分层渲染、近静音、导出验收、接点图表、工具降级、缓存、运行方法。

## 适用范围

本节补充 F/G 阶段工程执行。规则来自多轮实际返工与工程校验经验；参数仅作为可调试起点，优先服从本项目明确要求。任何具体文件、耗时或声压测量只有在当前项目实际复测后才能写成事实。

先读取 montage-rules 中的文字尺寸锚点、稳定阅读时间和章节卡规则。抽帧分析完成不等于可以跳过下述渲染检查。

## 双时间轴与最终坐标

分别保留源素材坐标与成片坐标。源坐标确定每段从哪里取画面、对白和环境声；成片坐标确定取出的东西何时播放。音轨既要源取段坐标，也要成片放置坐标，不能因为音频取自源段就沿用未压缩的放置时间。

为了兼容原有连续时间轴，timeline.json 保留未扣叠化的编排计划，并写 coordinate_space=assembly。所有需要渲染、字幕烧录、音轨放置、封面定位、接点核查的程序只读取编译后的 render-manifest.json，coordinate_space=output。不能把 output 再交给编译器重复扣除叠化。

冻结每段的输出帧数 L_i 和相邻叠化帧数 O_i，按整数帧计算：S_1=0；S_i=S_(i-1)+L_(i-1)−O_(i-1)；总帧数 N=ΣL_i−ΣO_i。硬切的 O_i=0；黑场卡是独立段落，它会增加总长。这个公式适用于顺序排列、相邻两段重叠的模式，不涵盖三段同时混合；本工具会拒绝三重叠化。

例如编排总长137.8秒、存在11处各计划0.35秒的叠化时，算术目标为133.95秒；固定帧率输出仍必须进一步量化为整数帧。例如30fps时0.35秒等于10.5帧，不能声称每处都是精确0.35秒。先选择并记录实际帧数，再统一编译，禁止多处分别四舍五入而不记录累计差异。

音轨、文字轨和封面定位应保存 anchor_event_id 与段内 local_in_frame/local_out_frame；编译后转换为成片位置。跨段文字若不随某一段移动，可明确 coordinate_space=output，但每次结构变动后必须人工重核它的绝对位置。相邻片段重叠区有两个源画面，不能用一条全局减法反推唯一源帧。

有 protected_ranges 的对白与关键动作不应落在被叠化遮挡或淡音削弱的区间。用额外 handles 或改切点解决；确需例外时填写针对该接点的 `overrides`：`violated_rule=protected_overlap`，绑定被影响的源区间、成功且版本一致的 review 及 Direct 2 创作决定。`overlap_protection_review` 的自由文字不再单独放行；详见 [执行完整性契约](execution-integrity.md)。

## 时长预算守恒

进入 ready_for_render 前先对 `timeline.duration_budget`。以整数帧求和：`Σ event frames − Σ transition overlap frames = computed_output_frames`。黑场卡、freeze / hold 等真正增加时间的元素必须作为 event 进入预算；普通覆盖式文字轨不与视频时长相加。若文字 stable hold 放不进当前 event，必须显式延长 / 新增事件、减字或从其他段释放预算，然后重新编译。

有明确时长上限时，预算未对平不得继续；调整段长、章节卡或转场后立即重新计算，而不是等导出后才发现超时。

## 分层渲染与局部返工

分层流程可使用 [Blender 局部合成与动态验证](visual-production.md)：模型先交方法，只对 `proof_composition_ids` 中代表性限定窗口使用同一工程渲染静态 Proof 和连续 demo，经当前版本审阅/确认后冻结 Production Lock；其余同类 Blender 窗口在最终授权后按锁定实现一次性正式渲染，再在正式 output 帧区间回接。`render_blender_composition.py` 只允许前置关口通过的 scoped build；`finish_ffmpeg.py` 复用正式 manifest/authorization，将已确认合成段插回 clean-video 并使用已确认 mix。工程 receipt 和最终 FFmpeg receipt 均不代替真实 QA。

1. 视频单元层：按已验证源切点生成规范化片段，统一画布、帧率、像素格式和时间基准。再按 render-manifest 生成无新增文字的 clean_video。用 xfade 时尤其要确认输入参数一致。
2. 音频层：从源坐标提取原声，按成片坐标混音，生成 mix_audio。单独记录对白、环境音、音乐及人声分离的来源和处理参数；每条重要音轨同时写 `narrative_role` / `treatment_reason`，先判断它承担对白信息、环境连续性、情绪音乐、节奏提示还是有意静默，再决定保留、分离、衰减、替换或删除。
3. 文字与交付层：在 clean_video 上烧录文字，合入 mix_audio，导出成片。黑场卡尽量保留无字底片，文字也在这一层添加。

只改字号、措辞或既有画面内的文字停留时，复用前两层；烧录文字改变像素，最终视频流仍需重新编码。音轨无改动且封装允许时可复制音频流。若使用独立字幕轨，才可能仅更新字幕并重新封装。不要笼统宣称“改字完全无需视频重编码”。

延长章节卡、改变片段长度或改动叠化时长会改变结构，须重新编译时间轴并使受影响的合成底片、音轨放置和文字层失效，不能作为纯文字修改处理。不要把已烧字成片再烧一遍新字；始终使用无字中间文件。

## 人声分离与近静音

人声分离可能同时移除环境声和配乐；对白稀疏的长动作段可能变得近乎无声。约−55至−67 dBFS 代表很低的非零电平，不能仅据此称为严格的数字零静音。

对选用的人声轨、mix_audio 和最终成片扫描低电平窗口。第一轮可用阈值−50 dBFS、最短连续1秒；随素材底噪和有意静默调整并记录。扫描只筛选待听位置，不能单凭命中判定错误，也不能把未命中当成音质正常。

命中后回听原音轨与分离轨，检查是合理停顿、背景被移除，还是截断/混音缺失。修复优先服从项目声音要求：

- 允许原片音乐时，可试人声加原声低电平垫底；“−30dB”指相对原轨的衰减起点，不是最终绝对dBFS目标。复听重复人声、相位、音乐残留及峰值，不能自动套用。
- 明确要求去掉音乐、只保留对白和环境音时，不得直接混回含音乐的原轨。优先找原场景可用的环境声或经核查的分离环境层；无可靠来源时保留缺口并说明，不能为填声音违反要求。
- 场景允许且符合用户要求时，可改回原轨。不得把高潮段统一静音或循环无关声音冒充现场。

## 导出验收

工具返回 true、done、exit 0 只能证明任务进程结束。每次导出必须完整解码，实测实际视频帧数、展示时长、首尾时间、帧率节奏和解码错误，并与 render-manifest 的预期值比较。禁止仅查看容器中声明的 duration 或 nb_frames。

固定帧率目标应得到预期 N 帧；偏差超过1帧硬失败，恰好1帧必须记录并查明边界或量化原因，不自动通过。时长比较用解码视频的展示区间，不能拿包含音频编码尾部的容器总时长直接套一帧阈值。若保留可变帧率，则改用源到输出的 PTS 映射与实际展示区间；本附带程序按固定帧率交付检查，不能认证 VFR 成片。

同时对最终文件做全片低电平扫描，并核对音轨是否存在、与画面时长及关键对白是否同步。程序会输出扫描记录；主观听感、单通道异常、对白清晰度、响度及同步仍需实际核查。音频扫描失败、没有音轨、未匹配到应解析的数据都不能写成“未发现静音”。有意静默写入 expected_quiet_ranges 并逐一复核，不因扫描命中而盲目加声。

## 每个接点的自动对照表

从实际最终导出文件抽取，使用同版本 render-manifest 中的成片帧号。禁止从源素材或未扣叠化的时间轴抽图代替最终接点。

- 硬切：至少抽 B−1 与 B 两帧；可额外看前后约0.25秒。
- 叠化：抽重叠前、开始、中间、结束前及结束后的帧，检查整个转场区间，不将它简化为一个切点。
- 每行标出接点序号、event_id、成片帧号及时间。分成多页也必须覆盖全部接点；生成原图和图表，不能只保存压缩缩略图。
- 保存素材成片哈希、manifest哈希及每张图的帧号，防止核查旧版本。没有 Pillow 时可保留全量带编号单帧和索引，不宣布“对照表已生成”。

对照表用于快速定位，不能替代真实播放。每个接点仍需检查前后至少一至两秒或完整叠化区间的动态与声音；由有能力的模型或人工逐项记录。四十个接点可分批检查，不以“肉眼不可能”为由省略。

## 工具缺失与解析失败

执行前发现 ffmpeg、ffprobe、Python、Pillow 及真实版本。不要默认存在 bc；用 Python 整数或 Fraction 计算时长与帧数。

审计和扫描脚本先写为 UTF-8 文件再执行，不通过多层 shell heredoc 传入正则。此项约束针对审计代码的实际运行，生成脚本本身仍可使用可靠的文件写入工具。调用媒体程序使用参数数组，避免引号、反斜杠和文件名被 shell 改写。

脚本启动时用已知日志样本校验正则和解析器；解析不到必要字段、出现未知格式或返回非零时输出 error，不将其当作零异常。安装或工具版本改变后，用已知有声/静音区间的短合成文件验证扫描链路。

缺少 ffprobe 时，ffmpeg -i 可用于获取容器声明时长的初步参考；不能取代完整解码计数。附带 audit_render.py 使用 FFmpeg 的 framemd5 完整解码输出取得帧数与展示时间，不依赖 ffprobe 或 bc。FFmpeg 也不可用时只能使用经验证的等价 MCP；否则保留未验证状态。

## 反馈分类与失效范围

收到一组修改意见时，先分类再返工，防止本可局部修改的问题触发全流程重烧，也防止结构变化只改表面层：

| 反馈类型 | 典型内容 | 必须失效 / 回退范围 |
|---|---|---|
| 纯文字层 | 措辞、字号、既有画面内文字停留 | text layer + final；clean video / 未改音轨可复用 |
| 声音层 | 去音乐、换音轨、混音策略 | audio layer + final |
| 结构层 | 切点、段长、章节卡长度、叠化 | 重新编译 timeline；所有依赖成片坐标的音频 / 文字 / final 失效 |
| 创意层 | 主线、段落功能、素材关系改变 | 回 D Direct；随后只重做受影响的 E Detail Structure 与下游 |

分类不改变用户已确认的核心表达。若一条反馈同时跨层，以影响范围最大的那一层为准，并记录为什么。

## 缓存与强制失效

每个片段建立 manifest。缓存键至少包含源版本、source_in_ms、source_out_ms、输出帧数、变速、裁切缩放、画布与帧率、编码参数及工具版本。片段编号或文件名相同不代表缓存可复用。

切点、长度任一变化，强制失效该片段缓存及依赖它的合成层。脚本可提供 --force 绕过缓存；如果实际工具没有该选项，改用新缓存键或删除明确对应的旧中间文件，不能虚构工具参数。重切后核对实际长度和首尾帧，再在新 manifest 里登记。

文字变化只更新文字层键；叠化变化更新成片布局与下游键；声音处理变化更新音频与最终输出键。无字底片、音轨和成片分别保存哈希与依赖键。版本未知、manifest缺失或长度不符时不得命中缓存。

## 运行方法

先完成 validate_project 的核心数据检查。确保 timeline.coordinate_space=assembly、fps 已确定，transitions 为每个接点记录 effect=hard_cut 或 xfade，overlap_frames 为实际整数帧数。音轨与文字使用段内锚点。

```text
python3 scripts/compile_render_manifest.py 项目目录
python3 scripts/audit_render.py 成片.mp4 项目目录/render-manifest.json --outdir 核查目录 --contacts
```

第一条生成编译时间轴和分层缓存键；它不会自行渲染。第二条完整解码、扫描近静音、按成片时间轴生成接点单帧和对照表；它不会判断剧情。根据 render-manifest 调用真实 MCP 或本地渲染流程后再运行第二条。审计结束后仍要正常速度播放全片，填写 qa。

技术依据：FFmpeg 官方 [xfade、silencedetect及相关过滤器说明](https://ffmpeg.org/ffmpeg-filters.html)、[解码与流复制说明](https://ffmpeg.org/ffmpeg.html)、[ffprobe帧计数说明](https://ffmpeg.org/ffprobe.html)。查阅日期为2026年9月29日。

## 渲染入口

正式编译默认只接受已授权的 ready_for_render 项目。规划草稿必须显式用 `--planning`；输出为 `render_allowed=false`。渲染适配器消费清单前运行 `check_render_authorization.py PROJECT MANIFEST`，检查授权、证据和输入是否仍是当前版本，并拒绝被改写的清单。外部渲染器须接入这一步，仓库不会控制绕过该入口的第三方程序。

声音缓存包含输出 fps 依赖；改变输出时基须重新确认授权并重编译。技术编译通过继续保留 playback_verified=false，动态听看按原流程执行。

---

## FILE: `references/qa-handoff.md`

# 检查与交接

## 区分四个验证层级

| 层级 | 实际做过什么 | 可以声明什么 |
|---|---|---|
| 静态核查 | 检查记录、引用、时间和文字逻辑 | 记录与计划已检查 |
| 源素材核查 | 回看候选原片并核听原声 | 入选片段的具体事实与切点已核实 |
| 粗剪核查 | 播放真实导出视频，检查接点与全片 | 该版本粗剪已看过，列实际问题 |
| 成片实看 | 检查最终导出、音画同步、文字和手机观看 | 该版本对应检查已通过 |

某一层通过不能代替后一层。用户未提供视频时可交付规范或方案，不得宣布完成实片验证。

## Structure 基础层回归检查

进入 Content Map、Direct 1、Direct 2 或 Execute 前，先确认 Structure 的最低信息地板没有被摘要替代：

- `frames.jsonl` 中每个已分析 sampled frame 都能在 `frame-observations.csv` 找到同一 `frame_id`；
- 每行基础观察显式保留帧号 / 时间 / 帧尾 ms、画面事实、动作 / 状态、`motif_tags`、硬字幕 / 可见文字、**原声要点及核听状态**、`change_from_previous`、`content_description`、**topic_judgment、confidence / confidence_basis**、unknowns；没有内容时使用 `none` / `unknown` / `not_applicable`，不留空；
- 动作 / 视线 / 站位 / 物件变化候选进入 `action-node-candidates.csv`；默认 4fps 局部窗口，偏离时有例外原因；
- 会改变场景理解、plan 或剪辑意义的问题进入 `structure-questions.csv`，其 unresolved / unverified 状态持续可见；
- Detail Structure 先保留 `detail-intervals.csv` 的进入原因 / 前情 / 当前背景 / 后续 / 目标问题，再对核心区域保留完整画面、背景、动作链、关键变化、情绪线索、硬字幕、原声及核听状态、before / after、主题判定、confidence、说话人裁决引用、问题引用、反证和未验证项；
- `speaker-adjudications.csv` 在有说话人 / 对象歧义时保留帧级口型 / 原声 / 字幕 / ASR 裁决；无歧义时也保留带表头文件。
- Broad Structure 的正式出口首先是这些文字化结构表单；overview、Content Map、情绪大意、Narrative Direction、Execution Plan、最终文案或 edit plan 都不能反向替代上述基础记录。
- 抽样中未出现的动作 / 台词 / 物件不得直接写成“没有发生”；4fps 只用于加密观察和缩小窗口。negative fact 必须限定 source-time scope，并按事实类型使用覆盖完整机会窗口的连续视频、覆盖声明区间的连续原声，或能直接排除该事实的可靠反证。
- 硬字幕 / 原声 / ASR 冲突有显式记录；方言 / 强口音 ASR 未核听时只作 locator，不作为唯一台词事实。
- 每个关键证据保持稳定 `source_id + source time`；`frame-observations.csv` 与 `frames.jsonl` 的时间一致，Deep observation 落在对应 Detail interval，speaker adjudication 与 utterance 源区间相符。
- 每个 source 的 `time_mapping` 与可用物理边界已记录；会限制 Direct 的 `usable_ranges / downstream_constraints` 已进入 Content Map / handoff。

缺字段或缺结构且没有异常说明，属于 Structure regression，应补回 B / E。原字段 / 产物保留且已显式声明无法获得的原因、影响与下游处理时，继续可做的整理 / 草案 / 交接，不把未知项当成事实，也不豁免正式渲染门槛。

## 跨模型 / 跨机器交付检查

每个大阶段结束时确认 `handoff.md` 已重新生成，并与当前 `project.json` / 产物一致。handoff 至少应可见：当前阶段与 Scope Lock、有效确认与 pending/stale、下一步、实际随附文件路径 + SHA-256 + bytes、project 状态 digest、source_id / source signature / time mapping / locator。Detail 另检查 `execution-handoff.md`。

换机器时，不要求原绝对路径保持不变；要求能用 source signature / time mapping 对新 locator 做重绑定。若关键素材没有随包、也没有可重绑定入口，必须在 handoff 写明外部依赖和影响，不能把旧机器路径当成已可访问资源。换模型 / 会话时接收方先读 handoff + project，再按 manifest 读取相关文件，不依赖上一轮聊天摘要恢复事实。

## Execute 前的规定动作

- Detail 的真实关键帧清单、可用图片、独立 `execution-handoff.md` 及异常随包交付；handoff 已直接写明下游完整输出要求。
- 已确认 Execution Package 同时包含计划与 `execution-reference.md`：必要文字全文 / 时间锚点、具体样式、音轨 / 接点、资产 / 约束和 QA 判据齐全，Execute 无需另定核心风格。锁定风格的 mockup 与参数随包交付（要求见 [执行包契约](execution-package.md)）；未完成样稿明确待补项。

- `timeline.duration_budget` 已按整数帧对平；普通覆盖式文字未被重复加到总长，真正延时的 card / hold 已成为 event；有时长上限时不得超预算进入 ready_for_render。
- 每个进入执行的 source event 已显式列出 `deep_observation_refs`；只校验本次实际采用的 observation，确认 source 一致、source-time 覆盖采用区间、evidence_status 为 supported / partial；同 unit 其他未采用的 pending / contradicted 记录不作为阻断项。
- 每个 source event 已引用 `edit_boundary_ref`；默认 source_in/out 落在 safe-in / safe-out windows 并覆盖 must-keep ranges。若 boundary override=true，必须确认它是有意创作选择，并有 reason + review refs，而不是切点未核准。
- audio track 已标 `narrative_role` / `treatment_reason`，不会因为提取 vocals 就把 BGM / ambience 的叙事作用默认为无效。
- 本轮反馈已经按文字 / 声音 / 结构 / 创意分类，并按对应 invalidation 范围处理。
- source time → assembly/output frame 的映射仍能回查，结构改动后旧绝对成片坐标没有被偷用。

## 导出后的规定动作

按“渲染与工程检查”对每次最终导出进行完整解码，核对实际帧数和视频展示时长。固定帧率偏差超过1帧失败，恰好1帧查明并记录，不以done或exit 0通过。保存预期值、实测值、解码错误、成片哈希及manifest哈希。

全片扫描近静音；区分扫描成功且没有命中、发现待核听窗口、没有音轨、工具或解析失败。后两种不是“没有问题”。按项目声音要求复核和修复，不自动混入原片音乐。

从同一最终文件、按编译后的成片帧号生成全部接点对照表；叠化覆盖开始、中间与结束。之后逐接点播放动态及原声，并正常速度看全片。自动化减少定位工作，不替代观看。qa 分别记录技术检查、图表检查、动态听看、手机实看，不合并成一个pass。

## EVA 项目

| 项目 | 要检查的具体问题 | 优先修正 |
|---|---|---|
| Narrative | 陌生观众能否理解人物、事件和重组关系 | 补回必要前情或减少论点 |
| Meaning | 是否截掉否定、条件、回应或制造虚假因果 | 恢复完整单元，调整主线 |
| Context | 重排是否把不同日期、关系阶段当成同一事件 | 明确时空变化或换素材 |
| Audio | 句首句尾、语气、底噪、原片音乐、音画同步 | 移切点、延长原段，再调整声音 |
| Rhythm | 是否人为碎切、动作未完成、重要反应看不清 | 合并段落、删除重复例子 |
| Visual | 站位、道具、服装、光线变化是否造成误读 | 改接点或接受明确场景切换 |
| Text | 能否正常速度读完；是否与原字幕争抢 | 减字、固定区域、延长停留 |
| Redundancy | 画面、台词、花字、结尾是否重复解释 | 指定主要表达载体，删重复 |
| Source | 每个判断、画面、台词能否回查到正确版本 | 修复引用与时间映射 |
| Mobile | 手机上是否看清、字幕遮挡和裁切是否合适 | 以实际手机检查记录为准 |
| ReferenceCompliance | 成片是否忠实于当前 selected Mockup + executable Proof + Implementation Lock，并且 selected REF 的 application trace 真正体现在 source role、字体/层级、颜色、版式比例、crop、renderer 与运动方法中 | 按当前 Implementation Lock 修正；`r1=r2` / pixel diff=0 只证明可复现，不证明设计一致 |
| CompositionCompliance | schema 1.9：采用的 Blender 工程、参数和素材是否与确认 demo 一致；`composition_windows` 必须逐项列出 render-manifest 的每个 composition_id、start/end frame 与 production video SHA-256，并为每段写 `status: pass` + 非空 `finding`；含 join 的段另写非空 `join_finding`；manifest + 各 composition video 作为 evidence | 按 validator 返回的具体 composition / 字段错误定位受影响合成，保留其余部分 |
| MotionContinuity | schema 1.9：推近/移动的起止、末尾状态、前后镜头接点是否自然；有无复位、跳切或图层漂移 | 正常速度看完整接点两侧，修改对应工程后重做动态验证 |
| DeliveryTechnical | schema 1.9：当前 FFmpeg 输出的帧数、规格、音轨和完整解码是否通过，是否绑定当前 manifest | 对实际成片重测；技术成功不代替视觉/听感验收 |

qa.json 包含 project_id、artifact_version、checks、blocking_issues、open_questions、rough_cut_verified、final_playback_verified。启用 workflow_control 时另存当前成片的 artifact_sha256，并在 project.workflow_control.render_output_ref 登记输出文件；最终交付检查会拒绝与当前成片不符的旧 QA。checks 每项记录 name、status、method、evidence、finding、action。status 只用 pass、fail、not_tested、not_applicable。

**覆盖检查的边界。** coverage 当前验证 element ID / method / renderer / join / native 工程来源，但 layer/group 的实际运动曲线参数尚未与 Implementation Lock element parameters 做 hash 级绑定；如果同一 element ID 下偷偷换曲线，仍需 Proof / Final QA 发现。后续硬化应增加参数映射与 hash，不把本轮无法机器证明的语义写成已校验。

无真实导出文件时 Audio 的计划逻辑可以检查，但实际听感必须记 not_tested；Mobile 未实看也记 not_tested；ReferenceCompliance 未实际对照当前 Mockup / Proof / Implementation Lock 时同样记 not_tested。`pass` 还必须绑定 selected REF IDs、mockup / proof(s) / implementation-lock 的 SHA-256 与证据路径；多 Proof 时 `ReferenceCompliance.proof_sha256s` 按 proof ref → SHA-256 完整列出。不能为了完成清单填全部 pass。

## 何时退回哪一步

- 指代、条件、动作因果或原声核听有误：退回 E Detail Structure；必要时补 C Content Map 的场景理解。
- Narrative Direction 的核心节点没有证据、反差来自截断原话、或新前后文会改变核心表达：把 evidence gap / 冲突证据退回 D1 Direct 调整主线；执行层不擅自重写主题。
- Detail 证据已经成立但最终素材取舍、排序、声音 / 文字 / 时长策略尚未确认：停在 D2 Direct，不直接进入 Execute。
- Direct 1 只调整局部节点：优先复用 Broad Structure 与已验证证据，只补受影响的 E 区域。
- 新方向依赖此前低覆盖区域：先补 B/C 对应区域，再进入 E。
- 声音与画面不顺：先 F 调切点；若改变意义，退回 E。
- 来源版本不一致、时码漂移：退回 A，暂停精确导出。
- 工具失败或能力缺失：保留已完成产物，更新 capability-map 和待补区间；不要从头重做已验证部分。

## handoff.md 模板

```text
项目与产物版本：
本轮目标及已确认范围：
当前阶段与实际完成情况：
已处理素材和区间：
未处理或低可信区间：
关键决定及对应证据 ID：
当前 brief / Narrative Direction / Editorial Execution Plan 及来源：
第二轮 Detail Structure 已补查节点与证据缺口（并确认 `deep-observations.csv` 是否已覆盖核心区域的画面 / 内容 / 背景 / 前后状态）：
关键帧清单 / 实际图片 / 提取异常：
Detail 的独立 execution-handoff 及其内嵌下游输出要求：
Execution Package（计划 / reference / 风格样本 / 资产 / 约束 / QA）及确认来源：
已有文件与路径：
实际使用的工具和能力缺口：
源版本及时间映射注意事项：
仍未验证的音画、语境与切点：
文字锚点、实际字号单位与稳定阅读时间：
成片manifest、导出哈希及预期/实测帧数：
近静音窗口、原因与修复记录：
全接点图表及动态复核完成情况：
可复用中间产物、缓存键及强制失效项：
下一步具体动作及输入文件：
不得改动的已确认内容：
```

交接时不只传此摘要；同时提供 sources、必要证据、候选和时间轴。长项目可按需传所选 scene/unit 及其引用的完整证据，但告知接收者其他区间尚未加载，不能把局部交接当成全片证明。

## 给另一模型的启动指令

首次任务可使用：

```text
请把随附《长视频混剪跨模型与MCP执行规范》作为本任务的工作说明。
先盘点我提供的素材、已有记录和实际可用的视频工具，输出能力映射。
第一轮先做 Broad Structure，建立可回查的 `frames.jsonl`、逐抽样帧 `frame-observations.csv`（含帧尾、原声要点、主题判定、confidence）、`action-node-candidates.csv`（动作节点默认 4fps 局部窗口并记录最小有效单元候选）、`structure-questions.csv`、场景、overview 和 Content Map；如果当前只要求内容地图，到这里正式交付。
如果要继续混剪，先把 Broad Structure 的正式文字化表单 + Content Map 交给我或独立 Director，形成 Narrative Direction；不要默认替代第一次创意决策。
拿到 Narrative Direction 后，先建 `detail-intervals.csv` 明确精查区间的前情 / 当前背景 / 后续 / 目标问题，再回原素材做 Detail Structure；目标问题、最小完整互动 / 动作单元、Edit Boundary、相关反证四项闭合后 STOP DETAIL。然后固定交付真实关键帧与独立 execution-handoff，并在其中直接写明 Scope Lock、`capability-map.json` 中相关分析 / 执行工具、execution-plan、制作 reference、文字 / 声音 / 转场、资源 / 约束和 QA 要求；再交回 Director 形成完整 Execution Package。视觉上先用一两个 Aesthetic Mockup 选审美，再由最终 Execute 可访问的同一实际工具链生成 Executable Proof；两步可跨模型 / 会话，proof_confirmed 前不得正式 Execute。
优先同集，保留完整对白与动作，不根据抽样帧或摘要补造未验证内容。
已有确认信息直接沿用。遇到缺口先完成可做部分，并指出具体缺少哪段素材或哪种能力。
素材位置：
限定集数或范围：
目标人物或关系（如有）：
已有 brief / Narrative Direction / Editorial Execution Plan：
时长和比例要求：
交付目标：详细执行稿 / 粗剪 / 成片
已确认方案或禁改项：
```

续接任务可使用：

```text
请按随附执行规范续接这个项目。先读 handoff、project、sources、coverage、Structured Observation Layer、content-map、brief、`narrative-direction`、`execution-handoff`、`keyframe-references`、`execution-plan`、`execution-reference`、异常说明和 capability-map；兼容旧项目时再读 legacy `editorial-plan`。随后读取当前 narrative / execution mapping 引用的 scene / unit / Deep observation / review / 原始证据。
先核对当前能力与源版本；复用已有成果，只补齐缺口，不重新概括替代原记录。
继续完成 handoff 中的下一步。报告实际核验范围，不把前一模型的摘要写成自己的直接观察。
```

## 交付表达

交付时列清：完成的是规范、计划、粗剪还是成片；覆盖了哪些素材；实际核验到哪一层；仍有哪些具体问题。若没有材料可处理，就交付可执行规范和输入清单，不假装已经处理过长视频。

## 授权与证据交接

交接保留 execution-authorization.json、采用证据的 source_signature / time_mapping_digest、清单 input_digest / manifest_digest 与 render_allowed。规划清单不得当作已允许渲染；素材或确认文件改变后先判断证据 / 方案失效范围，再重新核实、裁决和编译。机器检查通过与最终听看通过继续分开记录。

---

## FILE: `references/mcp-adapter.md`

# MCP 适配

## 能力发现与职责

开始时读取当前环境公开的工具列表、参数 schema、返回值和限制。不要猜测工具名、API 参数、模型上传上限、支持的时间戳粒度或剪辑软件导入格式。只有确认存在的能力才能填 actual_tool；未确认填 null。

模型负责素材结构化、语境理解、Content Map、rough plan 的证据映射、因果检查、定向精查、素材取舍和文字表达。创意主线默认来自人、brainstorming 或独立 Director 流程；只有用户明确授权本 Skill 参与 Direct 时，才把创意候选作为单独草案输出。视频 MCP 或本地工具负责媒体元数据、转码、抽帧、字幕音频处理、剪切、时间轴和导出。工具返回的“甜蜜、嫉妒”等标签属于解读，不自动升级为事实。

| 内部能力名 | 最低输入 | 预期返回 | 缺失时的处理 |
|---|---|---|---|
| inspect_media | 授权素材引用 | 时长、音视频流、帧率模式、时间基准 | 请求用户或工具补元数据；不生成精确切点 |
| get_transcript | source_id、区间、语言、匹配字幕 | 逐条起止时间、文字、来源、说话人或未知 | 读取现有字幕；仍无则做画面分析 |
| detect_shots | source_id、范围、检测参数 | 技术切换区间与参数 | 定时抽帧并标记切换边界未检 |
| extract_frames | source_id、时间列表或抽样规则 | 原图、实际时间戳、frame_id | 用已有带时间码的图片；无法定位则只做粗索引 |
| make_contact_sheet | frames、版式、标签 | 九宫格、每格与原图映射 | 不拼图，按带标签的单帧阅读 |
| inspect_av | source_id、区间、所需模态 | 真实观察记录、可回查证据与能力范围 | 请求用户核听/观看；保持 provisional |
| render_timeline | 已核对时间轴、源文件、输出配置 | 新输出文件、日志、实际参数 | 交付详细稿，不宣称有粗剪 |
| inspect_output | 输出文件、检查项目 | 时长、可播放性、音画与文字检查记录 | 只完成技术或静态检查，保留实看待办 |
| export_editor_project | 时间轴、目标软件已验证格式 | 工程文件或导入文件、日志 | 交付中立时间轴，标记尚需格式适配 |

本地原片且 identity 映射时优先用 `scripts/extract_frames.py`；远程 / MCP、代理 / 偏移或缺少本地工具时，使用 capability-map 中经短段校验的抽帧适配器，保留实测媒体时间、canonical source time 与源绑定。脚本限制不改变项目的既有时间映射；已有带时间码图片仍按表中降级路径处理。

抽帧适配器在小范围探测时须证明返回的是**每帧实测时间**：取一段约 2 秒的素材，用 ffprobe / showinfo 读出的帧 pts（或本地 `extract_frames.py` 的输出）逐帧比对，误差不超过一帧，并核对画面确为该时刻；结果写入该能力的 `timestamp_method`（`measured_pts` 或 `computed`）与 `tested_range`。只能给出"起点 + 序号 × 间隔"推算时间的适配器记为 `computed`，只用于粗定位，不用于 Detail 事实与切点。

inspect_av 可以由具备对应模态能力的模型、工具或人工完成。仅返回抽样图片的工具不能登记为连续音画观察。纯文字模型可处理记录与方案，但必须保留上游证据来源。

## capability-map.json

复制 `assets/capability-map-template.json` 建立项目能力映射。顶层为 `schema_version` 与 `capabilities`；每个 capability 至少写以下字段。`entrypoint` 是实际可调用的脚本、命令、模板、组件或服务入口；仅有工具名但没有可复现入口时，不能把 Visual Proof 标为 confirmed。

```json
{
  "capability": "extract_frames",
  "actual_tool": null,
  "entrypoint": null,
  "status": "unavailable",
  "input_mapping": {},
  "output_mapping": {},
  "time_unit": null,
  "end_semantics": null,
  "limits": {},
  "tested_range": null,
  "timestamp_method": null,
  "audio_observation": false,
  "video_observation": false,
  "fallback": "读取用户提供的带时间码单帧"
}
```

status 只用 available、unavailable、unverified。工具存在但未试过所需功能时写 unverified。一次成功测试只能证明该功能在测试条件下可用，不能推断所有编解码器和素材都支持。Visual Gate=`proof_confirmed` 时，不能由任意 available capability 代替 proof renderer：每个代表性 Proof 都必须由一条 available capability 的 `output_mapping` 实际映射，并同时具有可调用的 `actual_tool + entrypoint`；单 Proof 兼容字段是 `visual_proof_ref`，多 Proof 全量见 `visual_proof_refs`。

Broad / Detail 使用过的真实能力继续保留在同一 `capability-map.json`；进入 D2 时，execution-handoff 只摘录与本条有关的分析能力和最终 Execute 可访问的 render / layout / text / image 能力，不另建 toolchain 文件。Visual Proof 可以由其他模型 / 会话补做，但必须使用这里已登记且最终 Execute 可继续访问的 actual_tool / entrypoint；工具链变化先更新 capability-map 与 execution-reference，再重做 proof。

## 适配和调用顺序

1. 确认实际工具允许的输入位置：本地路径、远程 URL 或服务文件 ID。不要把本地路径当作远端可读 URL；如需上传，只传完成任务所必需且已获授权的素材。
2. 映射参数：将项目毫秒转换为工具单位，明确 end 是包含还是不包含。不要对时间戳连续取整；适配层返回原始值和规范化值。
3. 先用短区间检查元数据、时间码、画面及声音是否匹配。跨工具切换后复核偏移，不能只因同名文件就认为一致。
4. 每次调用登记 job_id、source_id、源版本、区间、参数、工具名、任务状态、返回文件和错误。除源路径外，日志不记录访问令牌、签名 URL 或秘密信息。
5. 独立只读处理可在服务限制内并发；有依赖的处理顺序执行。Broad Structure 与 Detail Structure 可以复用同一能力映射和缓存。第一轮应把已分析 sampled frames 同步整理为人可读 `frame-observations.csv`；第二轮除记录更密的实际观察范围，还应形成 `deep-observations.csv`，把核心区域的画面、内容、场景 / 叙事背景、前后状态和原声核验留下来。不要未经要求开多智能体流程。
6. 异步任务轮询已有 job_id，不反复提交相同渲染。限流或临时失败可按服务建议退避重试，默认最多两次；参数、权限、无效素材错误先修正原因。
7. 渲染到新文件。仅在成功读取并检查输出后标记 completed。错误或缺失的片段不得从 coverage 中悄悄消失。

## 时间与剪切陷阱

- 源视频 PTS、字幕时间、代理时间、成片帧号是不同坐标。统一映射后才组合；不能用九宫格第几格乘抽样间隔代替真实时间。
- 可变帧率源素材用实际展示时间定位。只有确认恒定帧率和起点，才能按帧率计算源帧号。成片帧号按最终输出帧率计算。
- 工具可能只在关键帧附近快速剪切。精确到对白起止的成片需验证实际切点；必要时使用支持精确重编码的路径。不要将快速复制切段结果默认视为帧精确。
- 现成字幕可能是译文、删节字幕或错误时间轴。保留来源类型；只有核听过的原声内容可标为原话已核实。
- 自动音源分离可能有伪影，也可能使对白稀疏的动作段近乎无声。逐段扫描分离轨、混音和最终文件；命中后核听，不以“人声提取成功”代替验收。原声垫底必须符合项目音频要求，禁止为填近静音混回用户已要求去除的音乐。

## 渲染工具与检查能力

将完整解码计数、全片低电平扫描和接点抽帧列为 inspect_output 的具体能力。记录实际方法、工具版本、返回码和可解析字段。渲染返回成功并不代表帧数、时长或音轨完整。

审计代码保存为文件后运行，调用程序使用参数数组，启动时用已知样本检验解析器。没有 ffprobe 时可用 ffmpeg -i 读取声明时长作初步参考，最终仍须完整解码计数；无 bc 时用 Python 计算。解析失败输出 error，不能伪装成“零异常”。详细规范及随附程序见“渲染与工程检查”。

## 参考实现边界

可参考 FFmpeg 的抽帧、tile 拼图、裁剪与音频过滤能力，以及 PySceneDetect 的镜头区间和代表图输出能力。这些是可选底层实现，不代表当前环境已安装或当前 MCP 已暴露。

- FFmpeg 官方过滤器文档：https://ffmpeg.org/ffmpeg-filters.html
- PySceneDetect 官方命令文档：https://www.scenedetect.com/docs/head/cli.html
- Whisper 官方模型局限说明：https://github.com/openai/whisper/blob/main/model-card.md

上述资料于 2026年9月29日查阅。运行时仍须核对实际安装版本；本规范不依赖某个模型名称或 API 版本。


## Blender 合成入口

制作方法和交付契约见 [visual-production.md](visual-production.md)。先检查真实 Blender 可执行文件或 MCP 的工具 schema，不能把插件里的说明当作 MCP 已安装。固定入口是 `scripts/render_blender_composition.py`（Blender CLI + FFmpeg）；复杂处理可由已验证 MCP / Blender Python 制作 `native_blend`，再用同一入口渲染并回读。MCP 只改变操作通道，不绕过 build_composition、代表性 Proof 的动态 review、当前版本确认或最终授权。动态 review 按 `proof_composition_ids` 的最小充分风险范围执行，不要求把每个 planned composition 都提前做成 demo；其余已覆盖的 production window 在最终授权后正式生产，并进入最终成片 QA。记录依赖、版本、局部帧与源时间映射；能力失败时交付缺口，不把效果静默替换成简单推拉。FFmpeg 回接入口是 `scripts/finish_ffmpeg.py`，保留现有 clean-video / mix 工作。

---

## FILE: `visual-reference/visual-reference-package-v2.4.3/references/visual-direction-atlas.md`

# Visual Direction Atlas · 人物互动 + 原声 + 中文观察文字


定位：**视觉知识资产，不是新的流程 Gate。**  
用途：在 V3 定具体字体、颜色、位置之前，先判断“这一段应该用什么视觉语言、为什么”。

---

## 0. 这份 Atlas 解决什么

现有 V0–V7 能保证：文案有来源、参考可追溯、Mockup 可验证、确认可绑定、参数能落地。它不能自动回答：

- 这一刻人物、动作、关系和创作者文字，谁应该先被看见？
- 文字是“评论者”“标注者”“第二声音”“情绪余韵”还是“包袱”？
- 文字应该贴近人物、落在关系轴上、进入负空间，还是暂时夺走画面主位？
- 趣味应该来自字体/颜色/动画，还是来自位置与 timing？
- 什么时候“克制”是高级，什么时候“克制”只是无聊？

因此，Direct 2 的视觉判断顺序应当是：

**内容/关系 beat → 注意力顺序 → 文字角色 → 图文空间关系 → 动态时序 → 字体/颜色/参数。**

不是反过来从“选字体 / 找一个参考”开始。

---

# 1. 六个前置判断轴

任何方案先回答这六个轴，再进入具体视觉参数。

## A1 · Attention Owner｜注意力所有者

这一刻第一眼必须属于谁？

- `face`：表情 / 眼神
- `action`：手、身体动作、物件
- `relationship`：两个人之间的距离、视线、让位、追逐、对峙
- `text`：文字本身就是信息或包袱
- `environment`：场景/空间承担叙事

**规则：** 如果第一眼应属于人物，文字就不能仅因为“更有设计感”而升级为大字主视觉。

## A2 · Text Role｜文字角色

创作者文字不是统一的“字幕”。至少区分：

- `observer_comment`：观众脑中冒出的观察
- `relationship_annotation`：把人物之间的关系结构说清
- `detail_label`：点出一个动作/物件/表情
- `ironic_second_voice`：和画面形成第二层意思
- `emotional_afterimage`：画面已经成立后留下余韵
- `punchline`：在某个瞬间短暂夺取主位
- `segment_marker`：章节/换场/时间地点

文字角色不同，决定完全不同的尺度、位置和 timing。

## A3 · Spatial Relation｜图文空间关系

不是“放左上/右上”，而是文字和人物发生什么关系：

- `adjacent`：贴近被观察对象，但不压关键动作
- `axis_bound`：沿人物视线 / 身体朝向 / 两人连线组织
- `negative_space`：进入画面已有负空间
- `surface_bound`：像长在墙、桌面、物件等承载面上
- `counterweight`：文字与人物分居画面两端形成平衡
- `dominant_field`：文字短暂成为画面主位
- `separate_field`：文字和影像轮流说话，不压图

## A4 · Typography Voice｜字体语气

字体不是“好看/不好看”，而是说话方式：

- `neutral_observer`：中性、清醒、像旁观者
- `warm_editorial`：温和、克制、有书写感但不文艺腔
- `dry_wit`：干、准、略有锋利感
- `playful_light`：轻、俏，但不靠卡通描边
- `assertive`：短促、强权重，只用于真正需要夺权的词

中文观察文字默认不以“可爱字体、综艺字体、手写体”来证明性格；性格优先来自**句子本身、落位、分行、字重和 timing**。

## A5 · Motion Relation｜动态关系

文字运动应回答“它为什么现在动”：

- `appear_with_fact`：信息一成立就出现
- `reaction_echo`：人物反应成立后，文字晚半拍补一刀
- `build_with_speech`：话正在形成，文字随语义推进
- `hold_as_afterimage`：动作结束后留住观察
- `enter_on_cut`：切镜即给结论
- `sound_bound`：只和明确声音/动作节拍绑定

**默认不是弹跳、放大、滑入。默认是先找到“出现的叙事理由”。**

## A6 · Emphasis Budget｜强调预算

一条视频的强调是有限资源。

- `low`：大多数正文观察。人物持续主导，文字只辅助。
- `medium`：关系转折、重要重新定义，可短暂提高文字权重。
- `high`：真正 punchline / 章节转折 / 开场标题。数量必须少。

如果每一句都是 high，等于没有重点。

---

# 2. 核心 Visual Directions

以下是这类视频最常用的 7 种方向。它们不是风格标签，而是**观看关系**。

---

## VD-01 · Observational Whisper｜轻观察

### 适用

人物行为本身已经有趣，创作者只需要让观众“注意到那个细节”。

### 观看结构

**人物/动作 → 观众先自己看到 → 文字补充确认。**

文字不能先于画面把答案说掉。

### 图文关系

- 文字靠近被观察对象，但保留明确呼吸距离。
- 优先使用对象附近的平静区域；没有平静区时宁可稍远，不为“贴”而挡动作。
- 不用箭头也能看懂时，不加箭头。
- 文字块尽量像“停在画面里”，而不是 UI 浮层。

### 字体语气

`neutral_observer` / `dry_wit`。  
常用中等字重；短句靠语义和位置生效，不靠多重描边、渐变、emoji。

### 动态

优先 `reaction_echo` 或 `appear_with_fact`。  
趣味通常来自**晚一点出现**，不是出现方式复杂。

### 适合文案

短观察、重新命名一个动作、点出潜台词。

### 不适合

长解释、信息密集、需要同时比较两个人的句子。

### 视觉失败信号

- 字比人物表情更先被看到；
- 每个动作都配标签；
- 文字离对象很远，只是“找了块空地方”；
- 用卡通字/贴纸替代真正的观察。

## VD-02 · Relationship Geometry｜关系几何

### 适用

视频真正有意思的不是某个人，而是**两个人之间发生了什么**：让、躲、靠近、互相照顾、嘴硬、追问、退一步、视线错位。

### 观看结构

**A → 两人关系 → B → 文字把关系结构显出来。**

文字不能变成第三个独立主角。

### 图文关系

- 先找到人物之间的视觉轴：视线、身体朝向、桌面边缘、走位路径。
- 文字优先沿关系轴的空白组织，而不是机械放边角。
- 两句文字如果分别属于 A / B，可以形成 `split_pair`，但必须共用一条关系逻辑，不能像两个无关标签。
- 如果一人主动、一人反应，主次应沿“动作 → 反应”建立，而不是两个名字同权重。

### 字体语气

整体克制；通过字重/尺度的**轻差异**表达谁先发起、谁后回应。  
不把两个人简单分成两种高饱和颜色，除非颜色本身有长期语义。

### 动态

- 第一条随动作/台词成立；
- 第二条随反应补上；
- 或只在两人关系已经完成时给一句总括，不逐人贴标签。

### 强项

这是“人物互动＋原声＋观察文字”最值得优先建立的默认方向之一。它会让设计服务于关系，而不是服务于版面。

### 视觉失败信号

- 文字只利用负空间，没有利用人物关系；
- 两个人都被贴上说明，像人物介绍页；
- 文字把视线轴切断；
- 为了左右对称牺牲真实主次。

## VD-03 · Reaction Punch｜反应补刀 / 轻 Q

### 适用

真正的趣味发生在**反应**，不是台词本身。观众先看表情/停顿，然后一句文字把那个反应重新命名。

### 观看结构

**触发 → 反应 → 微停 → 文字补刀。**

这是“Q”感最容易做高级的方式：**笑点来自观察和时机，不来自效果数量。**

### 图文关系

- 文字靠近反应主体，但不压眼睛、嘴、手势。
- 可稍微比 VD-01 更大胆，但仍不默认全屏大字。
- 如果反应非常小，文字也应小；设计不应替素材制造过大的情绪。

### 字体语气

`dry_wit` / `playful_light`。  
可以使用更紧的字距、更明确的粗细变化，仍避免多层描边、气泡、爆炸框。

### 动态

核心是 `reaction_echo`。  
**先让观众看到反应，再让文字出现。** 文字同时出现，往往会把笑点从“发现”变成“被告知”。

### 特殊高能版本

确有明确声音/动作节拍时，可将文字进出绑定到声音，但只用于短促的强调节点。

### 视觉失败信号

- 文字比 reaction 更早；
- 所有 reaction 都做弹跳；
- 文字过大，把“俏”做成“吵”；
- 加很多表情符号才能让笑点成立。

---

## VD-04 · Emotional Editorial｜情绪编辑

### 适用

人物表情、停顿、眼神已经很强，文字承担的是**余韵、关系补充、轻微重新理解**。

### 观看结构

**人物 → 情绪稳定下来 → 文字作为第二层阅读。**

### 图文关系

- 人脸与眼神绝对优先。
- 文字与人物保持更大的心理距离；不贴脸，不频繁追随动作。
- 可使用画面边缘、安静暗区、自然负空间。
- 允许文字不与人物“绑定”，而与整幅构图建立编辑关系。

### 字体语气

`warm_editorial` / `neutral_observer`。  
不要用极细字体来伪装“高级”，小屏条件下宁可略厚。

### 动态

`hold_as_afterimage`。  
常见策略是人物先完整演完一个小 beat，文字再进入并保持稳定。退出可以随切镜，不需要表演式动画。

### 视觉失败信号

- 为情绪强行加慢淡入、颗粒、胶片、手写；
- 文字替人物把情绪说尽；
- 文字离人物太近，破坏呼吸感；
- 用“文艺排版”压过真实表演。

## VD-05 · Ironic Second Voice｜反差第二声部

### 适用

文字不是解释画面，而是和画面形成**轻微矛盾、重新定义或反讽**。这是观察型账号最有“作者感”的方向之一。

### 观看结构

**观众先接受画面表层 → 文字改变它的含义。**

### 图文关系

- 不需要始终贴人物；适合进入能让“第二层意思”成立的区域。
- 可以故意与表层信息形成空间分离，例如人物在右，评论在左，像另一个观察者。
- 但不要做成 meme 上下两段模板。

### 字体语气

`dry_wit`。  
字面越锋利，视觉越要克制。文案已经有梗时，设计应少说话。

### 动态

常用 `reaction_echo` / `enter_on_cut`。  
有时最有效的是让文字在观众已经形成第一判断后才出现。

### 视觉失败信号

- 文案只是重复台词；
- 为了“讽刺感”加夸张红字/警报动画；
- 视觉比文案更用力。

---

## VD-06 · Spatial Annotation｜空间标注

### 适用

一个手势、物件、位置变化、服装细节、距离变化本身是叙事证据，需要观众准确看到。

### 观看结构

**对象 → 标签/短注 → 回到对象。**

### 图文关系

- 文字必须真的“属于”那个对象附近的空间。
- 先尝试无指示线邻接；只有对象不明确时才加细线。
- 如果对象在动，优先把文字锚定在稳定空间，不要默认跟踪主体；跟踪只在“空间绑定本身有意义”时使用。

### 字体语气

中性，短，信息型。  
不让标签假装成系统 HUD。

### 动态

`appear_with_fact`，必要时和对象出现同步。  
如果对象已经离开，标签也应尽快退出，不长期漂浮。

### 视觉失败信号

- 线、框、标签比对象更醒目；
- 每个细节都做 UI；
- “科技感”成为默认视觉语言。

---

## VD-07 · Controlled Takeover｜受控夺权 / Punchline

### 适用

真正的转折、段落结论、极短 punchline、章节标题。文字可以**短暂成为主视觉**，但正因为如此必须稀缺。

### 观看结构

**前面长期低权重 → 关键节点突然提升文字权重 → 很快归还画面。**

### 图文关系

- 可以大字、压画面、跨人物轮廓，但要确认当前人物不是需要保护的表情主位。
- 最好和前文形成明显权重差，而不是整条片一直大。

### 字体语气

`assertive`，但保持系统一致。  
不因为“大”就加入额外描边、发光、贴纸。

### 动态

短促明确。可以切入，也可以随着动作/声音出现；退出要干净。

### 视觉失败信号

- 每句结论都大字；
- 大字没有前文克制作为对比；
- 章节语法被拿来做正文观察句。

---

# 3. 三种常见“看起来设计了，其实没有方向”的情况

## 3.1 只找空白，不找关系

把字放在负空间是基础可用性，不是 Art Direction。  
如果人物之间有明显视线、动作和权力关系，文字位置首先应解释这种关系，其次才是“哪里空”。

## 3.2 只做字体气质，不做注意力顺序

换一套更细、更现代的字体不能解决：人物和文字谁先看、文字为何现在出现、为什么停这么久。

## 3.3 把“有趣”理解成更活跃

Q 感 / 综艺感最容易滑向：弹跳、描边、气泡、贴纸、音效。  
更好的默认策略是：**文案准确 + 位置聪明 + timing 晚半拍 + 效果少。**

---

# 4. Direction 选择矩阵

| 内容 beat | 首选方向 | 次选方向 | 谨慎使用 |
|---|---|---|---|
| 一个细节很可爱/很微妙 | VD-01 | VD-03 | VD-07 |
| 两个人之间的让/躲/照顾/拉扯 | VD-02 | VD-01 / VD-05 | VD-07 |
| 表情反应就是笑点 | VD-03 | VD-01 | VD-07 |
| 眼神、停顿、情绪余韵 | VD-04 | VD-05 | VD-03 |
| 画面与真实含义有反差 | VD-05 | VD-01 | VD-03 |
| 手势、物件、位置本身是证据 | VD-06 | VD-01 | VD-03 |
| 章节、真正转折、一次性 punchline | VD-07 | — | 连续使用 VD-07 |

同一段可以 `primary + secondary`，例如：

- 双人关系为主、reaction 轻补刀：`VD-02 + VD-03`
- 情绪为主、最后一句轻反差：`VD-04 + VD-05`

但**不能同时让三个方向争主位**。

---

# 5. 在当前素材上比较观看顺序

需要比稿时，固定源帧、画幅、文案与声音，只比较注意力顺序、落位、字重和出现时机。轻观察让动作先成立；关系几何通过位置和时序组织两个人之间的联系；反应补刀等反应可读再落字。比较结果用于决定本项目的表达尺度。

# 6. 使用原则

1. **先选观看关系，再选参考。**
2. Atlas ID 只是语言索引，不是模板名。
3. 复用某个 VD，不等于复用同样的位置、字体或动画。
4. 若真实素材不支持方向，回到内容判断，不要强行套视觉。
5. 同一条视频需要建立“强调预算”：大多数段落保持低/中权重，少量节点才允许 VD-07。
6. V5 A/B 应优先比较“方向是否更清楚”，而不仅是“新方案看起来更丰富”。

---

## FILE: `visual-reference/visual-reference-package-v2.4.3/references/scene-text-grammar.md`

# Scene × Text Grammar · 真人镜头里的中文观察文字

定位：Visual Direction Atlas 的镜头级补充。  
它不规定统一版式，而是回答：**面对不同真人镜头结构，文字怎样进入画面才像在参与叙事，而不是贴上去。**

---

## 1. Two-shot face-to-face｜对坐 / 对视双人

### 先读什么

- 两人视线轴；
- 谁主动、谁反应；
- 中间空间是“关系空间”还是仅仅空白；
- 是否已有下方硬字幕。

### 优先语法

- 关系是重点：`VD-02 Relationship Geometry`。
- 单个反应是重点：`VD-03 Reaction Punch`。
- 中间空间不要自动塞满字；如果它承载两人视线，文字压进去可能切断关系。

### 常见做法

- 文字放在主动者视线的延伸端，而不是挡在视线中间；
- 或文字靠近 reaction 主体外侧，保留人物之间的视觉连接；
- 两句成对文字要有先后，不做静态对称标签。

### 避免

- A 左边一块、B 右边一块，像人物介绍；
- 两人都上不同颜色；
- 中间大字把两人彻底分开。

---

## 2. Side-by-side｜并排 / 同向人物

### 先读什么

- 两个人是“同盟”还是“对比”；
- 身体朝向是否一致；
- 谁的微动作更重要。

### 语法

- 同盟：文字可作为一个共同观察，不必一人一标签。
- 对比：用位置/字重形成不对称，而不是颜色硬分。
- 一个词同时指两人时，可让同一短词在空间上关联两人，先核对指向是否清楚。

---

## 3. Single close-up reaction｜单人特写反应

### 首选

`VD-03 Reaction Punch` 或 `VD-04 Emotional Editorial`。

### 判断分叉

- 如果 reaction 是趣味：等 reaction 成立后补文字。
- 如果 reaction 是情绪：文字更远、更静，不贴脸。

### 保护区

眼睛、嘴、手势优先级高；文字宁可去侧边或头顶外侧，不覆盖微表情。

---

## 4. Hand / prop action｜手部 / 物件动作

### 首选

`VD-06 Spatial Annotation` / `VD-01 Observational Whisper`。

### 语法

- 文案短时，贴动作对象附近；
- 动作方向清楚时，文字沿动作方向留出“前方空间”，不要堵住运动路径；
- 文字若描述动作结果，可晚于动作出现；若是信息标签，可同步出现。

### 避免

动作在动，文字也同时大幅移动，造成双重运动竞争。

---

## 5. Moving subject｜人物持续移动

### 原则

**默认不追踪。**

只有当“文字属于这个人/物的空间”本身是视觉概念时，才使用 tracking。大多数观察文字更适合：

- 等人物进入稳定区再出现；
- 使用画面固定锚点；
- 或只在一个短 beat 上出现后退出。

追踪不是“更高级”，它只是更强的空间绑定。

---

## 6. Multi-person｜多人画面

### 先判断

- 是群体共同状态，还是其中两个人的关系？
- 观众是否能立刻知道文字在说谁？

### 语法

- 群体共同状态：可以一个短词多点重复，或一个总括句放在群体之外；
- 局部关系：先通过构图/剪辑收窄注意力，再加文字；
- 不要给多人逐一标签，除非“分类/识别”本身就是内容。

---

## 7. Complex background｜复杂背景

### 优先顺序

1. 换位置；
2. 缩短文案；
3. 调字重 / 明暗极性；
4. 非侵入式 protection；
5. 才考虑局部底板。

不要第一步就给文字加厚描边、黑框和阴影。

复杂背景会放大“旧综艺感”，因为多重保护效果很容易让文字像贴纸。

---

## 8. Existing burnt subtitles｜已有烧录字幕

### 原则

观察文字必须成为**第二套清晰语法**，不能和对白字幕抢同一水平带。

- 默认避开字幕带；
- 观察文字应在位置、字重或排列方式上与对白字幕区分；
- 不依赖“不同颜色”作为唯一差异；
- 如果画面实在没有第二个阅读区，减少观察文字比硬塞进去更好。

---

## 9. Long creator copy｜长观察文案

长文案首先是编辑问题，不是排版问题。

### 优先判断

- 能否拆成“发现 → 结论”两步；
- 是否只需要保留真正有新增信息的一半；
- 是否适合让文字在多个镜头之间持续，而不是一镜塞完。

### 版式

- 2–3 行以内优先；
- 分行按语义，而不是追求几何对称；
- 让关键语义词占据稳定位置，不通过五颜六色逐词强调。

---

## 10. Very short punchline｜极短 punchline

短不等于必须大。

先判断它属于：

- `VD-01`：只是轻观察 → 小而近；
- `VD-03`：reaction 补刀 → 稍强但仍服从人物；
- `VD-07`：真正转折 → 才允许短暂大字夺权。

---

## 11. Negative space｜画面有明显负空间

负空间只是“可放字”，不是“应该放字”。

先问：放进去之后，是否强化当前人物关系/观看顺序？如果只是因为空，就仍可能是模板化排版。

拍摄或选镜时就为信息留出合适的空间，让文字与所指对象建立清楚的对应。

---

## 12. Vertical 9:16 crop｜竖屏裁切

竖屏会放大三类风险：

- 人脸更大，文字更容易贴脸；
- 原有左右负空间消失；
- 下方平台 UI / 烧录字幕进一步压缩可用区。

因此竖屏不应直接把 16:9 方案等比缩小。优先重新判断：

- 人物上/下关系；
- 文字是否需要从横向轴改成上下层级；
- 是否需要减少字数，而不是压缩字号。

---

# Shot Grammar 快速表

| 镜头条件 | 首选视觉方向 | 文字与人物关系 | 核心风险 |
|---|---|---|---|
| 双人对视 | VD-02 | 沿关系轴 / 外侧平衡 | 切断视线轴 |
| 单人 reaction | VD-03 / 04 | 靠近但不贴脸 / 远离留白 | 抢表情 |
| 手势物件 | VD-06 / 01 | 邻接对象、避开运动路径 | UI 感过重 |
| 人物移动 | VD-01 | 固定锚点优先 | 无意义 tracking |
| 多人 | VD-01 / 02 | 群体总括或聚焦局部关系 | 每人贴标签 |
| 复杂背景 | 任意 | 先换位置再加 protection | 描边堆叠 |
| 烧录字幕 | 任意 | 建立第二阅读区 | 与对白争带宽 |
| 长文案 | VD-02 / 04 / 05 | 分阶段、跨镜头 | 一镜塞满 |
| 极短 punchline | VD-01 / 03 / 07 | 权重按叙事级别决定 | 短句一律大字 |

---

## FILE: `visual-reference/visual-reference-package-v2.4.3/references/timing-grammar.md`

# Timing Grammar · 观察文字什么时候出现，比怎么出现更重要

定位：同样的静态版式，用不同 timing 会变成完全不同的语气。  
以下是**设计关系**，不是固定帧数表；具体时间必须在真实素材 Dynamic Proof 中验证。

---

## TG-01 · Fact Sync｜事实同步

文字承担信息标签/对象标注。对象一旦清楚可见，文字即可出现。

适用：VD-06。  
风险：若文字比对象早，观众先读答案，再看画面。

---

## TG-02 · Reaction Echo｜反应后补

人物先完成一个可读 reaction，文字在其后进入。

适用：VD-01 / VD-03 / VD-05。  
这是“Q / 有梗”最重要的时间语法之一：**观众先发现，文字再确认。**

风险：同时出现会把发现感变成解释感。

---

## TG-03 · Two-step Relation｜关系两拍

第一句随主动动作/台词出现；第二句随对方反应或结果出现。

适用：VD-02。  
作用：让文字复现关系的因果，而不是一次把结论全部端出来。

风险：两句同时常会做成静态信息卡。

---

## TG-04 · Afterimage Hold｜余韵停留

动作/台词已经结束，文字在短暂稳定段进入并保持，让观众重新理解刚才发生的事。

适用：VD-04 / VD-05。  
风险：过早进入会压掉表演，过晚则像下一段字幕。

---

## TG-05 · Cut Definition｜切镜定义

新镜头一出现，文字立即给这一镜一个重新定义。

适用：强对比、章节、小结。  
风险：频繁使用会变成模板式“每镜一个标题”。

---

## TG-06 · Sound-bound Accent｜声音绑定

只有在有明确声音事件、敲击、拟声、节拍时，文字与声音同生同灭。

适用：VD-03 特殊高能版、VD-07。  

风险：把所有台词都当成 beat，会回到旧式综艺包装。

---


# Timing 的三个判断问题

在 V3 写每个文字元素前先回答：

1. **观众必须先看到什么，文字才成立？**
2. **文字出现后，是让观众继续看人物，还是暂时转去读字？**
3. **文字什么时候已经完成任务，应当退出？**

如果这三问答不出来，动画曲线再精致也只是装饰。

---

# Dynamic Proof 应验证的不是“动画顺不顺”

真正要看：

- 文字有没有抢在 reaction 前面；
- 文字出现时，人物关键动作是否仍然可读；
- hold 是否覆盖真正需要重新理解的那一拍；
- exit 是否把注意力及时还给下一镜；
- 连续几条文字是否都用同一个节奏，导致机械感。

---

## FILE: `visual-reference/visual-reference-package-v2.4.3/README.md`

# Visual Direction & Production Methods

| 内容 | 入口 |
|---|---|
| V0–V7 的阶段证据、模板和使用规则 | [视觉方案执行规程](visual-reference/visual-reference-package-v2.4.3/references/visual-design-procedure.md) |
| 注意力、文字角色、空间关系和强调尺度 | [Visual Direction Atlas](visual-reference/visual-reference-package-v2.4.3/references/visual-direction-atlas.md) |
| 真人镜头的图文关系、落位与阅读顺序 | [Scene × Text Grammar](visual-reference/visual-reference-package-v2.4.3/references/scene-text-grammar.md) |
| 文字进出时机、声音节点与动态验证 | [Timing Grammar](visual-reference/visual-reference-package-v2.4.3/references/timing-grammar.md) |
| 剪辑节奏、镜内运动、转场与混源调色 | [剧情剪辑方法](visual-reference/visual-reference-package-v2.4.3/references/editing-grammar.md) |
| 双人同框、关系观察、原声与长文案 | [人物关系观察](visual-reference/visual-reference-package-v2.4.3/references/cp-relationship-visual-application.md) |
| 动效、跟踪遮挡、景深和字幕落位 | [实现机制](visual-reference/visual-reference-package-v2.4.3/references/motion-implementation-map.md) |

视觉阶段模板在 `templates/visual-stage/`。V2 逐项记录如何依据当前项目的源帧和文案校准方向。新风格在 V5 做代表性同源 A/B，再用 V6 用户决定与 V7 参数锁定接回宿主 Implementation Lock。

运行 `python3 -I scripts/check_visual_stage.py PROJECT/visual`，依输出的 `NEXT_ALLOWED` 续接。依赖见 `scripts/visual-reference-requirements.txt`。

字幕落位工具的输入骨架见 [cue sheet](templates/caption-placement.json)。按当前 V3 样式填写 fonts、roles 和 ink，并登记项目帧与文案。裁切坐标以当前源帧为准。使用代理帧时，在对应 `frames.<id>.source_geometry` 填写 V0 登记的源宽、高。工具的输出画布为 1920×1080，文字检查阈值按项目政策填写。

---

## FILE: `visual-reference/visual-reference-package-v2.4.3/references/editing-grammar.md`

# 剧情剪辑方法 · 字与画面、剪辑节奏 · v2.4.3

适用：影视二创、CP 关系观察、剧情混剪及其他以真实人物表演为证据的视频。

**核心顺序：先判断观众此刻应该看谁、看什么，再决定文字如何进入；剪辑节奏服务证据和情绪，不为套曲线而套曲线。** 本文件沉淀可迁移的方法，不定义账号统一风格，也不替代当前项目的 Art Direction、`text_policy`、音频策略或用户确认。

## 0. 使用方式

把通用原则作为候选。在当前画幅、源帧、文案和原声上验证可读性、叙事作用和失效条件；用 V5–V7 的实际证据决定是否进入锁定。

## 1. 字与画面的关系

### 1.1 用文字指向明确的对象

先确定文字指向谁、哪个动作或哪个物件。观察视线、动作方向和周围的可读空间，再决定文字位置。双人镜头先判断当前注意力属于一人还是两人之间的关系。

### 1.2 用视觉轴建立对应

对象清楚、文字确实描述该对象时，可让文字与对象共用观看高度或方向。落位要保留脸、动作、物件和其他必要证据的可见范围。

### 1.3 选镜头时考虑文字空间

在选镜头时一起判断文字落位。必须遮住表情、手部、物件或另一位人物才能放下时，先换镜头、换时间点或减少文字。

### 1.4 在实际播放尺寸下检查对比

优先寻找低干扰区域。对比不足时按项目的 Style System 调整落位、选择局部保护或换镜头。核对文字停留期间背景的变化。

### 1.5 分清主行和补充信息

短主行可以承担视觉重心。补充信息较长时退一层，字面高度、行数和阅读速度服从项目 `text_policy`。长句放不下时先减字、延长停留或改布局。

### 1.6 为镜内运动留出空间

长句优先落在画面稳定、动作已可辨认的时段。镜内运动本身承载情绪时，可延后文字、缩短文字或另选镜头。动态文字在连续播放中验证。

### 1.7 按文字角色选择入场和退场

人物标注可稍晚于切入，让观众先认清人物；动作观察等动作成立后再落字；对白服从发音时序；长句和结尾给足完整阅读时间。分别记录切点、动作、声音和文字完整显示的时刻。

## 2. 用剪辑节奏组织证据和情绪

### 2.1 保留镜内动作的完整性

对视、靠近、接触或停顿本身有强度时，让镜头完整承载。镜长由动作完整性、表演停顿和信息量决定。

### 2.2 在阅读规则成立后压缩并列单元

第一组为观众建立理解方式。后续同类单元可以缩短；出现新证据、长句或关系变化时留出所需上下文。

### 2.3 让转场承担明确功能

举证段从清楚的硬切开始。需要转场时，说明它用于区分单元、衔接状态还是给观众换气，并核对动作、对白和情绪的连续性。

### 2.4 按动作、视线和叙事关系定切点

项目允许且素材实际有音乐时，可选择少数声音节点做强调。保留动作和原声所需的完整窗口。

### 2.5 在当前素材上比较色彩处理

确实存在多场景色彩不统一时，可同源比较原色与调色候选。颜色提供服装、灯光、时间或其他剧情线索时应保留。短片节奏优先服务必要上下文和叙事闭合。

## 3. 画幅、中文与烧录字幕

### 3.1 画幅换算

跨画幅比较时，先说明按等高、等宽还是裁切换算。执行时重新测量当前源帧几何、景别和安全区，以当前像素与画布为准。

### 3.2 中文文字

- 主行的实际字面高度、行数和宽度，以当前项目 `text_policy` 为准。
- 不照搬拉丁字母的主副行比例，也不照搬参考中的小字高度。
- 长句必须核验实际 glyph-height、行数、稳定 hold 和阅读速度。
- 字放不下时，先减字、延长、换版式或换镜头，不静默缩小。

### 3.3 烧录字幕

源片已有烧录字幕时，先标出字幕带和必须保护的内容。观察文字不得压住对白字幕、嘴部、手部或其他关键证据。对象位于画面下部时，优先考虑上方或侧面空位；仍冲突就换镜头或减少叠字。不得为了腾位置擅自裁掉原片字幕。

## 4. 与 CP 关系观察内容的衔接

人物关系观察的具体处理见 [CP 关系观察型视觉应用](cp-relationship-visual-application.md)。先分清人物标注、动作观察、关系观察、原声字幕、解释性长句和结尾文字。

核心原则：**先让动作、停顿、眼神或前后反差成为证据，再决定是否需要文字点破。** 文字不应提前替观众宣布结论，也不能用视觉效果代替素材证据。

## 5. 失效条件与不可迁移项

- 人物居中、两侧没有安静区域：单人“人脸对侧放字”不成立，换镜头或换布局。
- 双人同框：不能直接套用单人标注的左右关系；先判断当前注意力属于谁、是否属于两人。
- 对白密集或烧录字幕冲突：减少叠字，不让两套文字争夺阅读。
- 长中文文案：按实际字面高度、行数和稳定停留核验可读性。
- 镜头运动本身是情绪证据：不要用文字动画与之争夺注意力。
- 举证段：不为了统一色彩而去色，不为了情绪而加频闪。
- 多集混源调色：在当前素材上比较同源方案，并保留颜色证据。
- 科技 HUD、扫描线、故障字、窄体斜体拉丁字形：先说明叙事功能，再在当前素材上验证可读性和证据完整性。

## 6. 从成功剧情剪辑中沉淀方法

以后新增参考片，按以下步骤处理；不要求每次都新增一条参考，证据不足时保留为 queued / principle，不冒充 measured。

### 6.1 选片与范围

- 选取确实值得研究的剧情剪辑、二创或创作者自剪片段。
- 录屏需画面完整，尽量无播放器控件、弹幕和平台外挂字幕；只分析必要时间窗。
- 项目记录可保留来源、时间窗、文件 SHA-256 和测量结果，用于回查。

### 6.2 观察维度

| 维度 | 人工需要确认 | 工具可辅助测量 |
|---|---|---|
| 所指对象 | 字指向谁、哪个动作或物件 | 人脸 / 对象粗框、文字框、距离 |
| 空间位置 | 文字在对象哪一侧、是否位于视线前方 | 中心点、边距、字高、宽度 |
| 背景与层级 | 背景是否干扰、是否遮挡证据 | 亮度、起伏、对比度、色度 |
| 镜头运动 | 文字出现时画面是否稳定 | 推拉、平移、倾斜估算 |
| 时间 | 文字相对切点、动作、对白的时序 | 出现、显示完整、消失时间 |
| 节奏 | 段落功能、镜头长度、情绪递进 | 镜头数、镜长、转场、镜内运动 |
| 内容关系 | 为什么这个细节值得看 | 不能由脚本代替人工判断 |

### 6.3 写成可迁移规则

每条方法至少写清：
1. 做法：一句话说明画面关系或剪辑行为。
2. 实测：样本数、中位数、范围和源片条件。
3. 条件：什么画面条件下成立；可测的写测量依据。
4. 借什么：明确迁移的是原则还是数值。
5. 不借什么：原作品专属风格、素材和弱点。
6. 失效条件：什么情况下不成立。
7. 当前项目验证：需要怎样的真实关键帧、Mockup 或动态 Proof 才能确认。

### 6.4 记录与复核

将来源绑定、实测记录与迁移判断分开保存。只有逐帧或时序测量、来源 SHA 和适用条件齐备时才记录为 measured。缺少实测时，保留为待验证原则。

## 7. 接入 Direct 2 与执行

- **V1：**基于当前源帧记录 attention owner、所指对象、视觉轴、负空间、镜头运动、字幕带和保护区。测量使用真实 `source.geometry`。
- **V2：**逐项登记如何用当前源帧、文案和验证计划校准方向。区分单人标注、双人关系与长中文文字的使用条件。
- **V3：**先写 Art Direction，再决定文字角色、构图和时序。`motion_grammar` 是可选说明，不是新的审批或验证 Gate。
- **V4–V7：**继续执行既有 Mockup、small-screen / do-not-transfer、V6 实际展示文件 SHA、V7 参数路径解析与 Application Chain。参考方法不能替代真实 Keyframe、Mockup、Implementation Lock 或 Proof。
- **S0 序列计划：**`templates/sequence/S0-sequence-plan.json` 是可选的剪辑前规划表，不新增检查门。它不授权改变项目音频策略。

## 8. 分析工具与限制

`scripts/analyze_clip.py` 可辅助分析参考片或自己的成片：

```bash
# 结构、镜头、转场、分段节奏与色彩
python3 -I scripts/analyze_clip.py structure <视频> --out <目录> --start 0 --end <终点秒> --sections "<起点-终点:段名>"

# 文字卡：先人工填写粗框，再测文字框、背景和出现时间
python3 -I scripts/analyze_clip.py textcards <视频> --boxes <boxes.json> --out <目录>
```

可选依赖：ffmpeg / ffprobe、opencv-python-headless、scipy；具体见 `scripts/visual-reference-requirements.txt`。

**工具输出是测量辅助，不是自动剪辑评价。** 转场检测、镜头运动和颜色分类可能受闪光、快速运动、压缩噪声影响；文字框由人工提供，工具不理解文字语义、人物关系或情绪是否成立。关键切点和特殊效果需回看原片核对；不以脚本统计替代人工判断。

---

## FILE: `visual-reference/visual-reference-package-v2.4.3/references/cp-relationship-visual-application.md`

# CP 关系观察型内容 · 视觉应用补充

版本：v2.4.3 · 方法总则见 [剧情剪辑方法](editing-grammar.md)

本文件补充人物关系观察类内容的画面、文字与声音处理。选题、叙事和文案以当前项目的确认记录为准。

## 1. 内容目标如何影响视觉

从能被原片证实的互动细节进入。让素材和情绪承担主表达，再补上必要的观察或解释，给结尾留出余味。

因此，视觉设计的优先级应是：

1. 让原片动作、表情、原声和人物关系先成立。
2. 让文字帮助观众注意到容易漏看的细节，而不是替素材宣布结论。
3. 观察结论需要解释时，再给足可读时间；心理学只解释半步。
4. 结尾只保留素材自然支持的余味，不为了“升华”额外堆字。

## 2. 文字角色分流

同一条视频中的文字不是一种东西。不要用人物标注的版式、时序和停留时间处理所有文案。

| 文字角色 | 主要任务 | 画面 / 时序原则 | 不应做什么 |
|---|---|---|---|
| 开头钩子 | 建立继续看的理由，指出值得重看的位置 | 可以先于证据出现，但只提出异样或问题；不提前给出完整结论 | 不用文字把高潮提前讲完 |
| 原声对白 / 原片字幕 | 保留人物实际说了什么 | 以原声和源片字幕为准；如需补充说明，避开原字幕带 | 不重复打一遍相同对白，不遮挡原字幕 |
| 人物标注 | 让观众认清当前关注对象 | 先确定人物，再检查其周围是否有适合短标注的低干扰空间 | 不把单人标注规则套到双人关系镜头 |
| 动作 / 物件观察 | 指出某个容易漏掉的动作、停顿或物件 | 先让动作可见；文字可在动作成立后出现，必要时与对象共用视觉轴 | 不抢在动作前替观众解释，也不盖住动作本身 |
| 关系观察 / 点破 | 把前后反差或互动方式说清楚 | 证据先行；文字可以落在镜头空位，也可以在镜头稳定后单独出现 | 不要求每一镜都放字，不把关系判断钉在某个人脸上 |
| 解释性长句 / 诗句 | 提供文学表达或半步解释 | 按当前 `text_policy` 控制字高、行数、停留和阅读速度；优先选择能承载阅读的稳定画面 | 避免把短标注的字高和停留时长套给长句 |
| 结尾共鸣 / 黑屏文字 | 收住已经成立的观察 | 以句子本身的阅读时间决定停留；黑屏不是默认模板，只在内容需要时使用 | 不因参考片随镜头切点消失，就让结尾句过早消失 |

## 3. 双人同框：必须先判断关系焦点

以下方法须用当前项目的真实源帧与 Mockup 验证。

### 3.1 文字指向其中一个人

- 先确认这一拍的动作主体或观察对象是谁。
- 优先使用该人物视线 / 动作前方的空位，但不能遮住另一人的脸、反应或两人之间的距离关系。
- 如果画面没有足够空间，优先换到该人物单人镜头或反应镜头，不强行把字塞进两张脸之间。

### 3.2 文字指向两个人之间的关系

- 不把文字默认归属给其中一方。
- 先观察两人的距离、视线、动作先后和空间关系；文字可考虑中性负空间或两人之外的区域。
- 如果中性空间不足，可把观察文字移到动作成立后的下一镜，或拆成两次出现；不要为了“居中”压住两个人的关系轴。

### 3.3 一个人行动、另一个人反应

- 先让行动发生，再让反应完整出现。
- 如果观察点在反应，文字不要提前压住反应；必要时等反应被观众看见后再点破。
- 不删掉迟疑、拒绝或不回应的部分，再把后续剪成“主动回应”。

### 3.4 两个人都在行动

- 先确定当前镜头的叙事主次，不要求两人永远视觉权重相同。
- 如果两个人都不可缺，宁可不加字或把文字放到动作之后，也不要用单一标签把双人互动简化成单方行为。

## 4. 文字时序：按角色，而不是按统一秒数

- **人物标注：**需要观众先认清人物时，可让标注晚于切入。按切点和人物可辨认的时刻定入场。
- **动作观察：**等动作或停顿已经可辨认，再点破；若文案是开头钩子，可以先提出问题，但不提前给出答案。
- **对白：**服从原声实际发音和字幕时序。
- **长句 / 诗句：**按实际阅读速度给稳定停留。文字完整出现后仍需留出阅读时间；不能只按镜头长度决定。
- **结尾文字：**由句子长度和内容重量决定 hold；不必随镜头切点消失，也不必固定黑屏。

## 5. 中文文字与阅读负担

中文文案按当前项目的 `text_policy` 核验实际字面高度、行数、稳定停留和阅读速度。

执行顺序：

1. 先删掉不改变理解的词，避免一屏塞进多个判断。
2. 再调整换行、位置和阅读节奏。
3. 如果仍然放不下，延长停留或换更稳定的镜头。
4. 只有在内容允许时才拆成两次出现；不能把一个完整判断切碎到观众来不及读。
5. 不得静默缩小到 policy floor 以下。

## 6. 与 30 / 60 / 90 秒内容结构的关系

- **30 秒微观察：**通常只围绕一个细节。画面先给最小充分证据，文字只负责指出“值得重看”的位置和点破；如果 20–25 秒已经闭合，直接停，不为凑时长加结尾大段文字。
- **60 秒主力版：**让素材先建立证据，核心观察在中段兑现；视觉文字不应变成连续旁白的替代品。
- **90 秒增强版：**增加第二组证据或前后对照，不是增加装饰文字。不同证据组之间可以用镜头长度和空间关系形成节奏差异。

详细时长结构、内容权重和文案边界仍以当前项目的内容方案 为准。

## 7. 声音与视觉的边界

视觉参考中的音乐 BPM、拍点或音乐对齐测量只是来源片段的描述，不改变当前项目音频策略。是否保留原声、是否允许 BGM、是否允许旁白，仍由项目既有 audio / voiceover policy 决定；本文件不授权新增音乐或旁白。

## 8. V1–V7 中怎么使用

- **V1：**记录当前镜头的 attention owner（单人 / 双人 / 物件 / 动作）、文字所指对象、关系轴、可用负空间、烧录字幕带和动作保护区。
- **V2：**逐项说明当前画面和文案如何校准方向。新风格在 V5 用代表性同源 A/B 验证。
- **V3：**为每条文字写清 role、referent、reading_order、placement_logic 和 failure_condition。长句要说明阅读窗口；动态文字可选写 `motion_grammar`。
- **V4/V5：**用真实源帧和完整文案做 Mockup；检查脸、手、物件、字幕带、small-screen 和 do-not-transfer。长句必须按项目 policy 验证。
- **V6/V7：**继续绑定真实展示文件、用户原话、Mockup 和参数路径；本补充不改变既有 Gate。

**最终原则：文字是帮助观众看见素材，不是替素材表演。**

---

## FILE: `visual-reference/visual-reference-package-v2.4.3/references/motion-implementation-map.md`

# Motion Implementation Map v2.0 — Visual Reference Library 2.0

## 三条证据链必须分开

1. **Screen / Observed Reference**：第三方 REF 实际可见的构图、材质、层级、空间或运动线索；
2. **Source Implementation Evidence**：只有公开工程/作者资料真正支持时，才记录原作实现信息；
3. **Our Implementation Method**：IR-01–IR-11 是我们的 Blender / FFmpeg 实现路线，不能反写成原作技术栈。

## 11 套 Implementation Rig / System

### IR-01 · Transform Timing Rig
- 覆盖：`T01, T02, T03, T04, T05, T06, T07`
- 实现基座：F-Curves + Drivers + custom properties; optional offset tooling
- 主要控制：`progress, delay_frames, stiffness, damping, overshoot, hold_frames, phase, seed`

### IR-02 · Camera Depth Rig
- 覆盖：`C01, C02, C03, C04, C05, C06, C07, C08`
- 实现基座：Camera + Follow Path + Damped/Locked Track + depth planes + DOF
- 主要控制：`camera_path, offset_factor, look_target, lens, focus_target, fstop, depth_spacing, drift`

### IR-03 · Tracking & Occlusion Rig
- 覆盖：`S01, S02, S03, S04, S05`
- 实现基座：Movie Clip tracking + Camera/Object Solver + Follow Track + depth geometry/mattes
- 主要控制：`clip, track_name, use_3d_position, surface_proxy, occluder, handoff_influence`

### IR-04 · Spatial Typography Rig
- 覆盖：`G01, G02, G03, G04, G06, G07`
- 实现基座：Text/planes + Grease Pencil + Build + masks + stagger controls
- 主要控制：`char_delay, build_factor, mask_progress, world_anchor, divider, annotation_hold`

### IR-05 · Morph & Deform Rig
- 覆盖：`G05, R07, D01, D02`
- 实现基座：Shape Keys + Lattice/Displace + Geometry Nodes
- 主要控制：`shape_value, evaluation_time, deform_strength, falloff`

### IR-06 · Transition Choreography Rig
- 覆盖：`R01, R02, R03, R04, R05, R06`
- 实现基座：Geometry occlusion + camera path + DOF + light/compositor; editorial match when appropriate
- 主要控制：`transition_window, occluder_path, match_vector, camera_path, focus_curve, light_curve`

### IR-07 · Material & Optical Rig
- 覆盖：`I01, I02, I03, I04, I05, I06, I07`
- 实现基座：Principled materials + lights + render motion blur + compositor
- 主要控制：`roughness, ior, transmission, light_energy, shutter, grain, distortion, glow`

### IR-08 · Simulation Rig
- 覆盖：`D03, D04, D05, D06, D07, D08, P03`
- 实现基座：Soft/Rigid/Cloth + Geometry Nodes Simulation Zone + particles/volumes
- 主要控制：`mass, damping, collision, timestep, seed, cache, bake`

### IR-09 · Procedural Response Rig
- 覆盖：`P01, P02, P04, P06`
- 实现基座：Geometry Proximity + fields + Random Value + Sample Sound Frequencies + drivers
- 主要控制：`distance, falloff, seed, frequency_band, smoothing, response_range`

### IR-10 · Modular Motion System
- 覆盖：`P05, T04, T05, T06, G06`
- 实现基座：Collections + custom-property master controls + drivers/actions/NLA + component offsets
- 主要控制：`state, progress, component_delay, component_scale, motion_role, override`

### IR-11 · Editorial Time Rig
- 覆盖：`T08, T09, E01, E02, E03, E04, E05`
- 实现基座：VSE/compositor/planes when spatial; otherwise prefer FFmpeg timeline
- 主要控制：`source_range, speed_curve, crop_rect, freeze_hold, replay_count, time_offset, split_state`

## 当前项目使用规则

- Router 仍然先看当前真实 Keyframe 和视觉问题，用当前项目素材核对机制是否需要；
- 如果需要动态/空间机制，再从 Motion ID 路由到 IR；
- IR 规格用于选定实现方式，最终效果在当前项目 Mockup 和 Proof 中验证；
- 进入当前项目 Implementation Lock 时，将实现元素和可解析参数路径写入当前工程。
## IR-12 · Caption Slot & Adaptive Protection

- 覆盖：`L01 槽位选择, L02 自适应保护, L03 明暗切换, L04 锚点吸附`（v2.1 新增的屏幕文字落位 ID）
- 实现基座：Pillow + numpy 静帧工具；cue sheet 驱动；字体 / 颜色 / 字号由项目方案传入，工具不带内置风格
- 主要控制：`slot, slots_allowed, anchor, protection_cap, floor_exempt, style`
- 可选工具：`scripts/caption_place.py`，输入当前项目的 cue sheet 与帧图。
- Blender / FFmpeg 复刻：按同参数实现并单独 Proof；本版未验证像素一致性
