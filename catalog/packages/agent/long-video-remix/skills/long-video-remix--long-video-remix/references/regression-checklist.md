# Core Capability Regression Checklist

每次更新 README、定位、schema 或脚本后，都用此表确认已验证能力没有被包装层覆盖或删除。

## 主线不可变

`Broad Structure → Structured Observation Layer → Content Map / emotional cues → Direct 1 Narrative Direction → Detail Structure → Direct 2 Editorial Execution Plan → Execute → Timeline / Render / QA`

除非版本明确声明 breaking change，否则不得删除、跳过或把任一步默认为由另一层替代。

## 全流程时间标签稳定性

- Structure 的 canonical tag 始终是 `source_id + source_ms / range`；display timecode、抽样号、ASR 时间和代理时间不是主键。
- source 明确 `time_mapping`；代理 / 分轨 / 字幕均能映射回源时间。
- frame observation 与 `frames.jsonl` 同一 frame_id 的 source/time 一致。
- Deep observation 位于对应 Detail interval 内；speaker adjudication 与 utterance 源时间有重叠。
- Execute 使用 assembly / output frame，但保留 source time；track 用 event anchor + local frame 或明确 output coordinate。
- 源版本 / time mapping 变化时精确下游缓存与坐标失效。

## Broad Structure 最低信息地板

- `frames.jsonl` 保留可追溯 sampled-frame 证据。
- `frame-observations.csv` 每个已分析 sampled frame 一行，并与 `frames.jsonl` 的 `frame_id` 集合一致。
- 基础字段显式存在：帧号 / 时间 / 帧尾 ms、画面事实、动作 / 状态、意象标签、硬字幕 / 可见文字、原声要点及核听状态、与前帧变化、内容描述、topic_judgment、confidence / confidence_basis、unknowns。
- 表情 / 视线、空间、背景、情绪线索保留，不把情绪解释写成事实。
- `action-node-candidates.csv` 保留动作 / 视线 / 站位 / 物件变化候选；默认 4fps 局部窗口，偏离需记录原因；同时保留候选起止、最小有效单元候选、口型 / 说话线索与关系转折。
- `structure-questions.csv` 保留问题、回答、状态、证据、未验证项和下一步核查。
- Broad 的正式出口首先是上述文字化结构表单与 scene / segment observations；overview / Content Map / 情绪大意 / 最终文案不得替代以上基础记录。
- negative fact 不由稀疏抽样推出；方言 / 强口音 ASR 未核听只作 locator。
- 每个 source 有 usable ranges / downstream constraints；影响后续时长设计的物理边界已传给 Direct。
- 长任务支持增量落盘、coverage accounting 与断点续跑，不因静默中断重扫已完成区间。

## Detail Structure

- 核心区间重新回原素材，不只复用第一轮摘要。
- `detail-intervals.csv` 先保留进入精查原因、前情、当前背景、后续、目标问题和主题关联。
- `deep-observations.csv` 保留完整画面、构图、动作链、关键变化、情绪线索 / 谨慎解释、空间、场景背景、叙事背景、意象、内容描述、硬字幕、原声及核听状态、字幕 / ASR 冲突、before / after、topic_judgment、confidence / confidence_basis、说话人裁决引用、问题引用、反证和未验证项。
- `speaker-adjudications.csv` 保留说话人 / 对象的帧级裁决；无歧义时也保留表头。
- 先理解必要完整语境，再形成 unit / context_ranges / protected_ranges；目标问题 + 最小完整单元 + boundary + 反证四项闭合后 STOP DETAIL，不做保险性重复读取。
- Detail 必须继续形成正式 `edit-boundaries.csv`：真实音频尾部、动作 / 反应收束、preferred in/out、safe windows、must-keep ranges、handles、cut risk；字幕 / ASR 结束不能替代可剪边界。
- 证据冲突时先判断层级：主线级冲突返回 Direct 1；Detail 证据成立后必须交回 Direct 2 形成最终 execution plan，不由 Execute 偷改已确认主线。

