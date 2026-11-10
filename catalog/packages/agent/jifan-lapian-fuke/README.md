# 拉片复刻师

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


把一条爆款视频拆成逐镜结构表，再把结构搬到你自己的题材上，只借结构不搬素材。

## 内含技能

- 拉片拆解表生成｜逐镜时长景别信息点（`jifan-lapian-chaifen`）
- 结构复刻方案生成｜搬结构不搬素材（`jifan-lapian-jiegou`）
- 复刻执行清单生成｜素材镜头与工期（`jifan-lapian-qingdan`）
