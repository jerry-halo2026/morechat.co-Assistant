#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Portable project continuity card for long-manuscript-expert 2026.11.5 (rev 2).

Standard library only. Fixes the independently reproduced boundaries:

* save NEVER overwrites an existing author file: exclusive creation, and for
  an existing card it writes a NEW versioned file only after a matching
  expected preimage is supplied, then reads back the complete bytes.
* restore is not just a schema/version check: every referenced path is first
  confined to the CALLER-SELECTED project (absolute/parent-traversal/symlink
  escapes refused before any read; the card's self-reported root is never an
  authority), then the current draft and protected originals/hand edits are
  reopened and compared by full-byte digest. An unbound or missing current
  draft yields unknown/unbound, never verified.
* apply_event is an explicit, versioned transition consumer (continue /
  expression / evidence / user_explicit / rejection) with old-record digest,
  allowed fields, revision deltas, author basis and proposal lineage.
  Scoped revision validation itself lives in scoped_writer.py and is consumed
  by the real revision entry point in product_entry.py.

This module does not depend on cloud/local memory or backend state.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

VERSION = "2026.11.5"
# Bounded read-only compatibility: a legal old 2026.11.0200 card of the same
# schema family may be RESTORED read-only (original bytes/version/operation
# ids preserved on disk; never migrated or rewritten in place). Any other
# version keeps being rejected. New cards/receipts/summaries are new-version.
LEGACY_CARD_VERSION = "2026.11.0200"
SCHEMA = "paper.project-card.v2"
LEGACY_SCHEMAS = {"paper.project-card.v1"}


class CardError(ValueError):
    pass


class CardOverwriteRefused(CardError):
    pass


class CardPreimageChanged(CardError):
    pass


class CardSourceChanged(CardError):
    """Raised INSIDE the real card file-creation/write boundary when the one
    frozen source/asset closure no longer matches current bytes. Carries the
    changed/missing members so the caller can return a bounded partial without
    writing a card to changed sources."""

    def __init__(self, changed: list[str]):
        self.changed = list(changed)
        super().__init__("frozen closure changed at card write boundary: "
                         + ", ".join(self.changed))


