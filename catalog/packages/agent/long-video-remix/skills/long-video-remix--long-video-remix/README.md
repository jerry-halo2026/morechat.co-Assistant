# Long Video Remix — AI Video Editing Skill for Claude Code & Codex

**中文** | [English](README.en.md)

**公开方法版 · v1.5.1-public-methodology-clean。** 包含可复用的剪辑与视觉制作方法、模板和检查器。

Direct 2 使用当前项目素材校准视觉方向。新风格需做代表性同源 A/B。视觉方法见 [Visual Reference Router](references/visual-reference-router.md)。

**AI video editing Agent Skill for long video → shorts, highlights and remix edits.** 把长视频先变成可检索、可回查的结构化素材层，再通过两轮 human-in-the-loop Direct 确定“讲什么 / 怎么讲”，最后用 Visual Methods、Blender motion composition、FFmpeg rendering 与 QA 把确认后的方案做成可复现、可审计的成片执行。

`Claude Code · Codex · AI video editing · Long video to shorts · Video highlights · Blender · FFmpeg · Human-in-the-loop · Bilingual`

**它和“一键 AI 剪辑”的区别：** 不要求模型一次黑箱看完整部长视频并直接出成片。Broad 负责低成本建立 searchable video index，Detail 只深挖真正命中的区域；Direct 1 / Direct 2 保留人的创意判断，Execute 再把已确认结果落实为真实视觉制作、时间轴、渲染与最终播放 QA。

**视觉制作。** Direct 2 用 Style System 和 Visual Router 选择 M01–M14 方法及 F01–F09 备选方案。确认后用可编辑 Blender 合成、连续 Dynamic Demo 和 Executable Proof 验证实现，再经 FFmpeg 回接和最终 QA。详见 [视觉制作](references/visual-production.md)。

| 你最容易遇到的问题 | Long Video Remix 怎么处理 |
|---|---|
| **长视频每次都要重新看、重新理解** | Broad Structure 建立 searchable video index、Content Map 和源时间回查路径 |
| **创意和素材证据经常混在一起** | Direct 1 先定叙事方向，Detail 再定向核实，Direct 2 最后锁定执行方案 |
| **Detail / ASR 越做越重** | 最小充分证据后 STOP；字幕 + waveform / signals 优先，只在关键歧义点局部精听 / ASR |
| **Mockup 很漂亮，真正执行却变样** | Mockup 确认后生成 Implementation Lock；V7 锁定的视觉方案必须落到具体元素与参数，Proof 与 Execute 只能复现该锁 |
| **跨模型、跨会话以后决定容易漂** | source refs、boundary、D2 snapshot、authorization 与 render manifest 保留可机器检查的连续性 |

**核心产出：** `Content Map` · structured observations · Detail evidence · real keyframes · Direct 2 execution plan · implementation lock · executable visual proof · verified edit ranges · render manifest · QA / audit records

适合需要反复使用长视频素材、持续讨论创意、制作不同内容版本的 **MCN、编导、内容编辑、AI 视频工作流开发者**。

目标是减少反复理解原始多模态素材的开销，而不是承诺“零成本自动剪辑”。抽帧、局部 ASR、定向回看与 GPU 渲染仍需资源，具体成本取决于素材、模型和工具。

请仅使用你有权使用的素材。

当前版本说明、实测结果与安装方式见 [QA](QA.md) · [安装与更新](INSTALL.md)。

## AI Video Editing Use Cases / 适用场景

Long Video Remix 面向需要**长素材理解 + 人工创意判断 + 可执行视觉制作**的工作流，典型入口包括：

- **Long video to shorts / short-form video editing**：从长节目、活动、课程或直播中制作短视频；
- **Video highlights / highlight extraction**：访谈高光、赛事 / 活动重点、人物反应与剧情兑现；
- **Drama / variety-show remix editing**：剧情、综艺、CP / 关系观察、跨场景主题混剪；
- **Livestream clipping**：直播长素材的结构化检索、候选定位与切片；
- **AI-assisted montage editing**：由人 / Director 决定叙事，AI 负责结构化、核证、执行与 QA；
- **Blender motion composition**：对入选片段做可编辑的 2D 动态合成、连续 Demo 与 Proof；
- **FFmpeg video editing / rendering**：把确认后的视觉、音轨和字幕回接完整成片并审计；
- **Searchable video analysis**：把长视频转换为可复用的结构化数据层，用于检索、研究和内容效果分析。

