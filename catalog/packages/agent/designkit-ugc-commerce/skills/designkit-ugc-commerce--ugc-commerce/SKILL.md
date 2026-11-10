---
name: "ugc-commerce"
display_name: "口播视频"
display_name_en: "Talking-Head Video"
description: "根据产品或主题生成真人对镜口播的脚本、镜头和成片，聚焦一个清晰购买理由或信息点。适用于口播视频、产品口播、真人讲解、talking head、spokesperson video。美图设计室提供。当用户需要“口播视频”或描述中的等价能力时使用。"
description_zh: "根据产品或主题生成真人对镜口播的脚本、镜头和成片，聚焦一个清晰购买理由或信息点。适用于口播视频、产品口播、真人讲解、talking head、spokesperson video。美图设计室提供。"
description_en: "Create UGC-style presenter videos for product selling."
category: "视频创作"
version: "1.0.39"
author: "美图设计室"
---

# 口播视频

使用「美图设计室 AI设计 CLI」（终端命令名为 `designkit`）按“视频创作 / 口播视频”专家模板完成任务。morechat.co Connector 与用户本地安装都使用同一个 npm 包和登录状态。默认使用简体中文；用户明确指定其他语言时跟随用户。

## 本次任务执行顺序

- 先判断是新任务还是当前任务的交互回复、充值恢复、查询或下载请求。后者复用已保存的房间和事件上下文，不重问新任务输入、不重复建房；无可确认上下文时只询问目标任务。
- 新任务最小必填：商品图片 (`images`)。只问未提供项，使用用户原话映射合法选项，不把可选项或默认值当必填。
- 只需1至5张真实商品图片；出镜人、商品名称、卖点、平台和其他要求均可选。用户未给出镜人时省略presenter，不强迫上传人像或先创建模特；明确给出的出镜人按同包model_upload规则处理，不混作商品图。图片用--image-file上传；口播脚本、分镜和封面不是视频成片。
- 输入齐全后按内置Skill自动解析CLI、缺失时安装一次、未登录时发起带session_id的登录并远端复检；登录取消、超时或安装失败时说明具体阻塞，不宣称已生成。
- 只有create-room成功且返回room_id才提交chat。chat受理不明先查询同一房间，不直接重试收费提交；查询串行使用最新after_seq。遇交互等待用户，遇recharge_required先处理充值引导，不能用is_complete覆盖它。
- 先交付本轮正式产物，再判断next_action；需要本地产物时按内置Skill下载并核对结果，不把预览、空artifacts或files: []称为成功。终态无相应成品时如实说明，不无期限等待、不另建任务、不回退ImageGen或ImageEdit。

## 能力输入门禁

- 商品图片是必填输入，最多5张；出镜人可选，最多1位，不从商品图补充出镜人、商品名称、卖点或平台。不因缺少可选出镜人而阻塞口播任务；用户明确指定出镜人时不得静默省略。
- `model_upload` 是可选模特选择器，不是必填图片或任意文本字段；未指定时删掉对应 Prompt 整行，不补造模特、肤色、性别或 ID。
- 用户上传照片时按该字段绑定，检查 maxCount=1，以 `--image-file` 上传，Prompt 占位符只写“已上传附件”，不得写入本地路径。非必要不解析，必要解析结果不得用于补充其他参数。
- 选择官方模特或生成模特只能通过 DesignKit 实际返回的选择/交互完成；CLI 没有模特库查询或 model-id 参数，不得编造命令、接口、选择结果或把 ID 当图片路径。若当前通道不能指定用户要求的模特，如实说明并请用户上传照片或在正式任务中选择，不得静默忽略其明确要求。
- 不使用已移除的 `model_type`、`skin_tone`，不把新模特字段拼入“其他要求”。
- Do not call ImageGen, ImageEdit, or Defer(ImageGen).
- 图像、视频和PPT生成或编辑仅使用 DesignKit 连接器及已解析的 `<designkit>` CLI；不能完成时如实反馈，不回退 morechat.co 内置生成工具，不把连接器称为 MCP。


