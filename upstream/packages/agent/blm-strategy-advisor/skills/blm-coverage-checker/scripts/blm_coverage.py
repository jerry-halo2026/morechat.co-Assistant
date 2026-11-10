# -*- coding: utf-8 -*-
"""
BLM 覆盖度检查器（blm-coverage-checker 内核）
=============================================
对一份「战略分析/战略解码」文本做 5 项形式校验，防「看起来很美的空报告」：

  C1 双差距成对    ：业绩差距与机会差距各有 ≥1 条实质内容，不许互相顶替
  C2 五看齐全      ：看行业/看客户/看竞争/看自己/看机会 每看有实质内容
  C3 业务设计六要素：客户选择/价值主张/价值获取/活动范围/战略控制/风险管理
  C4 任务挂钩指标  ：关键任务存在，且挂钩衡量指标
  C5 编造信号扫描  ：市场规模/增长率等绝对数字必须挂「待验证」标签
  C6 证据锚点（警告级）：全文无任何证据锚点 → WARN「疑似空转」

源头判据纪律（每一格都是「这类输入必然误判」的系统性修复，非单点补丁）：
  1) 加粗行只有两种成节形态：**标签**：内容（冒号必需）、**短标题** 单独成行
     （≤20 字且不含句末标点）——其余加粗一律按正文，防止强调句被误拆成空壳节
  2) 占位词收紧：待填 后不跟 补 才算（「有待填补」不是占位）；去掉裸 （此处
  3) 指标词的 目标 必须带冒号或作 目标值——「目标客户」不是指标
  4) C5 自证标签扩到 需核实/待确认/预计/预测/估算/测算
  5) 模块识别覆盖 7 种高频写法：# 标题 / 整行短加粗 / 加粗标签 / 列表加粗标签 /
     编号加粗标签 / 表格行 / 纯文本「别名：内容」；正文顺带提及=未成节
  6) 空壳判定有兜底顺序：标题空壳 → 标签条目/表格行 → 正文实质讨论 →
     加粗强调句自证（标题比别名长且含实质表述、且来源为加粗行）→ 剩余才判空占位

纪律：
  - 只做形式判定，不评判战略内容好坏（内容判断归专家对话层）
  - 「0 个对象被检查」≠「全部通过」：文本过短（<200 有效字符）直接判 DEFECT
  - 认不出的引用一律不判；每个检查打印命中数

退出码：0 = 通过（允许有 WARN）；1 = 存在 DEFECT（报告照常输出）；2 = 用法错误
用法（双模式）：
  契约模式（权威判定面）：python blm_coverage.py <原文.md> --form <登记表.json>
      C1–C4 改为对登记表做确定性校验（13 模块齐/证据非占位/任务挂钩指标/证据逐字对账原文），
      自由文本解析不参与判定——解析歧义类缺陷在该模式下结构性不存在。
  自由文本模式（尽力而为）：python blm_coverage.py <分析文本.md|txt>
      7 种高频写法启发式解析，供用户自查存量文档；解析边界已尽力收敛但不承诺穷尽。
依赖：纯 stdlib，无第三方库。
"""
import argparse
import json
import re
import sys

PLACEHOLDER_RE = re.compile(r"待补充|待填(?!补)|待完善|XXX+|TBD|【占位】|此处省略|此处略去")
FABRIC_NUM_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:万亿|亿|万|%|％)")
FABRIC_TOPIC_RE = re.compile(r"市场规模|市场份额|市场容量|增长率|增速|渗透率|CAGR|复合增长")
FABRIC_LABEL_RE = re.compile(
    r"待验证|待核实|需核实|待确认|待查证|来源[:：]|数据源|引自|预计|预测|估算|测算")
METRIC_HINT_RE = re.compile(r"衡量指标|考核指标|指标|KPI|OKR|目标值|目标[:：]|基线|考核")
MIN_DOC_CHARS = 200

# 规范模块 → 可识别别名（命中任一别名即视为该模块出现）
MODULE_ALIASES = {
    "业绩差距": ["业绩差距", "业绩差距分析", "业绩未达成"],
    "机会差距": ["机会差距", "机会差距分析", "新机会差距"],
    "看行业": ["看行业", "行业趋势", "行业分析", "看趋势"],
    "看客户": ["看客户", "客户洞察", "看市场", "客户与市场分析"],
    "看竞争": ["看竞争", "竞争分析", "竞争对手分析", "竞品分析"],
    "看自己": ["看自己", "自身盘点", "内部盘点", "自我剖析"],
    "看机会": ["看机会", "机会洞察", "机会点", "市场机会"],
    "客户选择": ["客户选择", "目标客户"],
    "价值主张": ["价值主张"],
    "价值获取": ["价值获取", "盈利模式", "盈利方式"],
    "活动范围": ["活动范围", "业务范围"],
    "战略控制": ["战略控制", "竞争优势", "护城河"],
    "风险管理": ["风险管理", "风险与对策", "风险应对"],
    "关键任务": ["关键任务", "战略解码", "重点任务", "必赢之战", "核心任务"],
}

