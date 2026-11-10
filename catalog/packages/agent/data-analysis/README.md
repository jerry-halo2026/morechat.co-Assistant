# 数据分析专家团 · Data Team

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


**一个顶一个咨询公司**：六人专家团接力——澄清需求、体检数据、十大打法深挖，结论先过红队复核再交付，自带零依赖分析工具箱。

## 团队成员

| 成员 | 角色 | 职责 |
|---|---|---|
| **Horizon**（团长） | 首席分析师 | 需求澄清、任务拆解、进度调度、最终交付 |
| **陈澈** | 数据工程师 | 数据体检、清洗留痕，datakit 工具箱执掌人 |
| **严谨** | 统计学家 | EDA 与十大打法深挖，显著性把关，只认数据不认感觉 |
| **顾明** | 行业洞察顾问 | 六大行业指标体系，把发现翻译成"所以呢"和行动建议 |
| **陈述** | 可视化叙事官 | 三级交付物（一页纸/完整报告/附录），图表选型 |
| **甄核** | 复核官（红队） | 替代解释/口径/因果链/行动有效性四类挑战，裁决放行或打回 |

## 工作方式

8 阶段流水线：**需求澄清 → 数据理解 → 质检清洗 → 探索分析 → 深度分析 → 洞察提炼 → ★红队复核 → 报告交付**。简单问题团长灵活调度，但**所有结论必过甄核复核**。

## 自带工具箱 datakit.py（零依赖纯标准库）

`profile` 数据体检评级 · `clean` 清洗留痕 · `funnel` 漏斗瓶颈 · `cohort` 留存矩阵 · `rfm` 用户八分层 · `abc` 帕累托分级 · `sig` 显著性检验/样本量计算

- 自动识别 GBK/UTF-8 编码，懂"万/亿"中文计数
- 输出 utf-8-sig，Excel 打开不乱码

## 中国维度

电商/零售/餐饮/SaaS/内容/App 六大行业指标包 · 618/双11 大促脉冲校正 · 统计局/财报/第三方数据源口径 · PIPL 合规脱敏

## 技能联动

结论 → **数据可视化生成** 出信息图 → **杂志风网页PPT** 出汇报 deck

## 结构

```
data-analysis-expert/
├── 
│   └── plugin.json            # 团队清单（teamInfo + members）
├── agents/                    # 6 个成员人格文件
│   ├── data-team-lead.md      # Horizon 团长（maxTurns 200）
│   ├── data-engineer.md       # 陈澈
│   ├── data-statistician.md   # 严谨
│   ├── insight-consultant.md  # 顾明
│   ├── visual-storyteller.md  # 陈述
│   └── red-team-reviewer.md   # 甄核
├── avatars/                   # team.png + 6 成员头像（512×512）
├── skills/
│   └── data-analysis-cn/      # 内嵌完整技能包（SKILL.md + datakit.py + 8 篇 references）
└── README.md
```

---
Horizon 出品 · version 1.0.0
