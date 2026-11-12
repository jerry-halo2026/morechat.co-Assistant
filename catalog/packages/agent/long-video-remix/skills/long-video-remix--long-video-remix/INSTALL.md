# 安装与更新 · v1.5.1-public-methodology-clean

公开版包含方法、模板和检查器。项目 schema 为 1.9，workflow_control 为 1.3 / required_v4。当前验证见 [QA](QA.md)。

## 安装完整 ZIP

1. 解压得到 `long-video-remix/`；保留 SKILL.md、references、assets、scripts、tests、examples、agents 和 visual-reference 全部目录。
2. 将完整文件夹放入执行工具的本地技能目录：Claude Code 为 `~/.claude/skills/`，Codex 为 `~/.agents/skills/`；按实际工具已配置的技能目录安装。
3. 更新已有副本时，先备份，再替换完整文件夹。视频项目、源媒体与制作数据放在独立项目目录。
4. 使用时自行提供当前项目的源素材，项目数据和媒体放在安装目录之外。

## 当前制作与视觉规则

静态检查需 Python；正式渲染按已登记工具链运行。真实 Blender 渲染需 Blender，FFmpeg 回接/媒体核查需 FFmpeg/ffprobe；这些执行工具不打入 ZIP。未实测能力保持 unavailable/unverified，不代签完成。

正式 V0–V7 位于 `visual-reference/visual-reference-package-v2.4.3/`。V1 画面事实与方向初判 → V2 条件选择 → V3 Art Direction → V4 实图 → V5 比较 → V6 用户真实决定 → V7 锁定，再桥接 Implementation Lock / Proof。新风格才多案，复用需绑定既有真实确认；small-screen 保留，blur/blind 按条件使用。

参考目录初始为空。V2 用 `no_ref_needed` 逐项登记当前项目证据。新风格在 V5 做代表性同源 A/B。完整条件见 [Router](references/visual-reference-router.md)。

## 局部修订

现有 method 确认建立方法保持基线；Narrative 更新后使用 `workflow_control.py adapt PROJECT --patch PATCH.json`，仅修改已声明参数及绑定项。Step 0 仍服从原快照许可；中断恢复与方法变更入口见 [方法保持规程](references/workflow-control.md#方法保持与叙事参数补丁)。项目基线留在项目，不放入安装包。

## 验证

```sh
python -m unittest discover -s tests -v
```

分别在根目录和视觉方法目录核对各自的 SHA256SUMS。完整视觉回归需要 Pillow、NumPy、FFmpeg 和 ffprobe。设置 `BLENDER_EXECUTABLE` 为 Blender 可执行路径，可运行真实渲染集成测试。测试媒体在临时目录生成。

## 项目托底与阶段交接

PROJECT_INSTRUCTIONS.txt 用于更新长期项目说明；CHAT_PROJECT_REFERENCE.md 为同版可读参考，包含正式 visual-design-procedure.md，不携带版本更新历史。文件仅放在 ZIP 中不会自动替换现有 Project 文件。

每个大阶段结束运行 `python scripts/workflow_control.py handoff PROJECT --output handoff.md` 后再前向推进；Detail 另保留 execution-handoff.md。交接携带实际文件 SHA、源签名与时间映射，延续当前确认和 pending/stale 项。

非参数内容使用 revise，核对 diff 后绑定真实 plan 确认。细则见 [有范围的内容修订](references/workflow-control.md#有范围的内容修订)。
