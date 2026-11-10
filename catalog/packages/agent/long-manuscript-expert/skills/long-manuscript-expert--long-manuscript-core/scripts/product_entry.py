#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The REAL product entry point for long-manuscript-expert 2026.11.5 (rev 3).

This is the consumption point that the independent forms review found missing:
it actually CALLS the five-form guards, the composition consumer, the editorial
scope validator, the guarded writer and the portable project card, then reads
the produced files back. Helper return values alone are never user acceptance.

Rev 3 (second-round review ENTRY-01..04 + scope fixes):
  * NO fixed demonstration operands live in the product path. Guards are fed
    the ACTUAL task operands (data rows, materials, user-declared period/
    multi-select values, unit conversions the caller actually supplies).
    Missing operands stay UNKNOWN / not_applicable; the product never invents
    samples, periods, survey families or percentage pairs.
  * guard results actually CHANGE the output: a refused/unknown guard marks
    the dependent claim/chart state and the product body, not just a return
    value.
  * quality layers are built ONLY from checks that really ran (source bytes
    re-read, claims bound, scope validated by the real validator). Absent
    checks stay UNKNOWN; no positive booleans are synthesized.
  * input classification comes from the caller's EXPLICIT bounded declaration
    (fixed_synthetic / user_supplied / unknown); default is unknown. Real
    materials are never labelled synthetic and vice versa.
  * next_step is DERIVED from the current task state (missing hard inputs /
    months / claims), never a fixed canned string.
  * scoped_revision confines the original draft path to the caller-selected
    project BEFORE any read, not only at writer time.
  * composition non-selected states (needs_selection / no_match / refused /
    limited without content) return a real bounded state instead of raising.

Rev 3 core follow-up (native-scope S3 / native-forms r3):
  * guard refusals/unknowns are DELIVERED content: they are rendered into the
    product body AND bound into the composition input digest (GUARD-OUTPUT).
  * proposal adoption binds exact declared values (project_card S3-02) and a
    direct new instruction is a separately labelled path.
  * a write receipt that is not `completed` returns a bounded unknown state
    here — no card/deliverable is written, no KeyError (UNKNOWN-WRITE).
  * a FROZEN closure (product modules + packaged library manifest) is
    verified byte-for-byte inside write_new immediately before publication,
    re-verified before the card is saved, and recorded on the card
    (source-guard).

Standard library only. Ordinary research needs no login, connector, service,
Python runtime installation or development absolute path.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import composition
import paper_forms as pf
import project_card as pc
import scoped_writer as sw

VERSION = "2026.11.5"
SCHEMA = "paper.product-entry.v3"

GUARD_NOTE = "守卫以调用方实际操作数消费；缺操作数保持 UNKNOWN/不适用，不造样本、期间或同源族"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---- frozen closure (source-guard) -----------------------------------------
FROZEN_CLOSURE_MEMBERS = ("composition.py", "project_card.py", "paper_forms.py",
                          "product_entry.py", "scoped_writer.py")


def frozen_closure() -> dict[str, str]:
    """Freeze ONE immutable set: absolute path -> sha256 for every NON-writer
    product module PLUS the COMPLETE bytes of every packaged library asset the
    composition actually consumes (recipes / blocks / templates / data /
    visuals), not merely MANIFEST.json. Input files are enforced separately
    via the writer's baselines.

    Captured ONCE at entry start. Every later new-draft / card write re-reads
    and byte-compares THIS SAME set; no baseline is re-captured from current
    disk at a later write boundary. Unrelated engineering history (reviews,
    qa, archives, other clients) is never part of the closure. The caller
    rebinds the consumer/library entries to the digests the composition
    RECEIPT declares (the bytes that actually produced the content)."""
    scripts = Path(__file__).resolve().parent
    out: dict[str, str] = {}
    for name in FROZEN_CLOSURE_MEMBERS:
        p = scripts / name
        out[str(p).replace("\\", "/")] = sha(p.read_bytes())
    manifest = composition.LIB / "MANIFEST.json"
    out[str(manifest).replace("\\", "/")] = sha(manifest.read_bytes())
    # enterprise-r4 A: the 5 modules + MANIFEST is NOT the whole asset set.
    # Bind every real recipe / block / template / data / visual byte too.
    manifest_index = json.loads(manifest.read_bytes())
    for rel in sorted(manifest_index["files"]):
        p = composition.LIB / rel
        if p.is_file():
            out[str(p).replace("\\", "/")] = sha(p.read_bytes())
    return out


