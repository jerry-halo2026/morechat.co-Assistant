---
name: rea-analysis
description: REA (Reverse Engineer Anything) 工具链操作技能。提供环境安装与自检、多目标类型分析命令、证据输出解读、授权确认与免责声明模板。供逆向功能分析专家在分析闭源软件功能时使用。
---

# REA 逆向分析技能

本技能封装 REA（Reverse Engineer Anything，https://github.com/morluto/rea ，MIT 协议）的使用方法。REA 是 MCP Server + CLI，本身不做逆向，而是驱动 Ghidra、Hopper、IDA Pro、JADX、Frida 等专业工具，为 AI Agent 提供带证据的软件分析能力。

## 使用前提（不可跳过）

1. 已完成专家层定义的**授权与用途三问确认**，用户已接受免责声明。
2. 使用 templates/authorization-and-disclaimer.md 中的标准话术。

## 资源索引

| 文件 | 内容 | 何时读 |
|------|------|--------|
| [references/rea-setup-guide.md](references/rea-setup-guide.md) | 安装、引擎配置、doctor 诊断、已知问题（含 Windows 安全软件冲突） | 用户环境未就绪或报错时 |
| [references/rea-command-catalog.md](references/rea-command-catalog.md) | 按目标类型分类的核心命令表 | 选择分析命令时 |
| [references/sample-output-notes.md](references/sample-output-notes.md) | 真实分析输出的结构与解读要点 | 首次解读 Evidence JSON 时 |
| [templates/authorization-and-disclaimer.md](templates/authorization-and-disclaimer.md) | 授权确认话术 + 免责声明全文 | 每次会话开始时 |

## 快速路径

```bash
# 环境自检
npx rea doctor --json

# JS/Electron 静态分析（无需任何引擎，最安全）
npx rea analyze-javascript-application "目标应用的绝对路径" --json

# 网站分析
npx rea analyze-web-bundle --url "https://example.com" --json
```

输出遵循 Evidence 契约：每条结论附 `evidence`（证据位置与哈希）、`limitations`（局限声明）、`unknowns`（未知项）。解读方法见 sample-output-notes.md。
