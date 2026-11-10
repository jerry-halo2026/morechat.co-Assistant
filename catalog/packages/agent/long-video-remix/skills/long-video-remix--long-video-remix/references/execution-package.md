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
