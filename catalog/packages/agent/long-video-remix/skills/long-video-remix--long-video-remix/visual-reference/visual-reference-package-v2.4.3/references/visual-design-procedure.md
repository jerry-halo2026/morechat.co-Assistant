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

**先不要选字体。** 打开 `references/visual-direction-atlas.md`、`scene-text-grammar.md`、`timing-grammar.md`，完成 V3 的 `direction_read`：

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