## 两次 Direct

- Direct 1 明确输出 Narrative Direction：核心命题 / Narrative Spine / candidate regions / verification questions / constraints；不要求精确切点。用四行 Scope Lock 承接当前阶段、可修改、不可修改、已否决，不另建历史状态文件。
- Detail Structure 只围绕 Direct 1 已确认主线补证据；计划目标不能倒推 facts。
- Direct 2 在 Detail evidence package 完成后输出 Editorial Execution Plan：selected verified units、顺序、段落功能、保护范围、声音 / 文字 / 时长 / 转场意图、执行边界；采用视觉设计时完成 Aesthetic Mockup → 同一最终执行工具链的 Executable Proof。两步可跨模型 / 会话，但 proof_confirmed 前不得 Execute。
- Execute 不得从 Detail Structure 直接跳过 Direct 2 自行生成最终讲法；Visual Gate 已关闭时沿用 proof 对应的 capability-map / renderer 入口，不重新看 mockup 自由设计。

## Execute

- verified units、context_ranges、protected_ranges 保留。
- duration budget ledger 保留；event frames − transition overlaps 与预计 output frames 一致。
- audio track 保留 narrative_role / treatment_reason。
- 反馈分类 → invalidation / 回退范围规则保留。
- assembly timeline 与 output timeline 双坐标保留。
- transitions、audio_tracks、text_tracks、render-manifest 保留。
- render audit、近静音扫描、全接点图、动态听看与 handoff 保留。

## 发布前机械检查

1. JSON / CSV / YAML 可解析；Python 脚本可编译。
2. README / SKILL / workflow / data-contracts 对同一能力表述一致。
3. `scripts/validate_project.py` 对 Structure 最低信息地板与 Execute 静态引用进行检查。
4. 对照上一正式 Release 做文件级 diff；未列入版本目标的核心脚本 / 规则如有变化，必须单独解释。
5. 不得以“更简洁”“更吸引人”为理由删除已确认的数据字段或执行步骤。

## 实现层机械回归

- 4fps 只作为动作候选加密起点；不能单独证明某动作 / 台词 / 物件在整个区间“没有发生”。负面事实必须有明确 scope，并按视觉 / 原声事实类型使用连续 review 或直接反证。
- Broad 标记 complete 时，`frames.jsonl`、`frame-observations.csv`、`scenes.jsonl`、`coverage.json`、`overview.md`、Content Map 必须真实存在且基础表非空；动作候选 / Q&A 可以是带表头空表。
- `ready_for_render` 必须要求两次 Direct 均 `confirmed`、文档存在、Detail 完成、render_authorized=true；每个选中的 source event 必须显式列出本次实际采用的 `deep_observation_refs` 与 `edit_boundary_ref`，引用 observation 的 source / source-time 覆盖正确，且 evidence_status 为 supported / partial；schema 1.8+ 的入选 edit boundary 必须在 Execute Step 0 后为 `supported`，且最终 in/out 不得超出 `d2_selection_snapshot` 中 D2 固定的 safe windows / allowed adjustments；默认切点落在 safe windows 并覆盖 must-keep ranges；同 unit 未采用的 pending / contradicted observation 不得误伤本次执行。
- validator / compiler 共用累计量化与 overlap 后 output 坐标；文字 / 音频轨不得以 assembly 总长冒充 output 上界。
- 改变 `source.time_mapping` 必须改变相关 unit / clean / audio / final cache key；缓存可复用性按实际依赖分层判断，未知音频版本只关闭 mix_audio / final，不应误关已知版本的 clean-video。

## 可运行回归

运行 `python3 -m unittest discover -s tests -v`，检查证据版本、Direct 2 采用范围 / 顺序、源限制、独立对白、合法 J/L-cut / 截尾、无关或占位 override、规划清单与渲染入口。源内容改变不得只重写 source_signature；需要实际重新核实。Broad 覆盖统计、4fps 实际观察证明与说话人语义裁决仍按原规则人工 / 模型完成，本版本不声称全部已经机械实现。

