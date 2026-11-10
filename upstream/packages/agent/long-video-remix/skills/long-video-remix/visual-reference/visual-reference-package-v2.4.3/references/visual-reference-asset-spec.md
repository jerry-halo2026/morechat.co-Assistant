# Visual Reference Asset Spec

适用：`long-video-remix` 的 `Visual Reference Library`

## 1. 核心原则：图片本身不加任何说明层

所有第三方 Reference 图片必须尽量保持原始设计画面。

**禁止在图片上新增：**
- Reference only
- 案例编号
- 来源名称
- “不要照搬”
- 箭头、红框、标注线
- 解释性文字
- 我方 Logo / 水印
- 分类标签
- 色值说明
- 字体名称说明

原因：这些新增元素会成为 AI 视觉输入的一部分，可能被错误学习为目标风格。

### 允许保留
- 第三方作品原本就存在于画面中的标题、字幕、Logo、图形、文字；
- 原设计项目本身的 Style Frame / Subtitle Guide 中原生存在的标识；
- 原截图中不可避免但不干扰设计判断的少量内容。

如果网页 UI、浏览器栏、点赞按钮、作者头像、网页导航等不属于设计作品本身，应尽量裁掉。

---

## 2. 说明信息全部外置

每张图片的信息通过 MD / JSON 关联，不叠加到图片。

建议结构：

```text
assets/
└── reference-originals/
    ├── contemporary-editorial/
    │   ├── CE-01-01.webp
    │   ├── CE-01-02.webp
    │   └── ...
    ├── emotional/
    │   ├── EM-01-01.webp
    │   └── ...
    └── variety-witty/
        ├── VR-01-01.webp
        └── ...

references/
└── visual-reference-library.md

asset-manifest.json
```

MD / JSON 中记录：
- asset_id
- 项目名称
- 类别
- 原始来源 URL
- 设计方 / 平台（如已知）
- 参考重点
- 可迁移原则
- 不可照搬项
- 色彩方向
- 图片相对路径

---

## 3. 图片尺寸

目标：保证 AI 能看清字体、排版、边缘关系和图形细节，同时避免 4K 原图导致包体积和读取成本过高。

### 3.1 横向 Style Frame / 16:9 画面
**推荐：1600 × 900 px**

可接受：
- 1440 × 810
- 1600 × 900
- 1920 × 1080

默认优先 `1600 × 900`。

如果原图本身低于该尺寸，不做 AI 超分放大，不虚构细节；保留原尺寸。

### 3.2 4:3 / 3:2 / 杂志式画面
保持原始比例。

建议：
- 长边：1600 px 左右
- 最短不低于：1200 px（原图允许时）
- 一般不超过：2000 px 长边

### 3.3 竖版 / 海报 / 手机视觉
保持原始比例。

建议：
- 长边：1800–2000 px
- 短边：至少 1000–1200 px（原图允许时）

例如：
- 1080 × 1920
- 1200 × 1800
- 1350 × 1800

### 3.4 Subtitle Guide / 多组件设计板
这类图片文字和组件较密，应优先保证可读性。

建议：
- 长边 1800–2200 px
- 如果一张 Guide 过长，**宁可拆成 2–3 张连续截图**，不要把整页缩成一张看不清的小图。

推荐：
```text
VR-05-02a.webp
VR-05-02b.webp
VR-05-02c.webp
```

不要为了“一项目一张图”而压缩信息。

---

## 4. 图片格式

### 推荐默认：WebP
适合大多数第三方截图和 Style Frame。

建议：
- WebP quality：88–92
- 保持原尺寸，不二次反复压缩
- 适合照片 + 字体 + 图形混合内容

### PNG
适合：
- 纯图形
- 极细字体
- UI / Subtitle Guide
- 大面积纯色、锐利边缘较多
- WebP 压缩后文字边缘明显变糊的画面

### JPEG
只在原图本身就是 JPEG 且不需要进一步转换时保留。
不建议把文字很多的 PNG 强制转成低质量 JPEG。

---

## 5. 单图文件大小

