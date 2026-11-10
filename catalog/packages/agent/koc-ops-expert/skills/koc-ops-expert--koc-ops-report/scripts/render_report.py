#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KOC 全链路作战报告渲染器 —— 把结构化 JSON 渲染成单文件 HTML 报告。

设计原则：
  1. 单文件零外链：CSS / JS / 图表全部内联，断网可开，可直接发给同事；
  2. 图表用内联 SVG 手绘，几何由脚本计算，不依赖任何图表库；
  3. 明暗双模式：跟随系统 + 顶部手动切换，两种模式下的配色都经过 CVD（色觉障碍）校验；
  4. 可打印：A4 打印不断行、不丢色；
  5. 每张图都有直接数值标注或配套数据表，不靠颜色单独传递信息。

用法：
    python3 render_report.py --data report.json --out 报告.html
    python3 render_report.py --demo --out 示例报告.html        # 渲染内置示例
    python3 render_report.py --template                        # 打印数据结构模板
    python3 render_report.py --blocks                          # 打印所有区块类型速查
    python3 render_report.py --self-test                       # 自检（渲染全部区块类型）

数据结构见 --template，区块类型见 --blocks。
"""

from __future__ import annotations

import argparse
import html
import json
import math
import os
import re
import sys
from datetime import date, datetime, timedelta

# ---------------------------------------------------------------------------
# 配色：来自经过校验的分类色板（CVD 相邻对 ΔE ≥ 8，明暗两套独立取步）
# 校验方式：dataviz/scripts/validate_palette.js，明暗双模式全部 PASS。
# 分类色（s1-s8）用于"身份"，序数色（o1-o5）用于"有序层级"（漏斗/金字塔/阶梯）。
# ---------------------------------------------------------------------------

PALETTE = {
    "light": {
        "series": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"],
        "ordinal": ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"],
    },
    "dark": {
        "series": ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"],
        "ordinal": ["#b7d3f6", "#86b6ef", "#5598e7", "#2a78d6", "#184f95"],
    },
}

# 状态色固定，不随主题变化，且永远与"图标 + 文字"同时出现，绝不单独用颜色表达状态
STATUS = {
    "good": ("#0ca30c", "✓"),
    "warn": ("#fab219", "!"),
    "serious": ("#ec835a", "▲"),
    "critical": ("#d03b3b", "✕"),
    "info": ("#2a78d6", "i"),
}

TONE_ALIAS = {
    "ok": "good", "success": "good", "go": "good", "pass": "good",
    "warning": "warn", "fix": "warn",
    "danger": "critical", "kill": "critical", "error": "critical", "red": "critical",
    "note": "info", "tip": "info", "": "info",
}


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _lum(hexcolor: str) -> float:
    h = hexcolor.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))

    def f(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def _ink_on(hexcolor: str) -> str:
    """色块上的文字取白或近黑，保证 ≥ 4.5:1。"""
    return "#ffffff" if _lum(hexcolor) < 0.42 else "#0b0b0b"


def _palette_vars(mode: str) -> str:
    p = PALETTE[mode]
    out = []
    for i, c in enumerate(p["series"], 1):
        out.append(f"  --s{i}: {c};")
        out.append(f"  --s{i}-ink: {_ink_on(c)};")
    for i, c in enumerate(p["ordinal"], 1):
        out.append(f"  --o{i}: {c};")
        out.append(f"  --o{i}-ink: {_ink_on(c)};")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# 文本处理
# ---------------------------------------------------------------------------

def esc(s) -> str:
    if s is None:
        return ""
    return html.escape(str(s), quote=True)


_RICH_PATTERNS = [
    (re.compile(r"\*\*(.+?)\*\*"), r"<strong>\1</strong>"),
    (re.compile(r"`(.+?)`"), r"<code>\1</code>"),
]


def rich(s) -> str:
    """极简行内富文本：**加粗**、`代码`、换行。先转义再放行这几个标记。"""
    out = esc(s)
    for pat, rep in _RICH_PATTERNS:
        out = pat.sub(rep, out)
    return out.replace("\n", "<br>")


def prose_html(text: str) -> str:
    """段落 / 无序列表 / 有序列表的极简渲染。"""
    blocks, buf, mode = [], [], None

    def flush():
        nonlocal buf, mode
        if not buf:
            return
        if mode == "ul":
            blocks.append("<ul>" + "".join(f"<li>{rich(x)}</li>" for x in buf) + "</ul>")
        elif mode == "ol":
            blocks.append("<ol>" + "".join(f"<li>{rich(x)}</li>" for x in buf) + "</ol>")
        else:
            blocks.append(f"<p>{rich(' '.join(buf))}</p>")
        buf, mode = [], None

    for raw in str(text).split("\n"):
        line = raw.rstrip()
        if not line.strip():
            flush()
            continue
        if line.lstrip().startswith(("- ", "· ", "• ")):
            if mode != "ul":
                flush()
            mode = "ul"
            buf.append(line.lstrip()[2:])
        elif re.match(r"^\s*\d+[.、)]\s+", line):
            if mode != "ol":
                flush()
            mode = "ol"
            buf.append(re.sub(r"^\s*\d+[.、)]\s+", "", line))
        else:
            if mode in ("ul", "ol"):
                flush()
            mode = "p"
            buf.append(line.strip())
    flush()
    return "".join(blocks)


def fmt_num(v) -> str:
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, int):
        return f"{v:,}"
    if isinstance(v, float):
        if not math.isfinite(v):     # NaN / inf 不能让整份报告渲染失败
            return "—"
        if abs(v - round(v)) < 1e-9:
            return f"{int(round(v)):,}"
        return f"{v:,.2f}".rstrip("0").rstrip(".")
    return str(v)


def _num(v, default=0.0) -> float:
    """把任意输入安全地转成有限浮点数，脏数据不至于毁掉整份报告。"""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return default
    return f if math.isfinite(f) else default


def missing_note(text: str) -> str:
    """数据不足时不静默丢块 —— 明确告诉读者缺什么。"""
    return (f'<figure class="fig"><div class="co co-warn"><div class="co-i" aria-hidden="true">!</div>'
            f'<div class="co-b"><div class="co-t">此处数据不足，图表未生成</div>{rich(text)}</div></div></figure>')


def tone_of(name) -> str:
    n = str(name or "").strip().lower()
    return TONE_ALIAS.get(n, n if n in STATUS else "info")


def chip(text: str, tone: str = "info") -> str:
    t = tone_of(tone)
    color, icon = STATUS[t]
    return (f'<span class="chip chip-{t}"><span class="chip-i" aria-hidden="true">{icon}</span>'
            f'{rich(text)}</span>')


# ---------------------------------------------------------------------------
# SVG 基础件
# ---------------------------------------------------------------------------

def svg_open(w: float, h: float, label: str, cls: str = "") -> str:
    return (f'<svg class="viz {cls}" viewBox="0 0 {w:.0f} {h:.0f}" role="img" '
            f'aria-label="{esc(label)}" xmlns="http://www.w3.org/2000/svg">'
            f'<title>{esc(label)}</title>')


def txt(x: float, y: float, s: str, size: float = 13, anchor: str = "start",
        cls: str = "vt-2", weight: str = "400", fill: str = None) -> str:
    f = f' fill="{fill}"' if fill else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" '
            f'font-weight="{weight}" class="{cls}"{f}>{esc(s)}</text>')


def figure(inner: str, caption: str = "", note: str = "", table: str = "") -> str:
    """图题在上、图在中、脚注与数据表在下 —— 读者先知道在看什么，再看图。"""
    cap = f'<figcaption class="fig-cap">{rich(caption)}</figcaption>' if caption else ""
    nt = f'<p class="fig-note">{rich(note)}</p>' if note else ""
    return f'<figure class="fig">{cap}{inner}{nt}{table}</figure>'


def legend(items) -> str:
    """items: [(label, css_color_var, value_text)]"""
    lis = []
    for label, color, value in items:
        val = f'<span class="lg-v">{rich(value)}</span>' if value else ""
        lis.append(f'<li><span class="lg-s" style="background:{color}"></span>'
                   f'<span class="lg-t">{rich(label)}</span>{val}</li>')
    return f'<ul class="legend">{"".join(lis)}</ul>'


def mini_table(columns, rows, cls="tbl-mini") -> str:
    """图表的数据表孪生体 —— 保证每个值都能被读到，不依赖颜色。"""
    head = "".join(f"<th>{rich(c)}</th>" for c in columns)
    body = "".join("<tr>" + "".join(f"<td>{rich(c)}</td>" for c in r) + "</tr>" for r in rows)
    return (f'<div class="tbl-wrap"><table class="{cls}"><thead><tr>{head}</tr></thead>'
            f'<tbody>{body}</tbody></table></div>')


# ---------------------------------------------------------------------------
# 区块渲染器
# ---------------------------------------------------------------------------

def b_kpis(b) -> str:
    cells = []
    for it in b.get("items", []):
        unit = f'<span class="kpi-u">{esc(it.get("unit", ""))}</span>' if it.get("unit") else ""
        note = f'<div class="kpi-n">{rich(it.get("note", ""))}</div>' if it.get("note") else ""
        tone = it.get("tone")
        tcls = f" kpi-{tone_of(tone)}" if tone else ""
        cells.append(f'<div class="kpi{tcls}"><div class="kpi-l">{rich(it.get("label", ""))}</div>'
                     f'<div class="kpi-v">{esc(fmt_num(it.get("value", "")))}{unit}</div>{note}</div>')
    return f'<div class="kpis">{"".join(cells)}</div>'


def b_callout(b) -> str:
    t = tone_of(b.get("tone", "info"))
    color, icon = STATUS[t]
    title = f'<div class="co-t">{rich(b.get("title", ""))}</div>' if b.get("title") else ""
    body = prose_html(b.get("text", "")) if b.get("text") else ""
    return (f'<div class="co co-{t}"><div class="co-i" aria-hidden="true">{icon}</div>'
            f'<div class="co-b">{title}{body}</div></div>')


def _cell(c) -> str:
    if isinstance(c, dict):
        if c.get("tone"):
            return chip(c.get("text", ""), c["tone"])
        return rich(c.get("text", ""))
    return rich(c)


def b_table(b) -> str:
    cols = b.get("columns", [])
    heads, aligns = [], []
    for c in cols:
        if isinstance(c, dict):
            heads.append(c.get("name", ""))
            aligns.append(c.get("align", "left"))
        else:
            heads.append(c)
            aligns.append("left")
    thead = "".join(f'<th style="text-align:{a}">{rich(h)}</th>' for h, a in zip(heads, aligns))
    trs = []
    for r in b.get("rows", []):
        tds = "".join(f'<td style="text-align:{aligns[i] if i < len(aligns) else "left"}">{_cell(c)}</td>'
                      for i, c in enumerate(r))
        trs.append(f"<tr>{tds}</tr>")
    cap = f'<figcaption class="fig-cap">{rich(b["caption"])}</figcaption>' if b.get("caption") else ""
    note = f'<p class="fig-note">{rich(b["note"])}</p>' if b.get("note") else ""
    return (f'<figure class="fig">{cap}<div class="tbl-wrap"><table class="tbl">'
            f'<thead><tr>{thead}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>{note}</figure>')


def b_prose(b) -> str:
    return f'<div class="prose">{prose_html(b.get("text", ""))}</div>'


def b_quote(b) -> str:
    by = f'<cite>—— {rich(b["by"])}</cite>' if b.get("by") else ""
    return f'<blockquote class="quote">{rich(b.get("text", ""))}{by}</blockquote>'


def b_divider(b) -> str:
    return '<hr class="rule">'


def b_pyramid(b) -> str:
    """分层金字塔：顶层最窄、颜色最深（层级越高越稀缺）。"""
    levels = b.get("levels", [])[:5]
    n = len(levels)
    if n == 0:
        return missing_note("金字塔需要至少 1 层（levels）。")
    W, PITCH, BAR = 720.0, 78.0, 66.0
    H = n * PITCH + 10
    top_half, bot_half = 96.0, 330.0
    cx = W / 2
    parts = [svg_open(W, H, b.get("caption", "KOC 分层金字塔"))]
    for i, lv in enumerate(levels):
        y0 = i * PITCH + 6
        y1 = y0 + BAR
        f0 = (y0 - 6) / (n * PITCH)
        f1 = (y1 - 6) / (n * PITCH)
        h0 = top_half + (bot_half - top_half) * f0
        h1 = top_half + (bot_half - top_half) * f1
        slot = n - i  # 顶层用最深的序数色
        slot = max(1, min(5, slot))
        pts = f"{cx - h0:.1f},{y0:.1f} {cx + h0:.1f},{y0:.1f} {cx + h1:.1f},{y1:.1f} {cx - h1:.1f},{y1:.1f}"
        name = lv.get("name", "")
        tag = lv.get("tag", "")
        parts.append(f'<polygon points="{pts}" fill="var(--o{slot})"><title>{esc(name)} {esc(tag)}</title></polygon>')
        ink = f"var(--o{slot}-ink)"
        ty = y0 + BAR / 2
        if tag:
            parts.append(txt(cx, ty - 3, name, 16, "middle", "vt-on", "700", ink))
            parts.append(txt(cx, ty + 16, tag, 12.5, "middle", "vt-on", "400", ink))
        else:
            parts.append(txt(cx, ty + 6, name, 16, "middle", "vt-on", "700", ink))
    parts.append("</svg>")
    rows = [[lv.get("name", ""), lv.get("tag", ""), lv.get("size", ""), lv.get("desc", "")] for lv in levels]
    tbl = mini_table(b.get("columns") or ["层级", "标签", "规模/占比", "定义与晋级条件"], rows)
    return figure("".join(parts), b.get("caption", ""), b.get("note", ""), tbl)


def b_funnel(b) -> str:
    """招募/转化漏斗：宽度 ∝ 数量，左侧直标数值，右侧标环节转化率。"""
    stages = b.get("stages", [])
    n = len(stages)
    if n == 0:
        return missing_note("漏斗需要至少 1 个环节（stages）。")
    vals = [max(0.0, _num(s.get("value"))) for s in stages]
    vmax = max(vals) or 1.0
    W, PITCH, BAR = 900.0, 74.0, 60.0
    H = n * PITCH + 16
    cx, maxhalf, minhalf = 500.0, 250.0, 26.0
    parts = [svg_open(W, H, b.get("caption", "转化漏斗"))]
    for i, s in enumerate(stages):
        v = vals[i]
        y0 = i * PITCH + 8
        y1 = y0 + BAR
        h0 = max(minhalf, maxhalf * (v / vmax))
        nxt = vals[i + 1] if i + 1 < n else v
        h1 = max(minhalf, maxhalf * (nxt / vmax))
        slot = min(5, i + 1)
        pts = f"{cx - h0:.1f},{y0:.1f} {cx + h0:.1f},{y0:.1f} {cx + h1:.1f},{y1:.1f} {cx - h1:.1f},{y1:.1f}"
        parts.append(f'<polygon points="{pts}" fill="var(--o{slot})">'
                     f'<title>{esc(s.get("name", ""))}：{esc(fmt_num(v))}</title></polygon>')
        parts.append(txt(228, y0 + BAR / 2 - 2, s.get("name", ""), 14.5, "end", "vt-1", "600"))
        unit = b.get("unit", "")
        parts.append(txt(228, y0 + BAR / 2 + 17, f"{fmt_num(v)}{unit}", 13, "end", "vt-2"))
        if i + 1 < n and v > 0:
            conv = vals[i + 1] / v * 100
            parts.append(txt(772, y1 + 6, f"↓ {conv:.1f}%", 13, "start", "vt-2", "600"))
            hint = stages[i + 1].get("note", "")
            if hint:
                parts.append(txt(772, y1 + 24, hint, 11.5, "start", "vt-3"))
    parts.append("</svg>")
    rows = []
    for i, s in enumerate(stages):
        conv = f"{vals[i] / vals[i - 1] * 100:.1f}%" if i and vals[i - 1] else "—"
        tot = f"{vals[i] / vals[0] * 100:.1f}%" if vals[0] else "—"
        rows.append([s.get("name", ""), fmt_num(vals[i]) + b.get("unit", ""), conv, tot, s.get("note", "")])
    tbl = mini_table(["环节", "数量", "环节转化", "累计转化", "基准/备注"], rows)
    return figure("".join(parts), b.get("caption", ""), b.get("note", ""), tbl)


def b_radar(b) -> str:
    """雷达图：最多 2 个序列（现状 vs 目标），必带图例与数据表。"""
    axes = b.get("axes", [])
    series = b.get("series", [])[:2]
    n = len(axes)
    if n < 3 or not series:
        return missing_note("雷达图需要 ≥3 个维度且至少 1 组数值。维度不足时改用 kpis 或 bars。")
    vmax = _num(b.get("max"), 100.0) or 100.0
    W, H = 600.0, 500.0
    cx, cy, R = 300.0, 246.0, 168.0
    parts = [svg_open(W, H, b.get("caption", "健康度雷达"))]

    def pt(idx, val):
        a = -math.pi / 2 + 2 * math.pi * idx / n
        r = R * max(0.0, min(1.0, val / vmax))
        return cx + r * math.cos(a), cy + r * math.sin(a)

    for ring in (0.25, 0.5, 0.75, 1.0):
        pts = []
        for i in range(n):
            a = -math.pi / 2 + 2 * math.pi * i / n
            pts.append(f"{cx + R * ring * math.cos(a):.1f},{cy + R * ring * math.sin(a):.1f}")
        parts.append(f'<polygon points="{" ".join(pts)}" fill="none" class="grid-line"/>')
    for i in range(n):
        a = -math.pi / 2 + 2 * math.pi * i / n
        parts.append(f'<line x1="{cx}" y1="{cy}" x2="{cx + R * math.cos(a):.1f}" '
                     f'y2="{cy + R * math.sin(a):.1f}" class="grid-line"/>')
    # 红线阈值环
    thr = b.get("threshold")
    if thr:
        pts = []
        for i in range(n):
            a = -math.pi / 2 + 2 * math.pi * i / n
            r = R * float(thr) / vmax
            pts.append(f"{cx + r * math.cos(a):.1f},{cy + r * math.sin(a):.1f}")
        parts.append(f'<polygon points="{" ".join(pts)}" fill="none" stroke="{STATUS["critical"][0]}" '
                     f'stroke-width="1.5" opacity="0.65"/>')
    # 序列固定用 1 号（蓝）与 3 号（青）色位：避开 2 号橙，防止与红色红线阈值混淆
    slots = [1, 3]
    for si, s in enumerate(series):
        sl = slots[si % len(slots)]
        vals = [_clamp(_num(v), 0.0, vmax) for v in s.get("values", [])][:n]
        if len(vals) < n:
            vals += [0.0] * (n - len(vals))
        pts, marks = [], []
        for i, v in enumerate(vals):
            x, y = pt(i, v)
            pts.append(f"{x:.1f},{y:.1f}")
            marks.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="var(--s{sl})" '
                         f'class="mark-ring"><title>{esc(s.get("name", ""))} · '
                         f'{esc(axes[i] if isinstance(axes[i], str) else axes[i].get("name", ""))}：'
                         f'{fmt_num(v)}</title></circle>')
        parts.append(f'<polygon points="{" ".join(pts)}" fill="var(--s{sl})" fill-opacity="0.16" '
                     f'stroke="var(--s{sl})" stroke-width="2"/>')
        parts.extend(marks)
    for i, ax in enumerate(axes):
        name = ax if isinstance(ax, str) else ax.get("name", "")
        a = -math.pi / 2 + 2 * math.pi * i / n
        lx, ly = cx + (R + 30) * math.cos(a), cy + (R + 30) * math.sin(a)
        anchor = "middle" if abs(math.cos(a)) < 0.25 else ("start" if math.cos(a) > 0 else "end")
        parts.append(txt(lx, ly + 4, name, 13, anchor, "vt-2", "600"))
    parts.append("</svg>")
    lg = legend([(s.get("name", f"序列{i + 1}"), f"var(--s{slots[i % len(slots)]})", "")
                 for i, s in enumerate(series)]
                + ([("✕ 红线阈值", STATUS["critical"][0], str(thr))] if thr else []))
    names = [a if isinstance(a, str) else a.get("name", "") for a in axes]
    rows = []
    for i, nm in enumerate(names):
        row = [nm]
        for s in series:
            vs = s.get("values", [])
            row.append(fmt_num(vs[i]) if i < len(vs) else "—")
        if thr:
            row.append(str(thr))
        rows.append(row)
    cols = ["维度"] + [s.get("name", "") for s in series] + (["红线"] if thr else [])
    return figure("".join(parts) + lg, b.get("caption", ""), b.get("note", ""), mini_table(cols, rows))


def b_gantt(b) -> str:
    """甘特图：横轴为天，可选真实日期；同 track 同色，无 track 则单色。"""
    phases = b.get("phases", [])
    if not phases:
        return missing_note("甘特图需要至少 1 个阶段（phases）。")
    tracks = []
    for p in phases:
        t = p.get("track")
        if t and t not in tracks:
            tracks.append(t)
    tracks = tracks[:8]
    lo = min(_num(p.get("from")) for p in phases)
    hi = max(_num(p.get("to")) for p in phases)
    if hi < lo:
        lo, hi = hi, lo
    span = max(1.0, hi - lo)
    LBL, X0, X1 = 168.0, 182.0, 872.0
    PITCH, BAR = 36.0, 22.0
    top = 34.0 + (22.0 if b.get("markers") else 0.0)  # 有里程碑时抬高，避免与日期刻度撞行
    H = top + len(phases) * PITCH + 26
    W = 900.0

    def x_of(d):
        return X0 + (float(d) - lo) / span * (X1 - X0)

    step = 7 if span <= 45 else (14 if span <= 120 else 30)
    start = b.get("start")
    d0 = None
    if start:
        try:
            d0 = datetime.strptime(str(start), "%Y-%m-%d").date()
        except ValueError:
            d0 = None
    parts = [svg_open(W, H, b.get("caption", "节奏排期"))]
    t = math.floor(lo / step) * step
    while t <= hi + 0.01:
        if t >= lo - 0.01:
            x = x_of(t)
            parts.append(f'<line x1="{x:.1f}" y1="{top - 12:.1f}" x2="{x:.1f}" y2="{H - 22:.1f}" class="grid-line"/>')
            lab = (d0 + timedelta(days=int(t))).strftime("%m/%d") if d0 else (f"D{int(t)}" if t >= 0 else f"D{int(t)}")
            parts.append(txt(x, top - 18, lab, 11.5, "middle", "vt-3"))
        t += step
    for i, p in enumerate(phases):
        y = top + i * PITCH
        x0, x1 = x_of(_num(p.get("from"))), x_of(_num(p.get("to")))
        if x1 < x0:
            x0, x1 = x1, x0
        x0 = _clamp(x0, X0, X1)
        x1 = _clamp(x1, X0, X1)
        w = max(6.0, min(x1 - x0, X1 - x0))
        if p.get("track") in tracks:
            slot = tracks.index(p["track"]) + 1
            color, ink = f"var(--s{slot})", f"var(--s{slot}-ink)"
        else:
            color, ink = "var(--s1)", "var(--s1-ink)"
        parts.append(txt(LBL, y + BAR / 2 + 5, p.get("name", ""), 13.5, "end", "vt-1", "600"))
        parts.append(f'<rect x="{x0:.1f}" y="{y:.1f}" width="{w:.1f}" height="{BAR}" rx="4" fill="{color}">'
                     f'<title>{esc(p.get("name", ""))}：{esc(str(p.get("from", 0)))}→'
                     f'{esc(str(p.get("to", 0)))}</title></rect>')
        gate = p.get("gate") or p.get("note") or ""
        if gate:
            if w > 150:
                parts.append(txt(x0 + 10, y + BAR / 2 + 5, gate, 12, "start", "vt-on", "600", ink))
            else:
                parts.append(txt(x1 + 8, y + BAR / 2 + 5, gate, 12, "start", "vt-2"))
    for m in b.get("markers", []):
        x = x_of(m.get("day", 0))
        parts.append(f'<path d="M{x:.1f} {top - 40} l6 7 l-6 7 l-6 -7 z" fill="{STATUS["critical"][0]}"/>')
        parts.append(f'<line x1="{x:.1f}" y1="{top - 26:.1f}" x2="{x:.1f}" y2="{H - 22:.1f}" '
                     f'stroke="{STATUS["critical"][0]}" stroke-width="1" opacity="0.35"/>')
        parts.append(txt(x, top - 46, m.get("label", ""), 11.5, "middle", "vt-2", "700"))
    parts.append("</svg>")
    lg = legend([(t, f"var(--s{i + 1})", "") for i, t in enumerate(tracks)]) if len(tracks) > 1 else ""
    rows = []
    for p in phases:
        f_, t_ = p.get("from", 0), p.get("to", 0)
        when = f"D{f_} ~ D{t_}"
        if d0:
            when = (f"{(d0 + timedelta(days=int(f_))).strftime('%m/%d')} ~ "
                    f"{(d0 + timedelta(days=int(t_))).strftime('%m/%d')}")
        rows.append([p.get("name", ""), p.get("track", ""), when,
                     f"{int(float(t_) - float(f_))} 天", p.get("gate", "") or p.get("note", "")])
    tbl = mini_table(["阶段", "线", "时间窗", "时长", "卡点/交付"], rows)
    return figure("".join(parts) + lg, b.get("caption", ""), b.get("note", ""), tbl)


def b_donut(b) -> str:
    """环形图：≤6 段；超过 6 段自动降级为条形图（更易读）。"""
    items = b.get("items", [])
    if len(items) > 6:
        return b_bars({"items": [{"name": i.get("name"), "value": i.get("value"), "note": i.get("note", "")}
                                 for i in items],
                       "unit": b.get("unit", ""), "caption": b.get("caption", ""), "note": b.get("note", "")})
    items = [i for i in items if _num(i.get("value")) > 0]
    if not items:
        return missing_note("环形图需要至少一个正数值。")
    total = sum(_num(i.get("value")) for i in items) or 1.0
    W, H = 460.0, 300.0
    cx, cy, R, r = 150.0, 150.0, 118.0, 74.0
    parts = [svg_open(W, H, b.get("caption", "占比构成"))]
    ang = -math.pi / 2
    gap = 0.018  # 段间留 2px 级别的表面缝隙
    for i, it in enumerate(items):
        v = _num(it.get("value"))
        sweep = 2 * math.pi * v / total
        a0, a1 = ang + gap / 2, ang + sweep - gap / 2
        if a1 <= a0:
            ang += sweep
            continue
        large = 1 if (a1 - a0) > math.pi else 0
        x0, y0 = cx + R * math.cos(a0), cy + R * math.sin(a0)
        x1, y1 = cx + R * math.cos(a1), cy + R * math.sin(a1)
        xi1, yi1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
        xi0, yi0 = cx + r * math.cos(a0), cy + r * math.sin(a0)
        d = (f"M{x0:.1f} {y0:.1f} A{R} {R} 0 {large} 1 {x1:.1f} {y1:.1f} "
             f"L{xi1:.1f} {yi1:.1f} A{r} {r} 0 {large} 0 {xi0:.1f} {yi0:.1f} Z")
        parts.append(f'<path d="{d}" fill="var(--s{i + 1})"><title>{esc(it.get("name", ""))}：'
                     f'{esc(fmt_num(v))}（{v / total * 100:.1f}%）</title></path>')
        ang += sweep
    center = b.get("center") or {}
    parts.append(txt(cx, cy - 2, str(center.get("value", fmt_num(total))), 26, "middle", "vt-1", "700"))
    parts.append(txt(cx, cy + 20, str(center.get("label", "合计")), 12.5, "middle", "vt-3"))
    parts.append("</svg>")
    lg = legend([(it.get("name", ""), f"var(--s{i + 1})",
                  f'{fmt_num(it.get("value", 0))}{b.get("unit", "")} · '
                  f'{float(it.get("value", 0) or 0) / total * 100:.0f}%')
                 for i, it in enumerate(items)])
    return figure(f'<div class="donut-wrap">{"".join(parts)}{lg}</div>', b.get("caption", ""), b.get("note", ""))


def b_stack(b) -> str:
    """100% 堆叠条：段间留缝，宽度够就内标，不够就靠图例。"""
    raw = [i for i in b.get("items", []) if _num(i.get("value")) > 0]
    dropped = len(b.get("items", [])) - len(raw)
    items = raw
    if len(items) > 8:                       # 不静默截断：尾部合并成「其他」
        head, tail = items[:7], items[7:]
        items = head + [{"name": f"其他（{len(tail)} 项合并）",
                         "value": sum(_num(i.get("value")) for i in tail)}]
    if not items:
        return missing_note("堆叠图需要至少一个正数值。负数与零值不能参与 100% 构成图。")
    total = sum(_num(i.get("value")) for i in items) or 1.0
    W, H = 900.0, 96.0
    x, y, bar = 6.0, 26.0, 44.0
    usable = W - 12
    parts = [svg_open(W, H, b.get("caption", "构成占比"))]
    for i, it in enumerate(items):
        v = _num(it.get("value"))
        w = usable * v / total
        wd = max(2.0, w - 2)  # 2px 表面缝隙
        pct = v / total * 100
        parts.append(f'<rect x="{x:.1f}" y="{y}" width="{wd:.1f}" height="{bar}" rx="4" fill="var(--s{i + 1})">'
                     f'<title>{esc(it.get("name", ""))}：{esc(fmt_num(v))}（{pct:.1f}%）</title></rect>')
        if wd > 86:
            parts.append(txt(x + wd / 2, y + 20, it.get("name", ""), 12.5, "middle", "vt-on", "700",
                             f"var(--s{i + 1}-ink)"))
            parts.append(txt(x + wd / 2, y + 36, f"{pct:.0f}%", 12, "middle", "vt-on", "400",
                             f"var(--s{i + 1}-ink)"))
        x += w
    parts.append("</svg>")
    lg = legend([(it.get("name", ""), f"var(--s{i + 1})",
                  f'{fmt_num(it.get("value", 0))}{b.get("unit", "")}')
                 for i, it in enumerate(items)])
    note = b.get("note", "")
    if dropped:
        note = (note + " " if note else "") + f"（已剔除 {dropped} 项非正数值：构成图只接受正数）"
    return figure("".join(parts) + lg, b.get("caption", ""), note)


def b_bars(b) -> str:
    """横向条形图：单一度量单色（颜色不重复编码长度），值直标在条端。"""
    items = b.get("items", [])
    if not items:
        return missing_note("条形图需要至少 1 个数据项（items）。")
    vals = [max(0.0, _num(i.get("value"))) for i in items]
    vmax = max(vals + [max(0.0, _num(b.get("target")))]) or 1.0
    LBL, X0, X1 = 190.0, 200.0, 800.0
    PITCH, BAR = 34.0, 20.0
    H = len(items) * PITCH + 26
    W = 900.0
    parts = [svg_open(W, H, b.get("caption", "对比"))]
    tgt = b.get("target")
    if tgt:
        tx = X0 + float(tgt) / vmax * (X1 - X0)
        parts.append(f'<line x1="{tx:.1f}" y1="10" x2="{tx:.1f}" y2="{H - 20:.1f}" '
                     f'stroke="{STATUS["critical"][0]}" stroke-width="1.5"/>')
        parts.append(txt(tx + 6, 20, f'{b.get("targetLabel", "目标线")} {fmt_num(tgt)}', 11.5, "start", "vt-2", "600"))
    for i, it in enumerate(items):
        y = 22 + i * PITCH
        v = float(it.get("value", 0) or 0)
        w = max(3.0, v / vmax * (X1 - X0))
        tone = it.get("tone")
        color = STATUS[tone_of(tone)][0] if tone else "var(--s1)"
        parts.append(txt(LBL - 10, y + BAR / 2 + 5, it.get("name", ""), 13.5, "end", "vt-1", "600"))
        parts.append(f'<rect x="{X0}" y="{y}" width="{w:.1f}" height="{BAR}" rx="4" fill="{color}">'
                     f'<title>{esc(it.get("name", ""))}：{esc(fmt_num(v))}</title></rect>')
        vlabel = f'{fmt_num(v)}{b.get("unit", "")}'
        parts.append(txt(X0 + w + 8, y + BAR / 2 + 5, vlabel, 12.5, "start", "vt-2", "600"))
        if it.get("note"):
            # 备注紧跟数值之后，按数值文本宽度让位（中文按 12px 估算，数字按 7px）
            vw = sum(12 if ord(c) > 127 else 7 for c in vlabel) + 18
            parts.append(txt(X0 + w + 8 + vw, y + BAR / 2 + 5, it["note"], 11.5, "start", "vt-3"))
    parts.append("</svg>")
    return figure("".join(parts), b.get("caption", ""), b.get("note", ""))


def b_ladder(b) -> str:
    """阶梯图：等级/佣金阶梯，柱高 ∝ 数值，柱下标门槛，柱上标数值。"""
    steps = b.get("steps", [])
    n = len(steps)
    if n == 0:
        return missing_note("阶梯图需要至少 1 档（steps）。")
    vals = [max(0.0, _num(s.get("value"))) for s in steps]
    vmax = max(vals) or 1.0
    W = 900.0
    H = 330.0
    base, top = 250.0, 40.0
    slotw = (W - 60) / n
    parts = [svg_open(W, H, b.get("caption", "阶梯"))]
    parts.append(f'<line x1="30" y1="{base}" x2="{W - 30}" y2="{base}" class="axis-line"/>')
    for i, s in enumerate(steps):
        v = vals[i]
        h = max(6.0, (v / vmax) * (base - top))
        bw = min(120.0, slotw * 0.56)
        cx = 30 + slotw * (i + 0.5)
        x = cx - bw / 2
        y = base - h
        slot = min(5, i + 1)
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{h:.1f}" rx="4" '
                     f'fill="var(--o{slot})"><title>{esc(s.get("name", ""))}：{esc(fmt_num(v))}'
                     f'{esc(b.get("unit", ""))}</title></rect>')
        parts.append(txt(cx, y - 10, f'{fmt_num(v)}{b.get("unit", "")}', 14, "middle", "vt-1", "700"))
        parts.append(txt(cx, base + 22, s.get("name", ""), 13.5, "middle", "vt-1", "600"))
        if s.get("threshold"):
            parts.append(txt(cx, base + 42, s["threshold"], 12, "middle", "vt-2"))
        if s.get("note"):
            parts.append(txt(cx, base + 60, s["note"], 11.5, "middle", "vt-3"))
    parts.append("</svg>")
    return figure("".join(parts), b.get("caption", ""), b.get("note", ""))


def b_quadrant(b) -> str:
    """四象限定位图：x/y 取 0-100，用于选人（内容力 × 转化力）等定位判断。"""
    items = b.get("items", [])
    W, H = 720.0, 560.0
    L, R_, T, B = 90.0, 660.0, 40.0, 480.0
    parts = [svg_open(W, H, b.get("caption", "四象限定位"))]
    parts.append(f'<rect x="{L}" y="{T}" width="{R_ - L}" height="{B - T}" fill="none" class="axis-line"/>')
    mx, my = (L + R_) / 2, (T + B) / 2
    parts.append(f'<line x1="{mx}" y1="{T}" x2="{mx}" y2="{B}" class="grid-line"/>')
    parts.append(f'<line x1="{L}" y1="{my}" x2="{R_}" y2="{my}" class="grid-line"/>')
    ql = b.get("quadrants", {})
    parts.append(txt(mx + 12, T + 22, ql.get("tr", ""), 13, "start", "vt-3", "600"))
    parts.append(txt(mx - 12, T + 22, ql.get("tl", ""), 13, "end", "vt-3", "600"))
    parts.append(txt(mx + 12, B - 12, ql.get("br", ""), 13, "start", "vt-3", "600"))
    parts.append(txt(mx - 12, B - 12, ql.get("bl", ""), 13, "end", "vt-3", "600"))
    for i, it in enumerate(items):
        x = L + _clamp(_num(it.get("x")), 0, 100) / 100 * (R_ - L)
        y = B - _clamp(_num(it.get("y")), 0, 100) / 100 * (B - T)
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="var(--s1)" class="mark-ring">'
                     f'<title>{esc(it.get("name", ""))}（x={esc(str(it.get("x", 0)))}, '
                     f'y={esc(str(it.get("y", 0)))}）</title></circle>')
        dy = -14 if i % 2 == 0 else 22
        parts.append(txt(x, y + dy, it.get("name", ""), 12.5, "middle", "vt-1", "600"))
    parts.append(txt((L + R_) / 2, B + 34, b.get("xLabel", ""), 13, "middle", "vt-2", "600"))
    parts.append(f'<text x="26" y="{(T + B) / 2}" font-size="13" text-anchor="middle" font-weight="600" '
                 f'class="vt-2" transform="rotate(-90 26 {(T + B) / 2})">{esc(b.get("yLabel", ""))}</text>')
    parts.append("</svg>")
    rows = [[it.get("name", ""), it.get("x", ""), it.get("y", ""), it.get("note", "")] for it in items]
    tbl = mini_table([b.get("nameLabel", "对象"), b.get("xLabel", "X"), b.get("yLabel", "Y"), "处置建议"], rows)
    return figure("".join(parts), b.get("caption", ""), b.get("note", ""), tbl)


def b_flow(b) -> str:
    """链路图：HTML 箭头流程，文字自动换行，窄屏自动竖排。"""
    steps = b.get("steps", [])
    cells = []
    for i, s in enumerate(steps):
        tag = f'<div class="fl-tag">{rich(s.get("tag", ""))}</div>' if s.get("tag") else ""
        desc = f'<div class="fl-d">{rich(s.get("desc", ""))}</div>' if s.get("desc") else ""
        cells.append(f'<div class="fl-n">{tag}<div class="fl-t">{rich(s.get("title", ""))}</div>{desc}</div>')
        if i < len(steps) - 1:
            cells.append('<div class="fl-a" aria-hidden="true">→</div>')
    cap = f'<figcaption class="fig-cap">{rich(b["caption"])}</figcaption>' if b.get("caption") else ""
    note = f'<p class="fig-note">{rich(b["note"])}</p>' if b.get("note") else ""
    return f'<figure class="fig">{cap}<div class="flow">{"".join(cells)}</div>{note}</figure>'


def b_steps(b) -> str:
    """SOP 时间轴：每步含时间、负责人、动作、验收标准。"""
    items = b.get("items", [])
    lis = []
    for it in items:
        when = f'<span class="st-w">{rich(it.get("when", ""))}</span>' if it.get("when") else ""
        owner = f'<span class="st-o">{rich(it.get("owner", ""))}</span>' if it.get("owner") else ""
        gate = (f'<div class="st-g"><span class="st-gl">验收</span>{rich(it.get("gate", ""))}</div>'
                if it.get("gate") else "")
        desc = f'<div class="st-d">{prose_html(it.get("desc", ""))}</div>' if it.get("desc") else ""
        lis.append(f'<li class="st"><div class="st-h">{when}<span class="st-t">{rich(it.get("title", ""))}</span>'
                   f'{owner}</div>{desc}{gate}</li>')
    cap = f'<figcaption class="fig-cap">{rich(b["caption"])}</figcaption>' if b.get("caption") else ""
    return f'<figure class="fig">{cap}<ol class="steps">{"".join(lis)}</ol></figure>'


def b_checklist(b) -> str:
    items = b.get("items", [])
    lis = []
    for it in items:
        if isinstance(it, str):
            it = {"text": it}
        lvl = it.get("level", "must")
        tone = {"must": "good", "avoid": "critical", "watch": "warn", "check": "info"}.get(lvl, "info")
        color, icon = STATUS[tone_of(tone)]
        note = f'<div class="ck-n">{rich(it.get("note", ""))}</div>' if it.get("note") else ""
        lis.append(f'<li class="ck ck-{tone_of(tone)}"><span class="ck-i" aria-hidden="true">{icon}</span>'
                   f'<div><div class="ck-t">{rich(it.get("text", ""))}</div>{note}</div></li>')
    cap = f'<figcaption class="fig-cap">{rich(b["caption"])}</figcaption>' if b.get("caption") else ""
    return f'<figure class="fig">{cap}<ul class="checklist">{"".join(lis)}</ul></figure>'


def b_cards(b) -> str:
    items = b.get("items", [])
    cs = []
    for it in items:
        tag = f'<div class="cd-tag">{rich(it.get("tag", ""))}</div>' if it.get("tag") else ""
        meta = f'<div class="cd-m">{rich(it.get("meta", ""))}</div>' if it.get("meta") else ""
        cs.append(f'<div class="cd">{tag}<div class="cd-t">{rich(it.get("title", ""))}</div>'
                  f'<div class="cd-b">{prose_html(it.get("body", ""))}</div>{meta}</div>')
    cap = f'<figcaption class="fig-cap">{rich(b["caption"])}</figcaption>' if b.get("caption") else ""
    cols = int(b.get("columns", 3))
    return f'<figure class="fig">{cap}<div class="cards cards-{cols}">{"".join(cs)}</div></figure>'


BLOCKS = {
    "kpis": b_kpis, "callout": b_callout, "table": b_table, "prose": b_prose, "quote": b_quote,
    "divider": b_divider, "pyramid": b_pyramid, "funnel": b_funnel, "radar": b_radar,
    "gantt": b_gantt, "donut": b_donut, "stack": b_stack, "bars": b_bars, "ladder": b_ladder,
    "quadrant": b_quadrant, "flow": b_flow, "steps": b_steps, "checklist": b_checklist, "cards": b_cards,
}

BLOCK_HELP = {
    "kpis": '{"type":"kpis","items":[{"label":"KOC 池规模","value":320,"unit":"人","note":"目标 500","tone":"good"}]}',
    "callout": '{"type":"callout","tone":"warn|good|critical|info","title":"标题","text":"正文，支持 - 列表"}',
    "table": '{"type":"table","caption":"","columns":["列A",{"name":"列B","align":"right"}],'
             '"rows":[["值",{"text":"达标","tone":"good"}]],"note":"口径说明"}',
    "prose": '{"type":"prose","text":"段落。\\n- 列表项\\n1. 有序项"}',
    "quote": '{"type":"quote","text":"一句话","by":"出处"}',
    "divider": '{"type":"divider"}',
    "pyramid": '{"type":"pyramid","caption":"","levels":[{"name":"L4 合伙人","tag":"Top 1%",'
               '"size":"5 人","desc":"晋级条件…"}]}  # 最多 5 层，从顶层写起',
    "funnel": '{"type":"funnel","caption":"","unit":"人","stages":[{"name":"触达","value":5000,'
              '"note":"基准 100%"}]}',
    "radar": '{"type":"radar","caption":"","max":100,"threshold":60,"axes":["规模","活跃"],'
             '"series":[{"name":"现状","values":[40,55]},{"name":"3个月目标","values":[70,75]}]}',
    "gantt": '{"type":"gantt","caption":"","start":"2026-09-01","phases":[{"name":"招募启动",'
             '"track":"招募","from":0,"to":14,"gate":"入池 100 人"}],"markers":[{"day":30,"label":"复盘"}]}',
    "donut": '{"type":"donut","caption":"","unit":"元","center":{"label":"月预算","value":"8 万"},'
             '"items":[{"name":"寄样","value":30000}]}  # ≤6 段，超过自动转条形图',
    "stack": '{"type":"stack","caption":"","unit":"%","items":[{"name":"达人佣金","value":20}]}',
    "bars": '{"type":"bars","caption":"","unit":"人","target":100,"targetLabel":"月目标",'
            '"items":[{"name":"老客池","value":120,"note":"转化率最高"}]}',
    "ladder": '{"type":"ladder","caption":"","unit":"%","steps":[{"name":"L1 体验官","value":10,'
              '"threshold":"月出 1 篇","note":"无佣金，只给样品"}]}',
    "quadrant": '{"type":"quadrant","caption":"","xLabel":"内容力","yLabel":"转化力",'
                '"quadrants":{"tl":"高转化低内容","tr":"重点培养","bl":"淘汰观察","br":"内容素材位"},'
                '"items":[{"name":"KOC-张三","x":72,"y":65,"note":"升 L3"}]}',
    "flow": '{"type":"flow","caption":"","steps":[{"tag":"S1","title":"招募","desc":"六池扫描"}]}',
    "steps": '{"type":"steps","caption":"","items":[{"when":"D0","title":"入群欢迎","owner":"社群运营",'
             '"desc":"发放新人包","gate":"24h 内完成资料登记"}]}',
    "checklist": '{"type":"checklist","caption":"","items":[{"text":"报备笔记","level":"must|avoid|watch|check",'
                 '"note":"依据…"}]}',
    "cards": '{"type":"cards","caption":"","columns":3,"items":[{"tag":"渠道","title":"老客池",'
             '"body":"正文","meta":"预估 120 人"}]}',
}


# ---------------------------------------------------------------------------
# 页面骨架
# ---------------------------------------------------------------------------

CSS = """
*,*::before,*::after{box-sizing:border-box}
:root{
  color-scheme:light;
  --plane:#f9f9f7; --surface:#fcfcfb; --surface-2:#f3f3ef;
  --ink:#0b0b0b; --ink-2:#52514e; --ink-3:#898781;
  --grid:#e1e0d9; --axis:#c3c2b7; --border:rgba(11,11,11,.10); --border-2:rgba(11,11,11,.16);
  --brand:#d4503c; --brand-2:#f0785f; --brand-soft:rgba(212,80,60,.10);
  --shadow:0 1px 2px rgba(11,11,11,.04),0 8px 24px rgba(11,11,11,.06);
__LIGHT_PALETTE__
}
@media (prefers-color-scheme:dark){
  :root:where(:not([data-theme="light"])){
    color-scheme:dark;
    --plane:#0d0d0d; --surface:#1a1a19; --surface-2:#232322;
    --ink:#ffffff; --ink-2:#c3c2b7; --ink-3:#898781;
    --grid:#2c2c2a; --axis:#383835; --border:rgba(255,255,255,.10); --border-2:rgba(255,255,255,.18);
    --brand:#ff8a6b; --brand-2:#ffb27a; --brand-soft:rgba(255,138,107,.12);
    --shadow:0 1px 2px rgba(0,0,0,.4),0 10px 30px rgba(0,0,0,.35);
__DARK_PALETTE__
  }
}
:root[data-theme="dark"]{
  color-scheme:dark;
  --plane:#0d0d0d; --surface:#1a1a19; --surface-2:#232322;
  --ink:#ffffff; --ink-2:#c3c2b7; --ink-3:#898781;
  --grid:#2c2c2a; --axis:#383835; --border:rgba(255,255,255,.10); --border-2:rgba(255,255,255,.18);
  --brand:#ff8a6b; --brand-2:#ffb27a; --brand-soft:rgba(255,138,107,.12);
  --shadow:0 1px 2px rgba(0,0,0,.4),0 10px 30px rgba(0,0,0,.35);
__DARK_PALETTE__
}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--plane);color:var(--ink);
  font-family:system-ui,-apple-system,"PingFang SC","Hiragino Sans GB","Microsoft YaHei","Source Han Sans SC",sans-serif;
  font-size:15px;line-height:1.72;letter-spacing:.01em}
