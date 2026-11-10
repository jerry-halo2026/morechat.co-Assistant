# TikTok Ops Expert（TikTok运营实战专家）

TikTok 直播教程 + 全套运营干货 + 变现实操的 Agent 型专家：从账号定位、短视频爆款、
算法流量，到直播 SOP 与话术、TikTok Shop 带货、七条变现路径和数据诊断复盘。

## 类型

Agent 型（单个 AI 专家）—— 罗凯 Kai Luo，8 年出海短视频操盘手人设。

## 功能

- **直播教程**：权限开通、三档设备清单、开播 SOP、留人/过款/逼单话术框架、复盘指标
- **运营干货**：账号定位决策树、黄金 3 秒钩子公式、带货视频万能结构、流量池诊断树
- **变现实操**：联盟带货/直播打赏/Creator Rewards/自营店铺/商单/私域/知识付费全路径对比与落地
- **数据诊断**：播放量卡层级诊断、流量结构健康度、周报/复盘模板
- **避坑合规**：封号限流原因、内容红线、音乐版权、电商合规、割韭菜识别

知识库位于 `skills/tiktok-growth-playbook/references/`（8 份分册）。

## 使用示例

- 我想做 TikTok 带货，从 0 开始帮我规划账号定位、起号节奏和变现路径
- 帮我写一份 TikTok 直播全流程 SOP：设备清单、开播步骤、话术框架和复盘表
- 我的 TikTok 视频播放量卡在 500，帮我诊断原因并给出突破方案

## 头像

头像已自动生成在 `avatars/` 目录下。如需替换为自定义头像，要求：
- 格式：PNG（推荐）或 JPG
- 尺寸：512×512 px
- 大小：单张不超过 500KB

## 安装

将专家包目录放到专家目录下：

```
~/.workbuddy/plugins/marketplaces/my-experts/plugins/tiktok-growth-expert/
```

然后运行注册命令使其可见：

```bash
python3 scripts/register_expert.py <expert-dir>
```

## 打包分享

```bash
python3 scripts/package_expert.py <expert-dir> <output-dir>
```
