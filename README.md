# morechat.co-Assistant · 内容库

morechat.co（Multica）的**助手 / 小队 / 技能内容仓**：只放内容，不放客户端代码，不放头像图片。

- **39 个包**：34 个 Agent（单助手）+ 5 个 Squad（小队）
- **113 个技能**（`SKILL.md` 口径），跨包同名技能已命名空间化
- **977 个文件 / 14.28 MiB**（不含上游头像图，81 张 PNG 共 46.6 MB 未入库）
- 机器可读清单：[`index.json`](index.json)（schemaVersion 1）
- 逐字节上游快照：[`upstream/`](upstream)

---

## 1. 目录结构

```
.
├── catalog/
│   └── packages/
│       ├── agent/<id>/          # 34 个单助手包
│       │   ├── plugin.json      # 清单（上游原格式，仅替换运行期绑定字符串）
│       │   ├── README.md        # 说明（安装段已改写为「通过 morechat.co-Assistant 目录导入」）
│       │   ├── agents/*.md      # 助手提示词 / 工作流
│       │   ├── skills/<pkg>--<skill>/   # 技能目录（物理名 = 命名空间）
│       │   └── references|assets|rules/**   # 随包参考资料（如有）
│       └── team/<id>/           # 5 个小队包（多 agents + 多 skills）
├── upstream/                    # 上游原文快照，供溯源比对（无头像）
├── index.json                   # 目录索引（包/技能/依赖/哈希）
├── scripts/
│   ├── build-catalog.mjs        # 转换器：D:/dev/bot -> catalog/ + upstream/ + index.json
│   └── check-portability.mjs    # 硬门禁（G1–G5）
└── .github/workflows/validate.yml
```

## 2. Multica 如何加载

1. **整包导入**：把 `catalog/packages/<kind>/<id>/` 作为包根目录交给 Multica 导入 —— `plugin.json` 建 Agent/Squad，`agents/` 建角色，`skills/` 注册技能。
2. **索引消费**：列表页/检索/版本对比读 `index.json`；`path` 字段相对 `catalog/`，`sha256` 用于导入前校验与增量同步。
3. **小队装配**：`kind: "team"` 的条目带 `leadAgent` 与 `members[]`；编排由 leader 建 Multica Squad、以 `@成员` 派发子任务。
4. **依赖提示**：`requires` 由包内文件类型推断，`python`（含 `.py`）、`node`（含 `.mjs`）、`canvas`（含 `.ttf` 字体，技能侧画布渲染）；运行时按此预置环境。
5. **技能挂载**：技能以物理目录名 `<pkg>--<skill>` 作为唯一 `ns` 挂载，避免跨包同名冲突。

## 3. 包格式

`plugin.json`（上游字段全保留）：`name` / `version` / `description` / `displayName{zh,en}` / `profession{zh,en}` / `displayDescription` / `categoryId` / `tags` / `skills[]` / `agents[]`；小队另有 `teamInfo{leadAgent,memberAgents}`、`members[]`。
`avatar` 字段保留为元数据，**不随包分发**（见第 6 节）。

### 技能 frontmatter 约定（DSH / Multica 运行时）

工具声明键统一为 `allowed-tools-dsh`（原 `allowed-tools`），映射：

| 上游工具 | 仓内写法 |
|---|---|
| `Read` `Write` `Edit` `Bash` `Glob` `Grep` `WebSearch` | 同名保留 |
| `Task` | `subagent` |
| `AskUserQuestion` | `ask_user_question` |

正文中的运行期动作改写为：

| 上游写法 | 仓内写法 |
|---|---|
| `AskUserQuestion` / `ask_user` | 使用 dsh-tool-ask-user（ask_user_question）向用户提问；若运行时无该能力，改为在任务评论中提问并等待 |
| `present_files` / `WorkBuddy 产物` | 使用 dsh-tool-present 声明交付；在 Multica 中作为 Issue 附件提交 |
| `TeamCreate` | 创建 Multica Squad 并由 leader 通过 @ 派发子任务 |

## 4. 命名空间与重名技能

物理目录名 = index 里的 `ns` = `<pkg>--<skill>`。上游有 6 组跨包/包内重名：`research`、`research-deep`、`research-report`、`research-add-fields`、`research-add-items`、`fullstack-dev`。
同包内出现同名时，后出现者退回路径式命名以保持唯一，例如：

- `ai-engineer--research`（`skills/deep-research/research`）
- `ai-engineer--deep-research-research-en-research`（`skills/deep-research/research-en/research`）

`index.json` 中 `skills[].name` 仍保留上游原始名，`ns` 为物理目录名。

## 5. index.json（schemaVersion 1）

