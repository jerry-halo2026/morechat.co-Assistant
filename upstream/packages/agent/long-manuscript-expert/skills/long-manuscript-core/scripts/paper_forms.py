#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Five report forms + data/quality guards for 2026.11.5 (rev 2).

Standard library only. Fixes the independently reproduced false positives:

* select_form: an EXPLICIT user form wins over topic keywords; conflicting
  explicit forms stay ambiguous; heuristic suggestions are explicit=False.
* multiple_choice: a sum <= 100 does NOT prove mutual exclusivity; the
  multi-select entry NEVER permits an exclusive pie chart.
* conceptual_formula: having parameters does NOT calibrate a model; the
  conceptual entry never permits prediction.
* tgi: arithmetic alone is not evidence-condition validity; same-source,
  same-calibre, sample and subset metadata are required or state stays unknown.
* percentage points: requires an actual delta between two comparable ratios,
  never a bare unit relabel.
* period_label: empty/invalid months, negatives, booleans and non-finite values
  are refused or unknown; discontinuous months keep their actual set.
* evaluate_plan: declarations and verifications are separate; missing evidence
  is UNKNOWN, never a PASS inferred from a boolean.

The REAL product entry point that consumes these guards is product_entry.py
(and composition.py); this module's helpers are not user acceptance by themselves.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

VERSION = "2026.11.5"
SCHEMA = "paper.five-forms.v2"

FORM_NAMES = {"T01": "图鉴", "T02": "白皮书", "T03": "数据报告",
              "T04": "人群专题", "T05": "方法论"}
FORM_SLUGS = {"T01": "atlas", "T02": "whitepaper", "T03": "data-report",
              "T04": "population-study", "T05": "methodology"}
FORM_CUES = {
    "T01": ("图鉴", "场景洞察", "体验", "趋势启发", "atlas", "lookbook"),
    "T02": ("白皮书", "范式", "架构", "技术说明", "whitepaper"),
    "T03": ("数据报告", "kpi", "经营", "底表", "周期监测", "data report"),
    "T04": ("人群", "分群", "画像", "问卷", "population", "segment"),
    "T05": ("方法论", "sop", "操作指南", "路线图", "methodology", "playbook"),
}
EXPLICIT_FORM = re.compile(
    r"(?:写成|做成|整理成|生成|输出|采用|用|做|写|来一份|要|按|以)"
    r"\s*(?:一份|一篇|一个|一份|篇|份)?\s*"
    r"(图鉴|白皮书|数据报告|人群专题|方法论)"
    r"|(图鉴|白皮书|数据报告|人群专题|方法论)(?:形态|模板|格式|体例)")
FORM_ALIASES = {"图鉴": "T01", "白皮书": "T02", "数据报告": "T03",
                "人群专题": "T04", "方法论": "T05"}

FORM_META = {
    "T01": {"voice": "具体、可感知、短段落；先写观察再解释",
            "visual": "浅暖底、图文交替、原声卡、可对页", "key": "撤销图片或原声后合法降级"},
    "T02": {"voice": "主张—依据—机制—适用条件—小结",
            "visual": "克制双栏、全页架构、连续图号", "key": "厂商声明与独立测量分层；概念公式不数值化"},
    "T03": {"voice": "数值先行，明确期间、单位、基准",
            "visual": "白底细网格、原值底表、异常高亮", "key": "期间/单位/分母；缺月不补0；单对象不虚构TOP10"},
    "T04": {"voice": "样本范围内描述，原声与推断分开",
            "visual": "固定字段画像卡、N/n 就近标注", "key": "多选不归一；缺基准不算TGI；模拟不计真人"},
    "T05": {"voice": "讲清怎么做、为何做、何时不做",
            "visual": "过程链、步骤卡、角色与门槛表", "key": "缺前提受限或退出；未实测不画效果曲线"},
}
SHARED_BLOCKS = {
    "scope": "范围、读者与决定；实际可读取材料与已读/未读边界",
    "evidence": "来源定位、原始值、口径与来源家族",
    "claims": "承重主张与各自支持、反证/限制、适用条件、正文落点",
    "visuals": "图题、单位、期间、样本/分母、来源与静态替代",
    "limits": "未知、不可计算、待同步与唯一下一步",
}
FORM_BLOCK_ORDER = {
    "T01": ["scope", "evidence", "claims", "visuals", "limits"],
    "T02": ["scope", "claims", "evidence", "visuals", "limits"],
    "T03": ["scope", "evidence", "visuals", "claims", "limits"],
    "T04": ["scope", "claims", "visuals", "evidence", "limits"],
    "T05": ["scope", "claims", "evidence", "limits", "visuals"],
}
FORM_PAGE_ROLES = {
    "T01": ["范围与旅程", "趋势证据", "场景比较", "画像与原声", "案例拆解", "行动回顾"],
    "T02": ["摘要与范围", "定义与争议", "论点与证据", "参考架构", "方案与案例", "实施与限制"],
    "T03": ["范围和KPI", "总体与对象", "时间变化", "结构与排名", "异常与诊断", "行动与附录"],
    "T04": ["问题与样本", "分群与分布", "人群A", "人群B", "差异与旅程", "机会与验证"],
    "T05": ["问题与边界", "总体方法", "步骤与产物", "案例与反例", "执行路线", "检验与复盘"],
}


