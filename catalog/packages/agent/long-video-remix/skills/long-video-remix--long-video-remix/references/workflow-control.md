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