```jsonc
{
  "schemaVersion": 1,
  "packages": [{
    "id": "opc-team", "kind": "team",
    "name": { "zh": "…", "en": "…" },
    "profession": { "zh": "…", "en": "…" },
    "description": "…", "descriptionZh": "…", "version": "1.0.0",
    "path": "packages/team/opc-team",
    "files": 42, "bytes": 118351,
    "sha256": "…",                       // 目录内全部文件按相对路径排序后滚动哈希
    "skills": [{ "name": "opc-orchestrator", "ns": "opc-team--opc-orchestrator",
                 "path": "skills/opc-team--opc-orchestrator",
                 "files": 4, "bytes": 12345, "sha256": "…" }],
    "requires": ["python"], "tags": [{ "zh": "…", "en": "…" }],
    "categoryId": "12-IndustryConsultant",
    "leadAgent": "opc-team-lead", "members": [{ "id": "…", "name": {}, "profession": {}, "role": "lead" }]
  }]
}
```

**哈希算法**：对目录内文件按相对路径升序，逐个喂入 `utf8(relPath)` + `0x00` + 文件字节 + `0x00`，输出 sha256 十六进制。`check-portability.mjs` 用同一算法复算，任何字节改动都会导致 G4 失败。

文件按**源字节**入库：`.gitattributes` 用 `* -text` 关闭 EOL 转换（含系统级 `core.autocrlf` 的影响），任何平台 checkout 都得到同一份字节，因此 `sha256` 跨平台可比。

## 6. 不含头像、不含客户端代码

- 上游 `avatars/` 目录**一律不拷贝**（81 张 PNG / 46.6 MB）；头像由产品端生成（grok 引擎）。
- 门禁 G2 断言 `catalog/**` 内既无 `avatars/` 目录，也无任何 PNG/JPEG/GIF/WebP 图片文件。
- 本仓只有内容：无 Electron/前端/服务端代码，无构建产物，无密钥。

## 7. upstream/ 溯源

`upstream/packages/<kind>/<id>/` 保存上游原文（`plugin.json`、`agents/**`、`skills/**`、`README.md`、`references/**` 等，**不含头像**）。差异只在于：`upstream/` 保留上游运行期绑定字符串与上游安装说明，`catalog/` 已改写。两者可 `diff` 出全部转换点。

`catalog` 的 `plugin.json` 保持上游字段顺序、缩进与换行，仅把禁止的运行期字符串就地替换（`WorkBuddy`/`CodeBuddy` → `Multica`），其余字节未动；未改动的原文在 `upstream/packages/<kind>/<id>/plugin/plugin.json`（`.codebuddy-plugin/plugin.json` 的副本）。

## 8. 门禁与 CI

```bash
node scripts/check-portability.mjs
```

| 门禁 | 内容 |
|---|---|
| G1 | `catalog/**` 中 `WorkBuddy\|CodeBuddy\|workbuddy\|codebuddy\|\.workbuddy\|WORKBUDDY_CONFIG_DIR\|expert-manager\|package_expert\|present_files` 命中数必须为 **0** |
| G2 | 不得存在 `avatars/` 目录与图片文件 |
| G3 | 单文件 ≤ 1 MiB、单技能 ≤ 8 MiB / 512 文件、单包 ≤ 16 MiB |
| G4 | `index.json` 结构与逐包/逐技能 `sha256`、`bytes`、文件数复算一致 |
| G5 | 全部文本文件严格 UTF-8、全部 `.json` 可解析 |

CI：[`validate.yml`](.github/workflows/validate.yml) 在每次 push / PR 运行同一脚本，G4 即“index.json 的 sha256 校验”。

## 9. 本地重建

仅用 Node 内置模块，无第三方依赖：

```bash
node scripts/build-catalog.mjs --src D:/dev/bot --root .
node scripts/check-portability.mjs
```

## 10. 规模

| 指标 | 数值 |
|---|---|
| 包 | 39（34 agent / 5 team） |
| 技能 | 113（107 唯一名，6 组重名已命名空间化） |
| 文件 | 977 |
| catalog 体积 | 14.28 MiB |
| upstream 体积 | 14.37 MiB |
| 转换前源树 | 1104 文件 / 61.69 MB（含 81 张头像 PNG 46.6 MB） |
| 最大单包 | `agent/backend-architect` 5.56 MiB / 112 文件 |
| 最大单技能 | `backend-architect--frontend-dev` 98 文件 / 5.42 MiB |

## 11. 许可

各包沿用其上游 `license` 字段与随包 `LICENSE` / `LICENSE-NOTE.md`（MIT、CC-BY-NC-SA-4.0 等），本仓不另设统一许可证，也不改写上游许可文本。

## 12. 生成

由 `scripts/build-catalog.mjs` 从源库 `D:/dev/bot` 生成，`index.json` 的 `generatedAt` 为生成时间戳；重新生成后重新提交即可。