class FormError(ValueError):
    pass


def _finite_number(v) -> bool:
    return type(v) in (int, float) and math.isfinite(v)


def select_form(text: str, recommended: str | None = None) -> dict:
    """Explicit user choice is authoritative; keywords only suggest."""
    if not isinstance(text, str):
        raise FormError("select_form expects natural-language text")
    explicit = [FORM_ALIASES[g] for g in
                (m.group(1) or m.group(2) for m in EXPLICIT_FORM.finditer(text)) if g]
    low = text.lower()
    scores = {fid: sum(1 for c in cues if c.lower() in low)
              for fid, cues in FORM_CUES.items()}
    if len(set(explicit)) > 1:
        return {"schema": SCHEMA, "version": VERSION, "form_id": None,
                "form_name": None, "explicit": False, "ambiguous": True,
                "explicit_candidates": sorted(set(explicit)),
                "reason": "多个明确形态冲突，保留歧义并请用户选择",
                "scores": scores, "track_unchanged": True,
                "intent_revision_unchanged": True, "evidence_revision_unchanged": True}
    if explicit:
        fid = explicit[0]
        keyword_top = max(scores, key=lambda k: scores[k])
        conflict = scores[keyword_top] > scores[fid] and keyword_top != fid
        return {"schema": SCHEMA, "version": VERSION, "form_id": fid,
                "form_name": FORM_NAMES[fid], "explicit": True, "ambiguous": False,
                "keyword_conflict_preserved": conflict,
                "keyword_suggestion": keyword_top if conflict else None,
                "reason": "用户明确指定形态优先；题材关键词不覆盖",
                "scores": scores, "track_unchanged": True,
                "intent_revision_unchanged": True, "evidence_revision_unchanged": True}
    best = max(scores, key=lambda k: scores[k])
    tied = [k for k, v in scores.items() if v == scores[best]]
    if scores[best] == 0:
        chosen, reason, suggested = recommended or "T03", "无线索，采用推荐形态", True
    else:
        chosen = best if len(tied) == 1 else (recommended or tied[0])
        reason = "启发式关键词建议，非用户明确选择"
        suggested = True
    return {"schema": SCHEMA, "version": VERSION, "form_id": chosen,
            "form_name": FORM_NAMES[chosen], "explicit": False,
            "ambiguous": False, "recommended_only": suggested,
            "reason": reason, "scores": scores, "track_unchanged": True,
            "intent_revision_unchanged": True, "evidence_revision_unchanged": True}


