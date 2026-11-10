# 细分研究赛道方法模板

> 使用方式：每张模板卡只负责研究方法与证据适用条件。先完成本地双侧简报，再按 v2r2 选择唯一赛道或请求明确选择；未选择时不执行未接纳的在线赛道计划，原用户授权允许联网且有相应工具与预算时仍可继续不依赖该选择的原生有界检索。

## 1. 智能硬件产品研究

- track：`smart-hardware-product-research`（ID 仅作方法绑定，展示名不是证据）
- 适用：`sector=smart_hardware`，`scenario=product_feasibility`，目标为关键判断核验
- 需求侧：产品用途、使用场景、端侧/云端约束、可接受取舍、采购或验证决定
- 供给侧：规格、设备/固件版本、实测条件、功耗/续航/延迟/连通、数据边界、估算 BOM、制造交付与售后
- domain_checks：
  1. `device_test_conditions`：核对准确设备、型号、固件、负载、环境、基线、样本与试验条件；宣传摘要回查详细条件。
  2. `edge_cloud_boundary`：区分本地处理与云服务、离线限制、音频/数据传输与授权边界。
  3. `power_latency_connectivity`：只在相同统计量和可比条件下比较；不得从规格外推实测表现。
  4. `bom_manufacturing_support`：区分 BOM 估算、观察到的完整成本、量产、维护、保修与售后条件。
- 正文落点：需求与证据适配；规格和成本可比性；决策及验证条件。
- 停止条件：硬约束被证据否定、关键条件无法取得、预算耗尽、冲突未解或证据足以支持有边界决定。

## 2. 制造业售后 AI 辅助

- track：`manufacturing-aftersales-ai`
- 适用：`manufacturing` + `aftersales_ai`
- domain_checks：AI/人工派单边界、失败升级路线、工单证据与隐私范围。
- 正文落点：人工责任与 AI 辅助分界；异常升级；工单可见范围和授权；效果证据的同任务口径。
- 不把方法种子写成现实客户、案例覆盖或效果。

## 3. 企业软件竞品比较

- track：`enterprise-software-comparison`
- 适用：`enterprise_software` + `competitive_comparison`
- domain_checks：产品与版本身份、许可权益与价格单位、 benchmark 任务及分母对齐。
- 正文落点：对象身份、功能替代、商务权益、共同任务与原始结果分别呈现。
- 不用不同版本、不同任务或不同权益直接合成性价比排名。

## 4. 企业知识问答核验

- track：`enterprise-knowledge-qa`
- 适用：`enterprise_software` + `knowledge_qa`
- domain_checks：答案主张回溯引用、检索可见范围、知识时效。
- 正文落点：问题—答案—出处链；无权限内容不可见；旧知识和未更新范围；反证与未回答问题。
- 搜索命中或回答流畅不等于事实正确或已获授权。

## 无赛道基础与回退

仅改写、重排、已有材料核验、仅本地任务沿用 v1 原生方法。无匹配、目录不可用、需要选择或服务失败时，先交付有边界的本地研究首值，并标明本轮未使用在线细分策略。
