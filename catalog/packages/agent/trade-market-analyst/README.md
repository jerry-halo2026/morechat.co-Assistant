# 易查云海外市场洞察分析师

## 安装 / Installation

本包由 **morechat.co-Assistant** 内容仓分发，**通过 morechat.co-Assistant 目录导入**：

1. 在 morechat.co-Assistant 仓中取出 `catalog/packages/<kind>/<id>/`；
2. 该目录即包根目录，内含 `plugin.json`、`agents/`、`skills/`，整体作为包目录导入；
3. 导入后由平台注册 Agent / Squad 与技能，无需额外安装脚本或注册命令；
4. 头像不在仓内分发（`avatars/` 已移除），由产品端生成。

## 运行时适配 / Runtime notes

- 向用户提问：使用 dsh-tool-ask-user（ask_user_question）；运行时无该能力时，改为在任务评论中提问并等待。
- 交付产物：使用 dsh-tool-present 声明交付；在 Multica 中作为 Issue 附件提交。
- 多角色协作：创建 Multica Squad 并由 leader 通过 @ 派发子任务。
- 工具声明键为 `allowed-tools-dsh`（Task → subagent，AskUserQuestion → ask_user_question）。


作者：易查云（open@trade-ai.com）。

判断一个海外市场值不值得进、该怎么进：规模与走势、季节性、价格带、来源国份额、供应格局、买家集中度，以及准入与渠道。负责市场分析、国别分析，以及按产品、HS 编码、区域查询贸易记录。

## 包内容

- `plugin.json`：专家配置与连接器依赖。
- `agents/trade-market-analyst.md`：角色、技能路由和交付边界。
- `avatars/expert.png`：专家头像。
- `skills/trade-data-router/`、`skills/trade-market-entry/`、`skills/trade-research-report/`：随包技能。

## 运行条件

需连接“易查云贸易数据”。市场进入评估的方法步骤由服务端下发，运行时调用 `get_playbook` 取最新版本。交易数字只用数据工具结果，准入与渠道等联网信息会注明来源。

## 示例

> 评估越南市场的不锈钢保温杯（HS 961700）值不值得进：近两年进口规模走势、主要来源国份额和价格带，再给出进入建议。
