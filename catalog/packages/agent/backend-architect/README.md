# 磐石石 - 后端架构师

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


深耕分布式系统和高并发架构，擅长将复杂业务转化为优雅技术方案

## 功能特性

- **架构设计**：从单体到微服务，设计可扩展、高可用的系统架构。
- **高并发处理**：缓存、队列、限流、降级等高并发场景的方案设计。
- **数据存储选型**：关系型/NoSQL/时序等存储的合理选型与建模。
- **API 设计**：RESTful / gRPC 接口规范与版本演进策略。
- **性能与稳定性**：链路追踪、容量评估、故障隔离与容灾设计。

## 致谢

本专家在构建过程中参考并借鉴了以下开源项目，特此致谢：

- [agency-agents](https://github.com/msitarzewski/agency-agents)（MIT License）
- [JetBrains Mono](https://github.com/JetBrains/JetBrainsMono)（SIL Open Font License 1.1）

相关开源许可证文本见 [`license/`](./license) 目录。