## 快速开始

本地首次安装时，选择对应工具的一行命令；已有安装目录时见 [安装与更新](INSTALL.md)。

解压 ZIP，按 [安装与更新](INSTALL.md) 放置完整目录。

1. 安装完整文件夹，复制 `assets/project-template.json` 建立独立项目，登记源与可用模型 / 视频工具。
2. 完成 Broad 的正式观察层和 Content Map；只做结构化时可在此交付，后续剪辑可复用。
3. 人 / Director 定主线，Detail 核实命中区域并交付真实关键帧与独立 handoff，再由 Direct 2 确认 Execution Package（计划 + 制作 reference）与 planned ranges；回到实际执行环境后先做 Execute Step 0 精校入选边界，再按最终 ranges 准备 / 确认机器授权。
4. 执行静态校验与编译，渲染适配器在消费清单前检查授权：

```sh
python3 scripts/validate_project.py PROJECT
python3 scripts/compile_render_manifest.py PROJECT
python3 scripts/check_render_authorization.py PROJECT PROJECT/render-manifest.json
```

既有 FFmpeg / MCP 渲染器继续负责普通剪辑、clean-video 与 mix。随包提供 Blender 局部合成和 FFmpeg 回接入口，按 [视觉制作](references/visual-production.md) 交付工程、动态 demo 与实际 review；证据、授权、编译和导出审计继续沿用原入口。

本地原片抽帧优先用 `scripts/extract_frames.py`；MCP / 代理等按 [MCP 适配](references/mcp-adapter.md) 保留实测时间与源绑定。脚本的 `signals` 模式标出画面变化与有声区间，`strip` 模式输出逐帧条用于定切点。E 阶段的取证、切点与问题闭环见 [Detail 证据获取](references/detail-evidence.md)。

先用 `workflow_control.py init/status` 建立或查看关口。采用视觉制作时，按 V0–V7 完成设计和确认，项目方法用 `PM001…` 登记。

## 常用提问示例

把〔……〕替换成你的素材、主线或文件，按当前任务选用。

### 1. 还没有选题，先做 Broad Structure

**可以怎么问：**

> 请对〔视频素材〕做 Broad Structure，覆盖整段素材，建立可回查的结构化记录。交付逐抽样帧观察表、场景与动作索引、问题与未验证项、全片概览和 Content Map，注明已处理范围与缺口。本轮完成后停在 Broad 阶段。

**会拿到什么：** Broad 素材包，包括基础观察表、全片概览、Content Map 和覆盖记录；每条记录保留源素材与时间定位。

### 2. Broad 已完成，这批素材可以讲什么？

**可以怎么问：**

> 请基于〔Broad 素材包〕，提出少量有明显区别的创作方向。每个方向说明核心表达、叙事主线、对应素材区域、当前依据，以及需要 Detail 核实的问题，供我选择。

**会拿到什么：** 候选方向与第一轮 Direct 的主线草案。方向可由人或独立 AI Director 提出，讨论确认后用于定向精查。

### 3. 主线已确认，具体精查哪里？

**可以怎么问：**

> 已确认的主线是〔主线〕，必须保留的表达是〔重点〕。请从〔Broad 素材包〕中定位需要做 Detail Structure 的区间，逐项列出源视频、时间范围、选择原因、必要前后文和待核问题。本轮先交付精查任务单。

**会拿到什么：** 可直接交给精查环节的区间清单，每个区间说明为什么看、要核实什么；精确切点留到 Detail 核实。

### 4. 区间已选好，请完成 Detail 并交接

**可以怎么问：**

> 请按〔已确认主线〕和〔精查任务单〕回到原片做 Detail Structure。先用已有字幕原话和 waveform / signals 定位，只对会改变叙事判断的原话、speaker 或字幕冲突做局部精听 / ASR；不要等待整段 ASR。交付最小充分证据、可供 D2 选择的保守 edit boundary（未做最终精校可标 partial）、真实关键帧和独立 handoff。

