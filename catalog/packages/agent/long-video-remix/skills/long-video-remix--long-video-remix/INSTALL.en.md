# Install and upgrade · v1.5.1-public-methodology-clean

The public edition contains reusable methods, templates and validators. It uses project schema 1.9 and workflow_control 1.3 / required_v4. See [validation](QA.md).

## Install the complete ZIP

1. Extract the complete `long-video-remix/` folder, retaining SKILL.md, references, assets, scripts, tests, examples, agents and visual-reference.
2. Use the execution tool's configured local skills directory: `~/.claude/skills/` for Claude Code or `~/.agents/skills/` for Codex.
3. Back up an existing installation and replace the whole folder. Keep project media and production data in a separate project directory.
4. Supply the source media for each project and keep it outside the installation folder.

## Runtime and visual rules

Static validation needs Python. Native rendering needs the actual registered Blender toolchain; delivery/media validation needs FFmpeg/ffprobe. Those executables are not bundled. Missing or untested capabilities remain unavailable/unverified.

Use `visual-reference/visual-reference-package-v2.4.3/` for formal V0–V7. Complete V1 facts/direction before V2 references, then V3 Art Direction, V4 mockups, V5 review, the real V6 user decision and V7 lock before Implementation Lock / Proof. Exploration needs multiple candidates; confirmed reuse needs real prior evidence. Small-screen remains required; blur/blind review is conditional.

The initial reference catalog is empty. Record how current project evidence addresses each V1 problem in V2 `no_ref_needed`. New styles require representative same-source A/B in V5. See the [Router](references/visual-reference-router.md).

## Local revisions

The existing method decision establishes a preservation baseline. Apply Narrative-backed named slots with `workflow_control.py adapt PROJECT --patch PATCH.json`; unspecified values and the method stay fixed. Existing Step 0 permissions remain effective. See [method preservation](references/workflow-control.md#方法保持与叙事参数补丁) for bindings, recovery and explicit method changes. Project baselines are project data, not installation assets.

## Verify

```sh
python -m unittest discover -s tests -v
```

Verify both SHA256SUMS files from their respective directories. The full visual suite requires Pillow, NumPy, FFmpeg, and ffprobe. Set `BLENDER_EXECUTABLE` to the Blender executable to run render integration tests. Tests generate their media in temporary directories.

## Project fallback and handoff

PROJECT_INSTRUCTIONS.txt and CHAT_PROJECT_REFERENCE.md are the current fallback files; the reference includes the formal visual-design-procedure.md and omits release history. Placing them in the ZIP does not update an existing Project automatically.

Before each forward major-stage advance, regenerate handoff.md with workflow_control.py handoff. Detail also retains execution-handoff.md. Carry artifact SHA, source signatures/time mapping, real decisions and pending/stale items.

For non-parameter content edits, use revise, inspect the diff, and bind the actual plan confirmation. See [scoped revisions](references/workflow-control.md#有范围的内容修订).