def compose(form_id: str, *, topic: str, reader: str, decision: str,
            page_budget: int = 6, evidence_ready: bool = False) -> dict:
    """Page plan is a BUDGET, not a fixed six pages; data readiness can shrink it."""
    if form_id not in FORM_META:
        raise FormError(f"unknown form id: {form_id}")
    if not _finite_number(page_budget) or not (1 <= page_budget <= 6):
        raise FormError("page_budget must be 1..6")
    roles = FORM_PAGE_ROLES[form_id]
    # Missing/hard inputs legitimately reduce the page count; never pad.
    count = page_budget if evidence_ready else max(2, min(page_budget, 3))
    pages = [{"page": i + 1, "role": role,
              "shared_blocks": [b for b in FORM_BLOCK_ORDER[form_id] if b != "limits"],
              "reader_question": f"第{i+1}页回答：{role}"}
             for i, role in enumerate(roles[:count])]
    return {"schema": SCHEMA, "version": VERSION, "form_id": form_id,
            "form_name": FORM_NAMES[form_id], "topic": topic, "reader": reader,
            "decision": decision, "narrative": FORM_META[form_id]["voice"],
            "visual": FORM_META[form_id]["visual"],
            "hard_limits": FORM_META[form_id]["key"],
            "shared_block_order": FORM_BLOCK_ORDER[form_id],
            "shared_blocks": {b: SHARED_BLOCKS[b] for b in FORM_BLOCK_ORDER[form_id]},
            "page_plan": pages, "page_count": len(pages),
            "page_budget": page_budget, "evidence_ready": evidence_ready,
            "pages_reduced_for_missing_evidence": not evidence_ready,
            "static_visual_asset": f"assets/layout/{form_id}-layout.svg",
            "stylesheet": "assets/five-forms.css",
            "composition_revision_only": True,
            "note": "六页是首轮上限而非固定篇幅；实际配方/资产/数据由 composition.py 消费"}


# ---- data-limit guards ------------------------------------------------------
def normalize_units(raw_value, raw_unit: str, display_unit: str) -> dict:
    if not _finite_number(raw_value) or raw_value < 0:
        return {"value": None, "unit": display_unit, "raw_value": raw_value,
                "raw_unit": raw_unit, "state": "refused",
                "note": "负值/非有限值/布尔伪数值拒绝"}
    table = {("辆", "万辆"): 10000, ("人", "万人"): 10000,
             ("万人", "人"): 0.0001, ("元", "万元"): 10000}
    key = (raw_unit, display_unit)
    if key == ("%", "百分点"):
        return {"value": None, "unit": "百分点", "raw_value": raw_value,
                "raw_unit": "%", "state": "refused",
                "note": "百分比→百分点不是重贴标签；请用 percentage_point_delta(before, after)"}
    if key not in table:
        return {"value": None, "unit": display_unit, "raw_value": raw_value,
                "raw_unit": raw_unit, "state": "unknown",
                "note": "未登记换算，保持原值并标不可计算"}
    factor = table[key]
    return {"value": raw_value / factor, "unit": display_unit,
            "raw_value": raw_value, "raw_unit": raw_unit,
            "formula": f"{raw_value} / {factor}", "state": "computed"}


def percentage_point_delta(before_pct, after_pct) -> dict:
    """Explicit delta between two comparable ratios, with units and conditions."""
    if not (_finite_number(before_pct) and _finite_number(after_pct)):
        return {"delta": None, "unit": "百分点", "state": "refused",
                "note": "需两个有限可比比例；布尔/NaN/字符串拒绝"}
    return {"delta": round(after_pct - before_pct, 10), "unit": "百分点",
            "before_pct": before_pct, "after_pct": after_pct,
            "formula": "after_pct - before_pct", "state": "computed",
            "note": "差值语义；调用方仍须核同一对象/口径/期间"}


def period_label(observed_months, requested_label: str) -> dict:
    if not isinstance(observed_months, (list, tuple)):
        return {"state": "refused", "reason": "observed_months must be a list"}
    for m in observed_months:
        if type(m) is not int or not (1 <= m <= 12):
            return {"state": "refused", "reason": "month must be an int in 1..12 (bool rejected)"}
    months = sorted(set(observed_months))
    if not months:
        return {"actual_label": "unknown", "observed_months": [], "state": "unknown",
                "requested_label": requested_label, "full_year_fact_allowed": False,
                "missing_months": list(range(1, 13)),
                "note": "无覆盖为 unknown；不补零、不推断全年"}
    full = months == list(range(1, 13))
    missing = [m for m in range(1, 13) if m not in months]
    contiguous = months == list(range(months[0], months[-1] + 1))
    label = ("全年（1—12月，实际覆盖完整）" if full else
             f"{months[0]}—{months[-1]}月（实际覆盖 {len(months)} 个月"
             + ("" if contiguous else "，间断") + "）")
    return {"actual_label": label, "observed_months": months,
            "contiguous": contiguous, "missing_months": missing,
            "requested_label": requested_label, "state": "computed",
            "full_year_fact_allowed": full,
            "requested_label_is_fact": requested_label in ("全年", "2026全年") and full,
            "missing_months_padded_with_zero": False,
            "note": "目标范围与观测覆盖分开；间断月份保留实际集合，不以首尾暗示连续"}


