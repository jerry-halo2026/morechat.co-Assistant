# RC-xx · <作品名> <集数>：<一句话说这段值得学什么>

## 来源

| 项 | 内容 |
|---|---|
| 作品 | |
| 片段 | 录屏覆盖范围；分析窗口 |
| 录屏 | 文件名、分辨率、帧率、时长；画面是否完整、有无控件和弹幕 |
| SHA-256 | |
| 是否随包 | 否 |
| 事实来源 | 链接 |

## 方法

```bash
python3 -I scripts/analyze_clip.py structure <录屏> --out <目录> --start <S> --end <E> --sections "<分段>"
python3 -I scripts/analyze_clip.py textcards <录屏> --boxes measurements/boxes-<名字>.json --out <目录>
```

分段依据：<看片后怎么定的>。

## 结果

| 文件 | 内容 |
|---|---|
| `measurements/structure.json` | 镜头、转场、分段、色彩、音乐对齐 |
| `measurements/textcards-<名字>.json` | 每处字：紧框、字高、背景、对比、亮度差、出现 / 显示完整 / 消失时间 |

## 沉淀的方法

每条按结构卡格式：做法 / 实测（中位、范围、样本数） / 条件 / 借什么 / 不借什么 / 失效。写回的参考编号和结构卡：<XR-xx、MR-xx、SC-…>。

## 局限

<录屏还是原片；测不准的地方；哪些是目视标注；样本数；这段参考没覆盖的情况>
