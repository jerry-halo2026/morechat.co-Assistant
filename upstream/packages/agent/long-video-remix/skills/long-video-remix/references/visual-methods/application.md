# 将 Visual Methods 接入 Execution Package

这是 Direct 2 的设计知识层，不新增阶段、状态文件、确认 Gate 或 QA 层。完整生产顺序、Blender Composition、Proof、Dynamic Demo 与 FFmpeg 回接统一以 [visual-production.md](../visual-production.md) 为准。

## 从视觉问题到 Project Method

1. 从已确认 Narrative Direction 与 Detail 证据说明本段叙事功能，绑定 source_id、源时间、真实关键帧与必要上下文。
2. 用 [Visual Router](index.md) 判断当前问题；命中方法后读取 [完整方法库](method-library.md)，需要替代 / 兜底时读取 [fallback-recipes.md](fallback-recipes.md)。
3. 同一项目已确认的方法按 [方法保持合同](../workflow-control.md#方法保持与叙事参数补丁) 继承，只用具名参数补丁适配 Narrative；方法未确认时，Methods 用于校正和深化；没有成熟方案、方案过于普通或无法适配真实画面时，形成 1–3 个可制作候选，说明取舍并推荐一个。
4. 公开版新项目采用视觉设计时，参考研究和候选设计统一交给 [Visual Reference Router](../visual-reference-router.md) 的 V0–V7：V2 按问题说明如何用当前素材校准方向，V3 先 Art Direction 后参数。Visual Methods 不再另选参考，只负责把确认后的视觉问题/方案转成可生产的方法。
5. 把当前视频实际采用的 production method 写成 `visual-methods.json`；`method_id` 使用 PM001...，通用知识来源写在 `library_refs` / `fallback_refs`，需要时用 `visual_stage_problem_refs` 指向 V1 问题。参考来源、迁移原则和候选比较留在 V2/V3，不重复抄到 methods。
6. 真实参数继续进入 execution-reference、visual-methods、composition-plan 与 timeline；Mockup / Composition / Proof / Dynamic Demo / Gate 由视觉制作流程执行。

## 具体参数写到哪里

| 处理 | 当前执行包中写清 |
|---|---|
| 字幕与标题 | 实际文字、类别、字体与可用入口、字号单位、字重、换行、位置、安全区、图层、色彩、进出场和阅读窗口 |
| 裁切与缩放 | 源尺寸、输出画幅、crop / fit、起止框、锚点、主体运动范围、时间窗口、缓动与关键证据避让 |
| 变速或停顿 | 源区间、速度及变化方式、原声处理、动作和对白保护、输出时长及 source → output 映射 |
| 自制图形或空间文字 | 内容用途、语义对象、形状或组件、跟踪与遮挡方式、图层、可复现入口及失效处理 |
| 色彩 | 包装与原片处理的分工、正文与强调色角色、对比、肤色及场景光线保护 |

具体数值由本次画幅、素材和验证决定；方法库不提供所有项目共用的固定字号、固定坐标、固定倍速或固定时长。

## Project Method 推荐记录

以下字段不增加新项目文件，直接进入 `visual-methods.json` / execution-reference：

- `visual_problem`：当前观看问题与目标；
- `library_refs`：采用的 M01–M14；
- `fallback_refs`：采用的 F01–F09，可为空；
- `visual_stage_problem_refs`：采用视觉设计时可选，回指 V1 中由该 production method 负责实现的问题；
- Reference Selection / structure-card conditions / transfer / do-not-transfer：留在 V2；
- Art Direction / candidate comparison / per-shot composition grammar / shot dependency：留在 V3；
- `visual_reference_status / visual_reference_refs / viewed_reference_assets / candidate_treatments`：供兼容读取。采用视觉设计时以 V0–V7 为事实源；
- `selected_treatment` / `selection_reason`：当前采用方案与为什么；
- `parameters`：本次真实画幅和素材下的参数；
- `failure_modes` / `demo_checks`：失败信号与 Dynamic Demo 检查点。

这些字段帮助 Direct 2 形成可执行方案，但**不把方法库本身当成素材证据**。事实仍来自当前项目 Detail / source-time 证据；外部案例只能提供组织方法。

## 质量与兜底

如果 Direct 2 输出仍只是“更高级 / 更电影 / 更综艺 / 字大一点 / 放大人物”，或没有说明真实画面条件、候选取舍与可执行参数，就继续调用 Visual Methods，不进入 Mockup。

若当前方法库没有合适答案，可以按 [research-extension.md](research-extension.md) 扩展研究；无法联网时继续使用完整方法库与兜底组合。最终是否成立仍由当前真实关键帧、动态 Demo 和现有 QA 验证。
