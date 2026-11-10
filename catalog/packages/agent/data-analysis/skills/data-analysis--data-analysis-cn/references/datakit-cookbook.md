# datakit 工具箱菜谱

零依赖纯标准库，Python 3.7+。所有命令加 `--json` 输出 JSON（供程序消费）；文本模式输出中文表格。

**编码说明**：读取自动探测 UTF-8 / GB18030（国内 Excel 导出的 GBK 直接读）；写出的 CSV 统一 UTF-8-BOM（Excel 双击打开不乱码）。

**数字格式**：认识千分位（`45,230`）、百分号（`12.5%`）、万/亿/w/k 后缀（`128万`、`1.2亿`）。

**日期格式**：`2026-01-15`、`2026/01/15`、`20260115`、`2026-01`、`2026-01-15 10:30:00` 都认。

---

## 1. profile — 数据画像

```bash
python datakit.py profile 销售.csv [--json]
```

**输出**：行列数、重复行、质量评分（A/B/C/D）、逐列画像——数值列给 min/中位/max/均值/标准差/3σ 异常计数，文本列给 top5 高频值，日期列给时间范围。

**实战解读**：
- 质量评分 D → 先清洗或补数据再分析
- `outliers_3sigma` 大 → 有异常值，分析前决定剔除还是单独研究
- 某列 unique = 1 → 常量列，删掉
- 日期列范围和分析窗口对不上 → 数据导错了

## 2. clean — 自动清洗（决策留痕）

```bash
python datakit.py clean 销售.csv [--out 干净.csv] [--drop-col-threshold 0.5]
```

**做的事**：单元格去空格 → 去完全重复行 → 删缺失率 >50% 的列 → 数值列中位数填充、文本列填「未知」→ 输出干净 CSV + 每条决策的留痕日志。

**纪律**：留痕日志必须附在报告附录，回答得了"你动了哪些数据"。

## 3. funnel — 漏斗分析

```bash
# 直接给数（最常用）
python datakit.py funnel --counts 100000,32000,15000,9800 --labels 浏览,加购,下单,支付

# 明细 CSV 里选 0/1 步骤列
python datakit.py funnel 用户行为.csv --steps 浏览,加购,下单,支付
```

**输出**：逐步转化率、累计转化率、瓶颈环节（相对流失最大）。

**实战**：瓶颈环节不要停在大数上——把瓶颈环节按渠道/新老客拆开再算一遍，往往只有某一撮人拖后腿。

## 4. cohort — 同期群留存矩阵

```bash
python datakit.py cohort 活跃明细.csv --id 用户ID --date 活跃日期
```

**输出**：按首现月份分群的 M+0, M+1, M+2… 留存矩阵（人数 + 百分比）。

**实战解读**：
- 竖看（同一群衰减）：跌得快是拉新质量差或新手引导烂；有平台期说明有核心粘性
- 横看（群与群对比）：新群比老群留得好 = 产品在进步
- 大促月份拉来的群单独标注（大促拉新留存天然差一截）

## 5. rfm — 用户八层分群

```bash
python datakit.py rfm 订单.csv --id 用户ID --date 订单日期 --amount 金额 --out 分层明细.csv
```

**输出**：八层（重要价值/重要发展/重要保持/重要挽留/一般×4）各层人数、占比、均 R/F/M、收入占比；`--out` 给逐用户分层明细。

**实战**：先盯两层——**重要保持**（曾高频高额但最近没来：召回 ROI 最高）和**重要价值**（基本盘，防流失）。明细 CSV 可直接交运营做触达名单。

## 6. abc — 帕累托分级

```bash
python datakit.py abc 销售.csv --dim 商品 --value 销售额 [--top 20]
```

**输出**：A（累计 80%）/B（80-95%）/C（95%+）分级表 + Top1/5/10 集中度。

**实战**：Top1 > 30% 预警单品依赖；C 类过"砍留清单"时记得给新品按上架天数归一化一次。

## 7. sig — 显著性检验与样本量

```bash
# 两比率（A/B 实验转化率对比）
python datakit.py sig --prop-a 0.052,1200 --prop-b 0.068,1200

# 两均值（客单价对比：均值,标准差,样本量）
python datakit.py sig --mean-a 152.3,35,500 --mean-b 148.1,32,480

# 开实验前算样本量
python datakit.py sig --sample-size --baseline 0.05 --mde 0.01
```

**输出**：z 值、p 值、是否显著（p<0.05）、中文裁决语。

**实战**：
- p ≥ 0.05 不是"没差异"，是"现有数据不能排除随机"——继续攒样本或认怂
- 显著了先看效应量：+0.01pp 显著但没用
- 均值检验 n<30 时输出会警告，结论降级为间接证据

---

## 典型作战链路

```bash
# 拿到一份经营数据的完整动线
python datakit.py profile 经营数据.csv --json      # ① 体检
python datakit.py clean 经营数据.csv               # ② 清洗留痕
python datakit.py abc 经营数据_clean.csv --dim 商品 --value 销售额   # ③ 结构
python datakit.py rfm 订单.csv --id 用户ID --date 日期 --amount 金额 --out rfm.csv  # ④ 用户
python datakit.py cohort 活跃.csv --id 用户ID --date 日期            # ⑤ 留存
python datakit.py funnel --counts 10万,3.2万,1.5万,9800 --labels 浏览,加购,下单,支付  # ⑥ 转化
```
