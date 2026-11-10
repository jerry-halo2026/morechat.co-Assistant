# 倪叔IP外脑 (NiShu IP Brain)

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


科技博主倪叔的IP外脑，用26题深度问卷诊断个人IP定位，帮你找到人生中最有价值的事、放大信任成交。

## 类型

Agent 型（单个 AI 专家）

## 功能

- **IP定位诊断**：通过26题深度问卷，从8个维度（基本画像、原生家庭、成长磨砺、价值观与人格、人生故事、事业与商业、世界观与格局、自我认知与愿景）系统挖掘差异化定位。
- **信任锚点提炼**：从你的人生经历中，提取能让人"愿意相信你"的具体锚点。
- **创始人人设包装**：把零散经历整合成一句话定位 + 受众画像 + 差异化价值主张 + 可信度证据链。
- **30天第一步行动**：每份报告都给出最小可执行的下一步。

## 使用示例

- 你好，我是倪叔。先告诉我你做什么、想通过IP达成什么，我帮你做一份IP定位诊断报告。
- 我是一名创始人，想从0打造个人IP，第一步该怎么定位自己？
- 帮我梳理我的人生故事和核心优势，提炼出能促成信任与成交的独特价值点。

## 头像

头像不随本内容仓分发（`avatars/` 已移除），由产品端生成（grok 引擎）。

## 上传到开放平台

1. 将本目录打包为 .zip 压缩包（大小不超过 20MB）：
   ```bash
   zip -r nishu-ip-brain.zip nishu-ip-brain/
   ```
2. 进入 [Multica 开放平台](https://...) → 发布管理 → 专家 → 配置专家
3. 上传 `nishu-ip-brain.zip`，按提示确认信息、提交审核