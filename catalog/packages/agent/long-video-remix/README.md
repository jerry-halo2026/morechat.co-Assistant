# Long Video Remix — AI视频剪辑与长视频混剪专家

从几小时长片里找片段、出方案、做混剪：把本该反复重看的高成本多模态信息压成可复用、可回查的结构化数据与文档，再用工程化设计保证每一段画面的动态都被真正读懂；两次创意决策（讲什么 / 怎么讲）始终留给人。

## 核心特色

**一次结构化成数据，之后不必再重看原片。**

| 特色 | 说明 |
|---|---|
| **多模态 → 结构化数据与文档** | 画面、动作、对白、说话人、上下文、情绪、反证被压成逐抽样帧观察表、动作节点候选、结构化问答、scene / overview 与 Content Map，保留来源时间，可检索、可排序、可回查。 |
| **重复读取成本只付一次** | 检索、改稿、复盘、跨模型交接复用同一层数据；只有叙事主线命中的区域才回原片做定向高密度核验，而不是每次都重新理解整段素材。 |
| **工程化保证"真的看懂了"** | 证据与源版本 / `time_mapping` 绑定，Direct 2 机器授权，Edit Boundary / 对白保护，时间轴统一量化，分层缓存，导出实测与审计——每个判断能回原片，每个接点能实测。 |
| **创意决策留给人** | Direct 出现在流程里两次：先定 Narrative Direction，证据补齐后再定 Editorial Execution Plan；Execute 只落实已确认决定，不替人发明主线。 |
| **视觉方法有据可依** | Direct 2 从 14 个视觉方法与 9 个兜底配方中选定可制作方案，写清参数与失败信号；Blender 出工程、proof 与动态 demo，FFmpeg 回接成片。 |

## 类型

Agent 型（单个 AI 专家）

## 功能

- **Structure（结构化数据与文档）**：全时段 Broad Structure 输出正式的文字化 Structured Observation Layer（逐抽样帧观察表、动作节点候选、结构化问答）+ Content Map；主线确认后做 Detail Structure 定向高密度核验，只压回命中区域，字幕 / signals 优先，ASR 只查关键歧义。
- **Direct 接口**：为编导准备两次决策的输入与证据包——Narrative Direction（讲什么）与 Editorial Execution Plan（怎么讲）；Direct 2 给出选段计划与边界包络，跨模型 / 跨会话交接后由 Execute Step 0 在包络内精校。
- **Visual Methods（视觉方法生成）**：Direct 2 通过 Visual Router 按需加载方法库（M01–M14，兜底 F01–F09），把叙事作用、视觉重点、处理依据、参数与失败情形写成可确认的制作方法；已有想法时校正深化，只有抽象形容词或无法落地时才主动提候选。
- **Execute**：Step 0 精校入选片段及 handles → 授权 → 时间轴编译、转场 / 音轨 / 文字轨、`render-manifest.json`、分层渲染、导出实测（帧数 / 时长 / 近静音 / 全接点对照图）与 QA 交接。
- **Blender 合成**：固定 2D 适配器生成图层、父子组、曲线与末尾状态，输出原生 `.blend` 工程；实际渲染后交连续 Dynamic Demo、readback、receipt、静态 proof 与待填 review，再由 FFmpeg 回接既有 clean-video / mix 流程。
- **Visual Direction（视觉方向方法）**：Direct 2 先读 Visual Direction Atlas、Scene × Text Grammar、Timing Grammar，判断注意力顺序、文字角色、空间关系、字体语气、motion relation 与强调预算，再落 Art Direction 与 M01–M14 / F01–F09 制作方法；`visual-methods.json` 记录全局 `direction_read`、方法级 `direction_strategy` 与逐镜头 `direction_use`。
- **Sound（声音）**：执行计划写明声音策略并落在 `project.json.workflow_control.audio_choice`（模式 + 实际处理 + 确认来源），覆盖 preserve / isolate / attenuate / replace / remove / designed silence 与 gain / fade / duck / mix / normalize。
- **工程脚本**：`validate_project.py`、`timeline_math.py`、`compile_render_manifest.py`、`execution_integrity.py`、`prepare_execution_authorization.py`、`check_render_authorization.py`、`audit_render.py`、`extract_frames.py`、`detail_gates.py`、`workflow_control.py`（关口续接）、`visual_pipeline.py`（视觉方法）、`render_blender_composition.py` / `blender_composite_worker.py`（合成）、`finish_ffmpeg.py`（回接成片），需 Python 3.10+；渲染审计另需 FFmpeg，合成另需 Blender，接点拼图另需 Pillow。

## 本版要点（v1.5.0-public-methodology）

