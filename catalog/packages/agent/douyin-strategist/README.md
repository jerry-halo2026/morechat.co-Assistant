# 斗音音 - 抖音策略师

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


精通抖音算法和内容生态，打造短视频爆款并实现商业化变现

## 功能特性

- **算法解读**：深入理解抖音推荐机制，指导内容命中流量池。
- **爆款内容策划**：从选题、脚本、钩子到节奏，打造高完播高互动内容。
- **账号成长规划**：制定涨粉路径与人设定位，构建可持续的内容矩阵。
- **商业化变现**：覆盖直播带货、星图接单、私域引流等多元变现路径。
- **数据复盘**：基于完播率、互动率、转粉率等指标持续优化内容策略。

## 致谢

本专家在构建过程中参考并借鉴了以下开源项目，特此致谢：

- [agency-agents](https://github.com/msitarzewski/agency-agents)（MIT License）
- [anti-distill](https://github.com/leilei926524-tech/anti-distill)（MIT License）

相关开源许可证文本见 [`license/`](./license) 目录。