**会拿到什么：** Detail 证据包，包括精查区间、深度观察、必要说话人核验、selection-ready 边界、真实关键帧和交接文件。未入选候选不需要先做最终帧级声音精修。

### 5. Detail 已完成，请做 Direct 2 和视觉确认

**可以怎么问：**

> 请读取〔Detail handoff〕和真实关键帧，先形成 Direct 2 的最终叙事与执行计划；视觉部分按 Visual Reference v2.3.6 的 V0→V7 执行：V0/V1 明确输入与可测问题，V2 登记如何依据当前项目证据校准方向，V3 形成带 Art Direction 的候选，V4 出少量 Mockup，V5 做证据化 review 后停下来让我选择；把这次真实选择直接记录为 V6，不要另加一次审批，随后用 V7 锁定参数与 reference trace。再把 V7 映射进 Implementation Lock；如果当前环境具备最终 Execute 会继续使用的 renderer / layout 工具，用同一工具链重建 Executable Proof，并把 actual_tool、entrypoint、字体 / 资源和关键参数写进 execution-reference。若当前环境不能完成 proof，状态保持 awaiting_proof 并完整交接，不要用下游不可用的工具代替。

**会拿到什么：** 已确认的 Execution Plan、V0–V7 视觉设计记录、V6 确认的全部 Mockup、V7→Implementation Lock 映射；条件允许时还包括由最终执行工具链真实生成的 proof 和可复现入口。

### 6. Execution Package 已确认，请渲染并做 QA

**可以怎么问：**

> 请按〔Execution Package〕执行，不重新选择主线、素材或视觉风格。先做 Execute Step 0：只打开 D2 已选片段及 handles，用连续音画精校最终 in/out、句尾、停顿、尾音 / 反应和必要 J/L-cut；ASR 仅在局部确有需要时使用。逐段输出“D2 planned range → Step 0 verified range → delta / reason”对照；任何结果超出 `d2_selection_snapshot` 允许范围时立即停止并等确认，不自行扩张选段。全部在范围内且 selected boundary 已升为 supported 后，才准备 / 确认授权、编译 timeline / render manifest、渲染并做 QA。

**会拿到什么：** 可执行时间轴 / render manifest、成片（环境支持时）、技术审计与实际观看 QA 记录。

## 工作路径

| 环节 | 产出与决定 |
|---|---|
| Broad Structure → Structured Observation Layer → Content Map | 全局观察表、场景 / 动作 / 问题索引，保留覆盖与缺口 |
| Direct 1 · Narrative Direction | 人 / Director 确定主线、候选区域和待核问题 |
| Detail Structure + Edit Boundary | 最小充分证据后 STOP；字幕 / signals 优先，候选可交 partial 保守边界；证据不足返回 Direct 1 |
| Direct 2 · Execution Package | 锁定选段、planned range / boundary ref 与允许校准范围；mockup→proof 关闭 Visual Gate |
| Execute → Render / QA | Step 0 先精校入选 range 并把 boundary 升为 supported，再确认授权、制作与 QA |

**阶段命名统一：** 本版正式名称只使用 `Broad Structure → Direct 1 → Detail Structure → Direct 2 → Execute`。历史文档中的 Board、Deep、Directed Deep、Detailed Structure 都是旧称，不代表额外阶段。

## 丰富结构如何可靠进入执行

固定信息地板保留事实、派生解释与 unknowns；source-time 标签使每个判断能回原片；增量落盘和恢复减少重复扫描。执行完整性机制将采用的 evidence、boundary、review 和独立源音轨绑定当前素材版本，并对照 Direct 2 检查实际范围与顺序。

未就绪草稿只能显式用 `--planning` 编译为不可渲染清单。声音连续性检查保护对白与尾音，J/L-cut 或创作截尾必须有具体已确认依据。运行结果继续区分技术通过与最终听看验收。

工程字段见 [执行完整性契约](references/execution-integrity.md)。

<details>
<summary><strong>完整方法、Structure 表单、Direct 职责与工程说明</strong></summary>

## 为什么 Structure 值得单独做

