# REA 逆向功能分析专家（rea-reverse-engineer）

基于 REA（Reverse Engineer Anything）工具链的软件逆向功能分析专家：在无源码前提下分析软件功能实现，输出证据链说明与功能重建方案。

## 类型

Agent 型（单个 AI 专家）

## 功能

- **无源码功能分析**：定位并追踪软件功能（Electron 应用、网站、.NET、原生二进制、APK、固件）的内部实现路径
- **证据链输出**：每条结论附证据位置与 SHA-256 哈希，明确区分"已证实"与"静态推断"
- **功能重建**：在用户自己的技术栈中重建同类功能并设计验证用例
- **合规护栏**：会话开始强制执行授权与用途三问确认 + 免责声明，拒绝破解/克隆/绕过授权类请求
- **环境自检**：`rea doctor` 诊断与安装引导，含 Windows 安全软件冲突的已知问题处置

依赖工具：REA（morluto/rea，MIT，Node.js 22+）；原生二进制分析需用户自装 Ghidra/Hopper/IDA。

## 使用示例

- "我想分析一个软件的功能是怎么实现的，请先帮我做授权与用途确认"
- "我想在自己的项目里重建某个应用的类似功能，帮我规划逆向调查流程"
- "检查我的 REA 环境是否就绪，并推荐合适的分析方法"

## 头像

头像不随本内容仓分发（`avatars/` 已移除），由产品端生成（grok 引擎）。

## 安装 / Installation

本包由 **morechat.co-Assistant** 内容仓分发，**通过 morechat.co-Assistant 目录导入**：

1. 在 morechat.co-Assistant 仓中取出 `catalog/packages/<kind>/<id>/`；
2. 该目录即包根目录，内含 `plugin.json`、`agents/`、`skills/`，整体作为包目录导入；
3. 导入后由平台注册 Agent / Squad 与技能，无需额外安装脚本或注册命令；
4. 头像不在仓内分发（`avatars/` 已移除），由产品端生成。