# 易查云海外市场洞察分析师

作者：易查云（open@trade-ai.com）。

判断一个海外市场值不值得进、该怎么进：规模与走势、季节性、价格带、来源国份额、供应格局、买家集中度，以及准入与渠道。负责市场分析、国别分析，以及按产品、HS 编码、区域查询贸易记录。

## 包内容

- `.codebuddy-plugin/plugin.json`：专家配置与连接器依赖。
- `agents/trade-market-analyst.md`：角色、技能路由和交付边界。
- `avatars/expert.png`：专家头像。
- `skills/trade-data-router/`、`skills/trade-market-entry/`、`skills/trade-research-report/`：随包技能。

## 运行条件

需连接“易查云贸易数据”。市场进入评估的方法步骤由服务端下发，运行时调用 `get_playbook` 取最新版本。交易数字只用数据工具结果，准入与渠道等联网信息会注明来源。

## 示例

> 评估越南市场的不锈钢保温杯（HS 961700）值不值得进：近两年进口规模走势、主要来源国份额和价格带，再给出进入建议。