def top_n(entities: list[dict], n: int) -> dict:
    if type(n) is not int or n < 1 or not isinstance(entities, list):
        return {"state": "refused", "reason": "n must be a positive int"}
    ranked = sorted(entities, key=lambda e: e["value"], reverse=True)
    shown = ranked[:n]
    return {"requested_n": n, "eligible_count": len(ranked),
            "shown_count": len(shown), "shown": shown, "invented_members": 0,
            "state": "computed",
            "note": "对象不足时只显示实际数量与覆盖说明"}


def multiple_choice(percentages: list, *, declared_mutually_exclusive: bool = False,
                    declared_exhaustive: bool = False) -> dict:
    """Multi-select entry: NEVER infer exclusivity from the sum."""
    if not isinstance(percentages, list) or not percentages:
        return {"state": "refused", "reason": "percentages must be a non-empty list"}
    for p in percentages:
        if not _finite_number(p) or p < 0:
            return {"state": "refused", "reason": "non-finite/negative/bool percentage refused"}
    total = sum(percentages)
    return {"sum_percent": total,
            "overlapping": "unknown" if not declared_mutually_exclusive else False,
            "normalized": False,
            "pie_chart_allowed": False,
            "exclusive_pie_requires": ["declared_mutually_exclusive", "declared_exhaustive",
                                       "separate single-select entry point"],
            "state": "computed",
            "note": "多选入口一律禁用互斥饼图；合计<=100 不证明互斥，重叠状态未知"}


def tgi(segment_share, population_share, *, source_family: str | None = None,
        period: str | None = None, sample_n: int | None = None,
        subset_consistent: bool | None = None,
        same_calibre: bool | None = None) -> dict:
    """TGI is evidence-conditional; arithmetic alone is never an admission guard."""
    missing = [k for k, v in {"source_family": source_family, "period": period,
                              "sample_n": sample_n, "subset_consistent": subset_consistent,
                              "same_calibre": same_calibre}.items() if v is None]
    if not (_finite_number(segment_share) and _finite_number(population_share)):
        return {"value": None, "state": "unknown", "kind": "evidence_conditional",
                "note": "非有限/布尔比例拒绝"}
    arithmetic = (round(segment_share / population_share * 100, 6)
                  if population_share != 0 else None)
    if missing or subset_consistent is not True or same_calibre is not True or population_share == 0:
        return {"value": None, "arithmetic_only": arithmetic, "state": "unknown",
                "kind": "evidence_conditional", "missing_conditions": missing or
                ["subset_consistent_or_same_calibre_not_confirmed"],
                "note": "缺同源/时期/样本/子集/同口径依据时 TGI=unknown；算术值仅作参考、不得作准入守卫"}
    return {"value": arithmetic, "state": "computed",
            "formula": f"{segment_share} / {population_share} * 100",
            "source_family": source_family, "period": period, "sample_n": sample_n,
            "kind": "evidence_conditional",
            "note": "仅在基准合法、同源同口径、子集一致且样本已核时计算"}


def conceptual_formula(expression: str, parameters: dict | None) -> dict:
    """Parameters existing is not calibration; no prediction from concepts."""
    return {"expression": expression, "type": "conceptual",
            "parameters_provided": parameters if isinstance(parameters, dict) else None,
            "numeric_result": None, "prediction_allowed": False,
            "state": "declared",
            "note": "参数存在只说明提供了参数，不认证校准/测量/模型适用性；概念入口默认不预测"}