## 对白与音轨核听回归

同一命令包含 tests/test_dialogue_continuity.py：漏报整句 / 第二句、漏保对白的旧版本和假核查、scene / action 下的静音、缺采用 ID 或 speech 元数据、音轨 review 缺失 / 过期 / 错误模态 / 1ms 缺口，均须被静态校验、正式编译及入口阻断。充分核听的 J/L-cut、有效删句例外、明确改变政策的静音及取段外未采用对白须保留合法对照；音轨独有 review 改动须使旧证据确认失效。

## 独立源音轨对白回归

tests/test_independent_audio_dialogue.py 覆盖卡片对白、同源额外音轨、异源仅音频，以及确认后独立 utterance / 专属 review 改动。截句、静音、过期 / 未核实证据、错误标签和无效例外须被静态校验、正式编译及入口阻断；完整声音、异步放置、跨卡片连续接句、有效 track 删句例外和已确认政策变化须保持正向对照。另一成片位置的完整播放不能掩盖本次截句；源音轨全取段核听继续独立要求。纯音乐 / 环境声整体收束沿用人工职责边界。

## 阶段交付与制作参考回归

- 原 schema / CSV 表头未变；字段无法取得时 status / reason / impact / downstream_handling 随包输出，可做工作继续，未核实项不冒充事实或渲染完成。
- E 固定提供真实关键帧清单与自包含 handoff；handoff 直接含下游 Execution Package 要求，不依赖同一 Skill 环境。
- D2 同时交付计划与制作 reference，文字 / 声音 / 转场 / 资产 / 约束 / QA 参数足够执行；少量样本锁定全片规则，不逐镜头或字幕映射。
- Execute 接收完整包，Reference Compliance 进入原 QA；声明 reference 改动后旧确认 / 渲染入口失效，旧项目与原对白 / 授权 / 时间轴 / 缓存回归继续通过。

## 抽帧与 Detail 问题闭环回归

- `extract_frames.py` 输出的每张图，画面内容必须对应其 `source_ms`（用逐帧亮度编码视频反查真实帧号，不能只比较标签）；可变帧率素材同样成立。
- 本地脚本拒绝非 identity / 非本地输入，其他环境按适配器核验实测时间；目录清理须有专用标识并只清理登记输出，项目 / 源目录及外来文件受保护；逐帧条过长时拒绝。
- `signals` 能在源时间上定位局部运动、硬切与有声时段（合成用例误差 ≤ 2 帧）。
- Detail 未完成时，已有 Detail 文件的表头、ID、范围、枚举、引用与切点顺序即被检查。
- Detail 完成时：目标问题为稳定 ID 且被观察回指；绑定区间的问题必须在该区间目标列表中；`unresolved` 有具体缺口与 next_check；`contradicted / unresolved` 列入 handoff Question Closure Ledger 且状态一致、处理具体。
- `ready_for_render`：按实际区间 / 观察关联判断入选节点；重复 ID、来源 / 区间 / 节点及 ledger 关联不一致不得放行；`unresolved` 阻止渲染，`contradicted` 须有对应节点的人工 `confirmed_by`。
- SKILL.md 与 workflow.md 遵守 `tests/test_size_budget.py` 的字节限制，detail-evidence.md 不超过 8KB。
- 问题闭环表的标题含 "Question Closure Ledger" 或“问题闭环”即被识别（可附中文说明）；找不到这样的标题时给出明确提示，其他表格中的同名问题行不能代替确认。
- 回归测试验证观察与区间节点、问题与关联区间的一致性。
- MCP 抽帧适配器探测须记录 `timestamp_method`；`computed` 的适配器不用于 Detail 事实与切点。

## 轻量 Visual Gate 回归

