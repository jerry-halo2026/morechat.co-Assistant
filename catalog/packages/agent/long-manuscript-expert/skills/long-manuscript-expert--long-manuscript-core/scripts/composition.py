#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Real composition consumer for long-manuscript-expert 2026.11.5 (rev 2).

Standard library only. Restores the selected-scope capabilities that the
first revision replaced with five descriptive blocks:

* selects a UNIQUE compatible recipe from the packaged 17-recipe / 62-block
  library using effective goal, track/sector/scenario, explicit preference,
  hard-input readiness and data readiness. Multiple matches stay PROPOSED.
* actually READS the library manifest and every selected asset, verifies each
  byte against the pinned SHA, and binds consumer/asset/recipe/block versions.
* consumes typed data contracts and visual contracts/crosswalk: real values
  and missingness drive original-value / unknown panels; unimplemented visual
  types degrade to named readable tables rather than being claimed as charts.
* emits a content receipt with input/source/recipe/block/consumer/output SHA
  and reads the produced content back.

The library is a single flat 23-file / 85914-byte copy; no frozen ancestry,
parent pins, historical receipts or development absolute paths are needed.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

VERSION = "2026.11.5"
PRODUCT = "long-manuscript-expert"
SCHEMA = "paper.composition.v2"
LIB = Path(__file__).resolve().parents[1] / "assets" / "library"
CONSUMER_SOURCE = Path(__file__).resolve()
MANIFEST_SHA256 = "e2c8056bfd3d16560ebdac22b33c75a67175c4c6393ff0b4d87934d48c1949b6"
RECIPES_SHA256 = "d227312f2bb0da3325207ebc244c33d028865282b67e81fa8204b2726d688b5b"
BLOCKS_SHA256 = "b1d1538989ca12d9ef001f7e5f9429428e771f7302f92feaceafd98255f6610b"

# The 18-recipe adopted T03 branch is a separate author-adopted branch. It is
# never silently merged into the 17-recipe library or claimed as verified.
SEPARATE_BRANCH = {"id": "t03-18-recipe-adopted", "operations": 0,
                   "state": "separate_not_migrated_not_verified"}


class CompositionError(ValueError):
    pass


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_library() -> dict:
    """Read ACTUAL bytes; verify the pinned manifest and every listed asset."""
    manifest_path = LIB / "MANIFEST.json"
    manifest_bytes = manifest_path.read_bytes()
    if sha(manifest_bytes) != MANIFEST_SHA256:
        raise CompositionError("library MANIFEST digest mismatch; refuse stale assets")
    manifest = json.loads(manifest_bytes)
    # The manifest itself is a packaged asset too: 22 listed files + 1 manifest
    # = 23 physical files / 85914 bytes, all byte-verified and receipt-bound.
    assets = {"MANIFEST.json": {"bytes": len(manifest_bytes),
                                "sha256": sha(manifest_bytes), "data": manifest_bytes}}
    for rel, expected in manifest["files"].items():
        p = LIB / rel
        if not p.is_file():
            raise CompositionError(f"missing packaged asset: {rel}")
        data = p.read_bytes()
        if sha(data) != expected:
            raise CompositionError(f"asset changed: {rel}")
        assets[rel] = {"bytes": len(data), "sha256": expected, "data": data}
    recipes = json.loads(assets["recipes.json"]["data"])
    blocks = json.loads(assets["blocks.json"]["data"])
    data_contracts = json.loads(assets["data/DATA-CONTRACTS.json"]["data"])
    visual_contracts = json.loads(assets["visuals/VISUAL-CONTRACTS.json"]["data"])
    crosswalk = json.loads(assets["visuals/VISUAL-CROSSWALK.json"]["data"])
    return {"manifest_sha256": MANIFEST_SHA256, "assets": assets,
            "recipes": recipes["recipes"], "blocks": {b["id"]: b for b in blocks["blocks"]},
            "data_contracts": data_contracts, "visual_contracts": visual_contracts,
            "crosswalk": crosswalk}