视频、图片、字幕 / 原声、人物、动作、场景与上下文原本都是高成本的多模态信息。Structure 会把这些信息压成可检索、可排序、可回查的表格和文本层，例如 `frame-observations.csv`、scene / overview 与 `content-map.md`。后续的人、Director 或其他 Skill 可以优先消费这些紧凑数据，而不是每次重新加载原视频、九宫格和大量图片。

这带来一个很直接的变化：

| 过去 | Structure 之后 |
|---|---|
| 一条视频一条视频重新分析 | 把多条视频变成统一的结构化数据层 |
| 想看某个时间点，还要重新打开视频 | 直接定位到时间码对应的人物、动作、对白、背景和内容说明 |
| 不同任务要重复读取同一批多模态素材 | 剪辑、内容研究、效果复盘、检索可以复用同一套结构化结果 |
| 大量上下文消耗在“重新看一遍” | 高成本多模态读取集中到真正需要深挖的区域 |

## Execute 为什么同样是核心

Structure 解决“素材怎么看得清、怎么复用”，但最终要做成视频，还需要把已经确认的创意方案变成**保留证据与保护范围、可以渲染和核查**的时间轴。

Detail Structure 负责核实 verified units、必要前后文、`context_ranges` / `protected_ranges`，并给出足以供 D2 选段的 edit boundary；未入选候选可以保持 partial。Execute **不重做叙事选择**，但先用 Step 0 把 D2 真正采用的边界精校为 supported，然后负责：

- 仅对 D2 已选片段 + handles 精听 / 精看，按需定向 ASR，校准最终音画 in/out；
- 把 Direct 2 已确认的顺序与 verified cut 编译为 assembly timeline 与 output timeline；
- 落实 hard cut / xfade、音轨、文字轨和章节卡；
- 生成 `render-manifest.json` 并按授权入口执行渲染；
- 导出后做完整解码、帧数 / 时长检查、近静音扫描、全部接点对照图、Reference Compliance 与最终 QA。

因此，这个仓库不是“先结构化，后面交给你自己想办法剪”。**Structure 和 Execute 是两端的稳定能力，Direct 是两次需要人参与的创意决策点：先定主线，再定最终执行方案。**

## 一个最直观的例子：从“分析视频”到“分析内容”

假设你有 500 条已经发布的短视频，同时拿到了播放曲线、停留、跳出或互动数据。

过去通常只能先得到：

> 视频 A 在 12 秒留存上升；视频 B 在 8 秒开始流失；视频 C 完播率较高。

但真正想知道的是：**用户在那个时间点到底看到了什么。**

Structure 之后，每一个已分析时间点都可以对应到结构化内容：人物、动作、表情 / 视线、空间关系、对白、屏幕文字、场景背景和叙事功能。于是用户行为数据可以直接挂到内容节点上：

| 时间点 | 结构化内容 | 内容类型 | 用户表现 |
|---|---|---|---|
| 00:08 | 两人争执，其中一人转身离开 | 冲突 / 动作变化 | 留存上升 |
| 00:12 | 近景反应，无对白 | 人物反应 | 重播增加 |
| 00:19 | 长段解释性对白 | 信息说明 | 流失增加 |
| 00:27 | 前面埋下的信息得到兑现 | 情节兑现 | 留存再次上升 |

这时分析对象就不再只是“哪条视频表现好”，而可以进一步问：

- 哪一类画面更容易产生停留？
- 哪种人物动作经常对应重播？
- 用户流失前通常出现的是长对白、静态画面，还是信息密度下降？
- “冲突 → 反应 → 兑现”这样的结构在不同视频中表现是否稳定？
- 能不能直接找出所有“人物沉默 + 近景反应”的片段，再比较它们的表现？

**Structure 的价值，就是把视频从难以计算和组合的多模态对象，转换成可以检索、筛选、连接、比较和再次创作的数据层。**

同一套结构化结果，不只服务于剪辑，也可以继续用于内容复盘、用户行为分析、跨视频比较、研究、检索和其他 AI 工作流。

## 适用场景

这套方法适合任何“素材很长、需要反复理解和再利用”的视频工作：剧情 / 综艺 / 访谈 / 纪录片 / 课程 / 活动录像，以及已经发布内容的效果复盘。