**技能 v1.5.0 · 公开方法论版：方向先行、实现可锁、第三方参考库剥离**

- **视觉知识与第三方素材解耦**：移除个人自用的第三方视觉参考图库、参考 ID、来源队列与专属路由 / 校验工具，把可公开复用的知识独立成 `visual-direction-atlas.md`、`scene-text-grammar.md`、`timing-grammar.md`、`visual-design-methodology.md`；方法库只保留通用方法，不引用任何第三方作品。
- **方向先行**：D2 顺序固定为 内容与关系 beat → 画面事实 → 初步视觉方向 → 候选叙事逻辑 → Art Direction → 静态样稿 → 动态验证 → 实现锁定，不从字体和配色起手。
- **A/B 只证明变化，不证明更好**：新增 `scripts/check_visual_ab.py`，校验源帧文件身份、文案 ID 集合、画布与解码像素；像素相同只能记 `no_visible_change`，不同也不自动等于视觉提升。
- **实现锁定可追溯**：Implementation Lock 的 `reference_trace` 改为 `design_trace`，逐方法绑定当前 Mockup、真实 `target_element_ids`、可解析 `parameter_paths` 与 `proof_checks`；只写方法说明不落到真实元素与参数不算完成。
- **Proof 与生产锁收敛**：只在最小充分代表性集合上做 Proof，其余 composition 需 `proof_covered_by` 与理由；Production Proof Lock 冻结工具链后一次性生产，等价实现不能替换已锁定的 renderer。
- **沿用不变**：Broad / Direct 1 / Detail / Direct 2 / Execute / QA 主线、handoff 与 Scope Lock、执行授权、对白保护、Blender 组合与 FFmpeg 回接、导出实测与 DesignFidelity 全部保留。

**公开版资产边界**：发行包只含自制的两张流程 PNG、`assets/icon.svg` 与 `examples/synthetic-ready/` 下三张自制 SVG；不内置第三方图片、视频、音频、字体与案例来源。

## 历史版本要点（v1.3.1 及更早）

**技能 v1.3.1 · Visual Methods 方案生成 / 兜底与轻量交互**

- **视觉方案正式由 Visual Methods 承担**：Direct 2 用 Style System + Visual Router 生成或校正制作方法——已有明确想法时深化，只有抽象形容词、常见默认处理、真实画面无法落地或用户要求更强视觉时，才主动提出可制作候选、推荐理由、工具可执行性与失败信号。
- **瘦加载，不瘦知识**：默认只读 Router，命中后再取完整方法；方法库 M01–M14 与兜底配方 F01–F09 作为完整参考保留在包内。
- **方法选择只发生在 Direct 2**：Broad 不选方法，Direct 1 只定语气，Detail 提供真实画面条件；不新增阶段、Gate 或独立 QA，检查点映射到现有 Demo Review 与最终 QA。
- **方法 ID 与知识库分离**：项目实际方法写 `PM001...`，知识库通过可选 `library_refs` / `fallback_refs` 引用，避免 ID 冲突；旧项目 method ID 保持兼容。
- **交互收敛为两个确认束**：D2 Design Lock 与 Production Proof Lock；内部关口仍各自保存 digest / stale 状态，确认束不扩大用户授权。

**前序里程碑（v1.3.0 / v1.2.5 / v1.2.4）**

- **v1.3.0 制作方法与 Blender 工程**：新项目 schema 1.9，叙事作用 / 视觉重点 / 处理依据 / 参数与失败情形形成可确认方法；新增固定 2D Blender 适配器与原生 `.blend` 工程路径；method / composition 关口接入构建、授权草稿、正式编译与 FFmpeg 回接，参数、源范围、工程或资源一变旧验证即失效。导出成功不自动通过审美、用户确认或最终 QA。
- **v1.2.5 阶段内关口与 Chat 续接**：统一 `workflow_control` 状态存进原 `project.json`；同一项目续接先恢复有效 / 待确认 / 失效关口，变动只重开受影响记录；跨大块推进须过对应出口，partial handoff 保留全部未过关口。
- **v1.2.4 门槛与兼容性加固**：D2 选段快照 `d2_selection_snapshot` 限定 Execute Step 0 的校准包络；Visual Proof 必须由 `capability-map.json` 中 `output_mapping` 实际指向当前 proof 的可用能力生成；schema 1.7 恢复原严格度、1.8+ 才允许保守部分边界；畸形 schema 版本直接报错。

**展示信息（本版未改）**