def degrade_materials(materials: list[dict]) -> dict:
    out = []
    for m in materials:
        keep = m
        if m.get("role") == "decoration" and m.get("rights") != "available":
            keep = dict(m, state="placeholder_or_reflow", reason="无合法授权，装饰图不作证据")
        if m.get("kind") == "verbatim" and not m.get("locator"):
            keep = dict(m, state="unknown", reason="原声缺定位，不生成虚构受访者引语")
        out.append(keep)
    return {"materials": out, "verbatim_fabricated": 0,
            "decoration_counted_as_evidence": 0,
            "note": "撤销素材后合法降级为文字卡/占位/重排"}


def evaluate_plan(plan: dict, evidence: dict) -> dict:
    """Six layers reported SEPARATELY. A declaration is not a verification.
    Missing evidence is UNKNOWN; no boolean certifies source/semantic quality.
    """
    layers, notes = {}, {}
    # structure is a mechanical field check, not a quality certification
    layers["structure"] = ("PASS" if plan.get("page_plan")
                           and all(p.get("role") for p in plan["page_plan"]) else "FAIL")
    notes["structure"] = "机械字段检查；不证明回答了研究问题"
    # arithmetic requires bound input rows AND a recomputation record
    layers["arithmetic"] = ("PASS" if evidence.get("arithmetic_checked")
                            and evidence.get("bound_input_rows")
                            and evidence.get("recomputed_values_match") else "UNKNOWN")
    notes["arithmetic"] = "声明 arithmetic_checked 不等于已复算；缺绑定底表/复算记录为 UNKNOWN"
    # source requires real anchors with locators and a family/readback check
    anchors = evidence.get("source_anchors") or []
    layers["source"] = ("PASS" if anchors and all(isinstance(a, dict) and a.get("locator")
                                                  for a in anchors)
                        and evidence.get("source_readback_verified") else "UNKNOWN")
    notes["source"] = "字符串锚点或非空 flag 不证明来源有效；缺回查为 UNKNOWN"
    # semantic requires counterevidence AND explicit conditions AND an actual check
    layers["semantic"] = ("PASS" if evidence.get("counterevidence_present")
                          and evidence.get("conditions_recorded")
                          and evidence.get("semantic_recheck_performed") else
                          "FAIL" if evidence.get("semantic_violation_proven") else "UNKNOWN")
    notes["semantic"] = "反证声明与条件记录、实际回查分开；缺项为 UNKNOWN"
    # author protection requires explicit evidence, never a default
    layers["author_protection"] = (
        "PASS" if evidence.get("hand_edits_preserved") is True
        and evidence.get("scope_validation") else
        "FAIL" if evidence.get("hand_edits_preserved") is False else "UNKNOWN")
    notes["author_protection"] = "缺省不判 PASS；需局改范围验证器与手改字节回读"
    layers["visual_delivery"] = "UNKNOWN"
    notes["visual_delivery"] = "实际生成/读回/渲染/目视/宿主显示分别记录；SVG 存在不等于显示通过"
    return {"form_id": plan.get("form_id"), "layers": layers, "layer_notes": notes,
            "declarations": sorted(k for k in evidence if k.endswith("_checked")
                                   or k.endswith("_present")),
            "no_total_score_override": True,
            "note": "分层结果，缺证据 UNKNOWN；不存在综合高分覆盖关键失败"}


def build_catalog() -> dict:
    return {"schema": "paper.five-forms.catalog.v2", "version": VERSION,
            "state": "PACKAGED_RUNTIME_ASSET",
            "dimensions": ["research_question", "effective_intent", "industry_adapter",
                           "primary_report_form", "evidence_readiness", "material_readiness",
                           "output_medium"],
            "wire_change_authorized": False, "form_is_wire_field": False,
            "first_pass_max_pages": 30, "max_pages_each": 6,
            "forms": [{"id": k, "name": FORM_NAMES[k], "slug": FORM_SLUGS[k],
                       "narrative": v["voice"], "visual": v["visual"],
                       "hard_limits": v["key"], "page_roles": FORM_PAGE_ROLES[k],
                       "template": f"templates/{k}-{FORM_SLUGS[k]}.md"}
                      for k, v in FORM_META.items()]}


def _main() -> None:
    p = Path(__file__).resolve().parents[1] / "templates" / "FORM-CATALOG.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(build_catalog(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"written": str(p).replace("\\", "/"), "forms": 5,
                      "version": VERSION}, ensure_ascii=False))


if __name__ == "__main__":
    _main()