def _verify_closure_at_write(closure: dict[str, str]) -> list[str]:
    """Re-read EVERY frozen closure member NOW, at the actual card write
    boundary. This is a READ-ONLY byte check against the SAME set the caller
    bound at composition time; it never recaptures a new baseline, never
    substitutes the selected digest, and grants no write authority.

    Returns changed/missing member descriptors (empty list == intact)."""
    if not closure:
        return []
    changed: list[str] = []
    for path_key, expected in sorted(closure.items()):
        if not isinstance(path_key, str) or not path_key or not isinstance(expected, str):
            changed.append(f"malformed:{path_key!r}")
            continue
        try:
            data = Path(path_key).read_bytes()
        except OSError:
            changed.append(f"missing:{path_key}")
            continue
        if _sha(data) != expected:
            changed.append(f"changed:{path_key}")
    return changed


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def create_card(*, topic: str, reader: str, decision: str, scope: dict,
                input_declaration: dict | None = None) -> dict:
    """Input classification comes from the caller's EXPLICIT declaration only.

    Unspecified input defaults to `unknown`: a real user's material is never
    labelled synthetic and synthetic harness material is never labelled real.
    `human_adoption_claimed` is always false here — adoption is a human fact
    that code cannot infer from user_supplied or synthetic flags.
    """
    allowed = ("kind", "is_synthetic", "human_adoption_claimed", "note",
               "source_records")
    if input_declaration is None:
        decl = {"kind": "unknown", "is_synthetic": None,
                "human_adoption_claimed": False,
                "note": "输入真实/合成未声明时默认 unknown；不把真人材料写成合成，也不把合成材料写成真人"}
    else:
        if not isinstance(input_declaration, dict):
            raise ValueError("input_declaration must be an object")
        unknown_keys = sorted(set(input_declaration) - set(allowed))
        if unknown_keys:
            raise ValueError(f"input_declaration refuses unknown keys: {unknown_keys}")
        kind = input_declaration.get("kind")
        if kind not in ("fixed_synthetic", "user_supplied", "unknown", "mixed"):
            raise ValueError(f"input_declaration kind unsupported: {kind!r}")
        decl = {"kind": kind,
                "is_synthetic": input_declaration.get("is_synthetic"),
                "human_adoption_claimed": False,
                "note": input_declaration.get(
                    "note", "声明仅来自调用者；human_adoption_claimed 恒为 false，代码不推断真人采用")}
        if "source_records" in input_declaration:
            decl["source_records"] = input_declaration["source_records"]
    return {
        "schema": SCHEMA, "version": VERSION,
        "created_at": _now(), "updated_at": _now(),
        "topic": topic, "reader": reader, "decision": decision,
        "scope": scope,
        "input_declaration": decl,
        "revisions": {"intent_revision": 1, "evidence_revision": 1,
                      "composition_revision": 1, "draft_revision": 1},
        "form": None, "current_draft": None,
        "material_coverage": {"actually_read": [], "valid_evidence": [],
                              "adopted_into_output": [], "unread": [], "unreadable": []},
        "claims": [], "deliverables": [], "write_receipts": [],
        "proposals": {"pending": [], "adopted": [], "rejected": [],
                      "note": "继续不采纳提案；表达换形态不采纳提案；旧提案保留原值与来源"},
        "protected": {"originals": [], "hand_edits": [], "out_of_scope_sync_pending": []},
        "failures_or_unknown": [], "next_step": None, "stop_conditions": [],
        "events": [],
        # The 18-recipe adopted T03 branch is a SEPARATE legacy branch; it is
        # never silently merged into this card or claimed as migrated.
        "legacy_branches": {
            "t03_18_recipe_adopted": {
                "state": "separate_branch_not_migrated", "operations_in_this_card": 0,
                "note": "独立作者采纳分支，本卡不自动迁移、不冒称其验收结果"},
        },
    }


def bind_material(card: dict, *, path: str, data: bytes, category: str) -> dict:
    row = {"path": path, "bytes": len(data), "sha256": _sha(data)}
    layers = card["material_coverage"]
    key = {"read": "actually_read", "evidence": "valid_evidence",
           "adopted": "adopted_into_output", "unread": "unread",
           "unreadable": "unreadable"}.get(category)
    if key is None:
        raise ValueError(f"unknown coverage category: {category}")
    layers[key].append(row)
    card["updated_at"] = _now()
    return row


def bump(card: dict, which: str, *, reason: str, event: dict | None = None) -> dict:
    """Revision counters are changed ONLY through validated events (or an
    explicit, recorded direct bump for mechanical draft versions)."""
    if which not in ("intent_revision", "evidence_revision", "composition_revision", "draft_revision"):
        raise ValueError(f"unknown revision: {which}")
    card["revisions"][which] += 1
    card.setdefault("revision_log", []).append(
        {"revision": which, "reason": reason, "at": _now(),
         "value": card["revisions"][which], "event": event})
    card["updated_at"] = _now()
    return card["revisions"]


def set_form(card: dict, form_id: str, *, reason: str) -> dict:
    """Pure expression change: composition only, never intent/evidence."""
    old = card.get("form")
    before = dict(card["revisions"])
    card["form"] = form_id
    card["events"].append({"type": "expression", "at": _now(),
                           "from": old, "to": form_id,
                           "allowed_fields": ["form"], "reason": reason})
    bump(card, "composition_revision", reason=reason,
         event={"type": "expression", "field": "form"})
    return {"previous": old, "current": form_id,
            "intent_revision_unchanged": card["revisions"]["intent_revision"] == before["intent_revision"],
            "evidence_revision_unchanged": card["revisions"]["evidence_revision"] == before["evidence_revision"]}


