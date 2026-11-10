# 本地执行观察记录（paper.local-observation.v2）

本模板定义专家可用的本地执行摘要记录。目的是让一次任务的实际执行情况成为用户可带走、可按需分享的本地文件，而不是散落在对话里的自述。配套确定性脚本为 `../scripts/local_observation.py`（仅标准库），负责校验、规范化与写入。v2 取代 v1：文件名升级为 `paper.local-observation.v2-<observation_id>.json`，v1 原件保留、不会被新脚本改写或按 v2 解释。

## 填写原则（先于字段）

1. **只据本次实际执行证据填写**。模型自述、计划、预期都不算执行证据；没有实际观察到的字段保持 `null` 或 `unknown`，并列入 `unobserved_fields`，**不得补 0**。
2. **记录留在本地，默认不上传**。本脚本没有任何网络入口；是否分享、分享什么由用户另行决定。它与可选的结构化策略请求、经单独同意的反馈是三件分开的事。
3. **不是轻任务的前置，也不是要用户填的表单**。简单问答、单句修改等轻任务直接完成，不要求先建记录；记录由专家在有实际执行证据时自行生成。
4. **新文件专名、不覆盖原件**。文件名固定为 `paper.local-observation.v2-<observation_id>.json`，脚本以排他创建写入，同名文件已存在即拒绝，绝不覆盖用户原件或已有记录（包括 v1 记录）。
5. **平台记录与可携带交付物是不同范围**。平台自身的会话/工作区记录由宿主管理；本记录是用户可带走的交付物。不宣称宿主所有写入都只在交付目录；用户明确禁止额外写入时，专家不主动向边界外写摘要。

## 字段合同

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `schema` | 常量 | 固定 `paper.local-observation.v2` |
| `observation_id` | UUID | 本次记录 ID，同时构成文件名 |
| `package_version` | 常量 | 必须等于当前包版本（见脚本 `PACKAGE_VERSION`） |
| `task_kind` | 枚举 | `research` / `revision` / `recovery` / `material_review` / `light_task` / `other` |
| `run_category` | 枚举 | 运行类别：`unknown` / `synthetic` / `user_task`，默认 `unknown`。这是本地声明，不是可信用户身份、独立采纳证明或经营数据 |
| `timing_scope` | 枚举 | 计时口径：`unknown` / `observed_interval` / `task_total`，默认 `unknown`。这是记录的声明，不构成独立认证；详见下方计时规则 |
| `phases` | 枚举数组 | 实际经过的本地阶段，按执行顺序、不重复：`intake`、`evidence_review`、`external_research`、`extraction`、`judgment`、`drafting`、`revision`、`verification`、`delivery`、`recovery` |
| `started_at_utc` / `ended_at_utc` | 整数秒或 null | UTC 起止；结束不早于开始；未观测为 null |
| `elapsed_ms` | 非负整数或 null | 与 `timing_scope` 对应的耗时（毫秒），上限 24 小时 |
| `first_value_ms` | 非负整数或 null | 首个可用成果耗时；不大于 `elapsed_ms`；仅 `task_total` 可填 |
| `counts.tools_used` | 非负整数或 null | 实际工具**调用次数**（不是工具种类数）；只有存在完整可核对的调用记录时才填，否则 null；不得为填数字扫描其他会话或私有日志 |
| `counts.sources_read` | 非负整数或 null | 实际读取的研究证据来源数；方法说明与脚本不计入；未观测保持 null |
| `counts.claims_checked` | 非负整数或 null | 承重主张核验数；只有存在对应可回查的核验项依据时才填，否则 null |
| `strategy.client` | 枚举 | 本次策略客户端协议版本：`unknown` / `none` / `v1` / `v2` |
| `strategy.result` | 枚举 | `selected` / `skipped` / `no_match` / `needs_selection` / `native_short_path` / `native_fallback` / `capability_limited` / `local_only` / `not_used` / `unknown` |
| `strategy.catalog_revision` | 正整数或 null | 实际响应绑定的目录修订号（≤ 2,147,483,647） |
| `strategy.strategy_id` / `strategy.strategy_version` | 安全标识 / 正整数或 null | 实际选定方法模板 ID（小写 kebab-case，≤ 64 字符）与版本（≤ 1,000,000） |
| `strategy.track_id` / `strategy.track_version` | 安全标识 / 正整数或 null | v2 选定赛道的实际 ID 与版本；v1 无赛道，必须为 null |
| `deliverable_readback` | 枚举 | 成果实际读回状态：`read_back_verified` / `generated_not_read_back` / `not_generated` / `unknown` |
| `failure_categories` | 枚举数组 | 实际失败类别，可为空：`transport_failure`、`invalid_response`、`decision_expired`、`timeout`、`budget_exhausted`、`capability_limited`、`permission_denied`、`parse_failure`、`user_stop`、`other` |
| `feedback.consent` / `feedback.sent` | 布尔 | 反馈同意与是否已发送；`sent=true` 必须有 `consent=true`，未同意不得标记发送 |
| `unobserved_fields` | 枚举数组 | 所有保持 null / unknown 的字段名；与字段取值必须一一对应 |

