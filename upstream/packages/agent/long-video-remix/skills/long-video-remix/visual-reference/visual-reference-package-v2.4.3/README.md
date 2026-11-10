# Visual Direction & Production Methods

| 内容 | 入口 |
|---|---|
| V0–V7 的阶段证据、模板和使用规则 | [视觉方案执行规程](references/visual-design-procedure.md) |
| 注意力、文字角色、空间关系和强调尺度 | [Visual Direction Atlas](references/visual-direction-atlas.md) |
| 真人镜头的图文关系、落位与阅读顺序 | [Scene × Text Grammar](references/scene-text-grammar.md) |
| 文字进出时机、声音节点与动态验证 | [Timing Grammar](references/timing-grammar.md) |
| 剪辑节奏、镜内运动、转场与混源调色 | [剧情剪辑方法](references/editing-grammar.md) |
| 双人同框、关系观察、原声与长文案 | [人物关系观察](references/cp-relationship-visual-application.md) |
| 动效、跟踪遮挡、景深和字幕落位 | [实现机制](references/motion-implementation-map.md) |

视觉阶段模板在 `templates/visual-stage/`。V2 逐项记录如何依据当前项目的源帧和文案校准方向。新风格在 V5 做代表性同源 A/B，再用 V6 用户决定与 V7 参数锁定接回宿主 Implementation Lock。

运行 `python3 -I scripts/check_visual_stage.py PROJECT/visual`，依输出的 `NEXT_ALLOWED` 续接。依赖见 `scripts/visual-reference-requirements.txt`。

字幕落位工具的输入骨架见 [cue sheet](templates/caption-placement.json)。按当前 V3 样式填写 fonts、roles 和 ink，并登记项目帧与文案。裁切坐标以当前源帧为准。使用代理帧时，在对应 `frames.<id>.source_geometry` 填写 V0 登记的源宽、高。工具的输出画布为 1920×1080，文字检查阈值按项目政策填写。
