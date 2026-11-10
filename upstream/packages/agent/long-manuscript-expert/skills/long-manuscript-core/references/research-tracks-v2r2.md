# 细分研究赛道双侧协同方法（v2r2，领域方法保留）

> **入口声明（2026.11.5）**：本文件保留旧版领域方法与校验语义，作为**兼容层说明与校验器来源**，不是当前运行入口。0200 唯一当前入口是 `scripts/strategy_client_0200.py`（完整包装器，精确 `2026.11.5` + 闭合 `paper.intent.v2` + 同号只读回执）。`scripts/strategy_client_v2.py` 与 `scripts/strategy_client.py` 只作为**完整 v2 校验器被复用**：其 consumer 常量仍为旧 `2026.10.300`，旧发送循环允许同号重试，**不得**被自然加载为 0200 的当前发送入口、备用入口或重试路径。普通用户无需访问合同仓库或理解内部 ID。

开发维护时的历史合同参考为源项目 `contracts/v2r2/`（**仅开发参考与兼容层，不是运行权威**）；它继承 v1 的严格字段、有限数、空计划、摘要/版本绑定、时间/单调截止、反馈默认关闭与未知计数不上传规则。该开发目录不是市场包的运行依赖。**0200 的一切远端调用、恢复与回执消费的唯一运行权威是 `references/service-contract.md` 与 `scripts/strategy_client_0200.py`**；0200 客户端复用这里描述的**闭合字段与语义校验**（含请求绑定的候选/选择/预算语义），但精确版本准入、一次发送、原号回执、观测过期不可复活、排他恢复事件与反馈资格由 `references/service-contract.md` 及 `scripts/strategy_client_0200.py` 定义。

## 本地双侧简报

- 需求侧：用途、决定、读者、范围、场景、端云或隐私约束、交付与停止条件。
- 供给侧：材料可支持的主张、覆盖、来源状态、时效、适用限制与冲突。
- `sector` / `scenario` 保留 typed cell 的 value、origin、status、evidence_version。用户明确话语映射为 `user_explicit`；推断只能标 `derived`；缺失保持 `unknown`，冲突保持 `conflict`。完整主题、企业名、私密材料、作者判断与 salt 留本地。
- 未采纳建议不改变目标、硬条件或作者立场；“继续”不等于采纳。

## 选择与回绑

1. 新赛道任务使用 `paper.intent.v2`，`track_selection` 为 null 或精确 `{id,version,catalog_revision}`；v1 只保留无赛道基础兼容。
2. 唯一 eligible 且完全符合明确范围的已审有效赛道才可 `automatic_unique`。已知范围的两个 cell 必须均为 `user_explicit`。
3. 多候选或 derived 范围返回 `needs_selection`，先给首值与候选差异，不默选、不执行未接纳的在线赛道计划；原用户授权允许联网、相应工具可用且预算充足时，可继续不依赖该选择的原生有界检索，仅本地限制、权限拒绝或零网络预算仍不联网。用户明确选择后使用新 request_id 和当前目录修订精确回绑。
4. `unknown` 只命中显式包含 unknown 的规则；`conflict` 不eligible。暂停、未审核、未生效、到期、版本不符、缺条件和无匹配分别报告；不把无匹配解释成需要新建赛道。
5. `selected` 必须有 strategy/plan/track、非空 query/source/domain_checks，且 track 与唯一 eligible candidate/evaluation 一致。决定不得活过 `track.expires_at`；接收与执行前都检查版本、时间、单调截止和当前目录。
6. 服务不可用、无匹配或需要选择时，仍可按本地原生方法完成有边界研究，并明确本轮未采用在线细分策略。

## domain_checks 必须进入研究执行

赛道不是报告标签。将 domain_checks 映射到查询、原文核验、比较表和正文位置；查询/来源/通用检查只重排既有基础成员，预算取用户、基础模板和赛道上限的最小值，不扩大预算、不改变硬约束。方法审核有效期不证明外部证据新鲜，供应时效与来源日期仍逐项核验。

跨赛道比较分批绑定各自 ID/版本/目录修订和预算，只比较共同口径，不合成通用收益榜。

## 四个合成方法种子

这些种子是合成、已审方法模板，不代表现实服务资源、真人供给、客户、案例覆盖或效果。

- `smart-hardware-product-research`：device_test_conditions、edge_cloud_boundary、power_latency_connectivity、bom_manufacturing_support。
- `manufacturing-aftersales-ai`：aftersales_manual_dispatch、escalation_route、ticket_data_boundary。
- `enterprise-software-comparison`：competitor_identity_version、license_entitlements、benchmark_task_alignment。
- `enterprise-knowledge-qa`：qa_citation_grounding、retrieval_access_scope、stale_knowledge。

研究赛道只描述细分研究领域、研究问题、证据适用条件和协同策略，不承载其他身份、资源或关系路由。
