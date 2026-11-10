#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
datakit.py — 零依赖数据分析工具箱（纯 Python 标准库）

子命令：
  profile   CSV 数据画像：类型/缺失/重复/分布/异常值/质量评分
  clean     自动清洗：去重/缺失处理/高缺失列删除，决策留痕
  funnel    漏斗分析：逐步转化率 + 瓶颈定位
  cohort    同期群留存矩阵
  rfm       RFM 八层用户分群
  abc       帕累托 ABC 分级 + 集中度
  sig       显著性检验（两比率/两均值）+ 样本量估算

所有子命令支持 --json（ASCII 安全输出）。CSV 读取自动探测编码
（utf-8-sig / gb18030），写出统一 utf-8-sig（Excel 友好）。
"""

import argparse
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta

MISSING_TOKENS = {"", "na", "n/a", "null", "none", "-", "--", "nan",
                  "无", "未知", "缺失", "不详"}
ENCODINGS = ("utf-8-sig", "gb18030", "utf-8")
DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d", "%Y-%m",
                "%Y/%m", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S")


# ---------------------------------------------------------------------------
# 通用基建
# ---------------------------------------------------------------------------

def read_csv_rows(path):
    """读 CSV，返回 (header, rows, encoding)。编码自动探测。"""
    last_err = None
    for enc in ENCODINGS:
        try:
            with open(path, encoding=enc, newline="") as f:
                rows = [r for r in csv.reader(f) if r]
            if not rows:
                raise ValueError("empty csv")
            return rows[0], rows[1:], enc
        except (UnicodeDecodeError, UnicodeError) as e:
            last_err = e
            continue
    with open(path, encoding="utf-8", errors="replace", newline="") as f:
        rows = [r for r in csv.reader(f) if r]
    if not rows:
        raise ValueError("empty csv")
    return rows[0], rows[1:], "utf-8-replace"


def is_missing(v):
    return v is None or v.strip().lower() in MISSING_TOKENS


def parse_number(v):
    """尝试把字符串解析成数字，支持千分位、% 和 万/亿 后缀。"""
    if v is None:
        return None
    s = v.strip().replace(",", "")
    if not s:
        return None
    mult = 1.0
    if s.endswith("%"):
        s = s[:-1]
    elif s.endswith("万"):
        s = s[:-1]; mult = 1e4
    elif s.endswith("亿"):
        s = s[:-1]; mult = 1e8
    elif s.endswith("w") or s.endswith("W"):
        s = s[:-1]; mult = 1e4
    elif s.endswith("k") or s.endswith("K"):
        s = s[:-1]; mult = 1e3
    try:
        return float(s) * mult
    except ValueError:
        return None


def parse_date(v):
    if v is None:
        return None
    s = v.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def infer_type(values):
    """根据非缺失值推断列类型：int / float / date / string。"""
    vals = [v for v in values if not is_missing(v)]
    if not vals:
        return "empty"
    n = len(vals)
    num_hits = sum(1 for v in vals if parse_number(v) is not None)
    if num_hits / n >= 0.9:
        raw = [v.strip().replace(",", "") for v in vals if parse_number(v) is not None]
        if all(("." not in r and "e" not in r.lower() and
                not r.endswith(("万", "亿", "k", "K", "w", "W", "%"))) for r in raw):
            return "int"
        return "float"
    date_hits = sum(1 for v in vals if parse_date(v) is not None)
    if date_hits / n >= 0.9:
        return "date"
    return "string"


def mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def median(xs):
    if not xs:
        return 0.0
    s = sorted(xs)
    m = len(s) // 2
    return s[m] if len(s) % 2 else (s[m - 1] + s[m]) / 2


def stdev(xs):
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def normal_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def fmt_num(x):
    if x is None:
        return "-"
    if isinstance(x, float) and not x.is_integer():
        return f"{x:,.2f}"
    return f"{int(x):,}"


def emit(obj, as_json, text_fn):
    if as_json:
        print(json.dumps(obj, ensure_ascii=True, indent=2))
    else:
        text_fn(obj)


def err(msg):
    print(json.dumps({"status": "error", "message": msg}, ensure_ascii=True))
    sys.exit(1)


# ---------------------------------------------------------------------------
# profile
# ---------------------------------------------------------------------------

def cmd_profile(args):
    try:
        header, rows, enc = read_csv_rows(args.file)
    except Exception as e:
        err(f"read failed: {e}")
    ncol = len(header)
    rows = [r + [""] * (ncol - len(r)) if len(r) < ncol else r[:ncol] for r in rows]
    n = len(rows)

    dup = n - len({tuple(r) for r in rows})

    cols = []
    for ci, name in enumerate(header):
        values = [r[ci] for r in rows]
        miss = sum(1 for v in values if is_missing(v))
        uniq = len({v.strip() for v in values if not is_missing(v)})
        ctype = infer_type(values)
        col = {"name": name, "type": ctype, "missing": miss,
               "missing_pct": round(miss / n * 100, 1) if n else 0,
               "unique": uniq}
        if ctype in ("int", "float"):
            nums = [parse_number(v) for v in values if parse_number(v) is not None]
            if nums:
                mu, sd = mean(nums), stdev(nums)
                col.update({
                    "min": min(nums), "max": max(nums),
                    "mean": round(mu, 4), "median": median(nums),
                    "std": round(sd, 4),
                    "outliers_3sigma": sum(1 for x in nums if abs(x - mu) > 3 * sd) if sd > 0 else 0,
                })
        elif ctype == "date":
            ds = [parse_date(v) for v in values if parse_date(v)]
            if ds:
                col["min"] = min(ds).strftime("%Y-%m-%d")
                col["max"] = max(ds).strftime("%Y-%m-%d")
        else:
            top = Counter(v.strip() for v in values if not is_missing(v)).most_common(5)
            col["top"] = [{"value": k, "count": c} for k, c in top]
        cols.append(col)

    # 质量评分：缺失率、重复率加权扣分（每 1% 缺失扣 0.8，每 1% 重复扣 1.0）
    total_cells = n * ncol or 1
    miss_rate = sum(c["missing"] for c in cols) / total_cells
    dup_rate = dup / n if n else 0
    score = max(0, 100 - miss_rate * 80 - dup_rate * 100)
    grade = "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D"

    result = {
        "status": "success", "command": "profile", "file": args.file,
        "encoding": enc, "rows": n, "cols": ncol, "duplicate_rows": dup,
        "quality": {"score": round(score, 1), "grade": grade,
                    "missing_pct": round(miss_rate * 100, 1),
                    "duplicate_pct": round(dup_rate * 100, 1)},
        "columns": cols,
    }

    def text(r):
        print(f"== 数据画像 == {r['file']}（编码 {r['encoding']}）")
        print(f"行 {r['rows']:,} × 列 {r['cols']}，完全重复行 {r['duplicate_rows']}")
        q = r["quality"]
        print(f"质量评分 {q['score']}（{q['grade']}）：缺失 {q['missing_pct']}%，重复 {q['duplicate_pct']}%")
        print("-" * 78)
        for c in r["columns"]:
            line = (f"[{c['type']:<6}] {c['name']}  缺失 {c['missing_pct']}%  "
                    f"唯一 {c['unique']}")
            print(line)
            if "mean" in c:
                print(f"         min {fmt_num(c['min'])} | 中位 {fmt_num(c['median'])} | "
                      f"max {fmt_num(c['max'])} | 均值 {fmt_num(c['mean'])} | "
                      f"3σ异常 {c['outliers_3sigma']}")
            elif c["type"] == "date" and "min" in c:
                print(f"         {c['min']} ~ {c['max']}")
            elif "top" in c and c["top"]:
                tops = "，".join(f"{t['value']}×{t['count']}" for t in c["top"][:3])
                print(f"         高频：{tops}")
    emit(result, args.json, text)


# ---------------------------------------------------------------------------
# clean
# ---------------------------------------------------------------------------

def cmd_clean(args):
    try:
        header, rows, enc = read_csv_rows(args.file)
    except Exception as e:
        err(f"read failed: {e}")
    ncol = len(header)
    rows = [r + [""] * (ncol - len(r)) if len(r) < ncol else r[:ncol] for r in rows]
    n0 = len(rows)
    log = []

    # 1. 单元格去首尾空格
    rows = [[c.strip() for c in r] for r in rows]
    log.append({"action": "strip_whitespace", "detail": "所有单元格去首尾空格"})

    # 2. 去完全重复行
    seen, dedup = set(), []
    dup_n = 0
    for r in rows:
        t = tuple(r)
        if t in seen:
            dup_n += 1
            continue
        seen.add(t)
        dedup.append(r)
    rows = dedup
    if dup_n:
        log.append({"action": "drop_duplicates", "removed": dup_n})

    # 3. 高缺失列删除
    keep_idx, drop_cols = [], []
    for ci, name in enumerate(header):
        miss_rate = sum(1 for r in rows if is_missing(r[ci])) / (len(rows) or 1)
        if miss_rate > args.drop_col_threshold and len(header) > 1:
            drop_cols.append((ci, name, round(miss_rate * 100, 1)))
        else:
            keep_idx.append(ci)
    if drop_cols:
        for ci, name, pct in drop_cols:
            log.append({"action": "drop_column", "column": name,
                        "missing_pct": pct,
                        "reason": f"缺失率 > {args.drop_col_threshold*100:.0f}%"})
        header = [header[i] for i in keep_idx]
        rows = [[r[i] for i in keep_idx] for r in rows]

    # 4. 缺失填充：数值列中位数，文本列「未知」
    fills = []
    for ci, name in enumerate(header):
        values = [r[ci] for r in rows]
        ctype = infer_type(values)
        miss_idx = [i for i, v in enumerate(values) if is_missing(v)]
        if not miss_idx:
            continue
        if ctype in ("int", "float"):
            nums = [parse_number(v) for v in values if parse_number(v) is not None]
            fill = median(nums) if nums else 0
            fill_s = f"{fill:g}"
            for i in miss_idx:
                rows[i][ci] = fill_s
            fills.append({"column": name, "filled": len(miss_idx),
                          "strategy": "median", "value": fill_s})
        else:
            for i in miss_idx:
                rows[i][ci] = "未知"
            fills.append({"column": name, "filled": len(miss_idx),
                          "strategy": "constant", "value": "未知"})
    log.extend(fills)

    out = args.out or args.file.rsplit(".", 1)[0] + "_clean.csv"
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

    result = {"status": "success", "command": "clean", "input": args.file,
              "output": out, "encoding_in": enc,
              "rows_in": n0, "rows_out": len(rows),
              "cols_in": ncol, "cols_out": len(header),
              "decisions": log}

    def text(r):
        print(f"== 清洗完成 == {r['input']} → {r['output']}")
        print(f"行 {r['rows_in']} → {r['rows_out']}，列 {r['cols_in']} → {r['cols_out']}")
        print(f"决策留痕 {len(r['decisions'])} 条：")
        for d in r["decisions"]:
            print("  -", json.dumps(d, ensure_ascii=False))
    emit(result, args.json, text)


# ---------------------------------------------------------------------------
# funnel
# ---------------------------------------------------------------------------

def cmd_funnel(args):
    if args.counts:
        try:
            counts = [float(x.replace(",", "")) for x in args.counts.split(",")]
        except ValueError:
            err("--counts 需要逗号分隔的数字，如 10000,3200,1500")
        labels = args.labels.split(",") if args.labels else [f"步骤{i+1}" for i in range(len(counts))]
        if len(labels) != len(counts):
            err("--labels 数量必须和 --counts 一致")
    elif args.steps and args.file:
        try:
            header, rows, _ = read_csv_rows(args.file)
        except Exception as e:
            err(f"read failed: {e}")
        labels = args.steps.split(",")
        idx = []
        for lb in labels:
            if lb not in header:
                err(f"列不存在: {lb}（可用列: {', '.join(header)}）")
            idx.append(header.index(lb))
        counts = []
        for ci in idx:
            c = sum(1 for r in rows if ci < len(r) and parse_number(r[ci]) not in (None, 0))
            counts.append(float(c))
    else:
        err("需要 --counts 直接给数，或 --file + --steps 指定 0/1 列")

    steps = []
    base = counts[0] or 1
    prev = None
    for i, (lb, c) in enumerate(zip(labels, counts)):
        step = {"step": i + 1, "label": lb, "count": c,
                "cum_rate": round(c / base * 100, 2)}
        if prev is not None:
            step["conv_rate"] = round(c / prev * 100, 2) if prev else 0.0
            step["drop_rel"] = round((1 - c / prev) * 100, 2) if prev else 100.0
        steps.append(step)
        prev = c

    bottleneck = None
    if len(steps) > 1:
        bottleneck = max(steps[1:], key=lambda s: s.get("drop_rel", 0))
    overall = round(counts[-1] / base * 100, 2) if counts else 0

    result = {"status": "success", "command": "funnel", "steps": steps,
              "overall_rate": overall,
              "bottleneck": {"label": bottleneck["label"],
                             "step": bottleneck["step"],
                             "drop_rel": bottleneck["drop_rel"]} if bottleneck else None}

    def text(r):
        print("== 漏斗分析 ==")
        print(f"{'步骤':<6}{'环节':<14}{'人数':>12}{'逐步转化':>10}{'累计转化':>10}")
        for s in r["steps"]:
            conv = f"{s['conv_rate']}%" if "conv_rate" in s else "-"
            print(f"{s['step']:<6}{s['label']:<14}{fmt_num(s['count']):>12}"
                  f"{conv:>10}{str(s['cum_rate'])+'%':>10}")
        print(f"\n整体转化率 {r['overall_rate']}%")
        if r["bottleneck"]:
            b = r["bottleneck"]
            print(f"⚠ 瓶颈环节：第 {b['step']} 步「{b['label']}」，相对流失 {b['drop_rel']}%")
    emit(result, args.json, text)


# ---------------------------------------------------------------------------
# cohort
# ---------------------------------------------------------------------------

def cmd_cohort(args):
    try:
        header, rows, _ = read_csv_rows(args.file)
    except Exception as e:
        err(f"read failed: {e}")
    for col, flag in ((args.id, "--id"), (args.date, "--date")):
        if col not in header:
            err(f"列不存在: {col}（{flag}；可用列: {', '.join(header)}）")
    idi, dti = header.index(args.id), header.index(args.date)

    # 用户 → 首现月份 + 活跃月份集合
    first, active = {}, defaultdict(set)
    bad_dates = 0
    for r in rows:
        if max(idi, dti) >= len(r):
            continue
        uid = r[idi].strip()
        d = parse_date(r[dti])
        if not uid or d is None:
            if not is_missing(r[dti]):
                bad_dates += 1
            continue
        m = d.strftime("%Y-%m")
        if uid not in first or m < first[uid]:
            first[uid] = m
        active[uid].add(m)

    if not first:
        err("没有可用的 (ID, 日期) 数据，检查列名和日期格式")

    cohorts = defaultdict(list)
    for uid, m0 in first.items():
        cohorts[m0].append(uid)

    def month_offset(m1, m0):
        y1, mo1 = int(m1[:4]), int(m1[5:7])
        y0, mo0 = int(m0[:4]), int(m0[5:7])
        return (y1 - y0) * 12 + (mo1 - mo0)

    max_off = 0
    matrix = {}
    for m0 in sorted(cohorts):
        users = cohorts[m0]
        size = len(users)
        row = {}
        for uid in users:
            for m in active[uid]:
                off = month_offset(m, m0)
                row[off] = row.get(off, 0) + 1
                max_off = max(max_off, off)
        matrix[m0] = {"size": size, "offsets": row}

    table = []
    for m0 in sorted(matrix):
        e = matrix[m0]
        cells = []
        for k in range(max_off + 1):
            c = e["offsets"].get(k, 0)
            cells.append({"offset": k, "count": c,
                          "rate": round(c / e["size"] * 100, 1)})
        table.append({"cohort": m0, "size": e["size"], "periods": cells})

    result = {"status": "success", "command": "cohort",
              "users": len(first), "cohorts": len(table),
              "max_offset": max_off,
              "unparsed_dates": bad_dates, "matrix": table}

    def text(r):
        print(f"== 同期群留存矩阵 == 共 {r['users']} 用户，{r['cohorts']} 个群")
        if r["unparsed_dates"]:
            print(f"（{r['unparsed_dates']} 行日期无法解析已跳过）")
        head = "同期群    规模   " + "".join(f"M+{k:<6}" for k in range(r["max_offset"] + 1))
        print(head)
        print("-" * len(head))
        for row in r["matrix"]:
            cells = "".join((f"{p['rate']}%" if p["count"] else "·").ljust(7)
                            for p in row["periods"])
            print(f"{row['cohort']}  {str(row['size']).rjust(6)}  {cells}")
        print("\n（M+0 为首次出现当月，百分比 = 当月活跃/群规模）")
    emit(result, args.json, text)


# ---------------------------------------------------------------------------
# rfm
# ---------------------------------------------------------------------------

def _quintile_scores(pairs, reverse=False):
    """pairs: [(key, value)] → {key: 1..5}，rank 法处理并列。reverse=True 时值越小分越高。"""
    ordered = sorted(pairs, key=lambda kv: kv[1], reverse=reverse)
    n = len(ordered)
    scores = {}
    for rank, (k, _v) in enumerate(ordered):
        scores[k] = min(5, int(rank * 5 / n) + 1) if n else 1
    return scores


def cmd_rfm(args):
    try:
        header, rows, _ = read_csv_rows(args.file)
    except Exception as e:
        err(f"read failed: {e}")
    for col, flag in ((args.id, "--id"), (args.date, "--date"), (args.amount, "--amount")):
        if col not in header:
            err(f"列不存在: {col}（{flag}；可用列: {', '.join(header)}）")
    idi = header.index(args.id)
    dti = header.index(args.date)
    ami = header.index(args.amount)

    last, freq, money = {}, Counter(), Counter()
    max_date = None
    skipped = 0
    for r in rows:
        if max(idi, dti, ami) >= len(r):
            continue
        uid = r[idi].strip()
        d = parse_date(r[dti])
        amt = parse_number(r[ami])
        if not uid or d is None or amt is None:
            skipped += 1
            continue
        if uid not in last or d > last[uid]:
            last[uid] = d
        freq[uid] += 1
        money[uid] += amt
        max_date = d if max_date is None or d > max_date else max_date

    if not last:
        err("没有可用的 (ID, 日期, 金额) 数据，检查列名和格式")

    ref = max_date + timedelta(days=1)
    recency = {u: (ref - d).days for u, d in last.items()}

    r_sc = _quintile_scores(list(recency.items()), reverse=True)   # R 越小越好
    f_sc = _quintile_scores(list(freq.items()))
    m_sc = _quintile_scores(list(money.items()))

    # 经典八象限：R 高低 × F 高低 × M 高低（4-5 分为"高"）
    SEG8 = {
        (1, 1, 1): "重要价值客户", (1, 0, 1): "重要发展客户",
        (0, 1, 1): "重要保持客户", (0, 0, 1): "重要挽留客户",
        (1, 1, 0): "一般价值客户", (1, 0, 0): "一般发展客户",
        (0, 1, 0): "一般保持客户", (0, 0, 0): "一般挽留客户",
    }

    detail = []
    seg_stat = defaultdict(lambda: {"count": 0, "r": 0.0, "f": 0.0, "m": 0.0})
    for u in last:
        hi = lambda s: 1 if s >= 4 else 0
        seg = SEG8[(hi(r_sc[u]), hi(f_sc[u]), hi(m_sc[u]))]
        rec = {"id": u, "R_days": recency[u], "F": freq[u], "M": round(money[u], 2),
               "R_score": r_sc[u], "F_score": f_sc[u], "M_score": m_sc[u],
               "segment": seg}
        detail.append(rec)
        st = seg_stat[seg]
        st["count"] += 1
        st["r"] += recency[u]; st["f"] += freq[u]; st["m"] += money[u]

    n = len(detail)
    segments = []
    for seg, st in sorted(seg_stat.items(), key=lambda kv: -kv[1]["m"]):
        segments.append({
            "segment": seg, "count": st["count"],
            "pct": round(st["count"] / n * 100, 1),
            "avg_R_days": round(st["r"] / st["count"], 1),
            "avg_F": round(st["f"] / st["count"], 2),
            "avg_M": round(st["m"] / st["count"], 2),
            "total_M": round(st["m"], 2),
            "revenue_share": round(st["m"] / sum(money.values()) * 100, 1) if money else 0,
        })

    if args.out:
        with open(args.out, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(detail[0].keys()))
            w.writeheader()
            w.writerows(sorted(detail, key=lambda d: -d["M"]))

    result = {"status": "success", "command": "rfm", "users": n,
              "ref_date": ref.strftime("%Y-%m-%d"), "rows_skipped": skipped,
              "segments": segments,
              "detail_out": args.out or None}

    def text(r):
        print(f"== RFM 用户分层 == {r['users']} 用户（基准日 {r['ref_date']}）")
        if r["rows_skipped"]:
            print(f"（{r['rows_skipped']} 行数据不完整已跳过）")
        print(f"{'分层':<10}{'人数':>8}{'占比':>8}{'均R天':>8}{'均F':>6}{'均M':>12}{'收入占比':>9}")
        for s in r["segments"]:
            print(f"{s['segment']:<10}{s['count']:>8}{str(s['pct'])+'%':>8}"
                  f"{s['avg_R_days']:>8}{s['avg_F']:>6}{fmt_num(s['avg_M']):>12}"
                  f"{str(s['revenue_share'])+'%':>9}")
        if r["detail_out"]:
            print(f"\n逐用户明细 → {r['detail_out']}")
    emit(result, args.json, text)


# ---------------------------------------------------------------------------
# abc
# ---------------------------------------------------------------------------

def cmd_abc(args):
    try:
        header, rows, _ = read_csv_rows(args.file)
    except Exception as e:
        err(f"read failed: {e}")
    for col, flag in ((args.dim, "--dim"), (args.value, "--value")):
        if col not in header:
            err(f"列不存在: {col}（{flag}；可用列: {', '.join(header)}）")
    di, vi = header.index(args.dim), header.index(args.value)

    agg = Counter()
    skipped = 0
    for r in rows:
        if max(di, vi) >= len(r):
            continue
        key = r[di].strip() or "（空）"
        v = parse_number(r[vi])
        if v is None:
            skipped += 1
            continue
        agg[key] += v
    if not agg:
        err("没有可用的 (维度, 数值) 数据")

    total = sum(agg.values()) or 1
    ranked = agg.most_common()
    items = []
    cum = 0.0
    for i, (k, v) in enumerate(ranked):
        cum += v
        cum_pct = cum / total * 100
        cls = "A" if cum_pct <= 80.0001 else ("B" if cum_pct <= 95.0001 else "C")
        items.append({"rank": i + 1, "name": k, "value": round(v, 2),
                      "share": round(v / total * 100, 2),
                      "cum_share": round(cum_pct, 2), "class": cls})

    top = lambda k: round(sum(v for _n, v in ranked[:k]) / total * 100, 1)
    cls_count = Counter(it["class"] for it in items)
    result = {"status": "success", "command": "abc", "items": len(items),
              "total": round(total, 2), "rows_skipped": skipped,
              "concentration": {"top1": top(1), "top5": top(5), "top10": top(10)},
              "class_count": dict(cls_count),
              "table": items[:args.top]}

    def text(r):
        print(f"== ABC 帕累托分析 == {r['items']} 个维度项，总量 {fmt_num(r['total'])}")
        c = r["concentration"]
        print(f"集中度：Top1 {c['top1']}% | Top5 {c['top5']}% | Top10 {c['top10']}%")
        cc = r["class_count"]
        print(f"分级：A {cc.get('A',0)} 项 / B {cc.get('B',0)} 项 / C {cc.get('C',0)} 项")
        print(f"{'排名':<5}{'名称':<16}{'数值':>12}{'占比':>8}{'累计':>8}  级别")
        for it in r["table"]:
            print(f"{it['rank']:<5}{it['name'][:14]:<16}{fmt_num(it['value']):>12}"
                  f"{str(it['share'])+'%':>8}{str(it['cum_share'])+'%':>8}  {it['class']}")
        if r["items"] > len(r["table"]):
            print(f"（仅显示前 {len(r['table'])} 项，--top 可调）")
    emit(result, args.json, text)


# ---------------------------------------------------------------------------
# sig
# ---------------------------------------------------------------------------

def cmd_sig(args):
    if args.sample_size or (args.baseline and args.mde):
        if not (args.baseline and args.mde):
            err("--sample-size 需要同时给 --baseline 和 --mde")
        p, mde = args.baseline, args.mde
        if not (0 < p < 1) or mde <= 0:
            err("baseline 需在 (0,1)，mde 需 > 0")
        z_a, z_b = 1.95996, 0.84162  # α=0.05 双侧, power=0.8
        p_bar = p + mde / 2
        n = ((z_a + z_b) ** 2 * 2 * p_bar * (1 - p_bar)) / (mde ** 2)
        result = {"status": "success", "command": "sig", "mode": "sample_size",
                  "baseline": p, "mde": mde, "alpha": 0.05, "power": 0.8,
                  "n_per_group": math.ceil(n),
                  "note": "比率类指标的每组样本量；均值类用 n≈16σ²/δ² 粗估"}

        def text(r):
            print(f"== 样本量估算 == 基线 {r['baseline']*100:g}%，最小检测差异 ±{r['mde']*100:g}%")
            print(f"α=0.05（双侧）、power=80% → 每组需要 {r['n_per_group']:,} 样本")
            print(r["note"])
        emit(result, args.json, text)
        return

    if args.prop_a and args.prop_b:
        try:
            p1, n1 = [float(x) for x in args.prop_a.split(",")]
            p2, n2 = [float(x) for x in args.prop_b.split(",")]
        except ValueError:
            err("--prop-a/--prop-b 格式: 比率,样本量  如 0.052,1200")
        if p1 > 1 or p2 > 1:
            err("比率请用小数（0.052 而不是 5.2%）")
        p_pool = (p1 * n1 + p2 * n2) / (n1 + n2)
        se = math.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
        if se == 0:
            err("标准误为 0，无法检验")
        z = (p2 - p1) / se
        pval = 2 * (1 - normal_cdf(abs(z)))
        rel = (p2 - p1) / p1 * 100 if p1 else 0
        result = {"status": "success", "command": "sig", "mode": "two_proportion",
                  "a": {"p": p1, "n": n1}, "b": {"p": p2, "n": n2},
                  "diff_abs": round(p2 - p1, 6), "diff_rel_pct": round(rel, 2),
                  "z": round(z, 4), "p_value": round(pval, 6),
                  "significant_005": pval < 0.05,
                  "verdict": "差异显著" if pval < 0.05 else "差异不显著（不能排除随机波动）"}

        def text(r):
            print(f"== 两比率检验 == A {r['a']['p']*100:g}%(n={int(r['a']['n'])}) vs "
                  f"B {r['b']['p']*100:g}%(n={int(r['b']['n'])})")
            print(f"绝对差 {r['diff_abs']*100:.2f}pp，相对提升 {r['diff_rel_pct']}%")
            print(f"z = {r['z']}，p = {r['p_value']} → {r['verdict']}")
        emit(result, args.json, text)
        return

    if args.mean_a and args.mean_b:
        try:
            m1, s1, n1 = [float(x) for x in args.mean_a.split(",")]
            m2, s2, n2 = [float(x) for x in args.mean_b.split(",")]
        except ValueError:
            err("--mean-a/--mean-b 格式: 均值,标准差,样本量  如 152.3,35,500")
        se = math.sqrt(s1 ** 2 / n1 + s2 ** 2 / n2)
        if se == 0:
            err("标准误为 0，无法检验")
        z = (m2 - m1) / se
        pval = 2 * (1 - normal_cdf(abs(z)))
        note = "" if min(n1, n2) >= 30 else "注意：样本量 < 30，正态近似偏乐观，结论降级为间接证据"
        result = {"status": "success", "command": "sig", "mode": "two_mean_welch",
                  "a": {"mean": m1, "std": s1, "n": n1},
                  "b": {"mean": m2, "std": s2, "n": n2},
                  "diff": round(m2 - m1, 4), "z": round(z, 4),
                  "p_value": round(pval, 6),
                  "significant_005": pval < 0.05,
                  "verdict": "差异显著" if pval < 0.05 else "差异不显著（不能排除随机波动）",
                  "note": note or "Welch 两样本检验，大样本正态近似"}

        def text(r):
            print(f"== 两均值检验 == A {r['a']['mean']:g}(n={int(r['a']['n'])}) vs "
                  f"B {r['b']['mean']:g}(n={int(r['b']['n'])})")
            print(f"差值 {r['diff']:g}，z = {r['z']}，p = {r['p_value']} → {r['verdict']}")
            print(r["note"])
        emit(result, args.json, text)
        return

    err("需要以下之一：--prop-a + --prop-b / --mean-a + --mean-b / --sample-size --baseline --mde")


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def main():
    # Windows GBK 控制台兜底：中文输出改为 utf-8 + replace，防止 UnicodeEncodeError
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    ap = argparse.ArgumentParser(
        prog="datakit.py",
        description="零依赖数据分析工具箱：profile/clean/funnel/cohort/rfm/abc/sig")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add_json(p):
        p.add_argument("--json", action="store_true", help="输出 JSON（ASCII 安全）")

    p = sub.add_parser("profile", help="CSV 数据画像")
    p.add_argument("file"); add_json(p); p.set_defaults(fn=cmd_profile)

    p = sub.add_parser("clean", help="自动清洗 + 决策留痕")
    p.add_argument("file")
    p.add_argument("--out", help="输出 CSV 路径（默认 原名_clean.csv）")
    p.add_argument("--drop-col-threshold", type=float, default=0.5,
                   help="列缺失率超过该值则删列（默认 0.5）")
    add_json(p); p.set_defaults(fn=cmd_clean)

    p = sub.add_parser("funnel", help="漏斗分析")
    p.add_argument("file", nargs="?", help="CSV（--steps 模式需要）")
    p.add_argument("--counts", help="各环节人数，逗号分隔")
    p.add_argument("--labels", help="各环节名称，逗号分隔")
    p.add_argument("--steps", help="0/1 步骤列名，逗号分隔（配合 file）")
    add_json(p); p.set_defaults(fn=cmd_funnel)

    p = sub.add_parser("cohort", help="同期群留存矩阵")
    p.add_argument("file")
    p.add_argument("--id", required=True, help="用户 ID 列名")
    p.add_argument("--date", required=True, help="日期列名")
    add_json(p); p.set_defaults(fn=cmd_cohort)

    p = sub.add_parser("rfm", help="RFM 用户分层")
    p.add_argument("file")
    p.add_argument("--id", required=True)
    p.add_argument("--date", required=True)
    p.add_argument("--amount", required=True)
    p.add_argument("--out", help="逐用户明细 CSV 输出路径")
    add_json(p); p.set_defaults(fn=cmd_rfm)

    p = sub.add_parser("abc", help="帕累托 ABC 分级")
    p.add_argument("file")
    p.add_argument("--dim", required=True, help="维度列名（如 商品）")
    p.add_argument("--value", required=True, help="数值列名（如 销售额）")
    p.add_argument("--top", type=int, default=20, help="文本模式显示前 N 项")
    add_json(p); p.set_defaults(fn=cmd_abc)

    p = sub.add_parser("sig", help="显著性检验 / 样本量估算")
    p.add_argument("--prop-a", help="A 组 比率,样本量")
    p.add_argument("--prop-b", help="B 组 比率,样本量")
    p.add_argument("--mean-a", help="A 组 均值,标准差,样本量")
    p.add_argument("--mean-b", help="B 组 均值,标准差,样本量")
    p.add_argument("--sample-size", action="store_true", help="样本量估算模式")
    p.add_argument("--baseline", type=float, help="基线转化率（小数）")
    p.add_argument("--mde", type=float, help="最小检测差异（小数）")
    add_json(p); p.set_defaults(fn=cmd_sig)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