- 不新增 current-state / visual-style / music gate 文件；Scope Lock 只存在于现有 Direct / handoff 文档。
- `capability-map.json` 继续是工具能力来源；Detail handoff 摘录分析工具与最终 Execute 可访问的执行能力。
- schema 1.7 新项目必须显式包含三个 Visual Gate 字段；`visual_gate_status` 允许 not_started / mockup_confirmed / awaiting_proof / proof_confirmed / not_applicable；ready_for_render 只接受 proof_confirmed / not_applicable。
- proof_confirmed 时 selected mockup 与每个 executable Proof 必须路径不同且内容不相同；所有 Proof 与 `capability-map.json` 一起进入 `execution_reference_asset_refs`。`visual_proof_ref` 指首个兼容 Proof，多 Proof 时 `visual_proof_refs` 列全量；每个 Proof 都必须有 available capability 具备 actual_tool + entrypoint 且 output_mapping 指向该 Proof。任一 reference / toolchain 文件变化继续触发既有 asset 指纹失效。
- schema 1.6 旧项目没有 Visual Gate 字段时保持兼容行为；升级到 1.7 不要求重跑 Broad / Detail。


## 方法、合成与动态验收

- 方法须从叙事作用与真实原画选择；证据 ID、参数、失败情形、demo 验证点完整，不能只列效果名称。
- 缺 method 确认时实际 Blender 入口阻断；工程保存可重开，关键帧末态保持，父子图层不漂移。
- 动态 demo 覆盖接点两侧并保留相关声音；receipt 不自动生成 pass，实际 review 和当前版本确认缺一不可。
- `composition-plan.json` 含多个 Blender production window 时，Production Proof Lock 只要求 `proof_composition_ids` 的 scene / demo / proof / readback / receipt / review；不得因 composition 数量增加而逐段预渲染 demo。
- 非 proof composition 必须显式 `proof_covered_by` 指向 `proof_composition_ids` 中一个 Proof，并提供 `proof_coverage_reason`；无论是否声明 `proof_scope_policy` 都不能省略。机器必须拒绝 mode/renderer、Implementation Lock element、method 或 join 风险超出所指 Proof 的段。最终授权后才生成正式 scene / video / readback / receipt，不要求 demo / proof / review。
- `proof_composition_ids` 可以有 1 个或多个：同一实现族通常 1 个即可；出现第二种 materially distinct 实现族时追加第二个 Proof，而不是替换原 Proof 或强迫所有 composition 出 demo。
- Final `CompositionCompliance` 必须逐项覆盖 render-manifest 的每个 composition_id，记录 start_frame/end_frame 与 production video SHA-256，并把 `render-manifest.json` 和每个 composition video 列为 evidence。
- 修改资源、曲线、事件窗口或声音后旧工程 / review / 确认失效；未变独立工程保留。
- FFmpeg 仅替换声明的输出窗口；帧数、FPS、尺寸、完整解码及音轨验证通过，仍需原 QA 与新增三项后才 deliver_complete。
- 新 schema 删除 workflow_control 或 visual_pipeline 仍阻断；旧 1.8 项目保留原检查，显式 init 才采用新管线。
- 合成 fixture 和模拟确认只测工程与 Gate；不得当作用户同意或真实影片审美验收。

## Visual Methods 方案生成与轻量交互

- [ ] 仍只有原 A–G / 两次 Direct；Visual Methods 没有新增阶段、状态文件或 `VisualMethodsCompliance` Gate。
- [ ] Broad 只记录真实视觉条件，Direct 1 只给表达语气；M01–M14 的正式选择发生在 Direct 2。
- [ ] Visual Router 默认只做导航；命中方法后继续读取 method-library 的完整条目，不能把索引摘要当完整方法。
- [ ] 视觉方案仍只有抽象词、常见默认处理或无法适配真实关键帧时，会触发 Visual Methods 兜底并形成可制作候选 / 推荐 / 失败信号。
- [ ] 新模板 Project Method 使用 `PMxxx`，知识库 `M01–M14` / `F01–F09` 只出现在 refs；旧项目原 method ID 仍可通过。
- [ ] `library_refs` / `fallback_refs` / `candidate_treatments` 是 schema 1.0 的可选元数据，不改变 1.3.0 项目兼容性。
- [ ] 默认用户交互可收敛成 Design Lock 与 Production Proof Lock 两轮，但内部各 Gate 仍独立保存 digest 并在输入变化时 stale。
- [ ] Blender Composition、静态 Proof、Dynamic Demo、最终 FFmpeg 回接和真实 QA 没有因轻量化被删除或自动豁免。