它尤其适合以下情况：

- 素材多到无法靠一次摘要可靠理解；
- 同一批视频会被反复用于剪辑、研究、检索或分析；
- 创意方向需要人参与，而不是交给黑箱一次生成；
- 只有少量候选片段值得投入高密度多模态观察；
- 最终还需要把内容判断落实成稳定的时间轴、转场、音轨和 QA。

## 为什么是两轮 Structure

一次把整部长视频扫到帧级既昂贵，也容易在创意方向尚未确定时浪费计算。这里采用两轮不同目标的 Structure：

- **第一轮 Broad Structure：覆盖优先。** 用较低密度看完整素材，并把结果压成可复用的结构化工作层；
- **第二轮 Detail Structure：完整度优先。** 脚本方向确认后，只回到命中的区域补高密度画面、原声、前后语境和反证。

因此，真正昂贵的多模态观察集中在少量高价值区域；而创意讨论、检索和跨视频分析可以尽量基于已经结构化的数据进行。

## Structure 是可复用的工作层

这层结构化数据并不是为了替代原始证据，而是为了让后续工作不必每次从原视频重新开始。它可以被人和其他模型快速浏览、过滤、排序、搜索和引用。

它主要解决三个问题：

- **减少重复多模态读取**：后续 Direct 不需要为了每次创意讨论都重新把原视频、九宫格或大量图片塞进上下文；
- **降低创意阶段的上下文负担**：人工、Director 或其他 Skill 可以直接在 `frame-observations.csv`、scene / overview 和 `content-map.md` 上做组合与判断；
- **把高成本计算集中到命中区域**：只有确认脚本涉及的段落才回到原片进入 Detail Structure，高密度读取画面、原声和前后语境。

这不是把原始证据丢掉。所有结构化记录仍保留 `frame_id`、`scene_id`、时间码、evidence refs 等回查路径，需要时可以重新落回原素材。

## Structure 能做什么

Broad Structure 允许在还没有明确选题时启动。典型产物包括：

- 源素材与版本登记；
- 全时段画面抽样与字幕 / 转写覆盖；
- **Frame Observation Index**：每个已分析抽样帧一行，保留帧号 / 时间 / 帧尾 ms、画面事实、动作 / 状态、情绪线索、空间 / 背景、意象标签、硬字幕、**原声要点与核听状态**、内容说明、与前帧变化、**topic judgment、confidence / evidence basis**、interpretations 与 unknowns；
- **Action Node Candidates**：对动作、视线、站位、物件交接等变化候选建立默认 4fps 的局部加密窗口，并保留候选起止、最小有效单元、口型 / 说话线索和关系转折；
- **Structure Q&A**：把会影响理解的问题、回答、证据、未验证项与下一步核查结构化保存；
- scene 级事件结构；
- 可回查的对白、人物、地点和动作证据；
- source-order overview；
- 跨场景的 Content Map；
- 关系变化、重复线索、关键物件、无声互动等导航；
- coverage 与 unknowns，明确哪些地方只是抽样、哪些已经连续音画核实。

Structure 的目标不是“总结剧情”，而是把原本难以浏览的长视频变成一个**人和模型都能重新检索、组合和回查的素材空间**。

因此 Broad Structure 的正式交付不是“九宫格 + 一个总结”，也不是只交一个 Content Map，而是一套**文字化、结构化、可检索、可回查的工作数据包**：

1. **Raw evidence**：抽样单帧、九宫格、字幕 / ASR、原始定位；
2. **Structured Observation Layer（核心交付）**：`frames.jsonl` + 人可读的 `frame-observations.csv`、`action-node-candidates.csv`、`structure-questions.csv`，以及 scene / segment 级观察与 `overview.md`；
3. **Creative navigation layer**：在上述正式表单之上形成 `content-map.md`、情绪 / 关系线索与可用边界，供第一次 Director 在不重新加载原视频的情况下确定 Narrative Direction。

这里的逐帧指 **each analyzed / sampled frame**，不是声称对 25/30fps 的每一个视频帧都做了语义分析。

`deliverable=content_map` 时，可以在这一阶段正式结束，不必进入剪辑。

