# REA 安装与环境配置指南

## 环境要求

- **Node.js 22+**（必需，`node --version` 检查）
- 原生二进制分析另需其一：Ghidra 12.1.x（开源，需 64 位 JDK 21）/ Hopper（商业，可演示模式）/ IDA Pro（商业）
- JS/Electron、.NET 静态分析**无需任何引擎**

## 安装

```bash
# 方式一：项目内本地安装（推荐，避免全局污染）
mkdir rea-workspace && cd rea-workspace
npm init -y && npm install rea-agents

# 验证
npx rea --version

# 方式二：接入 AI Agent（会写入各客户端 MCP 配置，安装前会展示变更并备份）
npx rea-agents setup
```

## 原生分析引擎配置（仅二进制/APK/固件分析需要）

| 引擎 | 配置方式 |
|------|---------|
| Ghidra | 解压 Ghidra 12.1.x 后设置环境变量 `GHIDRA_INSTALL_DIR` 指向其目录 |
| Hopper | `rea setup` 可经用户同意后代装，或设置 `HOPPER_LAUNCHER_PATH` |
| IDA | 设置 `REA_IDA_MCP_CONFIG` 指向 IDA MCP 注册 JSON |
| JADX（APK） | REA 4.1+ 内置支持路径，按提示安装 |

## 自检与排障

```bash
npx rea doctor --json          # 全量审计
npx rea doctor --skill --json  # 只查技能
npx rea doctor --provider ghidra --json  # 只查单个引擎
```

`healthy: false` 不代表当前任务不可用——按 scope_checks 逐项看，只修与本次目标相关的项。

## 已知问题（实测记录，2026-10）

### Windows + 360 主动防御冲突

**现象**：JS 静态分析报
`REA Windows native controls are unavailable: Delete owned object by handle failed [...rea-native-probe-xxx] (Win32 5): 拒绝访问`

**根因**：REA 的 Windows 原生模块（rea-windows-x64.node）初始化时自检"创建带私有 DACL 的目录 → 按句柄删除"，360 主动防御（ZhuDongFangYu.exe）拦截该非常规删除语义。普通 rmdir 正常，可作对照。

**影响**：分析不中断——文件清单、SHA-256 证据链、应用图谱骨架正常输出；仅深层语义关系抽取（调用流/数据流等 12 个 family）降级为 `incomplete-module`。

**解决**：将 REA 安装目录与 Node.js 可执行文件加入 360 信任区（或临时退出主动防御）后重试。无 360 的机器上能力完整。

**技术定位参考**：探针逻辑在 `node_modules/rea-agents/dist/windows/WindowsNativeLoader.js`，失败时 Graceful degradation，不崩溃。

### 其他限制

- 超大目标（如 24MB+ ASAR）可能报 `RangeError: Invalid string length` 或输出不可读——缩小分析范围。
- Windows 上的 Ghidra 集成为实验性（只读）。
- 运行时捕获以用户权限运行目标程序，**不是沙箱**。
