---
name: trade-research-report
description: >-
  风控背调需要证据/反证/缺项（骗子判断另给分档结论）、按候选名单筛活跃/增长客户、找补货/供应机会、企业资料按产品/行业/相似度/公开标签获客、按产品找采购商、采购商/供应商/产品/HS/区域多条件逐笔记录、找决策人/查履历、查邮箱或电话、验证号码/邮箱/任职、采购商/供应商/市场/国别多维或单章分析或全面/公司背调需可恢复交付，以及做一份**外贸调研报告**时使用。报告由几部分任意组合：委托方画像、市场盘子与趋势、
  准入渠道与展会、品牌商与竞品、目标客户名单、老客户背调、单买家深挖、行动计划。
  用户说"出一份 XX 市场调研报告 / 客户开发报告 / 市场进入方案 / 给我 N 家目标客户并分析市场 /
  老客户背调 / 深挖某买家出报告"，或要 Word / Excel / 网页版的成品报告时触发。
  触发词：调研报告、市场调研、市场分析报告、客户开发报告、目标客户名单、出海方案、
  市场进入、老客户背调、买家深挖报告、market research report、buyer list report。
  本技能只管流程：先调 plan_report 拿计划，问清待确认项，按步骤执行、逐部分核实，
  再调 get_render_spec 取格式要求，渲染、自检、交付。方法、口径与踩坑都在计划里。
  不用于：单个事实问题（谁在买、趋势多少）——交给 trade-data-router 直接查；
  未落入已适配任务、只做单一目标又不要成品报告（如深挖一家买家）——调 get_playbook 取对应方法。
display_name: 易查云外贸调研报告
display_name_en: Trade AI Trade Research Report
description_zh: 外贸调研报告:先调报告编排拿计划,问清待确认项,按步骤执行、核实、按格式要求渲染并自检后交付。
description_en: >-
  Builds multi-part trade research reports with Trade AI trade data: gets a plan
  from plan_report, confirms open questions, executes the steps, verifies, then
  renders per get_render_spec and self-checks before delivery.
category: data
version: 1.1.6
author: 易查云
---

# 外贸调研报告：按计划执行

## 业务任务

按任务读：公开/AI7：`references/host-business.md`；风控4：`references/risk-evidence.md`；信号4：`references/signals.md`；获客7：`references/acquisition.md`；找人/履历：`references/people-background.md`；企业资料：`references/company-profiles.md`；贸易明细：`references/trade-records.md`；原名单/明细：`references/first-batch.md`；联系方式：`references/contacts.md`；验证：`references/verification.md`；分析/背调：`references/analysis.md`；网页（默认）：`references/html-report.md`。按计划执行；规划免费，缺项先确认。
S06默认25家，获客7项20家；贸易默认近12个月、规模不限；进口记录50条、全部市场；工商按资料期。关键人默认≤3位。输入优先。
按胶囊选契约，同名先澄清。

## 第 1 步　整理需求，调 `plan_report`

任务先读对应 references，按契约调 `plan_report` 的 task 分支，无需委托方且不混模块；再按计划查数、核实、交付。未支持则需更新，不编造模块。

旧多模块报告收委托方名称/官网（如有）、≤5个产品、市场国家/区域/配额、M0–M7（未选不填，服务推荐）、客户类型、老客户排名、期间、快/深度与格式；单买家给名称/国别。缺项交计划确认，不编造。

## 第 2 步　先问完待确认项

逐条问待确认项（pending_confirmations）：照 question 原文问，带上选项与建议值。
- **blocking 为 true 的不确认，对应步骤不执行**；不得拿建议值当答案跑下去。
- **replan 为 true 的**，用户的回答与建议不同或补了信息时，把全部答案合在一起**重新调用一次**
  `plan_report`。重新规划会再计规划期查询费用，先一次问完再重调，别答一条调一次。
- 其余项的答案按计划里 placeholders 的说明代入，不必重调。

## 第 3 步　建工作目录与进度文件

工作目录保存计划全文、答案、占位符最终值、状态及产出；付费调用记查询记录（已安装报告套件的 `query_log.py`，前 begin 后 done）。丢上下文读进度续办：先 summary，已完成查询不重跑；免费方法及格式要求可重取。

## 第 4 步　按步骤执行

计划 reasoning 的 how_to_use 是完整规则：
- kind 为 playbook 的步骤先调 `get_playbook` 取方法正文，再做它后面的步骤；
- kind 为 mcp 的调数据工具，参数照抄，`<名字>` 按 placeholders 代入；kind 为 web 的用宿主的联网检索；
- 带 for_markets 的对其中每个国家各做一次；if_quota_short_markets 里的国家只在凑不满配额时做；
- 宿主能开并行子任务就按 how_to_use 标明可并行的步骤并行，否则串行；子任务只回摘要，产出写进工作目录；
- 每次数据查询后读 warnings 与 meta.coverage_gaps，盲区原样记进进度文件，渲染时要用；
- 各部分的产出按计划 output_schema 的字段写成结构化数据（一行一条，字段名照抄）存进工作目录；
- kind 为 render 的步骤放到最后做，它列的是本次全部模块，没有单个模块号。

## 第 5 步　每部分做完就核实

按计划 checklist 里该部分的检查项、核实层（V1–V4）与"核实范围"一条自查。
没过的按核实层的做法降级、替换或标注，不静默保留。

## 第 6 步　取格式要求，渲染

每种格式重新调 `get_render_spec`（格式+本次模块），按规范用宿主文档、表格或代码能力生成文件；不凭压缩前记忆。

### 报告套件与宿主能力

首次要求文件时，按渲染规范的“报告套件与宿主能力”检查执行能力和本地套件；自检只跑一次。
连接成功不代表已安装；云端无法检测不等于未安装。需安装时给 https://mcp.trade-ai.com/start/#report-kit ，不改连接配置。
用户暂不安装则本会话不重复提示，按宿主原生文件能力继续；无法生成文件时说明限制，不虚构下载链接。普通查询不提示安装，安装失败不重复采数。

## 第 7 步　自检后交付

逐条过规范里的交付前自检与公共自检；"不得交付"项没过就先修，修不了如实告诉用户，不交付。
交付消息里按渲染规范的要求写自检结果与查询记录的费用汇总，并附名单的证据等级统计（如"120 = 证据 A 82 + 证据 B 29 + 证据 D 9"）。

## 服务不可用时

`plan_report` 或数据工具报连接失败、超时、工具不存在：先把原始错误原话告诉用户，说明本次没用到易查云数据，
不得静默改用网页数据拼一份报告。报"该功能需单独申请开通"：告诉用户报告编排要开通方法论授权。
报"Token 余额不足""今日用量已达上限""该功能暂不可用"：不重试，把提示原文告诉用户，在进度文件记下停在哪一步——充值、次日或开通后从那里接着做；不得用网页数据补齐剩下的部分。
报"请求过于频繁"：减少并行，稍等再试。