def add_claim(card: dict, *, text: str, support: list, counter: list,
              conditions: list, section: str) -> dict:
    claim = {"id": f"C{len(card['claims']) + 1:02d}", "text": text,
             "support": support, "counterevidence_or_limits": counter,
             "conditions": conditions, "section": section, "kind": "load_bearing"}
    card["claims"].append(claim)
    card["updated_at"] = _now()
    return claim


def add_deliverable(card: dict, *, path: str, kind: str, data: bytes,
                    readback: bool = False) -> dict:
    row = {"path": path, "kind": kind, "bytes": len(data), "sha256": _sha(data),
           "readback_verified": readback, "editable": kind in ("editable_draft", "data_table"),
           "note": "文件存在不等于宿主显示/目视通过"}
    card["deliverables"].append(row)
    if kind == "editable_draft":
        card["current_draft"] = path
    card["updated_at"] = _now()
    return row


def add_receipt(card: dict, receipt: dict) -> dict:
    row = {"operation_id": receipt["operation_id"], "state": receipt["state"],
           "path": receipt.get("path"), "sha256": receipt.get("sha256"),
           "before_write_check_count": receipt.get("before_write_check_count")}
    card["write_receipts"].append(row)
    card["updated_at"] = _now()
    return row


def note_unknown(card: dict, *, operation_id: str, reason: str) -> dict:
    row = {"operation_id": operation_id, "state": "unknown", "reason": reason,
           "at": _now(), "new_id_permitted": False, "replay_permitted": False}
    card["failures_or_unknown"].append(row)
    card["updated_at"] = _now()
    return row


def protect(card: dict, *, kind: str, path: str, data: bytes) -> dict:
    row = {"path": path, "bytes": len(data), "sha256": _sha(data)}
    card["protected"][kind].append(row)
    card["updated_at"] = _now()
    return row


# ---- explicit, versioned transition consumer -------------------------------
EVENT_RULES = {
    "continue":    {"allowed_fields": [], "revisions": [],
                    "note": "继续只恢复未完成工作，不采纳提案、不递增修订"},
    "expression":  {"allowed_fields": ["form", "page_plan", "visual", "stylesheet"],
                    "revisions": ["composition_revision"],
                    "note": "表达换形态；不采纳提案、不改意图/证据"},
    "evidence":    {"allowed_fields": ["material_coverage", "claims", "deliverables",
                                        "write_receipts", "current_draft"],
                    "revisions": ["evidence_revision", "draft_revision"],
                    "note": "证据变更；不隐式采纳任何提案"},
    "user_explicit": {"allowed_fields": ["decision", "scope", "reader", "stop_conditions"],
                      "revisions": ["intent_revision"],
                      "note": "用户明示变更；提案采纳须绑定实际 pending 提案与精确摘要"},
    "rejection":   {"allowed_fields": ["proposals"], "revisions": [],
                    "note": "拒绝保留原提案与来源"},
}


def _proposal_digest(proposal: dict) -> str:
    return _sha(json.dumps(proposal, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":")).encode("utf-8"))


