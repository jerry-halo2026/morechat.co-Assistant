# 简历·求职教练（Resume · Job Search Coach）

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


一位拥有 15 年经验的资深 HR / 招聘专家，从简历诊断、按 JD 定制，到面试准备、投递管理与周复盘——陪求职者走完整个求职周期，直到拿到 offer。

## 核心能力（求职全周期）

1. **简历诊断**：JD 匹配度、技能差距、ATS 友好度、量化成果检查，输出可落地的改写方案；
2. **按 JD 定制**：每投一个新岗位，基于简历主档做定向定制（标题/摘要对齐、技能排序、关键词原词对齐），输出岗位定制版简历；
3. **面试准备**：高频题预测 + STAR 回答框架（基于真实经历）、模拟面试逐题演练与反馈、面试后复盘；
4. **投递管理与周复盘**：维护求职看板、分析投递漏斗卡点、Offer 对比与谈薪建议；
5. **持久化档案**：求职档案 / 简历主档 / 求职看板 / 面试准备文档，跨对话延续进度，用户不用重复背景。

## 目录结构

```
resume-expert/
├── plugin.json     # 专家元信息
├── avatars/expert.png                # 头像（512×512）
├── agents/resume-match-expert.md     # 专家人设与工作流
├── skills/resume-match-expert--resume-match/              # 内置技能
│   ├── SKILL.md
│   ├── references/
│   │   ├── resume-guide.md           # 简历方法指南
│   │   ├── learning-resources.md     # 学习资源库
│   │   ├── interview-prep.md         # 面试准备与模拟面试方法
│   │   └── job-search-playbook.md    # 投递/Offer/复盘全流程方法
│   ├── templates/job-tracker.md      # 求职看板模板
│   └── scripts/
│       ├── analyze_resume.py         # 匹配分析（零依赖）
│       └── export_docx.py            # 简历导出 Word（零依赖）
└── README.md
```

## 版本

- **v2.0.0**（当前）：从「简历诊断」升级为「求职全周期」——新增按 JD 定制、面试准备与模拟面试、投递管理与周复盘、跨对话档案持久化；
- v1.0.0：简历诊断与匹配分析。

## 注意

- 头像 `avatars/expert.png` 为占位图（512×512），可替换为漫画/插画风格；
- 脚本仅用 Python 标准库，无需安装依赖；支持 md/txt/docx 格式的简历。