### 计时口径规则（v2 核心）

- **`unknown`（默认）**：计时未测量，四个计时字段必须全部保持 null，不得填任何数值。
- **`observed_interval`**：只记录实际测得的中途区间，可填 `started_at_utc`/`ended_at_utc`/`elapsed_ms`；`first_value_ms` 必须保持 null。中途区间**不得**被当作完整任务耗时或首个可用成果耗时，也不得作为反馈合同的整体任务/首值耗时上传。
- **`task_total`**：仅当存在真正完整的宿主事件起止，或用户明确提供/核对的起止证据时才可选择；此时 `first_value_ms` 可填且不大于 `elapsed_ms`。不得凭中途采样、文件事后检查时间或自我估计代填任务总耗时。
- 该范围是记录的声明，不构成独立认证；缺测量或只有中途区间不妨碍继续研究，保持未知即可。

### 计数口径规则（v2 核心）

- 计数是“截至记录生成检查点已经完成、且有依据的观察”，不宣称包含之后尚未发生的调用。
- 工具调用次数、工具种类数、输入文件数、研究证据来源数是不同口径，不可互换、不可互相改名。
- 本地观察中的来源/工具计数不能直接改名为反馈合同的预算执行 `reads`/`queries`；分母或同批次依据不明确时保持未知。
- 简单任务不为填指标强制制造台账；没有依据就留空（null）。

### 策略结果与绑定规则

- **未测量是 `unknown`，不是“确定没用”**：`strategy.client` 与 `strategy.result` 的默认状态是 `unknown`/`unknown`，且 `strategy.result=unknown` 必须列入 `unobserved_fields`；只有用户明确没有使用策略时才记 `none`/`not_used`。`client=unknown` 时结果只能是 `unknown`；`none` 只配 `not_used`；`v1`/`v2` 不允许 `not_used`。
- **已知协议 + 未确认结果合法**：实际调用了 v1/v2 但未确认返回结果时记 `client=v1|v2`、`result=unknown`，并正确列入 `unobserved_fields`；这不等于“不知道用了哪个协议”，也不允许附带任何绑定。
- **`selected` 必须有实际绑定**：`catalog_revision`、`strategy_id`、`strategy_version` 三者必填；v2 选定赛道时 `track_id`、`track_version` 必填；v1 无赛道，赛道字段必须为 null。绑定值只能来自本次实际响应。
- **非 selected 可保留已知目录版本**：`no_match`/`needs_selection`/`skipped`/`native_fallback` 的真实响应仍带有 `catalog_revision`，已实测的目录版本可以保存；方法与赛道字段仍为 null，不制造选择。无实际回执的回退保持目录为 null。`not_used`/`unknown`/`local_only`/`native_short_path`/`capability_limited` 没有服务回执，绑定字段全部保持 null。绝不虚构绑定，也不为补记录重新请求。
- **未观测列表可派生**：`build_record` 未提供 `unobserved_fields` 时，从实际为 null/unknown 的字段确定性生成；显式传入列表时继续严格双向校验。绝不填零或猜测执行。

## 明确不接收的内容

记录不接收：标题、主题、正文、文件全文或片段、绝对私人路径、账号或用户标识、URL、原始查询、Cookie/Token/凭据、完整对话。脚本在任意深度拒绝这些键；所有字符串取值只能是闭合枚举或严格格式，私密文本无处落脚。额外未知键同样被拒绝。

## 一致性规则

- 未观测 ⇔ 列入 `unobserved_fields`，两个方向都强制；有值却被列为未观测、或 null 却未列出，都拒绝。`strategy.result=unknown` 同样按此校验。
- 时间与计数必须为非负整数（布尔、浮点、字符串均拒绝）；绑定版本为有界正整数，绑定 ID 只接受小写 kebab-case 安全标识；重复键、非有限数、版本不符拒绝。
- 序列化是确定性的：同一记录永远得到同一字节序列与同一 SHA-256，便于回读核对。

## 使用方式

```bash
# 校验一份待写记录（只读，不写入）
python local_observation.py validate --record-json 待校验.json

# 校验并排他写入（已存在即拒绝，退出码非零并给出 error 代码）
python local_observation.py write --record-json 待写入.json --output-dir 记录目录/
```

程序化使用时调用 `build_record(...)` 组装并校验，或 `write_record(record, dir)` 直接写入。失败时抛出带稳定代码的 `Error`，不会静默降级。