# 分节标题形态
HEADING_RE = re.compile(r"^(#{1,6})\s*(.*)$")
# 加粗标签：**标题**：内容（冒号必需——无冒号的长句是强调，不是标题）
BOLD_LABEL_RE = re.compile(r"^\*\*([^*]{2,40})\*\*\s*[:：]\s*(.*)$")
# 整行短加粗标题：**标题** 单独成行（≤20 字且不含句末标点——否则是强调句）
BOLD_HEAD_RE = re.compile(r"^\*\*([^*]{2,20})\*\*\s*$")
SENT_END_RE = re.compile(r"[。！？；，,、]")


def split_sections(text):
    """返回 [(标题, [正文行], origin)]；origin ∈ {'heading','bold'}。
    加粗行只有两种成节形态（见模块 docstring 判据 1）；其余按正文处理。"""
    sections = []
    cur = None  # [title, body, origin]

    def _push():
        if cur is not None:
            sections.append((cur[0], cur[1], cur[2]))

    for raw in text.splitlines():
        line = raw.rstrip()
        m = HEADING_RE.match(line)
        if m:
            _push()
            cur = [m.group(2).strip(), [], "heading"]
            continue
        m = BOLD_LABEL_RE.match(line)
        if m:
            _push()
            rest = m.group(2).strip()
            cur = [m.group(1).strip(), ([rest] if rest else []), "bold"]
            continue
        m = BOLD_HEAD_RE.match(line)
        if m and not SENT_END_RE.search(m.group(1)):
            _push()
            cur = [m.group(1).strip(), [], "bold"]
            continue
        if cur is None:
            cur = [None, [], "heading"]
        cur[1].append(line)
    _push()
    return sections


def _is_substantive(line):
    s = line.strip().lstrip("-*•").strip()
    if not s:
        return False
    if PLACEHOLDER_RE.search(s):
        return False
    return len(s) >= 4


NEG_CHARS = ("缺", "无", "没", "未")


def _alias_hit(s, alias):
    """别名命中且未被否定前缀修饰（「缺机会差距」「无机会差距」≠ 模块存在；
    「不缺机会差距」= 存在）。文档标题/正文里的元描述不得当模块节。"""
    for m in re.finditer(re.escape(alias), s):
        i = m.start()
        pre = s[max(0, i - 2):i]
        if pre.endswith(("缺少", "没有")):
            continue
        if pre.endswith(NEG_CHARS) and not pre.endswith("不缺"):
            continue
        return True
    return False


def _label_or_table_hit(sections, aliases, require_substantive=True):
    """标签条目（**别名**：内容 / 别名：内容，可带列表/编号前缀）或表格行命中。
    与成节标题等效（真实文档的高频写法）。
    require_substantive=False 时命中「非实质的显式空槽」——那是明确的模块位，
    应判空占位而非缺失。返回 (alias, [line]) 或 None。"""
    for alias in aliases:
        esc = re.escape(alias)
        neg = r"(?<![缺无没未])"
        pat_label = re.compile(
            r"^\s*(?:[-*•]|\d+[\.、])?\s*\**\s*" + neg + esc + r"\s*\**\s*[:：]")
        pat_table = re.compile(r"^\s*\|.*" + neg + esc)
        for _title, body, _origin in sections:
            for l in body:
                matched = pat_label.match(l) or pat_table.match(l)
                if not matched:
                    continue
                if require_substantive:
                    if _is_substantive(l):
                        return alias, [l]
                elif l.strip():
                    return alias, [l]
    return None


def _weak_hit(sections, aliases):
    """弱命中：仅正文顺带提及（视为「未成节」，只作提示性计数）。"""
    for alias in aliases:
        for _title, body, _origin in sections:
            for l in body:
                if _alias_hit(l, alias) and _is_substantive(l):
                    return alias, [l]
    return None


