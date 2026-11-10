---
name: jifan-lapian-qingdan
display_name: 复刻执行清单生成｜素材镜头与工期
display_name_en: Production Checklist
description: 把复刻方案落成执行清单：要拍哪些镜头、需要什么素材、谁做、大概多久。用户提到执行清单、拍摄清单、素材清单、工期、分工、落地执行时使用。
description_zh: 把复刻方案落成执行清单：要拍哪些镜头、需要什么素材、谁做、大概多久。
description_en: Generates a ready-to-use draft deliverable from your own structured input.
allowed-tools-dsh: Bash
disable-model-invocation: false
user-invocable: true
version: 1.0.2
author: 广州极帆信息科技有限公司
---

# 复刻执行单

把复刻方案落成执行清单：要拍哪些镜头、需要什么素材、谁做、大概多久。

## 边界

- 输出是**待人工确认的计划草案**，不自动预订、付款、发布或代替用户与他人沟通。
- 成稿里的事实、数字、经历、承诺**全部来自你的输入**，本技能不替你编造未提供的信息。
- 输出是 Markdown 成稿，交付前请自己通读一遍再对外使用。

## 工作流

1. 把材料整理成 [输入结构](references/input-schema.md)。
2. 运行：

   `python3 scripts/build_jifan_lapian_qingdan.py --input examples/jifan-lapian-qingdan-sample.json --output /tmp/jifan-lapian-qingdan.md`

3. 打开生成的 .md，按「待确认项」逐条补齐，再改写成你自己的语气。

## 输出结构

| 区块 | 内容 |
|---|---|
| 标题 | 主题 ｜ 复刻执行单 |
| 元信息表 | 成稿类型、主题、条目数、待确认项数 |
| 正文 | 按你给的 items 逐节渲染 |
| 待确认项 | 你标注的 pending 原样列出 |
| 使用边界 | 固定文案，提醒人工复核 |
