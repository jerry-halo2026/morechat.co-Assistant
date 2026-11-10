# REA 核心命令目录（按目标类型）

> 完整目录以 `npx rea --help` 为准（6.4.0 有 60+ 命令）。全部加 `--json` 获得结构化 Evidence 输出。

## 0. 通用

| 命令 | 用途 |
|------|------|
| `npx rea doctor --json` | 环境自检 |
| `npx rea capabilities --json` | 列出当前可用的分析能力及副作用 |
| `npx rea analyze --json "路径"` | 目标概览（自动识别类型） |
| `npx rea compare --json A.json B.json` | 比较两份 Evidence |

## 1. JavaScript / Electron 应用（首选，纯静态无引擎）

| 命令 | 用途 |
|------|------|
| `analyze-javascript-application "路径" --json` | 全应用静态重建：模块、导入、入口、进程间通信、路由 |
| `compare-application-versions --json v1 v2` | 比较两个版本的应用图谱 |
| `compare-javascript-export-shots --json` | 比较导出返回形状（不执行代码） |

典型场景：Electron 应用的剪贴板/IPC/预加载桥分析（参考官方 Notion 案例）。

## 2. 网站

| 命令 | 用途 |
|------|------|
| `analyze-web-bundle --json` | 捕获并静态分析页面 bundle |
| `capture-web-screenshot --json` | 页面视口截图（限定 origin 范围内） |
| `capture-browser-scenario --json` | 运行一个有界 Playwright 场景并返回 Evidence |
| `export-web-scripts --json` | 导出网站脚本供静态分析 |
| `discover-webmcp-tools --json` | 被动发现页面声明的 WebMCP 工具 |

## 3. 原生二进制（需 Ghidra/Hopper/IDA）

| 命令 | 用途 |
|------|------|
| `analyze "路径" --json` | 二进制概览 |
| `decompile "路径" --json` | 读取部分内容为伪代码/汇编 |
| `address-to-file-offset --json` | 分析地址 → 文件字节偏移 |
| `demangle-swift --json` | Swift 符号还原（无需 Hopper） |

官方案例：DX-Ball 声道声像计算重建，3,205 个原始 x86 用例全部通过、63 个函数字节完全复现。

## 4. .NET 程序集（静态，无引擎）

- 元数据、IL 指令、声明的原生依赖检查；`compare-managed-members` 按类型/名称/签名比较成员清单。

## 5. Android / 固件

| 命令 | 用途 | 依赖 |
|------|------|------|
| `decode-android-resources --json` | APK 清单/元数据/字符串资源 | apktool（JADX 路径由 REA 4.1+ 支持） |
| `extract-firmware --json` | 固件提取与来源验证 | Binwalk/Unblob |
| `extract-artifact --json` | 安全提取制品内容 | — |
| `capture-adb-screen --json` | 设备截屏（PNG） | adb |
| `collect-adb-bugreport --json` | 设备 bugreport 收集 | adb |

## 6. 运行时捕获（⚠️ 高风险，须单独确认 + 建议虚拟机）

| 命令 | 风险点 |
|------|--------|
| `capture-process --json` | 以**用户权限**实际运行目标进程，不是沙箱 |
| `capture-native-ui-scenario --json` | 观察原生窗口场景 |
| `capture-electron-scenario --json` | 运行自有 Electron 场景 |

## 输出解读铁律

1. 每条结论必须能对应 `evidence`（含 sha256、artifact-path）。
2. `limitations` 与 `unknowns` 必须原样转述给用户，不得隐去。
3. 静态图谱是"保守的语法观察 + 候选关系"，**不证明运行时行为**。
4. 覆盖状态为 `partial` 时，缺失部分是"显式未知"，不是"不存在"。