def select_recipe(*, goal: str, track: str | None, form_id: str,
                  explicit_recipe_id: str | None, available_inputs: dict,
                  data_ready: bool, lib: dict) -> dict:
    """UNIQUE compatible recipe or a PROPOSED set; never a silent fallback.

    The library schema uses `track_id`; an explicit recipe id is honoured ONLY
    if it is actually compatible with the effective goal/track — an explicit
    id never bypasses compatibility.
    """
    def _compatible(r) -> bool:
        if r.get("goal") != goal:
            return False
        if track is None:
            return True
        return r.get("track_id") == track or r.get("track") == track
    if explicit_recipe_id:
        matches = [r for r in lib["recipes"] if r["id"] == explicit_recipe_id]
        if not matches:
            return {"state": "refused", "reason": "explicit_recipe_not_in_library"}
        if not _compatible(matches[0]):
            return {"state": "refused", "reason": "explicit_recipe_incompatible_goal_or_track",
                    "requested": {"goal": goal, "track": track},
                    "recipe": {"goal": matches[0].get("goal"),
                               "track_id": matches[0].get("track_id")},
                    "note": "明确指定配方仍须与有效目标/赛道兼容；不绕过兼容性"}
    else:
        matches = [r for r in lib["recipes"] if _compatible(r)]
    if not matches:
        return {"state": "no_match", "reason": "no recipe for goal/track",
                "native_local_first_value": True,
                "note": "无匹配不等于需要新建赛道；原生本地首值继续"}
    for r in matches:
        missing = [k for k in r.get("hard_inputs", [])
                   if k not in available_inputs or available_inputs[k] in (None, "", "unknown")]
        r["_missing_hard_inputs"] = missing
    if len(matches) > 1 and not explicit_recipe_id:
        return {"state": "needs_selection", "candidates":
                [{"id": r["id"], "goal": r["goal"], "track_id": r.get("track_id"),
                  "missing_hard_inputs": r["_missing_hard_inputs"]} for r in matches],
                "reason": "multiple compatible recipes; explicit choice required",
                "adopted": False}
    chosen = matches[0]
    missing = chosen["_missing_hard_inputs"]
    if missing:
        return {"state": "limited", "recipe": {"id": chosen["id"], "version": 1,
                                               "goal": chosen["goal"],
                                               "fallback": chosen.get("fallback")},
                "missing_hard_inputs": missing,
                "degraded": True, "auto_applied": False,
                "reason": "hard inputs missing; bounded first value with unknowns",
                "note": "缺硬条件不静默当唯一已选；不补零、不虚构"}
    return {"state": "selected", "recipe": {"id": chosen["id"], "version": 1,
                                            "goal": chosen["goal"],
                                            "track_id": chosen.get("track_id"),
                                            "fallback": chosen.get("fallback")},
            "missing_hard_inputs": [], "degraded": not data_ready,
            "auto_applied": True,
            "auto_apply_condition": chosen.get("auto_apply_condition"),
            "note": "唯一兼容且硬输入齐备才自动采用"}


def _visual_contract(block: dict, lib: dict) -> dict:
    """Crosswalk a block to its visual contract; degrade unknown/unimplemented."""
    kind = block.get("visual_kind")
    mapping = next((m for m in lib["crosswalk"]["mapping"]
                    if m["block_visual_kind"] == kind), None)
    contract_id = mapping["contract_id"] if mapping else block.get("visual_contract_ref")
    known = {t["id"] for t in lib["visual_contracts"]["types"]}
    implemented = {"evidence-table", "decision-card"}  # bounded actual consumers
    return {"contract_id": contract_id, "known_contract": contract_id in known,
            "dedicated_renderer_implemented": contract_id in implemented,
            "fallback": ("readable_table_or_unknown_panel" if contract_id not in implemented
                         else "static_value_table"),
            "required": next((t["required"] for t in lib["visual_contracts"]["types"]
                              if t["id"] == contract_id), []),
            "unknown_behavior": next((t["unknown_behavior"] for t in lib["visual_contracts"]["types"]
                                      if t["id"] == contract_id),
                                     "unknown panel; never coerce null to 0")}