def find_module(sections, aliases):
    """返回 (是否成节, 命中别名, 实质内容行数, 节内容行)。
    判定顺序（从强到弱，见模块 docstring 判据 5/6）：
      1) 标题含别名且节内有实质内容（多个命中取实质行最多——防空壳外层标题顶替）
      2) 标题命中但全空壳 → 标签条目/表格行兜底 → 正文实质讨论兜底
      3) 空壳若来自加粗行且标题比别名长（加粗强调句自证）→ 视为已实质覆盖
      4) 剩余空壳（裸标题无内容）= 空占位；无任何标题命中 = 未成节"""
    best = None  # (n_sub, alias, title, body, origin)
    for alias in aliases:
        for title, body, origin in sections:
            if _alias_hit(title, alias):
                n_sub = sum(1 for l in body if _is_substantive(l))
                if best is None or n_sub > best[0]:
                    best = (n_sub, alias, title, body, origin)
    if best is not None and best[0] > 0:
        return True, best[1], best[0], best[3]
    if best is not None:
        hit = _label_or_table_hit(sections, aliases) or _weak_hit(sections, aliases)
        if hit:
            return True, hit[0], 1, hit[1]
        _n, alias, title, body, origin = best
        if origin == "bold" and len(title) > len(alias) + 2 and _is_substantive(title):
            return True, alias, 1, [title]
        return True, alias, 0, body  # 空占位
    hit = _label_or_table_hit(sections, aliases)
    if hit:
        return True, hit[0], 1, hit[1]
    # 无标题命中但有非实质的显式空槽（标签条目/表格行）→ 模块存在但空占位
    empty_slot = _label_or_table_hit(sections, aliases, require_substantive=False)
    if empty_slot:
        return True, empty_slot[0], 0, empty_slot[1]
    hit = _weak_hit(sections, aliases)
    if hit:
        return False, hit[0], 1, hit[1]
    return False, None, 0, []


def check(text):
    defects, warns = [], []
    stats = {}
    sections = split_sections(text)

    valid_chars = len(re.sub(r"\s", "", text))
    stats["C0:有效字符数"] = valid_chars
    if valid_chars < MIN_DOC_CHARS:
        defects.append(f"C0 文本过短：有效字符 {valid_chars} < {MIN_DOC_CHARS}，无法有效覆盖 BLM 必需模块")
        return defects, warns, stats

    # C1/C2/C3 关键词：模块出现 → 节内实质内容 ≥1
    module_groups = {
        "C1": [("业绩差距", MODULE_ALIASES["业绩差距"]), ("机会差距", MODULE_ALIASES["机会差距"])],
        "C2": [("看行业", MODULE_ALIASES["看行业"]), ("看客户", MODULE_ALIASES["看客户"]),
               ("看竞争", MODULE_ALIASES["看竞争"]), ("看自己", MODULE_ALIASES["看自己"]),
               ("看机会", MODULE_ALIASES["看机会"])],
        "C3": [("客户选择", MODULE_ALIASES["客户选择"]), ("价值主张", MODULE_ALIASES["价值主张"]),
               ("价值获取", MODULE_ALIASES["价值获取"]), ("活动范围", MODULE_ALIASES["活动范围"]),
               ("战略控制", MODULE_ALIASES["战略控制"]), ("风险管理", MODULE_ALIASES["风险管理"])],
    }
    for code, mods in module_groups.items():
        missing, weak, empty = [], [], []
        for canon, aliases in mods:
            found, hit, n_sub, _ = find_module(sections, aliases)
            stats[f"{code}:{canon}"] = {"found": found, "alias": hit, "substantive_lines": n_sub}
            if not found:
                missing.append(canon + ("（仅正文提及，未成节）" if hit else ""))
            elif n_sub == 0:
                empty.append(canon)
        if missing:
            defects.append(f"{code} 模块缺失/未成节：{'、'.join(missing)}")
        if empty:
            defects.append(f"{code} 模块存在但为空占位（无实质内容）：{'、'.join(empty)}")

    # C4 关键任务 ↔ 衡量指标
    found, hit, n_sub, body = find_module(sections, MODULE_ALIASES["关键任务"])
    stats["C4:关键任务"] = {"found": found, "alias": hit, "substantive_lines": n_sub}
    if not found:
        defects.append("C4 缺少「关键任务/战略解码」模块——战略落不了地")
    elif n_sub == 0:
        defects.append("C4 「关键任务」模块为空占位")
    else:
        n_tasks = sum(1 for l in body if _is_substantive(l))
        n_metric = sum(1 for l in body if METRIC_HINT_RE.search(l))
        stats["C4:任务行数"] = n_tasks
        stats["C4:指标提及行数"] = n_metric
        if n_metric == 0:
            defects.append(f"C4 关键任务共 {n_tasks} 条，但未挂钩任何衡量指标/考核口径")

    # C5 编造信号：行业数字无「待验证/来源」标签（同一行内自证才认可）
    fab_hits = 0
    for i, raw in enumerate(text.splitlines(), 1):
        if FABRIC_TOPIC_RE.search(raw) and FABRIC_NUM_RE.search(raw) and not FABRIC_LABEL_RE.search(raw):
            fab_hits += 1
            defects.append(f"C5 第 {i} 行：出现行业数字但未挂「待验证/来源」标签——{raw.strip()[:60]}")
    stats["C5:无标签行业数字行数"] = fab_hits

    # 全局占位统计（WARN）
    ph = len(PLACEHOLDER_RE.findall(text))
    stats["全局占位标记数"] = ph
    if ph > 10:
        warns.append(f"全文占位标记 {ph} 处（>10）——检查是否把没做的工作写成了已完成")

    # C6（警告级）证据锚点：全文既无来源/待验证标签、也无任何带单位数字
    # → 模块形式上覆盖但可能整体空转。设为 WARN：学习/框架讲解类合法文档同样无锚点，
    #   不升格为 DEFECT；由专家对话层据此追问事实依据。
    has_anchor = bool(FABRIC_LABEL_RE.search(text) or FABRIC_NUM_RE.search(text))
    stats["C6:存在证据锚点"] = has_anchor
    if not has_anchor:
        warns.append("C6 全文未见任何证据锚点（来源/待验证标签/带单位数字）——"
                     "模块形式覆盖但疑似空转，请逐模块补事实依据或数据来源")

    return defects, warns, stats


