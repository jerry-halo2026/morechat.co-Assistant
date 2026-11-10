# 花叔文档审稿专家 · huashu-doc-reviewer

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


> morechat.co Expert · Agent 型专家
> 行业分类：11-SecurityCompliance（法务安全）

## 一句话

为「一人公司 / 超级个体」打造的 AI 审稿专家：直接在你的 .docx 原文里加批注气泡和修订痕迹，不返回新文档、不破坏原格式。专攻合同审查 / 报告改稿 / 方案评审三类高敏文档。

## 工程哲学

**让模型做判断，让代码做操作。**

模型只输出结构化 JSON 决策列表，所有文档操作（XML 解析、字符定位、批注 ID 分配）由代码完成。这让本专家对模型能力依赖极低，轻量模型也能稳定运行，规避「Agent 一跑偏整篇炸」的常见失败模式。

## 三种审稿模式

| 模式 | 适用场景 |
|---|---|
| `contract` | 商业合同、采购合同、NDA、劳动合同 |
| `report` | 商业报告、内部报告、白皮书 |
| `proposal` | 项目方案、产品 PRD、运营方案 |

## 文件结构


## 关于作者

陈云飞（@花叔 / Alchain），AI Native Coder、独立开发者、AI 自媒体博主。代表作小猫补光灯（App Store 付费榜 Top 1）、《一本书玩转 DeepSeek》。

B站 / X / YouTube / 小红书 / 公众号统一 ID：花叔。全网粉丝 30 万+，产品累计用户超百万。

## 联系方式

- 邮箱：alchaincyf3@gmail.com
- 官网：https://www.huasheng.ai/
- 完整演示视频：https://www.bilibili.com/video/BV159RQB6E4P/

## 与花叔另一个 Expert（huashu-data-pro）的关系

两个专家服务的是「一人公司」工作流的两端：
- **huashu-data-pro**：处理数据类敏感文件（财务表、订单表、薪资表）
- **huashu-doc-reviewer**：处理文档类敏感文件（合同、报告、方案）

各自独立、互不重叠。详见两个专家的 `displayDescription` 和场景分类（DataAI vs SecurityCompliance）。
