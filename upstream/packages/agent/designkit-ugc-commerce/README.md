# 真人口播专家

根据商品素材完成UGC口播带货AI视频创作，从购买理由、真人感口播脚本、镜头到成片，适配产品种草与广告投放。美图设计室提供。

## 类型

Agent 型（单个 AI 专家）

## 功能

通过内置 `ugc-commerce` Skill 调用 美图设计室 AI设计 CLI，读取标准表单、补齐必要输入、处理生成任务事件，并直接交付最终产物。

## 使用示例

- 为这个商品制作一支 TikTok UGC 真人口播带货视频。
- 把这些卖点做成自然真实的达人口播视频。
- 用这些商品图生成一支转化导向的 UGC 带货视频。

## 头像

头像已自动生成在 `avatars/` 目录下。如需替换为自定义头像，要求：

- 格式：PNG（推荐）或 JPG
- 尺寸：512×512 px
- 大小：单张不超过 500KB

## 安装

可在 WorkBuddy 专家中心导入 ZIP，或将专家目录放入：

```text
$WORKBUDDY_CONFIG_DIR/plugins/marketplaces/my-experts/plugins/
```

未设置 `WORKBUDDY_CONFIG_DIR` 时，默认根目录为 `~/.workbuddy`。放置后使用 WorkBuddy 内置 `expert-manager` 校验并注册。

## 运行要求

- 实际终端命令为 `designkit`；只用 `--version` 确认命令可执行，不解析或比较版本号。
- 未发现 `designkit` 或命令不可执行时，Agent 自动执行一次 `npm install -g meitu-designkit-cli`，由 npm 安装当前稳定最新版。只有安装失败或安装后仍无法执行 `designkit` 时，才引导用户打开「专家·技能·连接器」并进入「连接器」，搜索并连接「美图设计室 AI设计 CLI」。
- 登录状态统一保存在 `~/.designkit`，专家包不内置 CLI 或用户凭证。

## 打包分享

使用 WorkBuddy 内置 `expert-manager` 的 `package_expert.py` 生成可安装 ZIP。
