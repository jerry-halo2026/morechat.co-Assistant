# 简历·求职教练（Resume · Job Search Coach）

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
├── .codebuddy-plugin/plugin.json     # 专家元信息
├── avatars/expert.png                # 头像（512×512）
├── agents/resume-match-expert.md     # 专家人设与工作流
├── skills/resume-match/              # 内置技能
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
