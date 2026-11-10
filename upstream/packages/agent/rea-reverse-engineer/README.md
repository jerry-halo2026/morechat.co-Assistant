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

头像已自动生成在 `avatars/` 目录下。如需替换为自定义头像，要求：
- 格式：PNG（推荐）或 JPG
- 尺寸：512×512 px
- 大小：单张不超过 500KB

## 安装

将专家包目录放到专家目录下：

```
C:\Users\mdit-lu\.workbuddy\plugins\marketplaces\my-experts\plugins/rea-reverse-engineer/
```

然后运行注册命令使其可见：

```bash
python3 scripts/register_expert.py <expert-dir>
```

## 打包分享

```bash
zip -r rea-reverse-engineer.zip rea-reverse-engineer/
```
