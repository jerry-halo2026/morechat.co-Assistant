# 绩效薪酬顾问

## 安装 / Installation

本包由 **morechat.co-Assistant** 内容仓分发，**通过 morechat.co-Assistant 目录导入**：

1. 在 morechat.co-Assistant 仓中取出 `catalog/packages/<kind>/<id>/`；
2. 该目录即包根目录，内含 `plugin.json`、`agents/`、`skills/`，整体作为包目录导入；
3. 导入后由平台注册 Agent / Squad 与技能，无需额外安装脚本或注册命令；
4. 头像不在仓内分发（`avatars/` 已移除），由产品端生成。

## 运行时适配 / Runtime notes

- 向用户提问：使用 dsh-tool-ask-user（ask_user_question）；运行时无该能力时，改为在任务评论中提问并等待。
- 交付产物：使用 dsh-tool-present 声明交付；在任务评论中作为附件提交。
- 多角色协作：创建平台小队（Squad）并由 leader 通过 @ 派发子任务。
- 工具声明键为 `allowed-tools-dsh`（Task → subagent，AskUserQuestion → ask_user_question）。


借助简道云，基于绩效、薪酬、合同和异动数据，生成评分校准、薪酬异常、合同到期和流程风险复核清单。

## 运行模式

- 企业版及以上/试用版已连接 MCP：定位用户指定或可识别的现有应用，映射高敏字段并读取授权数据。
- 没有能支持当前任务的现有应用：推荐官方模板，安装后重新检测。
- 免费版、标准版或未连接：仅咨询，不使用 API Key 替代。
- 已连接但未获「新增数据」审核：只读连接模式，继续查询分析并生成待写入预览。
- 纯咨询直接回答；真实数据任务静默定位用户指定或唯一可识别的现有应用，存在多个同名应用时才请用户选择。

## 依赖与边界

- 连接器：`jiandaoyun`
- 官方模板（非使用前提）：https://www.jiandaoyun.com/index/solution_center/app/64f5a5bdbc68c7541396ba75?utm_src=agentjxxcwb
- 默认匿名化和群组汇总；个人薪酬/绩效仅在必要且授权时显示。
- 新增能力审核通过后需在 morechat.co 断开并重新连接；目标表单还需开放新增权限。
- 不自动调薪、定绩效、PIP 或解除；涉及法律与财税需专业人员复核。

官方文档：https://hc.jiandaoyun.com/open/25090

头像：`avatars/expert.png`，512×512 PNG，小于 500KB。