## Reference Application / Implementation Lock 回归

- [ ] 视觉设计流程：V0–V2 未 PASS 时 `make_mockup` blocked；`reuse_confirmed` 单案必须绑定真实既有 V6/V7/confirmed-artifact，`simple_text` 单案可通过，`explore_new` 单案必须失败；`reuse_confirmed` 声明图文关系/动效语言/几何策略变化必须失败并要求回 `explore_new`；`representative_first` 只要求代表帧 V4，但 V7 扩展元素必须有真实 `validation_basis/adaptation`，difficult deferred 镜头还必须有实际成图 QA；V6/V7 未 PASS、`visual_stage_binding` 不匹配、`confirmed_mockups` 少/多/变 hash、或存在 V7 trace 却未桥接到 Implementation Lock 时，`method` / `build_composition` 必须 blocked。
- [ ] 当前 design fingerprint：只改 JSON 空白/备注不使后序设计失效；改真实设计输入必须 stale；源素材、Mockup、shown artifact、Proof/执行产物仍按原始内容 SHA 绑定。
- [ ] V5 默认 small-screen 必须；blur/squint `not_needed` + reason 可通过；blind-map 只有实际 independent review 时要求。
- [ ] `explore_new` 若 V2 没有选中 `status=measured` 的同条件 XR/MR，V5 缺失同素材/同文案/同画幅 `same_source_ab` 必须失败；A/B candidate 必须绑定当前 V4 的实际 artifact；即使文件 SHA 不同，只要解码后像素相同，也不得声明 `visible_change`。
- [ ] V7 任一 element rect 超出 canvas 或坐标顺序非法必须失败；long_text / multi_person / complex_background 等 difficult deferred 镜头缺 `expansion_checks`、真实 artifact 或视觉 QA 时必须失败。

- [ ] V2 全 `no_ref_needed` 时 V3/V7 trace 可为空，不能因“没有参考”被 V3/V7 无条件阻断。
- [ ] Mockup 与 Proof 同文件/同 SHA 默认 blocked；只有 `visual_proof_reuse.mode=reuse_engineered_mockup` 且绑定非空真实工程 evidence 时允许，Dynamic Demo / execution verification 仍不可跳过。
- [ ] 兼容参考路由：`visual_reference_status=used` 只记录 REF / hash / observation 但 `implementation-lock.json#reference_trace` 缺失时，仍必须 blocked。
- [ ] 每个 `(method_id, REF)` 必须映射到当前 Mockup、真实 `target_element_ids` 与可解析的 `parameter_paths`；断开的 parameter path 必须失败。
- [ ] `composition-plan.json` 必须绑定当前 `implementation_lock_ref` 与 `implementation_element_ids`；锁定 `blender_native_blend` 的元素不能被 `layers` 替代，反之亦然。
- [ ] Mockup / Proof / Composition 的确认记录必须绑定当前实际展示文件 hash；没有 `--shown-ref` 时不能用“渲染视频 / 继续”补签视觉 Gate。
- [ ] Proof review 的 ReferenceCompliance 必须绑定 selected REF IDs + Mockup / Proof / Implementation Lock hashes；Final QA 同样要求。重复渲染一致只能证明 reproducibility，不得单独作为 design fidelity 的 pass 依据。
- [ ] Production Lock digest 必须包含 Implementation Lock 与 Reference application chain；任何 renderer、元素参数、Mockup 或 REF trace 变化只重开受影响锁。