- 名称「AI视频剪辑与长视频混剪专家」（AI Video Editing & Long-Video Remix Expert）；标签 视频剪辑 / 长视频转短视频 / 视频混剪。
- 推荐问法按使用场景组织的三条（首条同时作为首次对话引导语）：
  1. **直播切片（长素材二次利用）**：一场直播，能剪出哪些值得单独发的短视频？提取高光片段，制作直播切片并标注原片时间码。
  2. **影视综艺混剪（情绪与故事感）**：影视综艺CP混剪，怎样把好磕的瞬间剪成一段故事？找到关键对白、眼神和互动，串起情绪变化。
  3. **小红书／抖音短视频（开场与实际效果）**：小红书、抖音短视频，前三秒怎么让人想看下去？用素材设计开头钩子、字幕和配乐，先看画面样稿。

**已知限制**

- 视觉交付、音乐审美与混音几乎没有自动化检查：成片与样稿的风格匹配、音乐观感、分离听感与最终混音仍须人工试听 / 审阅；尚未在真实长视频上做 benchmark。
- Blender 合成需要本机可用的 Blender 与真实渲染能力；缺失时按 capability 规则记为待补，不生成替代证据。
- 真实 Multica 权限、网络、第三方安装与模型权重许可须在实际运行环境中确认。
- 此前 v1.0.3–v1.2.5 的证据绑定、执行授权、源范围约束、完整音轨核听、抽帧时间实测、两次 Direct、入选边界核验与阶段关口全部保留。

## 使用示例

**① 直播切片：突出长素材的二次利用**

- 一场直播，能剪出哪些值得单独发的短视频？提取高光片段，制作直播切片并标注原片时间码。

**② 影视综艺混剪：突出情绪与故事感**

- 影视综艺CP混剪，怎样把好磕的瞬间剪成一段故事？找到关键对白、眼神和互动，串起情绪变化。

**③ 小红书／抖音短视频：突出开场和实际效果**

- 小红书、抖音短视频，前三秒怎么让人想看下去？用素材设计开头钩子、字幕和配乐，先看画面样稿。

## 头像

头像不随本内容仓分发（`avatars/` 已移除），由产品端生成（grok 引擎）。

## 安装 / Installation

本包由 **morechat.co-Assistant** 内容仓分发，**通过 morechat.co-Assistant 目录导入**：

1. 在 morechat.co-Assistant 仓中取出 `catalog/packages/<kind>/<id>/`；
2. 该目录即包根目录，内含 `plugin.json`、`agents/`、`skills/`，整体作为包目录导入；
3. 导入后由平台注册 Agent / Squad 与技能，无需额外安装脚本或注册命令；
4. 头像不在仓内分发（`avatars/` 已移除），由产品端生成。
# 1. 校验（必须 0 error）
python3 scripts/validate_expert.py <expert-dir>
# 2. 注册到本地市场
python3 scripts/build-catalog.mjs <expert-dir>
# 3. 打包成上传包（zip 内第一层为 long-video-remix/）
python3 scripts/build-catalog.mjs <expert-dir> <output-dir>
```

得到 `long-video-remix.zip` 后在 Multica 开放平台提交：

1. 完成实名认证，完善开发者主页（头像 / 20~120 字简介 / 联系方式）；
2. 选择资产类型 **Expert（专家）**，填写名称与分类；
3. 上传 `long-video-remix.zip`，填写版本说明 `v1.5.0` + 本版功能与已知限制（公开方法论版：视觉知识独立为 Visual Direction Atlas / Scene × Text Grammar / Timing Grammar / Visual Design Methodology，方法库保留 M01–M14 与兜底 F01–F09；D2 方向先行，`visual-methods.json` 记录 `direction_read` / `direction_strategy` / `direction_use`；新增 `check_visual_ab.py`，像素相同只算 `no_visible_change`；Implementation Lock 用 `design_trace` 绑定真实元素、参数与 Proof 检查点；Proof 只做最小充分集合，Production Proof Lock 冻结工具链。移除第三方视觉参考图库、参考 ID、来源队列与专属工具，包内只保留自制流程 PNG、`assets/icon.svg` 与 `examples/synthetic-ready/` 三张自制 SVG。已知限制：Blender 与真实渲染能力须在实际环境确认，视觉审美 / 混音仍须人工审阅，尚未做真实长视频 benchmark；商用注意字体与音乐授权）；
4. 提交审核 —— 平台走「安全扫描 + AI 审核 + 人工抽检」三道关卡；
5. 通过后发布，可在数据看板查看用量。

> 提审前请确认：`description` 触发条件明确、包内无 `__pycache__` / `.git` 等缓存、依赖声明完整、无未说明的网络请求、头像 512×512 且 ≤500KB。
> 完整步骤见工作目录中的《开放平台发布步骤.md》。