### Structure 的最低信息地板

Structure 输出不能退化成“几句总结 + 一个 Content Map”。基础观察层是后续创意、分析和 Execute 的共同底座：

- 每个已分析 sampled frame 必须保留一行结构化记录；
- `visual_facts`、动作 / 状态、`motif_tags`、硬字幕 / 可见文字、`change_from_previous`、`content_description`、`unknowns` 必须显式填写；没有内容也写 `none` / `unknown` / `not_applicable`；
- 动作变化候选必须进入独立的 action-node 表并带 4fps 局部窗口或明确例外原因；
- 会影响理解的问题必须进入 Q&A 表，保留证据和未验证项；
- overview、Content Map、最终文案或剪辑建议只能建立在这些基础记录之上，不能替代它们。

这条约束的目的，是保证 Structure 真正成为可复用的数据层，而不是每次任务结束后只留下一个无法下钻的总结。

## Direct 为什么分两次

Direct 默认由外部完成，而且通常适合在一个**独立的研究 / 编导工作区**里完成。它不是一次性把“选题、证据核实、最终剪辑方案”全混在一起，而是分别出现在两轮 Structure 的两侧。

### Direct 1：Narrative Direction — “到底讲什么？”

第一次 Director 消费的是 Broad Structure 的正式文字化结构数据：逐抽样帧 / 分片段观察、动作节点、Q&A、scene / overview、Content Map、情绪 / 关系线索、可用素材边界，以及必要的外部研究。它的任务是抽选：

- 核心命题 / 观看关系；
- Narrative Spine；
- candidate regions / scenes；
- 希望 Detail Structure 回答的问题；
- 已确认的人工判断与禁改项。

这一步**不要求精确切点，也不应把结构化线索提前写成已验证事实**。可使用 `assets/narrative-direction-template.md`，也可以直接接入已有研究 / 编导文档。

### Direct 2：Execution Package — “这些材料最终怎么讲？”

Detail Structure 完成后，Director 第二次接收的是完整证据包：deep observations、原声 / 硬字幕核验、说话人裁决、context / counterevidence、verified units、protected ranges 与 evidence gaps。此时才形成最终执行包，其中 Editorial Execution Plan 包括：

- 最终选择 / 排除哪些 verified units；
- 顺序和每段叙事功能；
- 必须完整保留的对白 / 动作 / 反应；
- 声音、文字、转场、节奏与时长分配；
- 可替换范围和不得改变的核心表达。

同时交付 `execution-reference.md`：实际文字样式 / 位置 / 停留、画面处理、声音 / 转场、资源与 QA 判据；通常一两个样本即可锁定全片风格，不要求每个镜头 / 字幕逐项对应。Detail 的 handoff 已直接携带这套输出要求，换模型无需依赖安装环境。详见 [完整交付契约](references/execution-package.md)。 每个大阶段完成时还必须重新生成项目级 `handoff.md`，其中带当前 Scope Lock、Gate 状态、下一步、实际文件 manifest + SHA-256 与源媒体跨机器重绑定信息；前向跨块前 handoff 必须是当前版本。可使用 `assets/execution-plan-template.md` 和 `assets/execution-reference-template.md`。`assets/editorial-plan-template.md` 保留为兼容旧项目的合并式模板。Execute 默认只落实这个第二次 Director 已确认的方案；**最终素材取舍属于 Direct 2，不属于 Execute。** 如果核心 evidence 仍是 `pending / contradicted`，或两次 Direct 尚未确认，时间轴不能标为 `ready_for_render`。

## Detail Structure 为什么单独存在

第一次 Content Map 不应该为了某个主题把所有区域都扫描到帧级；那会非常昂贵，也会让 Structure 变成提前押题。

有了第一次 Direct 的 Narrative Direction 后，系统才知道应该在哪些区域增加信息密度。第二轮先把**当前目标问题所需的最小完整语境**看清，再做选段判断；它不要求把所有候选声音都做成最终逐字稿或帧级切点。典型动作包括：