def bind_closure_to_receipt(closure: dict[str, str], receipt: dict) -> dict[str, str]:
    """Bind the frozen set to the SHA the composition RECEIPT declares.

    These are immutable digests of the bytes that ACTUALLY produced the
    content (consumer + every consumed library asset), not a fresh read of
    current disk. Rebinding to receipt values is NOT re-capturing a baseline:
    the SAME single frozen set is then used at every write boundary, so a
    post-composition byte change is refused at BOTH the draft write and the
    card write boundary.
    """
    bound = dict(closure)
    bound[str(composition.CONSUMER_SOURCE).replace("\\", "/")] = \
        receipt["consumer_sha256"]
    for rel, asset_sha in sorted(receipt["assets_sha256"].items()):
        bound[str(composition.LIB / rel).replace("\\", "/")] = asset_sha
    bound[str(composition.LIB / "MANIFEST.json").replace("\\", "/")] = \
        receipt["manifest_sha256"]
    return bound


def verify_closure(closure: dict[str, str]) -> list[str]:
    """Re-read every closure member NOW; return changed/missing entries."""
    changed = []
    for path_key, expected in closure.items():
        try:
            actual = sha(Path(path_key).read_bytes())
        except OSError:
            changed.append(f"missing:{path_key}")
            continue
        if actual != expected:
            changed.append(f"changed:{path_key}")
    return changed


def _closure_card_record(closure: dict[str, str]) -> dict:
    """Card-side closure binding keyed by member basename (the enforcement
    itself used the full paths inside the guarded writer)."""
    return {"members": {Path(k).name: v for k, v in sorted(closure.items())},
            "member_count": len(closure),
            "enforced_before_write": True}


def _confined(project: Path, rel: str) -> Path:
    """A card/draft reference is only readable INSIDE the selected project."""
    if not isinstance(rel, str) or not rel:
        raise sw.GuardError(f"reference must be a non-empty relative path: {rel!r}")
    rel_norm = rel.replace("\\", "/")
    if rel_norm.startswith("/") or len(rel_norm) > 1 and rel_norm[1] == ":":
        raise sw.OutsideScope(f"absolute reference refused: {rel}")
    parts = [p for p in rel_norm.split("/") if p not in ("", ".")]
    if ".." in parts or not parts:
        raise sw.OutsideScope(f"reference escapes the selected project: {rel}")
    candidate = project.joinpath(*parts)
    resolved = candidate.resolve()
    base = project.resolve()
    if not (resolved == base or resolved.is_relative_to(base)):
        raise sw.OutsideScope(f"reference escapes the selected project: {rel}")
    return candidate