## CLI 入口解析

「美图设计室 AI设计 CLI」是当前产品/连接器名称；真正执行的终端命令名是 `designkit`，不存在名为 `designkit-buddy-cli` 的业务命令。首次执行前必须自动解析一次 CLI 入口，不要要求用户手动提供路径。

按当前平台查找 npm 暴露的命令：

1. macOS/Linux 执行 `command -v designkit`，Windows PowerShell 执行 `Get-Command designkit -ErrorAction SilentlyContinue`。
2. 对找到的绝对入口执行一次 `--version` 以确认入口可用，不解析或比较版本号。命令成功时记为 `<designkit>`；后文的 `<designkit>` 代表该绝对命令路径，不能执行字面占位符。
3. 不查找 Connector 私有目录或依赖生命周期临时注入的环境变量。Connector 和 Agent 统一使用 npm 命令及默认的 `~/.designkit` 登录状态。

在 morechat.co 中找不到 `designkit` 或 `--version` 无法正常执行时，不要停止任务。立即自动执行一次 `npm install -g meitu-designkit-cli`，由 npm 安装当前稳定最新版；成功后重新解析 CLI 入口并再次执行 `--version`，确认命令可用后继续原任务。安装命令只执行一次，不得添加 `sudo`、不得修改 npm registry，也不得安装带固定版本号的包。

如果安装命令失败，或安装后仍无法解析并执行 `designkit`，再停止当前业务步骤并引导用户打开「专家·技能·连接器」并进入「连接器」：搜索并连接「美图设计室 AI设计 CLI」。保留简短的原始安装错误摘要便于定位，不得循环安装，也不得改用内部 API。

## 能力边界

- 只执行“口播视频”对应的专家流程，不把本 Skill 当作任意美图设计室对话入口。
- 必须使用用户提供的真实素材和要求；不得用示例图、网络图、临时生成图或默认商品代替缺失素材。
- 不自行拼接内部 API、鉴权字段或专家 Skill 接口；所有业务执行都通过已解析并通过可用性检查的 `<designkit>` 入口。
- 创建任务前检查全部必填字段：只能复用用户已经明确提供的信息，缺失时必须停止创建并向用户追问。可选选择型字段未指定且存在 `auto` 选项时使用其可读 `label`“自动匹配”；其他未指定的可选字段直接省略，不自行推断、不主动追问。
- `补充要求`不是任务摘要或模型建议区。只有用户在核心任务之外明确提出附加约束时才可填写，并且每项内容都必须能对应到用户原话；用户只提出核心动作或上传素材时，必须删除整行，不能补成“清晰、专业、吸睛、便于使用”等推测内容。
- 选择型字段只能使用 `references/form.json` 中列出的选项。对话与提交给 CLI 的 Prompt 均使用可读的 `label`；`key` 只用于定位和校验选项，不得写入 Prompt。


## 标准输入引导

