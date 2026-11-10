# presets/ — 预设层（Preset layer）

本目录由 `scripts/build-presets.mjs` 从 `index.json` + `catalog/packages/**` 生成，**全部文件请勿手改**：
改了 `catalog/**` 或 `index.json` 之后运行 `node scripts/build-presets.mjs` 重新生成，
`node scripts/build-presets.mjs --check` 用于在 CI 中确认预设层没有漂移。

每个包（39 个：34 agent + 5 team）产出两份文件，供两个消费方使用：

| 文件 | 消费方 | 用途 |
|---|---|---|
| `presets/<kind>/<id>.preset.json` | Multica 侧「预设画廊」 | 白名单字段的展示与组合描述 |
| `presets/<kind>/<id>.cordis.yml` | DSH 侧 `@deepseek-ai/dsh-agent-preset` | Cordis patch 片段：人设/指令注入、skills 目录挂载、timed `ask_user_question` |

## preset.json 字段（白名单）

`schemaVersion` `id` `kind` `name{zh,en}` `description` `personaPath` `skills[]`
`conversationStarters[]` `team{leadAgent,members[]}` `requires[]` `sourcePackage`
`packageVersion` `contentSha256`

- `conversationStarters` 至多 3 条：取 `plugin.json` 的 `quickPrompts[].zh` 前 3 条，
  缺失时退回 `defaultInitPrompt.zh`，再缺失为空数组。
- `contentSha256` 是该包目录的 treeSha256，与 `index.json` 的 `sha256` 完全一致。
- **不包含任何模型、供应商、密钥或权限字段**（`model` / `provider` / `apiKey` / `secret` /
  `token` / `permission` / `role`）：这些属于宿主 profile，预设只描述内容与组合。
  门禁 G7 会拒绝上述字段出现，也会拒绝模型名与凭证形状的字面量。

## cordis.yml 形态

以 `@deepseek-ai/dsh-web-app/presets/standard.patch.yml` 为骨架，单个
`@deepseek-ai/dsh-agent-preset` 声明，`config.plugins` 至少包含：

- `persona`（`@deepseek-ai/dsh-persona`）：人设前缀指向该包的 `agents/*.md`，要求先读取再作答；
- `agent-instructions`（`@deepseek-ai/dsh-agent-instructions`）：工作区指令链，`maxBytes: 65536`；
- `skill-filesystem`（`@deepseek-ai/dsh-skill-filesystem`）：`customSkillDirs` 挂载
  `catalog/packages/<kind>/<id>/skills`（该包无 skills 时为 `[]`）；
- `tool-skill`、`tool-ask-user`（`mode: timed`、`timeout: 120`）。

文件内相对路径以本仓根目录（含 `catalog/`、`presets/` 的检出目录）为基准。