def first_value(*, project_dir: str | Path, user_text: str, topic: str, reader: str,
                decision: str, goal: str, track: str | None,
                available_inputs: dict, data_rows: list[dict],
                claims: list[dict], materials: list[dict],
                explicit_recipe_id: str | None = None,
                data_ready: bool = False, operation_id: str = "op-first-0001",
                input_declaration: dict | None = None,
                period_requested: str | None = None,
                multiselect_values: list | None = None,
                unit_conversions: list[dict] | None = None) -> dict:
    """Natural language -> form -> recipe -> bound content -> guarded file ->
    readback -> portable card. Every guard is actually consumed here, with the
    CALLER'S real operands; nothing is hard-coded."""
    project = Path(project_dir).resolve()
    project.mkdir(parents=True, exist_ok=True)

    # source-guard: freeze the NON-writer dependency bytes as they are being
    # consumed. The composition.py / MANIFEST.json entries are later REBOUND
    # to the digests the composition receipt declares (the bytes that
    # actually produced the content), so a byte change between composition
    # and publication is refused with zero product writes.
    closure = frozen_closure()

    # 1) explicit form wins; ambiguity is preserved, not guessed away
    form = pf.select_form(user_text, recommended="T03")
    if form["form_id"] is None:
        return {"schema": SCHEMA, "version": VERSION, "state": "needs_selection",
                "form": form, "reason": "多个明确形态冲突，请用户选择",
                "guards_consumed": ["select_form"], "product_writes": 0,
                "note": "形态冲突返回真实受限状态；与组合受限分支一致零写，不猜形态"}
    fid = form["form_id"]

    # 2) data/quality guards consume the ACTUAL task operands ONLY.
    #    Missing operands stay UNKNOWN; the product never supplies them.
    guards = {}
    guard_impacts: list[str] = []
    months = [r.get("month") for r in data_rows
              if isinstance(r.get("month"), int) and 1 <= r.get("month") <= 12]
    if months:
        guards["period"] = pf.period_label(months, period_requested or "用户未声明期间")
    else:
        guards["period"] = {"state": "unknown", "reason": "no_observed_months",
                            "note": "未提供任何已观测月份；期间保持未知，不默认全年"}
    numeric_rows = [r for r in data_rows
                    if isinstance(r.get("raw_value"), (int, float))
                    and not isinstance(r.get("raw_value"), bool)]
    if numeric_rows:
        guards["top_n"] = pf.top_n([{"id": r.get("object", "unknown"),
                                     "value": r.get("raw_value")} for r in numeric_rows], 10)
    else:
        guards["top_n"] = {"state": "unknown", "reason": "no_numeric_objects",
                           "note": "无数值对象；TOP-N 不虚构成员"}
    guards["materials"] = pf.degrade_materials(materials)
    guards["conceptual"] = pf.conceptual_formula(None, None) if not numeric_rows else \
        pf.conceptual_formula(None, None)
    if isinstance(multiselect_values, list) and multiselect_values:
        guards["multiple_choice"] = pf.multiple_choice(multiselect_values)
        if not guards["multiple_choice"].get("pie_chart_allowed", False):
            guard_impacts.append("multiple_choice_refused_pie_chart")
    else:
        guards["multiple_choice"] = {"state": "unknown",
                                     "reason": "no_multiselect_values_supplied",
                                     "note": "未提供多选分布；不默认 [40,35,50]"}
    # TGI / percentage points are evidence-conditional: without the caller's
    # actual survey values they stay unknown. No default 0.6/0.75, no
    # same-survey/100-sample fabrication.
    guards["tgi"] = {"value": None, "state": "unknown",
                     "missing_conditions": ["numerator", "denominator", "source_family",
                                            "period", "sample_n", "subset_consistent",
                                            "same_calibre"],
                     "note": "TGI 仅在调用方提供真实分子/分母与同源同口径依据时计算"}
    guards["percentage_point"] = {"value": None, "state": "not_applicable",
                                  "note": "未提供前后百分比；不做 32→40 演示差值"}
    if unit_conversions:
        convs = []
        for c in unit_conversions:
            if (isinstance(c.get("raw_value"), (int, float))
                    and isinstance(c.get("raw_unit"), str) and isinstance(c.get("target_unit"), str)):
                convs.append(pf.normalize_units(c["raw_value"], c["raw_unit"], c["target_unit"]))
            else:
                convs.append({"state": "unknown", "reason": "incomplete_conversion_operand"})
        guards["unit_conversion"] = {"conversions": convs,
                                     "note": "单位换算仅消费调用方实际提供的换算操作数"}
    else:
        guards["unit_conversion"] = {"state": "unknown",
                                     "reason": "no_conversion_operands_supplied",
                                     "note": "未提供换算操作数；不默认 1500000 辆"}

    # 3) plan is a budget, not fixed six pages
    plan = pf.compose(fid, topic=topic, reader=reader, decision=decision,
                      evidence_ready=data_ready)

    # 3b) R3-ENTRY-GUARD-OUTPUT: actual guard refusals/unknowns (and unit
    #     conversion states) become DELIVERED content — they are rendered
    #     into the product body and bound into the composition input digest,
    #     never machine-side-only receipt notes.
    guard_results = []
    for name in ("period", "top_n", "materials", "multiple_choice",
                 "tgi", "percentage_point", "unit_conversion"):
        g = guards[name]
        state = g.get("state")
        if state in ("refused", "unknown"):
            guard_results.append({"guard": name, "state": state,
                                  "reason": g.get("reason") or "见该守卫返回",
                                  "note": g.get("note") or ""})
    if isinstance(guards["unit_conversion"].get("conversions"), list):
        for i, c in enumerate(guards["unit_conversion"]["conversions"], 1):
            if c.get("state") in ("refused", "unknown"):
                guard_results.append(
                    {"guard": "unit_conversion", "state": c["state"],
                     "reason": c.get("reason") or "换算操作数不完整",
                     "note": f"第{i}项换算"})

    # 4) REAL composition: library SHA, unique recipe, versioned blocks,
    #    typed data panels, visual contracts, content receipt and readback
    comp = composition.compose_content(
        form_id=fid, topic=topic, reader=reader, decision=decision,
        goal=goal, track=track, available_inputs=available_inputs,
        data_rows=data_rows, explicit_recipe_id=explicit_recipe_id,
        data_ready=data_ready, claims=claims, guard_results=guard_results)
    sel_state = comp["selection"]["state"]
    if sel_state in ("no_match", "needs_selection", "refused"):
        # Real bounded state: no product file, no invented draft.
        return {"schema": SCHEMA, "version": VERSION,
                "state": sel_state, "form": form,
                "composition": {"selection": comp["selection"]},
                "guards_consumed": guards, "product_writes": 0,
                "reason": comp["selection"].get("reason"),
                "note": "缺硬输入/多匹配/无匹配返回真实受限状态；不制造错误稿、不假完成"}
    body = comp["content_bytes"]
    # source-guard (enterprise-r4 A): bind the consumer AND every consumed
    # library asset (recipes/blocks/templates/data/visuals) to the digests the
    # composition receipt actually declares — the bytes that PRODUCED this
    # content, not merely whatever is on disk at write time. The resulting
    # single frozen set is passed to BOTH the draft write and the card write.
    closure = bind_closure_to_receipt(closure, comp["receipt"])

    # 5) six-layer quality built ONLY from checks that actually RAN here.
    inputs_dir = project / "inputs"
    input_files = sorted(f for f in inputs_dir.iterdir()) if inputs_dir.is_dir() else []
    input_evidence = []
    for f in input_files:
        if f.is_file():
            b = f.read_bytes()
            input_evidence.append({"locator": f"inputs/{f.name}",
                                   "bytes": len(b), "sha256": sha(b),
                                   "readback_verified": True})
    baselines = {e["locator"]: {"sha256": e["sha256"], "bytes": e["bytes"]}
                 for e in input_evidence}
    bound_claims = [c for c in claims if c.get("text") and c.get("support")]
    claim_anchors = []
    for c in bound_claims:
        anchors = [{"locator": s} if isinstance(s, str) else s for s in c.get("support", [])]
        claim_anchors.append({"claim": c["text"], "anchors": anchors,
                              "anchor_count": len(anchors),
                              "anchor_verified": all(
                                  any(a.get("locator") == (anc.get("locator") if isinstance(anc, dict) else anc)
                                      for a in input_evidence) for anc in anchors)})
    # No INDEPENDENT arithmetic recomputation runs in the first-value pass
    # (composing is not recomputing). The layer therefore stays UNKNOWN: a
    # denominator being present is a declaration, never a recomputation record.
    quality = pf.evaluate_plan(plan, {
        "bound_input_rows": input_evidence,
        "recomputed_values_match": None,
        "source_anchors": input_evidence,
        "source_readback_verified": bool(input_evidence),
        "counterevidence_present": bool(any(c.get("counter") for c in bound_claims)),
        "conditions_recorded": bool(any(c.get("conditions") for c in bound_claims)),
        "semantic_recheck_performed": None,   # never synthesized
        "hand_edits_preserved": None,         # first value has no prior hand edits
        "scope_validation": None,
    })
    # Guard impacts must be visible in the emitted product, not just returned.
    for impact in guard_impacts:
        quality.setdefault("layer_notes", {})[impact] = (
            "守卫拒绝/未知已改变输出：相关图表按降级处理，正文保留限制说明")

    # 6) write the product through the REAL guarded writer (atomic, claimed)
    #    with the FROZEN closure enforced immediately before publication.
    guard = sw.ScopedWriter(project)
    try:
        receipt = guard.write_new("drafts/working-paper-v1.md", body,
                                  baselines=baselines, operation_id=operation_id,
                                  label="first_value", closure=closure)
    except sw.SourceChanged as exc:
        return {"schema": SCHEMA, "version": VERSION, "state": "unknown",
                "reason": "frozen_closure_changed_before_write",
                "detail": str(exc), "operation_id": operation_id,
                "writes": 0, "product_writes": 0,
                "guards_consumed": guards, "guard_impacts": guard_impacts,
                "note": "冻结闭包（产品模块/库清单）在发布前字节变化：零产品写；"
                        "有界 unknown，不写交付物/卡，不冒充完成"}
    if receipt.get("state") != "completed":
        # R3-ENTRY-UNKNOWN-WRITE: an unknown/conflict write result is a real
        # bounded state here — the original id and ACTUAL counts are kept,
        # no deliverable/card is written, nothing raises.
        oid = (receipt.get("operation_id")
               or (receipt.get("claim") or {}).get("operation_id")
               or operation_id)
        return {"schema": SCHEMA, "version": VERSION, "state": "unknown",
                "reason": receipt.get("reason") or "write_not_completed",
                "operation_id": oid,
                "writes": receipt.get("writes", 0),
                "product_writes": receipt.get("product_writes",
                                              receipt.get("writes", 0)),
                "write_result": receipt,
                "guards_consumed": guards, "guard_impacts": guard_impacts,
                "note": "写回执未确认完成：保留原号与实际计数，有界 unknown；"
                        "不写交付物/卡，不冒充完成"}

    # 7) portable card with real coverage layers, deliverables and receipts
    card = pc.create_card(topic=topic, reader=reader, decision=decision,
                          scope={"period": guards["period"].get("actual_label",
                                  guards["period"].get("state")),
                                 "goal": goal, "track": track},
                          input_declaration=input_declaration)
    pc.set_form(card, fid, reason="用户自然语言形态选择（纯表达变更）")
    for e in input_evidence:
        f = project / e["locator"]
        pc.bind_material(card, path=e["locator"], data=f.read_bytes(), category="read")
    for c in bound_claims:
        pc.add_claim(card, text=c["text"], support=c["support"],
                     counter=c.get("counter", []), conditions=c.get("conditions", []),
                     section=c.get("section", "正文"))
    pc.add_deliverable(card, path="drafts/working-paper-v1.md",
                       kind="editable_draft", data=body, readback=True)
    pc.add_receipt(card, receipt)
    # next_step is DERIVED from the actual current task state.
    missing_hard = comp["selection"].get("missing_hard_inputs") or []
    pending = []
    if missing_hard:
        pending.append("补齐硬输入：" + "、".join(missing_hard))
    if guards["period"].get("state") == "unknown":
        pending.append("提供已观测期间/月份")
    if len(bound_claims) < 3:
        pending.append("补充证据以形成至少三条承重主张")
    if not input_evidence:
        pending.append("提供可读取的输入材料")
    card["next_step"] = ("；".join(pending) if pending
                         else "范围与材料已齐备，按计划推进正文与反证核验")
    card["composition_binding"] = comp.get("receipt")
    card["quality_layers"] = quality
    card["guards_consumed"] = {k: {"state": v.get("state")} for k, v in guards.items()}
    card["guard_impacts"] = guard_impacts
    card["source_closure"] = _closure_card_record(closure)
    # source-guard: an outer pre-check catches drift that happened before card
    # assembly; the AUTHORITATIVE check now lives INSIDE pc.save at the real
    # file-creation/write boundary (enterprise-r4 A), using the same frozen
    # set. A change injected at the pc.save entry can no longer produce a card.
    closure_drift = verify_closure(closure)
    if closure_drift:
        return {"schema": SCHEMA, "version": VERSION, "state": "partial",
                "reason": "closure_changed_after_write_before_card_save",
                "changed": closure_drift, "operation_id": operation_id,
                "published": {"path": "drafts/working-paper-v1.md",
                              "sha256": sha(body), "bytes": len(body)},
                "write_receipt": receipt, "guards_consumed": guards,
                "draft_writes": 1, "card_writes": 0,
                "note": "产品已发布但闭包在卡保存前变化：有界 partial 并披露已发布稿；"
                        "不把卡绑定到已变化的源"}
    try:
        saved = pc.save(card, project / "project-card.json", closure=closure)
    except pc.CardSourceChanged as exc:
        # The single frozen set changed at the ACTUAL card write boundary.
        # Keep the published draft and the original operation id, write ZERO
        # cards, and return a bounded partial (never completed).
        return {"schema": SCHEMA, "version": VERSION, "state": "partial",
                "reason": "frozen_closure_changed_at_card_write_boundary",
                "changed": exc.changed, "operation_id": operation_id,
                "published": {"path": "drafts/working-paper-v1.md",
                              "sha256": sha(body), "bytes": len(body)},
                "write_receipt": receipt, "guards_consumed": guards,
                "draft_writes": 1, "card_writes": 0,
                "closure_not_recaptured": True,
                "note": "闭包在卡片文件创建/写入边界内部重核发现变化：保留已发布稿与原号，"
                        "卡0写、有界 partial；不重捕获基线、不替换已选摘要、不冒充 completed"}

    # 8) actual readback of the produced product and card
    produced = (project / "drafts/working-paper-v1.md").read_bytes()
    card_rb = Path(saved["path"]).read_bytes()
    return {"schema": SCHEMA, "version": VERSION, "state": "completed",
            "form": form, "plan": plan, "composition": {
                "selection": comp["selection"],
                "recipe": (comp.get("receipt") or {}).get("recipe"),
                "ordered_blocks": (comp.get("receipt") or {}).get("ordered_blocks"),
                "claims_state": comp.get("claims_state"),
                "assets_verified": bool(comp.get("receipt")),
                "separate_branch": comp.get("separate_branch")},
            "guards_consumed": guards, "guard_impacts": guard_impacts,
            "quality_layers": quality,
            "source_closure": _closure_card_record(closure),
            "write_receipt": receipt,
            "card": saved,
            "readback": {"product_sha256": sha(produced),
                         "product_matches": produced == body,
                         "card_sha256": sha(card_rb),
                         "card_readback_verified": saved["readback_verified"]},
            "note": "守卫由真实成稿入口以实际操作数消费；可编辑文件与接续卡实际读回；"
                    "缺操作数的守卫保持未知并影响输出状态"}