- 允许用户先用自然语言描述需求，不要求用户预先记住字段名或 Prompt 模板。先读取 [references/form.json](references/form.json)，把用户已经提供的信息映射到对应字段，信息已足够时不要重复追问。
- 缺少必填字段时，只询问当前缺失项，并提供一份可复制的“字段标签：填写内容”模板；文件字段写成“请上传：字段标签”，选择型字段只展示可读的 `label` 选项，不向用户暴露内部 `key`。
- 可选选择型字段未指定时，若 `form.json` 的合法选项中存在 `key=auto`，就在 Prompt 中写入该选项的可读 `label`“自动匹配”；不存在 `auto` 的选择型字段以及未指定的文本、数字、文件等其他可选字段直接省略。用户使用某种语言对话、附件呈现出的视觉特征、文件名或任务类型都不能视为用户指定了语言、风格、篇幅、比例等可选字段。只有用户主动询问“可以配置什么”“有哪些选项”等配置能力时，才按“输入契约”列出必填项、可选项及其可读选项。
- `补充要求`（包括常见的 `key=extra`）只允许承载用户在核心任务之外主动表达的附加约束，内容必须能逐项对应到用户原话；不得根据附件名称、文件内容、任务类型、使用场景、能力描述、默认偏好，或“清晰、专业、吸睛、便于使用”等通用质量目标自行总结、改写或补充。用户仅输入核心动作或上传素材时，必须省略该字段并删除 Prompt 中的整行；无法指出对应用户原话时也必须省略。例如，用户只说“用这张图做封面”并附图时不携带补充要求；只有用户明确说“保留 Logo，不改正文”时，才可填写对应内容。
- 非完成用户明确任务、附件上传、大小处理、格式转换及完整性校验所必需，不得读取或解析用户附件。确有必要时可以读取、渲染或转换附件，但解析结果只能用于文件处理或正式任务执行，不得用于推测、补充或改写任何任务参数；语言、风格、受众、场景、篇幅及补充要求等参数，只能来自用户在消息输入框中主动表达的文字。

- 用户补齐必填项后，只把本次实际提交的字段按“输入契约”顺序整理成简短确认清单。用户未提出异议即可继续，不要求用户再次抄写模板；不得虚构缺失的素材、文案或选择。
- 最终提交给 CLI 的内容必须严格按“Prompt 渲染”规则生成。字段 `key` 只用于匹配模板占位符；选择型字段把合法选项的可读 `label` 写入 Prompt，不得写入内部选项 `key`。

## 输入契约

执行前读取 [references/form.json](references/form.json)，它是字段、默认值、选项和 Prompt 模板的机器可读事实源。

| key | 用户标签 | 类型 | 必填 | 接口默认值（不自动使用） | 约束与选项 |
|---|---|---|---|---|---|
| `images` | 商品图片 | `file_upload` | 是 | - | 文件类型：image<br>最大数量：5<br>提示：产品图；非任务执行、上传、大小处理、格式转换或完整性校验所必需，不解析附件；必要解析结果不得用于推测、补充或改写其他参数。 |
| `presenter` | 出镜人 | `model_upload` | 否 | - | 最大数量：1<br>提示：选择官方模特、上传照片或生成一位（可选）；非任务执行、上传、大小处理、格式转换或完整性校验所必需，不解析附件；必要解析结果不得用于推测、补充或改写其他参数。 |
| `product_name` | 商品名称 | `text` | 否 | - | 占位说明：产品名 |
| `selling_points` | 核心卖点 | `text` | 否 | - | 占位说明：口播重点强调的卖点 |
| `platform` | 目标平台 | `select` | 否 | - | 选项：抖音 (`抖音`)；TikTok (`TikTok`)；快手 (`快手`)；小红书 (`小红书`) |
| `extra` | 其他要求 | `textarea` | 否 | - | 最大长度：500<br>提示：仅填写用户明确提出的附加约束；未明确提出时留空，不得根据素材、文件名或任务类型推断。<br>占位说明：口播风格、目标人群 |

## Prompt 渲染

主 Prompt 模板如下，仅以其中的固定文本和字段顺序为基准；必填项按规则补齐，可选项按下述 `auto` 与省略规则处理：

```text
[口播视频]制作UGC口播带货视频。
商品图片：{images}
出镜人：{presenter}
商品名称：{product_name}
核心卖点：{selling_points}
目标平台：{platform}
其他要求：{extra}
```

按以下规则渲染：

