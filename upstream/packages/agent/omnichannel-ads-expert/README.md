# 全渠道投放官 Omni

覆盖国内外主流媒体的全渠道广告投放专家，串起账户搭建、素材创意、投放监控与数据优化全链路。

## 类型

Agent 型（单个 AI 专家）

## 功能

- **跨平台投放策略**：按产品形态、客单价与回收周期，给出平台组合、预算切分与测试/放量/稳定三阶段节奏
- **账户与广告结构搭建**：按平台层级输出命名规范、计划数量、出价方式、定向组合与对照组设计
- **素材创意生产**：创意矩阵 → 钩子库 → 视频口播脚本 → 标题/CTA → 落地页首屏话术，批量产出可迭代素材
- **投放监控与诊断**：漏斗逐层排查，从日报定位问题层级，输出字段级的优化动作清单
- **出价与放量**：冷启动判断、调价幅度与观察窗口、放量节奏、止损规则
- **合规与审核风控**：强监管行业禁用表述与资质提示，素材上线前自检

覆盖平台：巨量引擎（含千川、TikTok for Business）、腾讯广告（朋友圈/视频号/优量汇）、快手磁力引擎、小红书（聚光/蒲公英）、B站、知乎、百度营销、阿里妈妈、京东京准通、微信生态，以及 Google Ads、Meta Ads、Apple Search Ads 等海外媒体。

## 使用示例

- 我有 5 万预算要推一款新 App，帮我做一份巨量引擎 + 腾讯广告的跨平台投放方案
- 帮我写一批信息流广告素材：3 条短视频口播脚本 + 5 组标题文案
- 这是我的投放日报，帮我诊断跑不起量、成本持续上涨的原因并给出优化动作

## 附带 Skill

`skills/omnichannel-ads-playbook` — 投放实战手册：

- `references/platform-playbooks.md` — 平台速查表、层级结构、命名规范、需求澄清清单、审核红线
- `references/creative-playbook.md` — 创意矩阵、钩子库、脚本结构、素材衰退应对
- `references/metrics-optimization.md` — 指标口径、漏斗排查、诊断决策树、出价与放量策略
- `templates/media-plan-template.md` — 跨平台投放方案
- `templates/creative-batch-template.md` — 素材批次交付
- `templates/daily-report-template.md` — 投放日报与诊断

## 头像

头像已自动生成在 `avatars/` 目录下。如需替换为自定义头像，要求：
- 格式：PNG（推荐）或 JPG
- 尺寸：512×512 px
- 大小：单张不超过 500KB

## 安装

将专家包目录放到专家目录下：

```
C:/Users/chenghao/.workbuddy/plugins/marketplaces/my-experts/plugins/omnichannel-ads-expert/
```

然后运行注册命令使其可见：

```bash
python3 scripts/register_expert.py <expert-dir>
```

## 打包分享

```bash
python3 scripts/package_expert.py <expert-dir>
```