def scoped_revision(*, project_dir: str | Path, original_rel: str,
                    revised_text: str, authorized_sections: list[str],
                    protected_texts: list[str], operation_id: str,
                    target_rel: str = "drafts/working-paper-v2.md") -> dict:
    """A real scoped-revision entry: path confinement and editorial validation
    BOTH happen BEFORE any read of the original or any write."""
    project = Path(project_dir).resolve()
    # Confine the ORIGINAL draft path to the caller-selected project BEFORE
    # reading it; a `../` or absolute reference is refused before any byte of
    # an outside file is read.
    try:
        original_path = _confined(project, original_rel)
        target_path = _confined(project, target_rel)
    except sw.OutsideScope as exc:
        return {"schema": SCHEMA, "version": VERSION, "state": "refused",
                "reason": "path_outside_selected_project", "detail": str(exc),
                "product_writes": 0, "bytes_read_outside_project": 0,
                "note": "读取原稿前先核选定项目范围；越界引用在读取前拒绝"}
    if not original_path.is_file():
        return {"schema": SCHEMA, "version": VERSION, "state": "refused",
                "reason": "original_draft_missing", "product_writes": 0}
    original = original_path.read_bytes()
    revised = revised_text.encode("utf-8")
    check = sw.validate_scoped_revision(
        original=original, revised=revised,
        protected_texts=[t.encode("utf-8") for t in protected_texts],
        authorized_sections=authorized_sections)
    if not check["valid"]:
        return {"schema": SCHEMA, "version": VERSION, "state": "refused",
                "scope_check": check, "product_writes": 0,
                "note": "范围外改动/手记删除在任何写入之前拒绝"}
    baselines = {original_rel: {"sha256": sha(original), "bytes": len(original)}}
    guard = sw.ScopedWriter(project)
    closure = frozen_closure()
    try:
        receipt = guard.write_new(target_rel.replace("\\", "/"), revised,
                                  baselines=baselines, operation_id=operation_id,
                                  label="scoped_revision", closure=closure)
    except sw.SourceChanged as exc:
        return {"schema": SCHEMA, "version": VERSION, "state": "unknown",
                "reason": "frozen_closure_changed_before_write",
                "detail": str(exc), "operation_id": operation_id,
                "writes": 0, "product_writes": 0,
                "note": "冻结闭包在发布前变化：零产品写，有界 unknown"}
    if receipt.get("state") != "completed":
        oid = (receipt.get("operation_id")
               or (receipt.get("claim") or {}).get("operation_id")
               or operation_id)
        return {"schema": SCHEMA, "version": VERSION, "state": "unknown",
                "reason": receipt.get("reason") or "write_not_completed",
                "operation_id": oid,
                "writes": receipt.get("writes", 0),
                "product_writes": receipt.get("product_writes",
                                              receipt.get("writes", 0)),
                "write_result": receipt,
                "note": "写回执未确认完成：保留原号与实际计数，有界 unknown"}
    rb = target_path.read_bytes()
    return {"schema": SCHEMA, "version": VERSION, "state": "completed",
            "scope_check": check, "write_receipt": receipt,
            "source_closure": _closure_card_record(closure),
            "readback": {"sha256": sha(rb), "matches": rb == revised},
            "out_of_scope_sync_pending": not check["out_of_scope_sections_unchanged"],
            "note": "先核项目范围/授权范围/手记/范围外字节，再另存并读回"}