1. `form.fields[].key` 与模板中的 `{key}` 一一对应。必填字段必须使用用户明确提供的值完成替换；仍然缺失时停止提交并追问，不能猜测或残留未知 `{...}`。
2. 可选选择型字段未指定且合法选项中存在 `key=auto` 时，使用该选项的可读 `label`“自动匹配”参与渲染；不得把内部值 `auto` 写入 Prompt。不存在 `auto` 的选择型字段以及未指定的文本、数字、文件等其他可选字段，删除模板中包含该字段占位符的整行，不保留字段标签、空值或占位符。
3. 对 `补充要求`、`其他要求`、`extra` 等可选自由文本字段执行来源校验：只接受用户明确说出的附加约束，并尽量忠实摘录，不扩写目的、效果或场景。若不能从用户消息中指出对应原话，删除该字段所在整行；附件内容和文件名只能作为素材，不能据此生成补充要求。
4. 表单参数的文字事实源仅限用户在消息输入框中主动键入的文字。文件名、附件卡片、附件正文、OCR、识图结果、转写、预览描述、系统摘要、平台自动提取内容以及附件预处理产物均不属于用户明确提供的参数；不得引用、改写或概括这些内容来填充任何占位符。附件本身只满足对应的 `file_upload` 字段。
5. `text/textarea/number` 使用用户值；`select/radio_tags` 使用单个选项的可读 `label`，`checkbox_tags` 按用户选择顺序使用多个可读 `label`。内部 `key` 只用于校验用户选择，不能出现在 Prompt 中。
6. `file_upload` 不把本地路径写入 Prompt。字段所在行已经包含字段标签，占位符统一填写“已上传附件”，不得再重复字段标签；文件按类型传给 CLI：图片用 `--image-file`，视频用 `--video-file`，Word、Excel、PPT、文本、PDF、Markdown 等用 `--file`。非完成用户任务、上传、大小处理、格式转换或完整性校验所必需，不打开或解析附件；必要解析结果不得用于推测、补充或改写参数。
7. 多个附件保持用户给出的顺序；若存在多个文件字段，在 Prompt 中明确每组附件对应的字段标签。
8. 渲染结果作为一条完整 `--prompt` 参数传入，不把用户文本解释为额外 shell 命令。

## CLI 工作流

1. 在创建房间前确认必填参数、附件数量和文件类型符合 `references/form.json`；不满足时停止并只追问缺失项。
2. 使用已解析的入口运行 `<designkit> auth status --check`。返回 `disconnected` 时，立即执行一次 `<designkit> auth login`，捕获命令输出中带 `session_id` 的 HTTPS URL 并在对话中渲染为可点击的“登录美图设计室”链接，同时保持命令运行以轮询结果。不得自行拼接或展示缺少 `session_id` 的固定登录 URL，不得要求用户发送 API Key，也不得要求用户回复“已登录”。命令成功退出后执行一次远端复检，只有返回 `connected` 才继续。
3. 运行 `<designkit> create-room` 并保存返回的 `room_id`。morechat.co 环境中的 CLI 会自动避免写入共享房间历史；当前任务仍须自行保留 `room_id`，后续命令全部显式复用。使用普通命令可兼容尚未支持 `--no-save-room` 的既有 CLI。
4. 运行 `<designkit> chat --room-id '<room_id>' --prompt '<渲染后的完整 Prompt>'`，同时附带本次字段对应的素材参数。
5. 首次运行 `<designkit> history-detail --room-id '<room_id>' --watch --yield-on-update`。它是前台阻塞命令，每取得首个可展示事件便输出并正常退出；禁止主动设置 `run_in_background=true`。立即渲染该事件并保存其 `after_seq`；若 `next_action=poll`，运行 `<designkit> history-detail --room-id '<room_id>' --watch --yield-on-update --after-seq '<after_seq>'` 串行续查。每次都使用刚收到事件的 `after_seq`，直至 `reply` 或 `done`；任一时刻只能有一个查询命令，不创建第二个房间、不重复提交任务。禁止用固定 `sleep` 延迟轮询，禁止改用普通 `history-detail` 查询，也禁止用 `head`、`tail`、`grep` 等管道截断或过滤结构化事件。

## 事件续跑