def apply_event(card: dict, event: dict) -> dict:
    """Validate the COMPLETE transition FIRST, then commit atomically.

    Validation (all before any mutation):
      * event type and its rule shape are complete (a missing rule key is a
        validation error, never a mid-mutation KeyError);
      * changes are an object within the rule's allowed fields;
      * previous_record_sha256 matches the CURRENT card digest;
      * user_explicit: an author basis is required. A proposal ADOPTION
        additionally requires a proposal_id that EXISTS in pending AND an
        adopted_proposal_digest equal to that actual proposal's canonical
        digest; a non-empty string is never authorization. The proposal must
        ALSO declare the exact value it proposes (field_path + value, or a
        proposed_changes map): every adopted field must equal the declared
        value — a correct digest never authorizes adopting a DIFFERENT value
        (S3-02). A direct new instruction without a proposal_id is a
        separate, explicitly labelled direct_instruction path.

    Only after every check passes is a DEEP COPY mutated and committed, so a
    failed transition leaves the card byte-identical.
    """
    etype = event.get("type")
    if etype not in EVENT_RULES:
        raise CardError(f"unknown event type: {etype}")
    rule = EVENT_RULES[etype]
    for rule_key in ("allowed_fields", "revisions", "note"):
        if rule_key not in rule:
            raise CardError(f"event rule incomplete for {etype}: missing {rule_key}")
    changes = event.get("changes", {})
    if not isinstance(changes, dict):
        raise CardError("changes must be an object")
    unexpected = sorted(set(changes) - set(rule["allowed_fields"]))
    if unexpected:
        raise CardError(f"event {etype} refuses fields {unexpected}")
    expected_prev = event.get("previous_record_sha256")
    if not expected_prev:
        raise CardError("previous_record_sha256 required")
    actual_prev = _sha(json.dumps(card, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    if expected_prev != actual_prev:
        raise CardPreimageChanged("previous record digest mismatch; refuse stale transition")

    adoption = None
    if etype == "user_explicit":
        if not event.get("author_basis") or not isinstance(event.get("author_basis"), str):
            raise CardError("user_explicit requires an explicit author basis")
        pid = event.get("proposal_id")
        if pid is not None:
            pending = [p for p in card["proposals"]["pending"] if p.get("id") == pid]
            if not pending:
                raise CardError(
                    "proposal adoption requires an EXISTING pending proposal id; "
                    "a non-empty digest or invented id is not authorization")
            proposal = pending[0]
            expected_digest = event.get("adopted_proposal_digest")
            if not expected_digest or expected_digest != _proposal_digest(proposal):
                raise CardError(
                    "adopted_proposal_digest must equal the actual pending proposal's "
                    "canonical digest; a non-empty string is not authorization")
            allowed_change_keys = set(changes)
            proposal_allowed = set(proposal.get("allowed_fields", []))
            if allowed_change_keys and not allowed_change_keys <= proposal_allowed:
                raise CardError(
                    f"adoption changes fields outside the proposal's allowed fields: "
                    f"{sorted(allowed_change_keys - proposal_allowed)}")
            # S3-02: the proposal must declare the EXACT value it proposes
            # (field_path + value, or a proposed_changes map). Every adopted
            # field must equal the declared value: a correct digest never
            # authorizes adopting a different value under this proposal.
            declared = None
            if isinstance(proposal.get("proposed_changes"), dict):
                declared = dict(proposal["proposed_changes"])
            elif isinstance(proposal.get("field_path"), str):
                declared = {proposal["field_path"]: proposal.get("value")}
            if declared is None:
                raise CardError(
                    "proposal declares no exact values (field_path+value or "
                    "proposed_changes); adopting caller-supplied values refused")
            for k, v in changes.items():
                if k not in declared:
                    raise CardError(
                        f"adoption changes a field the proposal does not declare: {k}")
                if declared[k] != v:
                    raise CardError(
                        f"adopted value for {k} differs from the proposal's declared "
                        f"value; a different value requires a NEW proposal or the "
                        f"direct_instruction path, not this digest")
            adoption = {"proposal_id": pid, "proposal_digest": expected_digest,
                        "author_basis": event["author_basis"],
                        "adopted_values": dict(changes)}

    # ---- full validation passed: commit on a deep copy, then swap ----------
    import copy as _copy
    working = _copy.deepcopy(card)
    for key, value in changes.items():
        if key in ("form", "decision", "scope", "reader", "stop_conditions",
                   "page_plan", "visual", "stylesheet", "current_draft"):
            working[key] = value
        elif key in ("material_coverage", "claims", "deliverables",
                     "write_receipts", "proposals"):
            working[key] = value
        else:
            raise CardError(f"field not writable by event: {key}")
    if etype == "rejection":
        pid = event.get("proposal_id")
        pending = working["proposals"]["pending"]
        moved = [p for p in pending if p.get("id") == pid]
        working["proposals"]["pending"] = [p for p in pending if p.get("id") != pid]
        working["proposals"]["rejected"] += moved
    if etype == "user_explicit" and adoption is not None:
        pid = adoption["proposal_id"]
        adopted = [_copy.deepcopy(p) for p in card["proposals"]["pending"]
                   if p.get("id") == pid]
        for p in adopted:
            p["adopted_with_basis"] = adoption["author_basis"]
            p["adopted_proposal_digest"] = adoption["proposal_digest"]
            p["superseded_lineage_retained"] = True
        working["proposals"]["adopted"] += adopted
        working["proposals"]["note"] = "采纳绑定实际 pending 提案与精确摘要；原提案与来源保留"
    before = dict(card["revisions"])
    for rev in rule["revisions"]:
        working["revisions"][rev] += 1
    # S3-02: proposal adoption and a direct new instruction are recorded as
    # SEPARATE paths; a direct instruction is never mislabelled as adoption.
    instruction_path = None
    if etype == "user_explicit":
        instruction_path = ("proposal_adoption" if adoption is not None
                            else "direct_instruction")
    working["events"].append({"type": etype, "at": _now(),
                              "allowed_fields": sorted(changes),
                              "previous_record_sha256": expected_prev,
                              "revision_delta": {r: working["revisions"][r] - before[r]
                                                 for r in working["revisions"]},
                              "author_basis": event.get("author_basis"),
                              "adoption": adoption,
                              "instruction_path": instruction_path,
                              "note": rule["note"]})
    working["updated_at"] = _now()
    # commit: replace the caller's card contents with the validated copy
    card.clear()
    card.update(working)
    return {"type": etype, "applied": True,
            "revision_delta": {r: card["revisions"][r] - before[r] for r in card["revisions"]},
            "adoption": adoption, "instruction_path": instruction_path,
            "continue_did_not_adopt": etype != "user_explicit" or adoption is None,
            "old_proposals_retained": True,
            "note": "先完整验证再原子提交；失败时卡保持原状"}


# ---- exclusive, versioned save ---------------------------------------------
def _next_version_path(path: Path) -> Path:
    stem, suffix = path.stem, path.suffix
    m = re.search(r"\.v(\d+)$", stem)
    n = int(m.group(1)) + 1 if m else 2
    base = re.sub(r"\.v\d+$", "", stem)
    candidate = path.parent / f"{base}.v{n}{suffix}"
    while candidate.exists():
        n += 1
        candidate = path.parent / f"{base}.v{n}{suffix}"
    return candidate


def save(card: dict, path: str | Path, *, expected_sha256: str | None = None,
         closure: dict[str, str] | None = None) -> dict:
    """Exclusive creation with full-byte readback. NEVER overwrites an author file.

    If the target already exists, an expected preimage MUST be supplied and
    match; the new bytes are then published under a NEW versioned filename.

    enterprise-r4 A: when ``closure`` is supplied, the SAME frozen
    source/asset set is re-verified HERE, inside the real file-creation/write
    boundary, immediately before the exclusive open. A change after an outer
    pre-check is therefore still refused with ZERO card writes; the closure is
    never recaptured from current disk and the selected digest is never
    replaced. Callers without a closure keep the original behaviour.
    """
    p = Path(path)
    # Verify INSIDE the write boundary, before any directory/file creation, so
    # a drift detected at the pc.save entry cannot produce a card at all.
    if closure is not None:
        drift = _verify_closure_at_write(closure)
        if drift:
            raise CardSourceChanged(drift)
    p.parent.mkdir(parents=True, exist_ok=True)
    original_path = p
    if p.exists():
        if expected_sha256 is None:
            raise CardOverwriteRefused(
                "existing card file would be overwritten; supply expected_sha256 for a new version")
        if _sha(p.read_bytes()) != expected_sha256:
            raise CardPreimageChanged("card preimage changed; refuse to overwrite")
        p = _next_version_path(p)
    encoded = json.dumps(card, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
    text = encoded + b"\n"
    # Re-verify once more immediately before the exclusive create: the gap
    # between the outer pre-check and this line is exactly the window the r4
    # counter-example exploits.
    if closure is not None:
        drift = _verify_closure_at_write(closure)
        if drift:
            raise CardSourceChanged(drift)
    fd = os.open(str(p), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
    except BaseException:
        try:
            p.unlink()
        except OSError:
            pass
        raise
    rb = p.read_bytes()
    if rb != text:
        raise CardError("card readback mismatch")
    return {"path": str(p).replace("\\", "/"), "bytes": len(text), "sha256": _sha(text),
            "exclusive_create": True, "overwrote_existing_file": False,
            "versioned_new_file": str(p) != str(original_path),
            "readback_verified": True}


def _confined(base: Path, rel: str) -> Path:
    """Resolve a card-referenced path ONLY inside the caller-selected project.

    A card is untrusted metadata: its self-reported paths never grant read
    authority. Absolute references, parent traversal (`..`), drive-relative
    forms and symlink escapes are refused BEFORE any file byte is read. The
    card root is never an authority; only the caller-supplied base is.
    """
    if not isinstance(rel, str) or not rel:
        raise CardError(f"card reference is not a non-empty relative path: {rel!r}")
    rel_norm = rel.replace("\\", "/")
    if rel_norm.startswith("/") or re.match(r"^[A-Za-z]:", rel_norm):
        raise CardError(f"card reference is absolute; refuse outside selected project: {rel}")
    parts = [p for p in rel_norm.split("/") if p not in ("", ".")]
    if ".." in parts:
        raise CardError(f"card reference traverses outside selected project: {rel}")
    if not parts:
        raise CardError(f"card reference resolves to the project root itself: {rel}")
    candidate = base.joinpath(*parts)
    resolved_base = base.resolve()
    resolved = candidate.resolve()
    try:
        inside = resolved == resolved_base or resolved.is_relative_to(resolved_base)
    except (OSError, ValueError) as exc:
        raise CardError(f"card reference unresolvable inside selected project: {rel}") from exc
    if not inside:
        raise CardError(f"card reference escapes the selected project: {rel}")
    # Reject symlink escapes inside the chain (final component may be a real file).
    cur = candidate.parent
    while True:
        if cur.is_symlink():
            raise CardError(f"symlink parent in card reference chain: {cur}")
        if cur == resolved_base or cur.parent == cur:
            break
        cur = cur.parent
    return candidate


def verify_current_files(card: dict, base_dir: str | Path) -> dict:
    """Reopen CURRENT product bytes; a schema check alone is NOT verification.

    Every referenced path is first confined to the caller-selected project
    (absolute/parent-traversal references are refused before any read). A
    current draft must be digest-bound and actually read back; zero checks or
    an unbound/missing current draft yields unknown/unbound, never verified.
    """
    base = Path(base_dir)
    checks = []
    refusals = []

    def _check(kind: str, row: dict) -> None:
        try:
            f = _confined(base, row["path"])
        except CardError as exc:
            refusals.append({"path": row.get("path"), "kind": kind,
                             "refused": str(exc)})
            return
        if not f.is_file():
            checks.append({"path": row["path"], "kind": kind, "state": "missing"})
            return
        data = f.read_bytes()
        checks.append({"path": row["path"], "kind": kind,
                       "state": "verified" if _sha(data) == row["sha256"] else "changed",
                       "sha256": _sha(data), "bytes": len(data)})

    for kind in ("originals", "hand_edits"):
        for row in card["protected"].get(kind, []):
            _check(kind, row)
    for d in card["deliverables"]:
        _check("deliverable", d)

    # The CURRENT DRAFT must be digest-bound and really read back.
    current_draft = card.get("current_draft")
    draft_binding = None
    if current_draft is None:
        draft_state = "unbound"
    else:
        binding = [d for d in card["deliverables"]
                   if d.get("path") == current_draft and "sha256" in d]
        if not binding:
            draft_state = "unbound"
        else:
            draft_binding = binding[0]
            entry = [c for c in checks if c["path"] == current_draft]
            if not entry or entry[0]["state"] == "missing":
                draft_state = "missing"
            elif entry[0]["state"] == "verified":
                draft_state = "verified"
            else:
                draft_state = "changed"

    bad = [c for c in checks if c["state"] != "verified"]
    verified = (not bad and not refusals and draft_state == "verified"
                and len(checks) >= 1 and draft_binding is not None)
    return {
        "checked": len(checks), "verified_count": len(checks) - len(bad),
        "changed_or_missing": bad, "refused_references": refusals,
        "current_draft": current_draft, "current_draft_state": draft_state,
        "current_product_verified": verified,
        "byte_integrity_scope": "caller-selected project only; card metadata grants no authority",
        "note": "当前稿/手改/原件摘要实际读回；空检查或未绑定当前稿为 unknown/unbound，不冒充已核实",
    }


def restore(path: str | Path, *, base_dir: str | Path | None = None,
            verify_current_files_flag: bool = True) -> dict:
    """Resume ONLY from the portable project file, with real byte verification."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"no project card to resume from: {p}")
    card = json.loads(p.read_text(encoding="utf-8"))
    card_version = card.get("version")
    legacy_read_only = card_version == LEGACY_CARD_VERSION
    if card_version not in (VERSION, LEGACY_CARD_VERSION):
        raise CardError("project card version mismatch; refuse silent migration")
    if card.get("schema") not in ({SCHEMA} | LEGACY_SCHEMAS):
        raise CardError("project card schema unsupported; keep original and report")
    verification = None
    if verify_current_files_flag:
        verification = verify_current_files(card, base_dir or p.parent)
    card["_restore_verification"] = {
        "schema_checked": True, "version_checked": True,
        "legacy_version_read_only": legacy_read_only,
        "legacy_version_preserved": LEGACY_CARD_VERSION if legacy_read_only else None,
        "current_bytes_checked": verification is not None,
        "current_product_verified": verification["current_product_verified"] if verification else None,
        "current_draft_state": verification["current_draft_state"] if verification else None,
        "changed_or_missing": verification["changed_or_missing"] if verification else [],
        "refused_references": verification["refused_references"] if verification else [],
        "claim_full_semantic_sync": False,
        "note": "schema/version 不证明当前产物已核实；逐字节回读与越界引用拒绝见本字段；"
                "旧 0200 卡只读恢复：原字节/原版本/原操作号保留，不原地迁移或重写",
    }
    return card


def summary(card: dict) -> dict:
    return {
        "schema": "paper.project-card.summary.v2", "version": VERSION,
        "topic": card["topic"], "reader": card["reader"], "decision": card["decision"],
        "form": card["form"], "current_draft": card["current_draft"],
        "revisions": card["revisions"],
        "claims": [c["id"] for c in card["claims"]],
        "deliverables": [d["path"] for d in card["deliverables"]],
        "write_receipts": [r["operation_id"] for r in card["write_receipts"]],
        "coverage_counts": {k: len(v) for k, v in card["material_coverage"].items()},
        "protected_counts": {k: len(v) for k, v in card["protected"].items() if isinstance(v, list)},
        "unknown": [u["operation_id"] for u in card["failures_or_unknown"]],
        "next_step": card["next_step"],
        "events": [e["type"] for e in card.get("events", [])],
        "legacy_branches": card.get("legacy_branches", {}),
        "current_product_verified": (card.get("_restore_verification") or {}).get("current_product_verified"),
        "resumed_from": "portable_project_file_only",
        "memory_used": False, "backend_state_used": False,
    }