.wrap{max-width:1180px;margin:0 auto;padding:0 22px 96px}
a{color:var(--brand);text-decoration:none;border-bottom:1px solid var(--brand-soft)}

/* 顶栏 */
.topbar{position:sticky;top:0;z-index:50;backdrop-filter:saturate(1.4) blur(10px);
  background:color-mix(in srgb,var(--plane) 88%,transparent);border-bottom:1px solid var(--border)}
.topbar-in{max-width:1180px;margin:0 auto;padding:9px 22px;display:flex;align-items:center;gap:12px}
.tb-t{font-weight:700;font-size:14px;letter-spacing:.02em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tb-s{color:var(--ink-3);font-size:12.5px;white-space:nowrap}
.tb-sp{flex:1}
.btn{appearance:none;border:1px solid var(--border-2);background:var(--surface);color:var(--ink-2);
  border-radius:8px;padding:5px 11px;font-size:12.5px;cursor:pointer;font-family:inherit;white-space:nowrap}
.btn:hover{border-color:var(--brand);color:var(--brand)}

/* 封面 */
.cover{padding:60px 0 34px;border-bottom:1px solid var(--border)}
.cover-tag{display:inline-flex;align-items:center;gap:8px;font-size:12.5px;font-weight:700;letter-spacing:.16em;
  color:var(--brand);text-transform:uppercase}
.cover-tag::before{content:"";width:26px;height:2px;background:var(--brand);border-radius:2px}
h1.cover-t{font-size:clamp(30px,4.6vw,46px);line-height:1.2;margin:16px 0 10px;letter-spacing:-.01em;font-weight:800}
.cover-s{font-size:clamp(15px,1.7vw,18px);color:var(--ink-2);max-width:74ch;margin:0 0 22px}
.cover-meta{display:flex;flex-wrap:wrap;gap:8px 20px;font-size:13px;color:var(--ink-3);margin-bottom:26px}
.cover-meta b{color:var(--ink-2);font-weight:600}
.verdict{display:flex;gap:16px;align-items:flex-start;border:1px solid var(--border);border-left:4px solid var(--vc);
  background:var(--surface);border-radius:12px;padding:18px 20px;box-shadow:var(--shadow);max-width:960px}
.verdict-i{font-size:19px;line-height:1.3;color:var(--vc);font-weight:800}
.verdict-l{font-size:12.5px;font-weight:700;letter-spacing:.08em;color:var(--vc);margin-bottom:3px}
.verdict-t{font-size:17px;font-weight:700;margin-bottom:5px;line-height:1.5}
.verdict-b{color:var(--ink-2);font-size:14.5px}

/* 布局 */
/* minmax(0,1fr) 而不是 1fr：否则栅格轨道会被内容顶宽，导致页面横向溢出 */
.layout{display:grid;grid-template-columns:minmax(0,1fr);gap:34px;margin-top:34px}
@media (min-width:1080px){.layout{grid-template-columns:212px minmax(0,1fr);gap:44px}}
.layout>*{min-width:0}
.toc{align-self:start;font-size:13.5px;min-width:0}
@media (min-width:1080px){.toc{position:sticky;top:70px;max-height:calc(100vh - 100px);overflow:auto}}
/* 窄屏：目录收成一行可换行的胶囊，避免长列表占满一屏 */
@media (max-width:1079px){
  .toc{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
  .toc-h{width:100%;margin:0 0 2px}
  .toc a{border-left:0;border:1px solid var(--border);border-radius:999px;padding:4px 11px;white-space:nowrap}
  .toc a.on{border-color:var(--brand)}
}
.toc-h{font-size:11.5px;letter-spacing:.14em;color:var(--ink-3);font-weight:700;margin-bottom:10px}
.toc a{display:block;padding:5px 10px;border-left:2px solid var(--border);color:var(--ink-2);border-bottom:0;
  border-radius:0 6px 6px 0}
.toc a:hover{color:var(--brand);background:var(--brand-soft)}
.toc a.on{color:var(--brand);border-left-color:var(--brand);font-weight:600;background:var(--brand-soft)}

section.sec{scroll-margin-top:74px;margin-bottom:52px}
.sec-h{display:flex;align-items:baseline;gap:12px;margin-bottom:6px;padding-bottom:12px;border-bottom:1px solid var(--border)}
.sec-n{font-size:12.5px;font-weight:800;color:var(--brand);letter-spacing:.1em;font-variant-numeric:tabular-nums}
h2.sec-t{font-size:clamp(20px,2.4vw,25px);margin:0;font-weight:750;letter-spacing:-.005em}
.sec-s{color:var(--ink-2);font-size:14.5px;margin:10px 0 20px;max-width:80ch}
h3.sub{font-size:16.5px;margin:30px 0 12px;font-weight:700}

/* KPI */
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(178px,1fr));gap:12px;margin:16px 0 22px}
.kpi{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:15px 16px;box-shadow:var(--shadow)}
.kpi-l{font-size:12.5px;color:var(--ink-3);margin-bottom:6px;font-weight:600}
.kpi-v{font-size:27px;font-weight:750;line-height:1.15;letter-spacing:-.02em}
.kpi-u{font-size:14px;font-weight:600;color:var(--ink-2);margin-left:3px}
.kpi-n{font-size:12px;color:var(--ink-3);margin-top:5px;line-height:1.5}
.kpi-good{border-top:3px solid #0ca30c}.kpi-warn{border-top:3px solid #fab219}
.kpi-critical{border-top:3px solid #d03b3b}.kpi-serious{border-top:3px solid #ec835a}
.kpi-info{border-top:3px solid #2a78d6}

/* 提示条 */
.co{display:flex;gap:13px;border:1px solid var(--border);border-left:4px solid var(--cc);background:var(--surface);
  border-radius:10px;padding:14px 16px;margin:16px 0}
.co-i{font-weight:800;color:var(--cc);font-size:15px;line-height:1.6}
.co-b{flex:1;min-width:0}
.co-t{font-weight:700;margin-bottom:3px}
.co-b p{margin:.35em 0}.co-b ul,.co-b ol{margin:.4em 0;padding-left:1.15em}
.co-good{--cc:#0ca30c}.co-warn{--cc:#fab219}.co-critical{--cc:#d03b3b}.co-serious{--cc:#ec835a}.co-info{--cc:#2a78d6}

/* 表格 */
.tbl-wrap{overflow-x:auto;-webkit-overflow-scrolling:touch;border:1px solid var(--border);border-radius:12px;
  background:var(--surface);margin:12px 0}
table{border-collapse:collapse;width:100%;font-size:13.8px;min-width:520px}
th,td{padding:10px 13px;text-align:left;border-bottom:1px solid var(--grid);vertical-align:top;line-height:1.62}
th{background:var(--surface-2);font-weight:700;font-size:12.5px;color:var(--ink-2);white-space:nowrap;
  position:sticky;top:0}
tbody tr:last-child td{border-bottom:0}
tbody tr:hover{background:var(--brand-soft)}
td{font-variant-numeric:tabular-nums}
.tbl-mini{font-size:13px}
code{background:var(--surface-2);border:1px solid var(--border);border-radius:5px;padding:1px 5px;font-size:.9em;
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace}

/* 图 */
.fig{margin:20px 0 26px;padding:0}
.viz{width:100%;height:auto;display:block;overflow:visible}
.fig-cap{font-size:14px;font-weight:700;color:var(--ink-2);margin-bottom:10px}
.fig-note{font-size:12.5px;color:var(--ink-3);margin:8px 0 0;line-height:1.6}
.grid-line{stroke:var(--grid);stroke-width:1}
.axis-line{stroke:var(--axis);stroke-width:1}
.mark-ring{stroke:var(--surface);stroke-width:2}
.vt-1{fill:var(--ink)}.vt-2{fill:var(--ink-2)}.vt-3{fill:var(--ink-3)}
.vt-1,.vt-2,.vt-3,.vt-on{font-family:inherit}
.legend{list-style:none;display:flex;flex-wrap:wrap;gap:6px 20px;padding:0;margin:12px 0 0;font-size:13px}
.legend li{display:flex;align-items:center;gap:7px;color:var(--ink-2)}
.lg-s{width:11px;height:11px;border-radius:3px;flex:none}
.lg-v{color:var(--ink-3);font-variant-numeric:tabular-nums}
.donut-wrap{display:flex;flex-wrap:wrap;gap:8px 28px;align-items:center}
.donut-wrap .viz{max-width:380px;flex:1 1 300px}
.donut-wrap .legend{flex-direction:column;gap:8px;flex:1 1 220px;margin:0}

/* 链路 */
.flow{display:flex;flex-wrap:wrap;align-items:stretch;gap:8px;margin:14px 0}
.fl-n{flex:1 1 168px;background:var(--surface);border:1px solid var(--border);border-radius:11px;padding:13px 15px;
  box-shadow:var(--shadow)}
.fl-tag{font-size:11px;font-weight:800;letter-spacing:.1em;color:var(--brand);margin-bottom:4px}
.fl-t{font-weight:700;font-size:14.5px;margin-bottom:4px}
.fl-d{font-size:12.8px;color:var(--ink-2);line-height:1.6}
.fl-a{display:flex;align-items:center;color:var(--ink-3);font-size:17px;flex:none}

/* SOP 时间轴 */
.steps{list-style:none;padding:0;margin:14px 0;counter-reset:st}
.st{position:relative;padding:0 0 18px 26px;border-left:2px solid var(--border);margin-left:6px}
.st:last-child{border-left-color:transparent;padding-bottom:0}
.st::before{content:"";position:absolute;left:-7px;top:7px;width:12px;height:12px;border-radius:50%;
  background:var(--brand);border:2px solid var(--surface)}
.st-h{display:flex;flex-wrap:wrap;align-items:baseline;gap:9px}
.st-w{font-size:12px;font-weight:800;color:var(--brand);background:var(--brand-soft);border-radius:5px;
  padding:1px 7px;font-variant-numeric:tabular-nums}
.st-t{font-weight:700;font-size:15px}
.st-o{font-size:12px;color:var(--ink-3);border:1px solid var(--border);border-radius:5px;padding:0 6px}
.st-d{font-size:13.6px;color:var(--ink-2);margin-top:3px}
.st-d p{margin:.25em 0}.st-d ul{margin:.3em 0;padding-left:1.1em}
.st-g{font-size:12.8px;color:var(--ink-2);margin-top:6px;background:var(--surface-2);border-radius:7px;
  padding:5px 10px;display:inline-block}
.st-gl{font-weight:700;color:var(--ink-3);margin-right:7px;font-size:11.5px;letter-spacing:.06em}

/* 清单 */
.checklist{list-style:none;padding:0;margin:14px 0;display:grid;gap:8px}
.ck{display:flex;gap:11px;background:var(--surface);border:1px solid var(--border);border-left:3px solid var(--kc);
  border-radius:9px;padding:11px 14px}
.ck-i{color:var(--kc);font-weight:800;line-height:1.6}
.ck-t{font-size:14px;line-height:1.6}
.ck-n{font-size:12.5px;color:var(--ink-3);margin-top:3px;line-height:1.55}
.ck-good{--kc:#0ca30c}.ck-warn{--kc:#fab219}.ck-critical{--kc:#d03b3b}.ck-info{--kc:#2a78d6}.ck-serious{--kc:#ec835a}

/* 卡片 */
.cards{display:grid;gap:12px;margin:14px 0}
.cards-2{grid-template-columns:repeat(auto-fit,minmax(260px,1fr))}
.cards-3{grid-template-columns:repeat(auto-fit,minmax(220px,1fr))}
.cards-4{grid-template-columns:repeat(auto-fit,minmax(190px,1fr))}
.cd{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:15px 16px;box-shadow:var(--shadow)}
.cd-tag{font-size:11px;font-weight:800;letter-spacing:.09em;color:var(--brand);margin-bottom:5px}
.cd-t{font-weight:700;font-size:15px;margin-bottom:6px}
.cd-b{font-size:13.4px;color:var(--ink-2);line-height:1.68}
.cd-b p{margin:.3em 0}.cd-b ul{margin:.3em 0;padding-left:1.1em}
.cd-m{font-size:12px;color:var(--ink-3);margin-top:9px;padding-top:9px;border-top:1px solid var(--border)}

/* 其他 */
.chip{display:inline-flex;align-items:center;gap:5px;font-size:12.5px;font-weight:600;border-radius:999px;
  padding:1px 9px;border:1px solid var(--chc);color:var(--chc);white-space:nowrap}
.chip-i{font-weight:800;font-size:11px}
.chip-good{--chc:#0ca30c}.chip-warn{--chc:#c98f00}.chip-critical{--chc:#d03b3b}
.chip-serious{--chc:#ec835a}.chip-info{--chc:#2a78d6}
:root[data-theme="dark"] .chip-warn{--chc:#fab219}
@media (prefers-color-scheme:dark){:root:where(:not([data-theme="light"])) .chip-warn{--chc:#fab219}}
.prose p{margin:.6em 0}.prose ul,.prose ol{margin:.6em 0;padding-left:1.2em}.prose li{margin:.28em 0}
.quote{margin:18px 0;padding:14px 20px;border-left:3px solid var(--brand);background:var(--brand-soft);
  border-radius:0 10px 10px 0;font-size:15px;color:var(--ink-2)}
.quote cite{display:block;margin-top:7px;font-size:13px;color:var(--ink-3);font-style:normal}
.rule{border:0;border-top:1px solid var(--border);margin:26px 0}
footer.ft{margin-top:56px;padding-top:22px;border-top:1px solid var(--border);font-size:12.5px;color:var(--ink-3);
  line-height:1.75}
footer.ft b{color:var(--ink-2)}

@media print{
  @page{size:A4;margin:13mm}
  .topbar,.toc,.btn{display:none!important}
  body{background:#fff;font-size:11.4px}
  .wrap{max-width:none;padding:0}
  .layout{display:block}
  section.sec{break-inside:auto;margin-bottom:22px}
  .fig,.kpi,.cd,.co,.verdict,.tbl-wrap{break-inside:avoid}
  .sec-h{break-after:avoid}
  h1.cover-t{font-size:26px}.cover{padding:0 0 16px}
  table{min-width:0}
  *{-webkit-print-color-adjust:exact;print-color-adjust:exact}
}
"""

JS = """
(function(){
  var root=document.documentElement, key='koc-report-theme';
  try{var saved=localStorage.getItem(key); if(saved){root.setAttribute('data-theme',saved);}}catch(e){}
  var btn=document.getElementById('themeBtn');
  function label(){
    var t=root.getAttribute('data-theme');
    var dark = t==='dark' || (!t && window.matchMedia('(prefers-color-scheme:dark)').matches);
    if(btn) btn.textContent = dark ? '☀ 浅色' : '☾ 深色';
  }
  if(btn){btn.addEventListener('click',function(){
    var t=root.getAttribute('data-theme');
    var dark = t==='dark' || (!t && window.matchMedia('(prefers-color-scheme:dark)').matches);
    var next = dark ? 'light' : 'dark';
    root.setAttribute('data-theme',next);
    try{localStorage.setItem(key,next);}catch(e){}
    label();
  });}
  label();
  var pb=document.getElementById('printBtn');
  if(pb) pb.addEventListener('click',function(){window.print();});
  var links=[].slice.call(document.querySelectorAll('.toc a'));
  var secs=links.map(function(a){return document.querySelector(a.getAttribute('href'));}).filter(Boolean);
  if('IntersectionObserver' in window && secs.length){
    var io=new IntersectionObserver(function(es){
      es.forEach(function(e){
        if(e.isIntersecting){
          links.forEach(function(l){l.classList.remove('on');});
          var i=secs.indexOf(e.target);
          if(i>=0&&links[i]) links[i].classList.add('on');
        }
      });
    },{rootMargin:'-72px 0px -72% 0px',threshold:0});
    secs.forEach(function(s){io.observe(s);});
  }
})();
"""


def render(doc: dict) -> str:
    meta = doc.get("meta", {})
    sections = doc.get("sections", [])
    title = meta.get("title", "KOC 全链路作战报告")
    subtitle = meta.get("subtitle", "")
    today = meta.get("date") or date.today().strftime("%Y-%m-%d")

    metas = []
    for k in ("brand", "category", "platform", "period", "owner", "author"):
        if meta.get(k):
            label = {"brand": "品牌", "category": "品类", "platform": "主阵地", "period": "周期",
                     "owner": "负责人", "author": "出品"}[k]
            metas.append(f"<span><b>{esc(label)}</b>　{esc(meta[k])}</span>")
    metas.append(f"<span><b>日期</b>　{esc(today)}</span>")

    verdict = meta.get("verdict")
    v_html = ""
    if verdict:
        t = tone_of(verdict.get("level", "info"))
        color, icon = STATUS[t]
        v_html = (f'<div class="verdict" style="--vc:{color}">'
                  f'<div class="verdict-i" aria-hidden="true">{icon}</div><div>'
                  f'<div class="verdict-l">{esc(verdict.get("label", "核心结论"))}</div>'
                  f'<div class="verdict-t">{rich(verdict.get("title", ""))}</div>'
                  f'<div class="verdict-b">{rich(verdict.get("summary", ""))}</div></div></div>')

    toc, body = [], []
    for i, sec in enumerate(sections, 1):
        sid = sec.get("id") or f"sec-{i}"
        stitle = sec.get("title", f"章节 {i}")
        toc.append(f'<a href="#{esc(sid)}">{esc(f"{i:02d}")}　{esc(stitle)}</a>')
        inner = []
        if sec.get("summary"):
            inner.append(f'<p class="sec-s">{rich(sec["summary"])}</p>')
        for blk in sec.get("blocks", []):
            if not isinstance(blk, dict):
                continue
            if blk.get("heading"):
                inner.append(f'<h3 class="sub">{rich(blk["heading"])}</h3>')
            bt = blk.get("type")
            fn = BLOCKS.get(bt)
            if fn is None:
                raise ValueError(f"未知区块类型：{bt!r}。可用类型：{'、'.join(sorted(BLOCKS))}")
            inner.append(fn(blk))
        body.append(
            f'<section class="sec" id="{esc(sid)}">'
            f'<div class="sec-h"><span class="sec-n">{i:02d}</span><h2 class="sec-t">{rich(stitle)}</h2></div>'
            f'{"".join(inner)}</section>')

    footer = meta.get("footer") or (
        "本报告由「KOC运营专家」生成。所有平台规则、费率与行业基准均标注了来源与整理时点，"
        "执行前请以平台最新官方公告与自有后台数据为准；标注为「假设值」的数字需由业务方复核后再进入预算与考核。")

    css = CSS.replace("__LIGHT_PALETTE__", _palette_vars("light")).replace("__DARK_PALETTE__", _palette_vars("dark"))

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="color-scheme" content="light dark">
<meta name="generator" content="KOC运营专家 · koc-ops-report">
<title>{esc(title)}</title>
<style>{css}</style>
</head>
<body>
<div class="topbar"><div class="topbar-in">
  <span class="tb-t">{esc(title)}</span>
  <span class="tb-s">{esc(today)}</span>
  <span class="tb-sp"></span>
  <button class="btn" id="themeBtn" type="button">☾ 深色</button>
  <button class="btn" id="printBtn" type="button">打印 / 存 PDF</button>
</div></div>

<div class="wrap">
  <header class="cover">
    <div class="cover-tag">{esc(meta.get("kicker", "KOC 全链路作战报告"))}</div>
    <h1 class="cover-t">{rich(title)}</h1>
    {f'<p class="cover-s">{rich(subtitle)}</p>' if subtitle else ''}
    <div class="cover-meta">{"".join(metas)}</div>
    {v_html}
  </header>

  <div class="layout">
    <nav class="toc" aria-label="目录"><div class="toc-h">目录</div>{"".join(toc)}</nav>
    <main>{"".join(body)}
      <footer class="ft">{rich(footer)}</footer>
    </main>
  </div>
</div>
<script>{JS}</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

TEMPLATE = {
    "meta": {
        "title": "{品牌} KOC 全链路作战方案",
        "subtitle": "一句话说清这份方案解决什么问题、覆盖多长时间、要达成什么结果",
        "kicker": "KOC 全链路作战报告",
        "brand": "{品牌}", "category": "{品类}", "platform": "小红书 + 微信私域",
        "period": "2026-09-01 ~ 2026-11-30", "owner": "{负责人}",
        "date": "2026-08-17",
        "verdict": {
            "level": "good",
            "label": "核心结论",
            "title": "先做 120 人的核心圈层 KOC 池，跑通单人产出模型再扩量",
            "summary": "不建议一上来铺 1000 人：当前内容承接能力只能带 150 人以内。",
        },
        "footer": "口径与免责说明",
    },
    "sections": [
        {"id": "summary", "title": "决策摘要", "summary": "章节导语（可省略）",
         "blocks": [{"type": "kpis", "items": [{"label": "示例指标", "value": 120, "unit": "人"}]}]},
    ],
}


def demo_path() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(here), "templates", "example-report.json")


def self_test() -> int:
    """渲染一遍全部区块类型，验证不抛异常、产物完整。"""
    doc = {
        "meta": {"title": "自检报告", "subtitle": "全部区块类型渲染验证",
                 "verdict": {"level": "warn", "title": "自检", "summary": "全部区块渲染"}},
        "sections": [{
            "id": "all", "title": "全部区块",
            "blocks": [
                {"type": "kpis", "items": [{"label": "A", "value": 1200, "unit": "人", "note": "备注", "tone": "good"},
                                           {"label": "B", "value": 12.5, "unit": "%"}]},
                {"type": "callout", "tone": "warn", "title": "提示", "text": "正文\n- 项一\n- 项二"},
                {"type": "prose", "text": "段落 **加粗** 与 `代码`。\n1. 有序\n2. 有序"},
                {"type": "table", "columns": ["列A", {"name": "列B", "align": "right"}],
                 "rows": [["值", {"text": "达标", "tone": "good"}]], "caption": "表", "note": "口径"},
                {"type": "pyramid", "caption": "金字塔",
                 "levels": [{"name": f"L{4 - i}", "tag": f"tag{i}", "size": f"{i * 10}", "desc": "d"} for i in range(5)]},
                {"type": "funnel", "caption": "漏斗", "unit": "人",
                 "stages": [{"name": "触达", "value": 5000}, {"name": "报名", "value": 800},
                            {"name": "通过", "value": 260}, {"name": "出稿", "value": 190}]},
                {"type": "radar", "caption": "雷达", "threshold": 60,
                 "axes": ["规模", "活跃", "质量", "转化", "留存", "成本"],
                 "series": [{"name": "现状", "values": [40, 55, 62, 30, 48, 70]},
                            {"name": "目标", "values": [70, 75, 80, 60, 68, 75]}]},
                {"type": "gantt", "caption": "排期", "start": "2026-09-01",
                 "phases": [{"name": "招募", "track": "招募", "from": 0, "to": 14, "gate": "入池 100"},
                            {"name": "培育", "track": "培育", "from": 7, "to": 30, "gate": "出稿率 60%"},
                            {"name": "分销", "track": "分销", "from": 21, "to": 60, "gate": "GMV 达标"}],
                 "markers": [{"day": 30, "label": "复盘"}]},
                {"type": "donut", "caption": "预算", "unit": "元", "center": {"label": "月预算", "value": "8万"},
                 "items": [{"name": "寄样", "value": 30000}, {"name": "佣金", "value": 28000},
                           {"name": "激励", "value": 12000}, {"name": "投流", "value": 10000}]},
                {"type": "stack", "caption": "佣金分配", "unit": "%",
                 "items": [{"name": "达人佣金", "value": 20}, {"name": "团长服务费", "value": 5},
                           {"name": "平台技术服务费", "value": 5}, {"name": "品牌留存", "value": 70}]},
                {"type": "bars", "caption": "渠道", "unit": "人", "target": 100,
                 "items": [{"name": "老客池", "value": 120, "note": "转化最高"}, {"name": "社群", "value": 80}]},
                {"type": "ladder", "caption": "阶梯", "unit": "%",
                 "steps": [{"name": "L1", "value": 10, "threshold": "月 1 篇"},
                           {"name": "L2", "value": 15, "threshold": "月 2 篇"},
                           {"name": "L3", "value": 20, "threshold": "月 4 篇"}]},
                {"type": "quadrant", "caption": "定位", "xLabel": "内容力", "yLabel": "转化力",
                 "quadrants": {"tl": "A", "tr": "B", "bl": "C", "br": "D"},
                 "items": [{"name": "张三", "x": 70, "y": 60, "note": "升级"},
                           {"name": "李四", "x": 30, "y": 80}]},
                {"type": "flow", "caption": "链路",
                 "steps": [{"tag": "S1", "title": "招募", "desc": "六池"}, {"tag": "S2", "title": "培育"}]},
                {"type": "steps", "caption": "SOP",
                 "items": [{"when": "D0", "title": "入群", "owner": "运营", "desc": "发新人包", "gate": "24h 登记"}]},
                {"type": "checklist", "caption": "红线",
                 "items": [{"text": "必须报备", "level": "must", "note": "依据"},
                           {"text": "禁止刷单", "level": "avoid"}, "纯文本项"]},
                {"type": "cards", "caption": "卡片", "columns": 3,
                 "items": [{"tag": "渠道", "title": "老客池", "body": "正文", "meta": "120 人"}]},
                {"type": "quote", "text": "引用", "by": "出处"},
                {"type": "divider"},
            ],
        }],
    }
    out = render(doc)

    # 极端输入：脏数据不能让整份报告渲染失败，也不能静默丢块
    extreme = {
        "meta": {"title": "极端输入自检"},
        "sections": [{"id": "x", "title": "脏数据", "blocks": [
            {"type": "stack", "items": [{"name": "负数", "value": -50}, {"name": "正常", "value": 20}]},
            {"type": "stack", "items": [{"name": f"项{i}", "value": i + 1} for i in range(12)]},
            {"type": "stack", "items": [{"name": "全零", "value": 0}]},
            {"type": "radar", "axes": ["只有两维", "不够"], "series": [{"name": "a", "values": [1, 2]}]},
            {"type": "radar", "axes": ["A", "B", "C"], "max": 100,
             "series": [{"name": "越界", "values": [999, -50, float("nan")]}]},
            {"type": "funnel", "stages": [{"name": "只有一段", "value": 100}]},
            {"type": "funnel", "stages": [{"name": "全等", "value": 10}, {"name": "全等2", "value": 10}]},
            {"type": "funnel", "stages": [{"name": "零值", "value": 0}, {"name": "零值2", "value": 0}]},
            {"type": "gantt", "phases": [{"name": "倒序", "from": 30, "to": 5},
                                         {"name": "越界", "from": -10, "to": 999}]},
            {"type": "donut", "items": [{"name": "全零", "value": 0}]},
            {"type": "bars", "items": [{"name": "负值", "value": -20}, {"name": "无穷", "value": float("inf")}]},
            {"type": "ladder", "steps": [{"name": "零", "value": 0}, {"name": "零2", "value": 0}]},
            {"type": "quadrant", "items": [{"name": "越界", "x": 500, "y": -300}]},
            {"type": "pyramid", "levels": []},
            {"type": "kpis", "items": [{"label": "非数值指标", "value": float("nan")},
                                       {"label": "无穷指标", "value": float("inf")}]},
        ]}],
    }
    ext_out = render(extreme)

    checks = [
        ("所有区块类型均已覆盖", set(BLOCKS) - {b.get("type") for b in doc["sections"][0]["blocks"]} == set()),
        ("极端输入不崩溃", len(ext_out) > 5000),
        ("极端输入无 NaN/Infinity 漏进产物", "NaN" not in ext_out and "Infinity" not in ext_out),
        ("数据不足时给出提示而非静默丢块", ext_out.count("此处数据不足") >= 4),
        ("超长堆叠合并为「其他」而非截断", "其他（" in ext_out),
        ("产物非空", len(out) > 20000),
        ("无未替换占位符", "__LIGHT_PALETTE__" not in out and "__DARK_PALETTE__" not in out),
        ("含深色模式定义", '[data-theme="dark"]' in out and "prefers-color-scheme:dark" in out),
        ("含打印样式", "@media print" in out),
        ("SVG 已内联", out.count("<svg") >= 8),
        ("无外链资源", "http://" not in out.replace("http://www.w3.org/2000/svg", "")
         and "https://" not in out),
        ("目录已生成", 'class="toc"' in out),
    ]
    ok = True
    for name, passed in checks:
        print(("  [PASS] " if passed else "  [FAIL] ") + name)
        ok = ok and passed
    print("\n自检结果：" + ("全部通过" if ok else "存在失败项"))
    return 0 if ok else 1


def main() -> None:
    ap = argparse.ArgumentParser(description="KOC 全链路作战报告渲染器")
    ap.add_argument("--data", help="报告数据 JSON 文件路径")
    ap.add_argument("--json", help="直接传入 JSON 字符串")
    ap.add_argument("--out", help="输出 HTML 路径")
    ap.add_argument("--demo", action="store_true", help="渲染内置示例数据")
    ap.add_argument("--template", action="store_true", help="打印数据结构模板")
    ap.add_argument("--blocks", action="store_true", help="打印所有区块类型速查")
    ap.add_argument("--self-test", action="store_true", help="渲染全部区块类型做自检")
    a = ap.parse_args()

    if a.template:
        print(json.dumps(TEMPLATE, ensure_ascii=False, indent=2))
        return
    if a.blocks:
        print("可用区块类型（放在 sections[].blocks[] 里，每个区块可加 \"heading\" 生成小标题）：\n")
        for k in BLOCKS:
            print(f"● {k}\n    {BLOCK_HELP.get(k, '')}\n")
        return
    if getattr(a, "self_test"):
        sys.exit(self_test())

    if a.demo:
        path = demo_path()
        if not os.path.exists(path):
            print(f"示例数据不存在：{path}", file=sys.stderr)
            sys.exit(2)
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
    elif a.data:
        with open(a.data, encoding="utf-8") as f:
            doc = json.load(f)
    elif a.json:
        doc = json.loads(a.json)
    else:
        ap.error("需要 --data / --json / --demo 之一（或用 --template 查看数据结构）")

    out_html = render(doc)
    out_path = a.out or (doc.get("meta", {}).get("title", "KOC报告").replace("/", "-") + ".html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(out_html)
    print(f"已生成：{os.path.abspath(out_path)}（{len(out_html) / 1024:.0f} KB，单文件零外链）")


if __name__ == "__main__":
    main()