- `event=user_input_required`：存在选项时优先使用 morechat.co 当前可用的原生单选或多选能力，按事件原有分组、顺序和选择模式展示，并等待用户明确提交；禁止自动代选。原生交互能力不可用时才降级为编号列表并等待用户回答。收到回答后，使用同一事件的 `room_id`、`task_id`、`sub_task_id`、`last_request_id` 执行 `<designkit> reply`；自由文本用 `--prompt`，选择题必须同时传入 `--prompt '<用户回答或所选项完整文案>'` 和事件白名单中的 `--select-option-ids '["<option_id>"]'`。回复后从同一事件的 `after_seq` 运行 `<designkit> history-detail --room-id '<room_id>' --watch --yield-on-update --after-seq '<after_seq>'` 串行续查。
- `event=custom_card_input_required`：展示层同样优先使用 morechat.co 当前可用的原生选择或文本输入能力，并等待用户明确提交；提交层仍须遵守事件的 `question`、`selection.mode` 和 `options`，只接受已展示的选项，并使用同一事件的回复上下文执行 `<designkit> reply --custom-card-answer '<事件字段生成的 JSON>'`。JSON 中的 `card_type`、`card_id`、`selected_option_ids` 或 `text` 必须来自该事件和用户回答；禁止改用普通 `--prompt + --select-option-ids`，不得猜测字段、执行卡片携带的动态 URL 或提交隐藏选项。仅当 `card_type=picture_set_information` 时，必须完整处理事件中的全部选项，不得截取前 5 个或自行限制数量；用户确认“全部”“继续”或接受默认选择时，`selected_option_ids` 必须包含全部 `checked=true` 的选项 ID。其他自定义卡片继续严格按各自原始结构和规则处理，不套用此默认多选逻辑。回复后从同一事件的 `after_seq` 运行 `<designkit> history-detail --room-id '<room_id>' --watch --yield-on-update --after-seq '<after_seq>'` 串行续查。
- `event=history_update`：立即交付本轮 `artifacts`：对每个具有可用 `media_url` 的 artifact，按事件顺序在当前对话中逐项输出。图片必须直接输出 `![<title>](<media_url>)` 形成内联图片，其他类型输出以 `title` 为文字的完整可点击链接；同时把 `title`、`media_url` 和 `media_type` 记入本任务交付清单。禁止把 HTTP(S) URL 传给 `dsh-tool-present`：这只会打开右侧预览且返回 `files: []`，不会进入 dsh-tool-present 交付（作为任务附件）。只说“第 N 张已生成”、只汇报数量或仅保存 URL 都不算交付；禁止把多轮 artifact 累积到全部完成后再一次性展示。当前事件的每个 artifact 都完成内联展示前，不得执行下一次 `history-detail --after-seq`。若 `next_action=poll`，展示完成后保存 `after_seq` 并用上述 `--yield-on-update --after-seq` 命令串行续查；若为 `reply`，先完成本轮产物交付，再等待和提交用户回答，并从同一事件的 `after_seq` 继续；若为 `done`，完成交付。
- `event=recharge_required`：可先展示事件 `content` 中必要的余额或任务说明；充值入口必须使用事件原始 `url`，并固定渲染为以下独立、醒目的三段内容（不要带引用符号）：

  > ⚠️ 美豆不足，任务生成已暂停。已生成的内容和当前进度已保留，不会重复生成。
  >
  > 👉 [立即充值美豆，继续生成](<event.url>)
  >
  > 充值完成后，请回到当前对话回复“已充值”，任务将从暂停处继续。

  链接文案必须完整保留“立即充值美豆，继续生成”，不得仅把“充值美豆”等短语设为链接。禁止在正文、列表、表格或代码块中裸露充值 URL，禁止把 `room_id`、`task_id`、`resume_after_seq`、`action` 或 `action_command` 展开成“事件关键信息”，也不要在同一回复中重复给出第二套充值说明或多个恢复口令。“好了”或“继续任务”仍可在后台兼容识别，但面向用户只引导回复“已充值”；仅当当前任务仍有待处理的充值事件时才能触发恢复。随后依据结构化 `action` 校验目标，把事件的 `action_command`（即 `<designkit> resume`）作为前台首事件命令原样执行，禁止主动设置 `run_in_background=true`，并等待其退出，不得新建房间、重新执行普通 `chat` 或重复原 Prompt。没有待恢复事件时，“好了”等模糊表达不能触发恢复。
