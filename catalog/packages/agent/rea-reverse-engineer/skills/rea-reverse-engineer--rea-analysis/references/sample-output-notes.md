# Evidence 输出结构与解读要点（基于 6.4.0 实测）

以下为一个 Electron 测试应用（主进程剪贴板桥 + Express/JWT 后端）经
`npx rea analyze-javascript-application "目标路径" --json` 的输出结构提炼。

## 顶层结构

```
rea_progress[]        进度事件（inventory → read → parse → ...）
error?                仅当整体失败；注意 Graceful degradation 时无 error 但有 partial
partial_observation   部分失败时仍有价值的观察（重点看这里）
```

## partial_observation 内的关键字段

| 字段 | 含义 | 解读 |
|------|------|------|
| `subject.digest.sha256` | 目标根制品哈希 | 记录到报告的"证据清单"，保证可复现 |
| `normalized_result.inventory_*` | 文件清单清单 ID 与图谱哈希 | 溯源基准 |
| `normalized_result.graph.nodes[]` | 应用图谱节点 | `kind: artifact/unknown`；每个节点含 observations |
| `observations[].properties.limitation` | 该节点分析被中断/受限的原因 | **必须转述给用户** |
| `normalized_result.jsrg(语义图)` | 12 个关系 family：call-flow、data-flow、boundary、request、child-process、promise-ownership、event、timer、resource-lifecycle、configuration、closure、object-flow | `retained_relations: 0` + `reason: incomplete-module` = 深层抽取降级 |
| `limitations[]` | 全局局限声明 | 每条都要进最终报告 |
| `coverage.status` | `complete` / `partial` | partial 时缺的是"显式未知" |

## 判读三步法

1. **先看成败**：有无顶层 `error`；无 error 时看 `coverage.status`。
2. **再看证据链**：`subject.digest` + `inventory_manifest_id` + 各 observation 的 `artifact.sha256` 与 `location.path` —— 这些构成可复现的证据。
3. **最后看语义**：jsrg 各 family 的 `retained_relations` > 0 才有实质关系抽取；若全为 0 且 detail 里是探针失败（如 Windows 原生控件不可用），按 setup-guide 的"360 冲突"节处理或降级汇报。

## 给用户的报告模板

```markdown
## 功能解释
（该功能由哪些模块/调用路径/数据流实现，通俗+技术双层描述）

## 证据清单
| 证据 | 位置 | SHA-256 |
|------|------|---------|
| 主进程入口 | src/main.js | 9c8d... |
| 根制品 | artifact-root | fb3f... |

## 局限与未知
（原样转述 limitations[] 中与本次分析相关的条目 + unknowns）

## 重建建议
（在用户技术栈中的实现方案 + 验证用例设计）
```
