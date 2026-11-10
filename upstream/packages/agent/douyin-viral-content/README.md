# 抖音爆款内容制造专家

从热点发现到安全出稿，全自动闭环生产爆款内容。

## 类型

Agent 型（单个 AI 专家）

## 功能

四段爆款生产线，一键闭环：

1. **热点捕捉**：热榜神器 + 实时作品搜索 + AI 信息源，三维扫描当下最热话题与内容形态
2. **爆款对标**：每日常驻作品榜 + 七日点赞飙升榜，锁定「正在涨」的爆款样本
3. **文案复刻**：复刻蒸馏写作 + 违禁词检测，拆解爆款逻辑生成仿写脚本，发布前自动扫雷
4. **效果验证**：每日点藏飙升榜，追踪发布后是否进入飙升榜单

内置 8 个专项技能：`douyin-hot-trend`、`douyin-search`、`douyin-ai-feed`、`douyin-daily-hot`、`douyin-weekly-surge`、`multi-copywrite-alchemy`、`douyin-prohibited-word`、`douyin-content-surge`。

## 使用示例

- 帮我从热点捕捉开始，走完爆款对标、文案复刻、违禁词扫雷的全流程，产出一条可直接发布的抖音爆款文案。
- 扫描当下抖音最热话题，找出适合我赛道的爆款选题和内容形态。
- 追踪我发布的抖音作品，看它是否进入每日点藏飙升榜。

## 前置条件

- 需配置环境变量 `REDFOX_API_KEY`（红狐hub API Key，前往 https://redfox.hk/settings/api-keys 获取）
- Python 3.x + `requests` 库

## 头像

头像已自动生成在 `avatars/` 目录下。如需替换为自定义头像，要求：
- 格式：PNG（推荐）或 JPG
- 尺寸：512×512 px
- 大小：单张不超过 500KB

## 安装

将专家包目录放到专家目录下：

```
C:\Users\马祯\.workbuddy\plugins\marketplaces\my-experts\plugins/douyin-viral-content/
```

然后运行注册命令使其可见：

```bash
python3 scripts/register_expert.py <expert-dir>
```

## 打包分享

```bash
zip -r douyin-viral-content.zip douyin-viral-content/
```