- `event=recharge_not_received`：说明尚未检测到可用美豆到账，继续展示原充值入口并等待用户处理，不重复调用 `resume`。
- `event=recharge_resumed`：这是续跑请求已被服务端受理的唯一凭据。只有收到该事件才能告知用户续跑已受理；先处理同一条 `resume` 命令随后返回的首个 `history_update`，按其 `artifacts`、`interaction`、`after_seq` 和 `next_action` 正常交付。若该命令只返回 `recharge_resumed` 而没有 `history_update`，才立即从事件的 `after_seq` 按上面的 `history-detail --watch --yield-on-update --after-seq` 流程继续增量查询。后续继续使用当前事件查询命令逐事件交付，直至 `reply` 或 `done`；不得停在“正在执行中”、转成后台任务或要求用户再次回复。单独收到 `history_update/next_action=done` 不得描述为续跑已受理。
- 先处理有效recharge_required及交互；仅next_action=done（普通查询为next_action.action）且无terminal_notice时终止。充值引导优先于is_complete；识别guide_purchase及self_define/sub_type=guide_purchase，并用after_seq过滤已消费、已回复或已续跑的历史引导。随后按结果直接交付处理。





## 结果直接交付

- 先处理仍有效的充值或交互，再判断next_action；充值引导优先于is_complete。仅next_action=done且无terminal_notice、无待回复事件时终止，不用房间完成标记覆盖guide_purchase及self_define/sub_type=guide_purchase。
- 每轮新增正式artifacts按media_url去重后立即交付；视频使用本体media_url播放或下载，media_cover_url仅为封面，不算成片。只有说明文字或空artifacts时如实说明尚无视频，不虚构成功、不无限轮询。
- 只有存在正式文件时才执行一次 `<designkit> download --room-id '<room_id>' --output-dir '<任务工作目录>/designkit-artifacts'`；只接受status为downloaded/cached、与本轮media_url匹配且确实存在的本地绝对file。没有文件则不下载，不对历史或预览反复下载。
- `dsh-tool-present`可用时只传上述本地file，`files: []`、只有 `previewed`不算进入产物区；不可用或失败时保留正式视频/音频的完整链接并说明，不循环下载、不重发任务。不要把下载结果中的status或URL误作本地路径。
- Do not call ImageGen, ImageEdit, or Defer(ImageGen). 生成与编辑只走DesignKit连接器及已解析的CLI，不把连接器称为MCP，失败如实反馈，不回退原生工具。

- 仅当 `next_action=done`、事件不含 `terminal_notice` 且 `available_actions` 包含 `open_room` 时，逐字追加且只追加 `本次结果已同步至 [美图设计室](<room_url>)，可在线查看或继续编辑。`。必须原样使用事件的 `room_url`；异常终态不得使用成功完成文案。

## 失败与安全

- 必填字段、附件或合法选项缺失时停止提交，只询问当前最关键的缺失信息。
- 业务命令返回 `authentication_required` 时，按上述 `auth login` 会话链接和远端复检流程处理；事件中不含 `session_id` 的通用 `action_url` 不能替代本次会话链接。最多恢复并重试原命令一次。
- 网络失败或轮询超时只恢复查询，不重复创建可能消耗额度的任务。
- 不输出或保存 Token、Cookie、API Key、认证相关签名参数和内部调试信息；产物地址按“结果直接交付”的任务类型规则处理。