- 从十秒级概览抽样提高到一秒一至两张或连续播放；动作 / 视线 / 站位等关键变化节点继续使用默认 4fps 局部窗口加密观察；
- 先建立 **Detail Interval Card**：写清为什么进入精查、前情、当前背景、后续、目标问题和主题关联；
- 对选中的核心区域建立 **Deep Observation Index**，记录完整画面描述：人物、站位 / 朝向、动作链、关键视觉变化、可观察情绪线索 / 谨慎情绪解释、表情 / 视线、人物间距离、关键物件、意象标签、景别 / 构图；
- 补充**内容描述**：这一小段实际发生了什么，而不是只抄关键词或台词；
- 补充**场景背景与叙事背景**：地点 / 时间 / 环境、前一事件、为什么会来到这一刻；
- 从字幕关键词回到**足以裁决目标问题的必要原声窗口**；字幕 + waveform / signals 先定位，只对关键原话、speaker / addressee、重叠说话或字幕冲突做局部核听 / ASR。区分硬字幕 / ASR / 真实原声；有歧义时用 **Speaker Adjudication** 做口型 / 原声 / 字幕 / ASR 裁决；
- 从单个场景扩到前后十五至三十秒，必要时继续扩到完整事件，记录 before_state / after_state；
- facts、interpretations、unknowns 分开，保留 `question_refs` / 未验证项，并检查 Narrative Direction 的反证、缺口、错误因果和时空关系；
- 最后才把已充分理解的核心区域收敛为 unit、context_ranges、protected_ranges 和可执行剪辑判断。

如果证据与 Narrative Direction 冲突，工具应报告问题并返回 Direct 1 调整；如果证据成立，则把 Detail Structure 的完整证据包交回 Director，形成第二次 Direct 的 Execution Package（Editorial Execution Plan + 制作 reference），再进入 Execute。

## Execute 能做什么

进入 Execute 时，创意方向已经确定，相关素材也经过第二轮定向深挖。后续工作包括：

- 形成可执行 edit plan；
- 建立 assembly timeline 与 output timeline；
- 处理 hard cut / xfade、音轨、文字轨、章节卡；
- 使用 `protected_ranges` 防止剪掉必要语义和动作；
- source event 按累计时长统一量化到目标 fps，validator 与 compiler 共用同一套 output 坐标计算，避免逐段四舍五入累积漂移；
- `source.time_mapping` 进入精确缓存身份，映射变化会使相关视频 / 音频 / final 缓存失效；
- 编译 `render-manifest.json`；
- 分层缓存视频、音频和文字产物；
- 导出后完整解码、核对帧数和展示时长；
- 扫描近静音；
- 自动生成全部接点对照图；
- 区分技术检查、动态听看和最终成片验收。

当前仓库提供时间轴编译与导出审计脚本，但**不绑定唯一渲染器**。你可以把 `render-manifest.json` 交给 FFmpeg、视频 MCP、剪辑软件适配器或自己的渲染流程。

## 主要文件

```text
long-video-remix/
├── README.md / README.en.md
├── INSTALL.md / INSTALL.en.md
├── LICENSE
├── SHA256SUMS
├── PROJECT_INSTRUCTIONS.txt
├── CHAT_PROJECT_REFERENCE.md
├── SKILL.md
├── agents/
│   └── openai.yaml
├── assets/
│   ├── capability-map-template.json
│   ├── composition-plan-template.json
│   ├── delivery-spec-template.json
│   ├── visual-methods-template.json
│   ├── execution-plan-template.md
│   ├── execution-reference-template.md
│   ├── execution-handoff-template.md
│   ├── project-template.json
│   ├── timeline-template.json
│   └── …其余 Structure / Detail 模板与工作流图
├── references/
│   ├── workflow.md
│   ├── workflow-control.md
│   ├── visual-production.md
│   ├── style-system.md
│   ├── visual-methods/
│   │   ├── index.md
│   │   ├── method-library.md
│   │   ├── fallback-recipes.md
│   │   ├── application.md
│   │   ├── resources.md
│   │   └── research-extension.md
│   ├── detail-evidence.md
│   ├── data-contracts.md
│   ├── execution-integrity.md
│   ├── execution-package.md
│   ├── montage-rules.md
│   ├── render-engineering.md
│   ├── qa-handoff.md
│   ├── regression-checklist.md
│   ├── structure-regression-matrix.md
│   ├── mcp-adapter.md
├── scripts/
│   ├── workflow_control.py
│   ├── visual_pipeline.py
│   ├── blender_composite_worker.py
│   ├── render_blender_composition.py
│   ├── finish_ffmpeg.py
│   ├── versioning.py
│   ├── extract_frames.py
│   ├── validate_project.py
│   ├── detail_gates.py
│   ├── compile_render_manifest.py
│   ├── timeline_math.py
│   ├── execution_integrity.py
│   ├── prepare_execution_authorization.py
│   ├── check_render_authorization.py
│   └── audit_render.py
├── examples/synthetic-ready/
├── examples/synthetic-ready/
├── tests/
│   └── …其余 Detail / Execute / audio / checksum 回归测试
├── visual-reference/
└── QA.md
```

