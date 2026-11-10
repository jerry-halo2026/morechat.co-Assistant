# 播旺旺 - 直播电商教练

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


精通直播带货全链路运营，从话术到投流帮助实现GMV突破

## 功能

- 设计直播带货全链路运营方案，覆盖选品、话术、节奏与转化
- 优化直播间投流策略与流量结构，提升 GMV
- 复盘直播数据，输出可执行的增长改进建议

## 致谢

本专家的 agent 提示词方法论参考、改编了以下开源项目，感谢该项目及其贡献者：

**项目一**
- 项目名称： agency-agents
- 项目地址： https://github.com/msitarzewski/agency-agents
- 开源许可证： MIT License
- 使用说明： 本专家的 agent 提示词在结构与方法论上改编自该项目，并结合直播电商场景进行了修改与本地化。

适用于本专家所参考的开源项目版本的许可证原文，可查阅专家包内 `license/` 文件夹（`agency-agents.LICENSE`）。

如本专家包含源自上述项目的开源内容，该等内容仍受原开源许可证约束，本声明不改变、替代或限制该等许可证项下的任何权利和义务。用户在使用、修改或分发该等内容时，应自行查阅并遵守原开源许可证，包括其中适用的署名、声明保留、源代码提供及相同许可证授权等要求。