建议目标：

- 普通 Style Frame：**250 KB – 1.2 MB**
- 信息密集 Guide：**500 KB – 2 MB**
- 极少数复杂大图：可到 2.5 MB 左右

一般不建议单张超过 3 MB。

原因：
- 22–35 张核心图时，整个 Reference Asset 包控制在约 **20–40 MB** 会比较合适；
- AI 读取时也不需要反复加载 4K / 8K 原图。

---

## 6. 截图裁切规则

### 应保留
- 原作品完整构图
- 字体与人物 / 图像的关系
- 图形元素的边界
- 必要的上下左右留白
- 原设计中的字幕 / Logo / 标签 / 动态截图关键状态

### 应裁掉
- 浏览器地址栏
- 播放平台或网页侧栏
- 点赞、评论、分享按钮
- 作者头像（除非属于作品画面）
- 页面标题、网页导航
- 与设计无关的空白区域
- 我方任何标记或注释

### 不要过度裁切
如果裁掉某个边缘后会破坏：
- 字体与画面的比例
- 留白关系
- 人物位置
- 图形系统的边界

则宁可多保留一点作品画布。

---

## 7. 一个项目保留几张

不要求“一项目一张”。

### 普通项目
建议 2–3 张：
1. Overall Style Frame
2. 文字 / 字幕落地
3. 另一种有代表性的构图或颜色状态

### 视觉系统完整的项目
建议 3–5 张：
1. Overall / Key Visual
2. Subtitle Guide
3. Layout Guide
4. Real Footage Integration
5. End Card / Title / Freeze Frame（如有价值）

### 不要重复
如果两张图表达的信息高度相同，只留更清晰、更典型的一张。

---

## 8. Contact Sheet 的使用

Contact Sheet 可以存在，但**不能替代核心原图**。

用途：
- 快速浏览
- 人工筛选
- AI 初步定位可能的方向

规则：
- Contact Sheet 单独放在 `assets/contact-sheets/`
- 不作为唯一 Reference
- 不在 Contact Sheet 上加入“好/坏”“推荐”等视觉标注
- 可仅用极小的编号作为索引时，也建议优先通过文件顺序和 MD 映射完成，避免编号成为视觉干扰

正式分析时，AI 应读取对应的单张原图。

---

## 9. 第三方设计的使用边界

这些图片是 **design reference / visual research**，不是复现目标。

可以学习：
- 信息层级
- 字体尺度关系
- 字与人物 / 画面的空间关系
- 色彩组织方式
- 图形组件密度
- 视觉节奏
- 留白与强调方式
- 不同信息等级如何区分

不得直接复制：
- Logo
- 品牌专属字形
- 完整版式
- 独特图标
- 特定装饰元素组合
- 相同人物画面
- 原文案
- 具体动画轨迹
- 具有明显识别度的完整视觉系统

AI 应当提取原则，再基于当前素材形成新的设计方案。

---

## 10. 默认推荐参数

如果没有特殊情况：

```yaml
default_asset:
  format: webp
  target_width: 1600
  target_height: preserve_aspect_ratio
  quality: 90
  max_long_edge: 2000
  preferred_file_size: "<= 1.2 MB"
  annotation_overlay: false
  preserve_original_design_text: true
  crop_web_ui: true
```

Subtitle / Layout Guide：

```yaml
guide_asset:
  format: png_or_webp
  max_long_edge: 2200
  split_if_unreadable: true
  annotation_overlay: false
```

---

## 11. 最终检查

每张图入库前确认：

- [ ] 没有新增我方说明文字
- [ ] 没有新增箭头 / 框 / 水印
- [ ] 网页 UI 已尽量裁掉
- [ ] 原作品构图没有被破坏
- [ ] 字体在正常查看尺寸下仍可辨识
- [ ] 图片没有因压缩出现明显文字糊边
- [ ] 色彩没有被错误转换
- [ ] 原始来源已写入 manifest
- [ ] 已写明“可学习什么”
- [ ] 已写明“不能照搬什么”
- [ ] 文件大小处于合理范围
