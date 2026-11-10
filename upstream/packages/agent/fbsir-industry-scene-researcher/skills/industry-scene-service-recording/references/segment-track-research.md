# 细分赛道双侧研究与本地sidecar

## 定位与首值

赛道只在当前项目内组织研究问题、案例/方法供给和迁移条件，不是群、二维码、上下游关系、在线赛道资源或企微空间。它不替代业务问题，也不要求创建线上分类、账号、权限或全局服务。

先交当前可支持的判断或问题图，再给最多两条会改变研究方向的建议。仅说“智能硬件研报”时保持多义，先展示售后分诊、异常复核、端侧交互三个研究分支，不强选、不把未知填成other；普通研究无需等待赛道ID。唯一明确流程可形成非变更性的工作选择，但不冒充Owner确认。自动关键词匹配使用有限否定/排除前缀检查，被排除项不设为current且退出自动建议；纠正表达无法确定时保持needs_selection和中性分支首值，不扩展为通用语义引擎。用户显式track ID仍是独立受控入口。换赛道、扩范围、改硬条件或选择新供需目标必须明确采纳。

## 双侧与适配

- 需求侧：待支持决定、情境、流程、读者/验收角色、目标和已确认约束。
- 供给侧：案例、方法、资源的可证能力、适用条件、限制、版本和现实可用性。
- 公开案例不证明企业愿意合作或资源现实可得；不能据案例推断用户雇主、双方商业意愿或实际收益。
- `fit_matrix`逐条件使用`aligned/conditional/not_aligned/unknown/conflict`，同时列支持与反证、限制和下一验证。硬条件冲突不可直接迁移；机制相似但资源或责任未知只能conditional/unknown。
- 案例相似性、证据覆盖、可迁移性、资源可得性和用户采用分列，不计算未经校准的总分或匹配百分比。

## 三张合成方法卡

包内`templates/smart-hardware-method-cards.json`与`examples/smart-hardware-*.md`是可携带、可续接的合成研究方法示例，不是三个真实产品或成功案例：

1. `smart-hardware-service-triage`：售后故障分诊、人审与升级。
2. `smart-hardware-quality-review`：试制/生产异常提示与人工复核。
3. `smart-hardware-edge-interaction`：端侧交互任务、端云边界与实测假设。

卡片变量不是默认已知事实，方法边界不能暗加成用户永久硬约束。功耗、时延、良率、准确率、价格、收益和市场规模无证据时保持unknown/null。用户可另选流程或提出`user_proposed`本地赛道；它不会注册为全局已审类别。

## 独立sidecar

复杂比较、长期续接或明确需要赛道记录时，在项目内使用`*.track-research.json`，schema为`research.track-research/v1`。模板见`templates/track-research.json`，闭合结构见`schemas/track-research.schema.json`。简短问答不强制建文件或填表。

sidecar绑定`brief_id/brief_version/intent_revision/ResearchBrief canonical SHA256`，但不向ResearchBrief或严格`research.bundle/v2`顶层增加track字段，不改变八类对象、claims-lite或legacy v1只读规则。引用仅限项目授权的source/claim/case/observation ID及版本或受限项目相对路径；helper不打开引用、不执行URL/命令。

每条事实保留`value_text/origin/status/evidence_refs/source_version/observed_at`，状态为`known/unknown/conflict/withheld`。数值以文本保留单位、时期和口径；withheld不等于不存在，冲突并列证据。多赛道复用同一来源不增加独立证据数。

## 采纳、版本与手改

未采纳建议只留`suggested_unaccepted`，Brief、intent_revision和selection均不变。明确采纳目标/范围/硬条件变化才增加intent_revision；证据修订增加brief_version；track记录有独立record_version。

`scripts/track-research.mjs`复用现有kernel的Schema校验和canonical SHA，提供：

- `selectTrack`：明确/多义选择及最多两条未采纳建议；不修改Brief。
- `validateTrackResearch`：独立sidecar结构与语义检查。
- `projectTrackToIntent`：只投影原`case.intent.v1`支持的demand/supply单元，不输出track元数据。
- `applyTrackSelection`：未采纳原样返回；明确采纳才生成新记录版本。
- `reconcileTrackResearch`：按实际差异判断用户决定；底层直调真实变更selection、Brief内容、推进intent_revision或显式select/switch必须`accepted: true`，相等字段不算变化。未采纳保持决定及绑定不变；纯证据/复核可单独推进brief_version且日志始终`accepted: false`。两个绑定版本禁止低于前驱；按track、supply和source版本只标相关fit为needs_review/stale，保留用户手改、未受影响证据和前驱SHA。
- `applyTrackSelection`的`intentScopeChange/briefVersionChange`只接受布尔值，字符串或数字不按真值解释。

保存为新版本并实际读回，不覆盖前驱。Brief SHA、使用卡版本或关联来源变化不全量清空研究，只重核受影响矩阵和派生主张。

## 网络与绩效边界

`case.intent.v1`、正式端点、R2和反馈字段完全不变。track ID/标题/卡片、案例URL、原文、资源明细、群/二维码/上下游/空间字段不进入resolve或feedback，也不为track标签另做digest。摘要仍来自有效本地Brief和任务内随机盐；用户真正采纳的业务范围变化正常进入Brief。

unknown保持unknown；conflict在API中保持`status=conflict,value=unknown`，不摊平为unknown状态；withheld或API不支持的多义值投影为unknown并保留本地原因。网络projection不改变原约束。

已搜/已读覆盖、关键主张核验、反证与迁移条件、自愿采用和真实后续结果分别记录来源、期间和分母。内置卡数量、请求数、计划命中或页面打开不证明研究质量或经营效果。
