---
name: omnichannel-ads-playbook
description: 全渠道广告投放实战手册。当需要输出跨平台投放方案、搭建广告账户与计划结构、批量生产投放素材脚本与文案、设计出价与预算策略、做投放监控日报与效果诊断复盘时使用。覆盖巨量引擎、腾讯广告、快手、小红书、B站、知乎、百度、阿里妈妈、微信生态及 Google/Meta/TikTok 等国内外主流媒体。
---

# 全渠道广告投放实战手册

本手册是全渠道广告投放专家的落地工具箱。核心原则：**先定目标与口径 → 再定平台组合 → 再搭结构 → 再产素材 → 最后靠监控闭环迭代。**

## 使用原则

1. 任何方案先确认「产品形态 + 转化目标 + 出价方式 + 预算周期 + 目标人群 + 承接链路」六项前提（见 `references/platform-playbooks.md` 的需求澄清清单）。信息缺失时先问，不做臆断。
2. 平台规则、计费方式、审核政策会频繁变更，输出具体数值规则时必须标注「以平台当前官方文档/后台为准」。
3. 优化动作必须可执行到字段级别：哪个层级、改哪个字段、改成什么、观察多久。

## 工作流

### 1. 需求澄清（必做）
读 `references/platform-playbooks.md` 的「需求澄清清单」，把缺失的关键前提一次性问清。

### 2. 平台组合与预算切分
按产品形态和回收周期从 `references/platform-playbooks.md` 的平台速查表中挑选主投平台，确定：
- 主投 1-2 个平台跑模型，其余作为次级放量或种草阵地
- 测试期 / 放量期 / 稳定期的预算百分比与止损线

### 3. 账户与广告结构搭建
按 `references/platform-playbooks.md` 中各平台的层级结构和命名规范输出搭建清单，每个平台明确：层级数量、预算分配、出价方式、定向组合、版位开关、对照组设计。

### 4. 素材生产
读 `references/creative-playbook.md`：
- 先搭「人群 × 痛点 × 场景 × 卖点」创意矩阵
- 再按钩子类型产出差异化脚本（每条素材必须有不同的首帧钩子）
- 同步产出标题、CTA、落地页首屏话术，保证承诺一致

### 5. 出价与预算策略
读 `references/metrics-optimization.md` 的出价策略章节，确定冷启动出价、提价/压价幅度、放量节奏与止损规则。

### 6. 监控与诊断
用 `references/metrics-optimization.md` 的漏斗排查法和诊断决策树定位问题层级，输出「指标现状 → 归因判断 → 动作清单」。

### 7. 交付
- 投放方案 → 套用 `templates/media-plan-template.md`
- 日报诊断 → 套用 `templates/daily-report-template.md`
- 素材批次 → 套用 `templates/creative-batch-template.md`

## References

- `references/platform-playbooks.md` — 平台速查表、层级结构、命名规范、需求澄清清单、审核红线
- `references/creative-playbook.md` — 创意矩阵、钩子库、脚本结构、标题/CTA 写法、素材衰退应对
- `references/metrics-optimization.md` — 指标口径与公式、漏斗排查法、诊断决策树、出价与放量策略、冷启动规则

## Templates

- `templates/media-plan-template.md` — 跨平台投放方案
- `templates/creative-batch-template.md` — 素材批次交付
- `templates/daily-report-template.md` — 投放日报与诊断
