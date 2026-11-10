---
name: jifan-lapian-chaifen
display_name: 拉片拆解表生成｜逐镜时长景别信息点
display_name_en: Shot-by-shot Breakdown
description: 把你描述的视频拆成逐镜表：每镜时长、景别、画面内容、信息点和它在结构里的作用。用户提到拉片、逐镜拆解、分镜表、时长、景别、结构拆解时使用。
description_zh: 把你描述的视频拆成逐镜表：每镜时长、景别、画面内容、信息点和它在结构里的作用。
description_en: Generates a ready-to-use draft deliverable from your own structured input.
allowed-tools-dsh: Bash
disable-model-invocation: false
user-invocable: true
version: 1.0.2
author: 广州极帆信息科技有限公司
---

# 拉片拆解

把你描述的视频拆成逐镜表：每镜时长、景别、画面内容、信息点和它在结构里的作用。

## 边界

- 输出是**候选清单**，供用户挑选与改写；不替用户做最终选择，也不保证任一条目的实际效果。
- 成稿里的事实、数字、经历、承诺**全部来自你的输入**，本技能不替你编造未提供的信息。
- 输出是 Markdown 成稿，交付前请自己通读一遍再对外使用。

## 工作流

1. 把材料整理成 [输入结构](references/input-schema.md)。
2. 运行：

   `python3 scripts/build_jifan_lapian_chaifen.py --input examples/jifan-lapian-chaifen-sample.json --output /tmp/jifan-lapian-chaifen.md`

3. 打开生成的 .md，按「待确认项」逐条补齐，再改写成你自己的语气。

## 输出结构

| 区块 | 内容 |
|---|---|
| 标题 | 主题 ｜ 拉片拆解 |
| 元信息表 | 成稿类型、主题、条目数、待确认项数 |
| 正文 | 按你给的 items 逐节渲染 |
| 待确认项 | 你标注的 pending 原样列出 |
| 使用边界 | 固定文案，提醒人工复核 |
