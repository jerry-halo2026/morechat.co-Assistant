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
