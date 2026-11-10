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