## 最小使用方式

### 只做 Structure

1. 复制 `assets/project-template.json` 为项目目录中的 `project.json`；
2. 登记 sources 和实际可用工具；
3. 完成 Broad Structure，并同时保留 `frames.jsonl` 与人可读的 `frame-observations.csv`（可复制 `assets/frame-observation-template.csv`）；动作变化候选进入 `action-node-candidates.csv`（默认 4fps 局部窗口），结构化问题 / 回答 / 未验证项进入 `structure-questions.csv`；
4. 在逐抽样帧观察之上形成 scene / `overview.md` / `content-map.md`，可参考 `assets/content-map-template.md`；
5. 将 `project.deliverable` 设为 `content_map` 即可在这里交付。

### 做完整 Remix

1. 先完成 Broad Structure，交付正式的 Structured Observation Layer + Content Map；
2. 由人 / Director 基于这些文字化结构数据和必要外部研究形成 Narrative Direction（Narrative Spine + candidate regions + verification questions）；
3. 把 Narrative Direction 接回项目，对命中区域进行 Detail Structure，并生成 `deep-observations.csv`，把核心区域的画面、内容、背景、前后状态、原声证据、反证和保护范围补全；
4. 交付真实关键帧、证据与独立 handoff（含下游完整输出要求），交回 Director 形成 Execution Package；
5. Execute 先做 Step 0：只回看 D2 已选片段 + handles，精校最终音画边界并把入选 boundary 升为 `supported`；随后按已确认计划 + 制作 reference 编译 edit plan / timeline，按冻结样式制作；
6. Step 0 后按 [执行完整性契约](references/execution-integrity.md) 用最终 ranges 保存证据绑定并准备 / 确认机器授权，再运行：

```text
python3 scripts/validate_project.py 项目目录
python3 scripts/compile_render_manifest.py 项目目录
python3 scripts/check_render_authorization.py 项目目录 项目目录/render-manifest.json
```

7. 使用实际渲染器生成视频后运行：

```text
python3 scripts/audit_render.py 成片.mp4 项目目录/render-manifest.json --outdir 核查目录 --contacts
```

## 边界

- 抽帧负责发现，不等于连续观看；
- 字幕 / ASR 负责检索，不等于核听原声；
- Broad Structure 的正式表单是文字化结构数据，Content Map 建立在其上，不能反向替代表单；
- Direct 1 的 Narrative Direction 是编导意图，不等于已经得到素材证明；
- Detail Structure 负责把 Narrative Direction 重新压回原片证据；
- Direct 2 基于核实后的证据与关键帧形成完整 Execution Package；Execute 不默认跨过这一步自行决定最终讲法或风格；
- 工具可以建议某个节点的素材不足或替代片段，但默认不擅自改写已经确认的核心表达；
- 渲染成功日志不等于成片通过验收。

## 当前状态

这套仓库更接近一个 **AI-native long-video analysis + remix execution framework**，而不是自动生成短视频的一键工具。

它最适合放在“内容理解”和“实际剪辑工程”之间：先把长素材变得看得见，再把人的创意可靠地做出来。

## License

本项目由权利人授权的代码及配套文档按 [MIT 许可](LICENSE) 使用，保留原版权和许可声明。处理或分发项目中使用的第三方素材时，按素材自身的授权范围办理。

</details>