# ===================== 契约模式（--form，权威判定面） =====================
# 源头纪律：自由文本解析的判断面是无界的（历史 7 个判据缺陷中 6 个源于此类）。
# 契约模式把 C1–C4 的判定对象从「猜出来的文档结构」换成「专家层填的结构化登记表」，
# 解析歧义在该模式下结构性不存在；检查器只做确定性校验 + 证据对账。

FORM_MODULES = [m for m in MODULE_ALIASES if m != "关键任务"]


def _norm(s):
    return re.sub(r"\s", "", s or "")


def _valid_evidence(item):
    if not isinstance(item, str):
        return False
    s = item.strip()
    if not s or PLACEHOLDER_RE.search(s):
        return False
    return len(s) >= 4


def check_form(form, text=""):
    """登记表校验：F1 完整性 / F2 任务挂指标 / F3 证据对账 / F0 词表纪律。
    C5/C6 仍扫原文；未提供原文则如实报 WARN（剥离即放弃须上报，不静默）。"""
    defects, warns = [], []
    stats = {"模式": "契约模式（--form）"}

    mods = form.get("modules")
    if not isinstance(mods, dict):
        defects.append("F0 登记表缺少 modules 对象")
        mods = {}
    unknown = sorted(k for k in mods if k not in FORM_MODULES)
    if unknown:
        defects.append("F0 登记表出现词表外模块名：" + "、".join(unknown)
                       + "——只认 13 个规范模块名，别名不许入表")
    for canon in FORM_MODULES:
        v = mods.get(canon)
        ev = v.get("evidence") if isinstance(v, dict) else None
        items = [e for e in (ev or []) if _valid_evidence(e)]
        stats[f"F:{canon}"] = {"evidence_total": len(ev or []), "evidence_valid": len(items)}
        if ev is None:
            defects.append(f"F1 登记表缺模块「{canon}」")
            continue
        if not items:
            defects.append(f"F1 「{canon}」无有效证据（空占位或证据过短 <4 字）")
            continue
        if text:
            ntext = _norm(text)
            for e in items:
                if _norm(e) not in ntext:
                    defects.append(f"F3 「{canon}」证据未在原文中找到（摘句须逐字摘自原文）——{str(e)[:40]}")

    tasks = form.get("key_tasks")
    if not isinstance(tasks, list) or not tasks:
        defects.append("F2 登记表缺关键任务清单（key_tasks 为空或缺失）")
    else:
        stats["F:key_tasks"] = {"条数": len(tasks)}
        for i, t in enumerate(tasks, 1):
            if not (isinstance(t, dict) and _valid_evidence(t.get("task", ""))):
                defects.append(f"F2 第 {i} 条关键任务：task 缺失或空占位")
            metric = t.get("metric") if isinstance(t, dict) else None
            if not (isinstance(metric, str) and metric.strip()
                    and not PLACEHOLDER_RE.search(metric)):
                defects.append(f"F2 第 {i} 条关键任务未挂钩衡量指标——没有指标的任务不许入清单")

    if text and text.strip():
        fab = 0
        for i, raw in enumerate(text.splitlines(), 1):
            if FABRIC_TOPIC_RE.search(raw) and FABRIC_NUM_RE.search(raw) \
                    and not FABRIC_LABEL_RE.search(raw):
                fab += 1
                defects.append(f"C5 第 {i} 行：出现行业数字但未挂「待验证/来源」标签——{raw.strip()[:60]}")
        stats["C5:无标签行业数字行数"] = fab
        has_anchor = bool(FABRIC_LABEL_RE.search(text) or FABRIC_NUM_RE.search(text))
        stats["C6:存在证据锚点"] = has_anchor
        if not has_anchor:
            warns.append("C6 原文未见任何证据锚点（来源/待验证标签/带单位数字）——疑似空转，请逐模块补事实依据")
    else:
        warns.append("C5/C6 未执行：未提供原文——证据真实性未经扫描，须如实上报不得省略")

    return defects, warns, stats