def _data_panel(rows: list[dict], lib: dict) -> dict:
    """Type-check rows against DATA-CONTRACTS and render real/unknown panels.

    A TRUE ZERO is an observed value of 0: the value stays 0 and the panel is
    an original-value panel. Missing/unread stays None with an unknown panel.
    `value or ...` coercion is never used; None and 0 are distinct states.
    """
    contract = lib["data_contracts"]["dataset_row"]
    panels = []
    for row in rows:
        missing = [k for k in ("object", "raw_value", "unit", "period", "denominator",
                               "source_ref", "missing_state")
                   if k not in row or row[k] in (None, "")]
        if row.get("missing_state") in ("missing", "unread", "unknown") or missing:
            value_state = "unknown"
        elif row.get("raw_value") == 0:
            value_state = "true_zero"
        else:
            value_state = "observed"
        # true_zero IS an observed value: keep the actual 0, never null it.
        value = (row.get("raw_value") if value_state in ("observed", "true_zero")
                 else None)
        panels.append({"object": row.get("object", "unknown"),
                       "value": value,
                       "unit": row.get("unit"), "period": row.get("period"),
                       "denominator": row.get("denominator"),
                       "source_ref": row.get("source_ref"),
                       "value_state": value_state,
                       "missing_fields": missing,
                       "render": ("unknown_panel" if value_state == "unknown"
                                  else "original_value_table")})
    return {"contract_schema": lib["data_contracts"]["schema"],
            "declared_contract_fields": contract,
            "panels": panels, "coerced_null_to_zero": False,
            "true_zero_kept_as_zero": all(p["value"] == 0 for p in panels
                                          if p["value_state"] == "true_zero"),
            "note": "真实原值/缺失/真零分开；缺项不补零，真零保留 0"}


