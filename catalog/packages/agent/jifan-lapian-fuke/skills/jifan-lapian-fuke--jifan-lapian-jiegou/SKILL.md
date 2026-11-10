---
name: jifan-lapian-jiegou
display_name: 结构复刻方案生成｜搬结构不搬素材
display_name_en: Structure Transfer Plan
description: 把拆出来的结构映射到你自己的题材上，逐镜说明你该拍什么，不复制原片画面与文案。用户提到结构复刻、套结构、换题材、爆款结构、模仿结构、借鉴时使用。
description_zh: 把拆出来的结构映射到你自己的题材上，逐镜说明你该拍什么，不复制原片画面与文案。
description_en: Generates a ready-to-use draft deliverable from your own structured input.
allowed-tools-dsh: Bash
disable-model-invocation: false
user-invocable: true
version: 1.0.2
author: 广州极帆信息科技有限公司
---

# 结构复刻

把拆出来的结构映射到你自己的题材上，逐镜说明你该拍什么，不复制原片画面与文案。

## 边界

- 输出是**待人工确认的计划草案**，不自动预订、付款、发布或代替用户与他人沟通。
- 成稿里的事实、数字、经历、承诺**全部来自你的输入**，本技能不替你编造未提供的信息。
- 输出是 Markdown 成稿，交付前请自己通读一遍再对外使用。

## 工作流

1. 把材料整理成 [输入结构](references/input-schema.md)。
2. 运行：

   `python3 scripts/build_jifan_lapian_jiegou.py --input examples/jifan-lapian-jiegou-sample.json --output /tmp/jifan-lapian-jiegou.md`

3. 打开生成的 .md，按「待确认项」逐条补齐，再改写成你自己的语气。

## 输出结构

| 区块 | 内容 |
|---|---|
| 标题 | 主题 ｜ 结构复刻 |
| 元信息表 | 成稿类型、主题、条目数、待确认项数 |
| 正文 | 按你给的 items 逐节渲染 |
| 待确认项 | 你标注的 pending 原样列出 |
| 使用边界 | 固定文案，提醒人工复核 |