def render(defects, warns, stats):
    lines = []
    lines.append("# BLM 覆盖度检查报告")
    lines.append("")
    total_checked = len(stats)
    lines.append(f"- 检查对象统计项：{total_checked} 项；DEFECT {len(defects)} 条；WARN {len(warns)} 条")
    if total_checked == 0 and not defects:
        lines.append("- [DEFECT] 检查器内部异常：0 个对象被检查，拒绝判通过")
        return "\n".join(lines)
    lines.append("")
    lines.append("## 模块覆盖明细")
    lines.append("")
    lines.append("| 检查:模块 | 成节 | 命中别名 | 实质内容行 |")
    lines.append("|---|---|---|---|")
    for k, v in stats.items():
        if isinstance(v, dict) and "found" in v:
            lines.append(f"| {k} | {'是' if v['found'] else '否'} | {v['alias'] or '—'} | {v['substantive_lines']} |")
        elif isinstance(v, dict):
            lines.append(f"- {k}: {json.dumps(v, ensure_ascii=False)}")
    for k, v in stats.items():
        if not isinstance(v, dict):
            lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## 结论")
    lines.append("")
    if defects:
        lines.append(f"**不通过**：{len(defects)} 条缺陷。逐条如下：")
        lines.append("")
        for d in defects:
            lines.append(f"- [DEFECT] {d}")
    else:
        lines.append("**通过**：0 缺陷。")
    if warns:
        lines.append("")
        lines.append("警告：")
        for w in warns:
            lines.append(f"- [WARN] {w}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="BLM 覆盖度检查器（纯 stdlib，双模式）")
    ap.add_argument("input", nargs="?", default=None,
                    help="战略分析文本（.md/.txt）；契约模式下可省略（C5/C6 将如实报未执行）")
    ap.add_argument("--form", dest="form", help="模块登记表 .json（契约模式，权威判定面）")
    ap.add_argument("--json", dest="json_out", help="摘要 JSON 输出路径")
    ap.add_argument("--quiet", action="store_true", help="只输出结论行")
    args = ap.parse_args()

    if args.form:
        try:
            with open(args.form, "r", encoding="utf-8") as f:
                form = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"用法错误：登记表无法读取/解析 {args.form}: {e}", file=sys.stderr)
            sys.exit(2)
        text = ""
        if args.input:
            try:
                with open(args.input, "r", encoding="utf-8") as f:
                    text = f.read()
            except OSError as e:
                print(f"用法错误：无法读取 {args.input}: {e}", file=sys.stderr)
                sys.exit(2)
        defects, warns, stats = check_form(form, text)
    elif args.input:
        try:
            with open(args.input, "r", encoding="utf-8") as f:
                text = f.read()
        except OSError as e:
            print(f"用法错误：无法读取 {args.input}: {e}", file=sys.stderr)
            sys.exit(2)
        defects, warns, stats = check(text)
    else:
        ap.error("需要提供原文路径，或 --form 登记表.json")
        return
    report = render(defects, warns, stats)
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump({"defects": defects, "warns": warns, "stats": {
                k: v for k, v in stats.items()}}, f, ensure_ascii=False, indent=2)
    if args.quiet:
        print(f"DEFECT={len(defects)} WARN={len(warns)}")
    else:
        print(report)
    sys.exit(1 if defects else 0)


if __name__ == "__main__":
    main()