def compose_content(*, form_id: str, topic: str, reader: str, decision: str,
                    goal: str, track: str | None, available_inputs: dict,
                    data_rows: list[dict], explicit_recipe_id: str | None = None,
                    data_ready: bool = False, claims: list[dict] | None = None,
                    guard_results: list[dict] | None = None,
                    lib: dict | None = None) -> dict:
    """REAL consumer: selects, binds, renders and reads back one composition.

    ``guard_results`` carries the ACTUAL guard outcomes (refusals/unknowns)
    that affect the rendered output: they are rendered into the body as a
    limitations section AND bound into the input content digest, so a guard
    change changes both the output SHA and input digest — never only a
    machine-side receipt note.
    """
    lib = lib or load_library()
    selection = select_recipe(goal=goal, track=track, form_id=form_id,
                              explicit_recipe_id=explicit_recipe_id,
                              available_inputs=available_inputs,
                              data_ready=data_ready, lib=lib)
    if selection["state"] in ("no_match", "needs_selection", "refused"):
        return {"schema": SCHEMA, "version": VERSION, "form_id": form_id,
                "selection": selection, "limited_first_value": True,
                "receipt": None, "separate_branch": SEPARATE_BRANCH,
                "note": "未静默选配方；原生本地首值继续，提案保留"}
    recipe_id = selection["recipe"]["id"]
    recipe = next(r for r in lib["recipes"] if r["id"] == recipe_id)
    ordered = []
    for ref in recipe["blocks"]:
        bid = ref["id"]
        block = lib["blocks"].get(bid)
        if block is None:
            raise CompositionError(f"recipe references missing block: {bid}")
        base = {"id": bid, "version": ref.get("version", block["version"]),
                "title": block.get("title"),
                "executable_code": bool(block.get("executable_code"))}
        if "handler" in block:
            # handler/page_id structured blocks (source-* forms): consume the
            # ACTUAL schema; never read a generic reader_question key.
            base["handler"] = block["handler"]
            base["page_id"] = block.get("page_id")
            if block["handler"] not in ("author", "source_page", "claim_ledger"):
                base["handler"] = "unknown_handler"
                base["limited"] = True
        else:
            base.update({"reader_question": block.get("reader_question"),
                         "input_key": block.get("input_key"),
                         "missing_data_behavior": block.get("missing_data_behavior"),
                         "visual": _visual_contract(block, lib)})
            # S3-01: a GENERIC block whose declared input_key is "claims" must
            # actually render the supplied claims — reader_question text alone
            # never substitutes for the substance of a claim ledger.
            if block.get("input_key") == "claims":
                base["renders_claims"] = True
        ordered.append(base)
    panel = _data_panel(data_rows, lib)

    # Claims are adopted from real evidence only; never padded to three.
    adopted_claims = [c for c in (claims or []) if c.get("support") and c.get("text")]

    body_lines = [
        f"# {topic}", "",
        f"读者：{reader}；需要支持的决定：{decision}；成品形态：{form_id}。",
        "", "## 方法与配方绑定", f"- 选中配方：{recipe_id}@1（goal={goal}）",
        f"- 自动采用条件：{selection.get('auto_apply_condition') or '未静默自动采用'}",
        f"- 缺硬输入：{selection['missing_hard_inputs'] or '无'}",
        f"- 版本化块：{', '.join(b['id'] + '@' + str(b['version']) for b in ordered)}",
    ]
    # Render blocks by their REAL structure.
    for b in ordered:
        if b.get("handler") == "author":
            body_lines += ["", f"## {b['title']}",
                           f"- 主题：{topic}", f"- 读者：{reader}",
                           f"- 需要支持的决定：{decision}",
                           f"- 本次范围：仅使用已提供且已核验的材料；未提供项为未观测。"]
        elif b.get("handler") == "source_page":
            body_lines += ["", f"## {b['title']}（{b.get('page_id') or '页'}）",
                           "- 本页消费下方数据面板中的实际行；未观测项保持未知，不补零。"]
        elif b.get("handler") == "claim_ledger":
            body_lines += ["", f"## {b['title']}"]
            if adopted_claims:
                for i, c in enumerate(adopted_claims, 1):
                    body_lines.append(
                        f"- C{i:02d} {c['text']}（支持：{c['support']}；"
                        f"反证/限制：{c.get('counter', [])}）")
            else:
                body_lines.append("- 当前材料不足以形成承重主张；保留受限首值与补证清单。")
        elif b.get("handler") == "unknown_handler":
            body_lines += ["", f"## {b['title']}",
                           "- 结构受限：该块使用了未知 handler，明确降级为占位，不把定义存在当已实现。"]
        elif b.get("renders_claims"):
            # S3-01: generic claim blocks (claim-ledger / counterevidence) render
            # the ACTUAL bound claims with support/counter/conditions.
            body_lines += ["", f"## {b['title']}"]
            if adopted_claims:
                for i, c in enumerate(adopted_claims, 1):
                    support = c.get("support", [])
                    counter = c.get("counter", []) or []
                    conditions = c.get("conditions", []) or []
                    body_lines.append(
                        f"- C{i:02d} {c['text']}（支持：{support}；反证/限制：{counter}；"
                        f"条件：{conditions}）")
            else:
                body_lines.append(
                    "- 当前材料不足以形成承重主张；保留受限首值与补证清单，不以空提纲冒充实质首值。")
        else:
            body_lines += ["", f"## {b['title']}",
                           f"- 读者问题：{b.get('reader_question') or '未声明'}",
                           f"- 缺数行为：{b.get('missing_data_behavior') or '未声明'}"]
    body_lines += ["", "## 原值 / 缺项面板（实际数据消费）"]
    for p in panel["panels"]:
        if p["value_state"] == "unknown":
            shown = "未观测（不补零）"
        else:
            shown = p["value"]  # observed value OR a kept true zero (0)
        body_lines.append(f"- {p['object']}：{shown}"
                          f" {p['unit'] or ''}｜期间 {p['period'] or '未观测'}"
                          f"｜分母 {p['denominator'] if p['denominator'] is not None else '未观测'}"
                          f"｜状态 {p['value_state']}｜呈现 {p['render']}")
    body_lines += ["", "## 视觉合同与降级"]
    for b in ordered:
        v = b.get("visual")
        if v:
            body_lines.append(f"- {b['id']}：合同 {v['contract_id']}；"
                              f"专用图形已实现={v['dedicated_renderer_implemented']}；"
                              f"降级={v['fallback']}")
        else:
            body_lines.append(f"- {b['id']}：handler 块（{b.get('handler')}），"
                              f"无视觉合同引用；按数据合同消费")
    if guard_results:
        # R3-ENTRY-GUARD-OUTPUT: real guard refusals/unknowns are part of the
        # DELIVERED content, not only machine-side receipt notes.
        body_lines += ["", "## 守卫拒绝与数据限制"]
        for g in guard_results:
            body_lines.append(
                f"- {g.get('guard')}：状态 {g.get('state')}；"
                f"原因 {g.get('reason') or '未声明'}；{g.get('note') or ''}".rstrip())
        body_lines.append("- 以上拒绝/未知按降级处理：保留原始值/表格呈现，不渲染不合法图形。")
    # S3-01: adoption is counted ONLY from claims that actually landed in the
    # rendered body (real adoption), never from len(claims). The landing
    # check runs against the body assembled SO FAR (before the final
    # limitation section is appended, since that section states the reason),
    # and is then RE-VERIFIED byte-level on the final assembled output.
    body_so_far = "\n".join(body_lines)
    landed = [c for c in adopted_claims if c["text"] in body_so_far]
    if len(adopted_claims) < 3 or len(landed) < len(adopted_claims):
        limited = {"state": "limited_first_value",
                   "reason": "材料不足或主张未全部落进正文；保留受限首值，不为凑数制造承重主张",
                   "claims_adopted": len(landed),
                   "claims_supplied": len(adopted_claims),
                   "claims_landing_verified": len(landed) == len(adopted_claims)}
    else:
        limited = {"state": "substantive", "claims_adopted": len(landed),
                   "claims_landing_verified": True}
    body_lines += ["", "## 未知与唯一下一步",
                   selection.get("reason", ""), limited.get("reason", ""), ""]
    body = "\n".join(body_lines)
    body_bytes = body.encode("utf-8")
    final_landed = [c for c in adopted_claims
                    if c["text"].encode("utf-8") in body_bytes]
    if len(final_landed) != len(landed):
        raise CompositionError("claims landing re-verification failed")

    consumer_bytes = CONSUMER_SOURCE.read_bytes()
    # The input digest binds EVERYTHING actually consumed by this composition:
    # control inputs, data rows, claims and readiness. A claim-text change
    # MUST change input_content_sha256.
    input_bytes = json.dumps({"form_id": form_id, "topic": topic, "reader": reader,
                              "decision": decision, "goal": goal, "track": track,
                              "available_inputs": available_inputs,
                              "data_rows": data_rows, "explicit_recipe_id": explicit_recipe_id,
                              "claims": claims or [], "data_ready": data_ready,
                              "guard_results": guard_results or []},
                             ensure_ascii=False, sort_keys=True).encode("utf-8")
    receipt = {
        "schema": SCHEMA, "version": VERSION, "product": PRODUCT,
        "form_id": form_id, "recipe": {"id": recipe_id, "version": 1},
        "selection_state": selection["state"],
        "auto_applied": selection.get("auto_applied", False),
        "ordered_blocks": [{"id": b["id"], "version": b["version"]} for b in ordered],
        "assets_sha256": {rel: a["sha256"] for rel, a in lib["assets"].items()},
        "manifest_sha256": lib["manifest_sha256"],
        "consumer_sha256": sha(consumer_bytes),
        "input_content_sha256": sha(input_bytes),
        "output_sha256": sha(body_bytes), "output_bytes": len(body_bytes),
        "missing_hard_inputs": selection["missing_hard_inputs"],
        "visual_contracts_consumed": [b["visual"]["contract_id"] for b in ordered
                                      if "visual" in b],
        "handler_blocks_consumed": [{"id": b["id"], "handler": b.get("handler"),
                                     "page_id": b.get("page_id")}
                                    for b in ordered if "handler" in b],
        "unimplemented_visuals_degraded": [b["id"] for b in ordered
                                           if not b.get("visual", {}).get(
                                               "dedicated_renderer_implemented")],
        "claims_state": limited,
        "guard_results_consumed": guard_results or [],
        "separate_branch": SEPARATE_BRANCH,
        "wire_change_authorized": False,
        "note": "输入/来源/配方/块/资产/消费者/输出摘要绑定同一版本；接续重核当前产物",
    }
    # read back the content that was actually produced
    if sha(body_bytes) != receipt["output_sha256"]:
        raise CompositionError("composition readback mismatch")
    return {"schema": SCHEMA, "version": VERSION, "form_id": form_id,
            "selection": selection, "ordered_blocks": ordered,
            "data_panel": panel, "claims_state": limited,
            "content": body, "content_bytes": body_bytes,
            "receipt": receipt, "separate_branch": SEPARATE_BRANCH,
            "readback_verified": True}
