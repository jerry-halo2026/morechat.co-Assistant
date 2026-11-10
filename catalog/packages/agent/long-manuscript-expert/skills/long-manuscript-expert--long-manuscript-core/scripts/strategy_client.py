#!/usr/bin/env python3
"""Deterministic strategy client for long-manuscript-expert (paper.* wire).

This module is the expert-side client for the frozen strategy contract
``strategy-v1.json`` and the four JSON Schemas (request / response / feedback /
catalog). It is standard-library Python only (no third-party dependencies) and
is meant to be shared verbatim with the backend (Codex) for local integration:
the same ``prepare_request`` / ``validate_response`` / ``call_dev`` entry points
are used both offline (no network) and against the explicit development endpoint.

Hard rules enforced here (see contracts/ and docs/ in the source project):
  * Canonical JSON: UTF-8, recursively sorted keys, no whitespace, non-ASCII
    left unescaped, ``,``/``:`` separators, integers only on the request,
    duplicate keys rejected, non-finite numbers rejected at every depth
    (including ``1e999`` which a parser turns into +inf).
  * Request digest = SHA-256 of the exact canonical request bytes.
  * Brief digest = SHA-256( 32 raw salt bytes || canonical local brief ).
  * Fixed endpoints only: ``http://127.0.0.1:8768`` (explicit dev) or the
    separately enabled HTTPS production mount. No arbitrary URL, no redirect
    following, no TLS downgrade, no other expert service.
  * Timeout 3s, at most ONE identical-body retry for the same request_id -
    and only for unknown/timeout outcomes; HTTP rejections and type-
    classifiable DNS/TLS/connection failures are never retried (their
    catalog retry_policy is no_automatic_retry).
  * A ``selected`` response MUST carry a non-null strategy + plan with non-empty
    ``query_axes`` and ``source_classes`` (ERRATA-02); schemas alone accept the
    shape, semantic checks reject empties.
  * A cell ``evidence_version`` must never exceed the request ``evidence_revision``
    (ERRATA-01, ``future_evidence_version``).
  * Time window: issued<expires, duration<=600s, |issued-now|<=30s receive skew,
    still unexpired; monotonic local deadline = min(expires-received, 600).
  * The response NEVER grants tools/materials/permission to the expert.

RESERVED EXTENSION POINT — research segment (Owner addition 2026-10-27):
  Adds a *segmented research-track bilateral strategy*. The segment is used ONLY
  for the research field, the research question, evidence-applicability
  conditions and strategy. It MUST NOT link to group QR codes, group joining,
  group capacity, or upstream/downstream spaces. The wire contract for this
  extension will be issued separately by Codex; this client does NOT invent any
  interface or wire field. The segment is stored ONLY in the local brief /
  local annotations and is never sent on ``paper.intent.v1`` (which is closed).
"""

from __future__ import annotations

import argparse
import copy
import errno
import hashlib
import json
import math
import os
import re
import socket
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Tuple

__all__ = [
    "Error", "StrategyClient", "ResearchSegment", "RESEARCH_SEGMENT_NOTE",
    "canonical", "digest", "strict_json", "compute_brief_digest",
    "validate_request", "validate_catalog", "validate_response",
    "validate_feedback", "prepare_request", "build_local_brief",
    "DEV_BASE_URL", "PLANNED_PRODUCTION_BASE_URL",
]

# --- Fixed endpoints (no other host is ever contacted) -----------------------
DEV_BASE_URL = "http://127.0.0.1:8768"
PLANNED_PRODUCTION_BASE_URL = "https://api2.u3w.com/working-paper"
PRODUCTION_BASE_URL = PLANNED_PRODUCTION_BASE_URL  # released paper-20261027-r2
DEV_WIRE_PATH = "/v1/strategies/resolve"
PRODUCT = "long-manuscript-expert"
VERSION = "2026.10.300"
REQUEST_SCHEMA = "paper.intent.v1"
RESPONSE_SCHEMA = "paper.strategy-decision.v1"
FEEDBACK_SCHEMA = "paper.feedback.v1"
CATALOG_SCHEMA = "paper.catalog.v1"
REQUEST_MAX_BYTES = 16384
CATALOG_MAX_BYTES = 65536
DEFAULT_TIMEOUT = 3.0
MAX_TOTAL_TIMEOUT = 6.0
LOCAL_PROCESSING_RESERVE = 0.05
READ_CHUNK_BYTES = 8192
MAX_SKEW_SECONDS = 30.0
MAX_DURATION_SECONDS = 600.0
SALT_BYTES = 32

SHORT_PATH_MODES = ("verify_only", "rewrite_only", "reorder_only", "local_only")

# Closed enums shared with the frozen schemas.
GOALS = ("industry_overview", "competitive_comparison", "decision_verification",
         "incremental_update", "unknown")
CONTEXTS = ("industry", "company", "topic", "other", "unknown")
CONSTRAINTS = ("specified", "partial", "unknown")
RELATIONS = ("aligned", "partial", "misaligned", "unknown")
EVIDENCE = ("primary", "complementary", "vendor_only", "mixed", "unknown")
APPLICABILITY = ("known", "partial", "unknown")
FRESHNESS = ("current", "stale", "unknown")
CONFLICTS = ("present", "absent", "unknown")
MODES = ("new_research", "update_research", "verify_only", "rewrite_only",
         "reorder_only", "local_only")
CAPABILITIES = ("web_search", "page_read", "file_read")
AXES = ("scope_boundary", "primary_data", "comparable_dimensions",
        "independent_outcomes", "counterevidence", "applicability_conditions",
        "latest_updates", "change_impact")
SOURCES = ("primary", "independent", "complementary", "vendor_disclosed")
CHECKS = ("subject_period", "denominator_metric", "independence", "counterevidence",
          "applicability", "source_freshness", "conflict_alignment",
          "author_protection", "claim_to_section", "alternative_explanation")
STOPS = ("budget_exhausted", "material_conflict_unresolved", "source_unavailable",
         "evidence_sufficient", "no_new_evidence")
ESSENTIAL_CHECKS = {"subject_period", "denominator_metric", "independence",
                    "counterevidence", "applicability", "source_freshness",
                    "conflict_alignment", "author_protection", "claim_to_section"}
ESSENTIAL_STOPS = set(STOPS)
REASON_CODES = ("goal_match", "unknown_preserved", "conflict_preserved",
                "native_short_path", "no_active_strategy", "capability_limited")
BUDGET_KEYS = ("max_queries", "max_reads", "max_claims", "max_rounds")
BUDGET_MAX = {"max_queries": 12, "max_reads": 20, "max_claims": 12, "max_rounds": 2}
USER_DERIVED = ("user_explicit", "derived", "unknown")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
KEBAB_ID = re.compile(r"^[a-z][a-z0-9-]{2,47}$")

RESEARCH_SEGMENT_NOTE = (
    "Reserved local-only extension point: segmented research-track bilateral "
    "strategy. Used ONLY for research field, research question, evidence "
    "applicability conditions and strategy. MUST NOT link to group QR codes, "
    "group joining, group capacity, or upstream/downstream spaces. The wire "
    "contract is issued separately by Codex; this client invents no interface "
    "and adds no field to paper.intent.v1."
)


class Error(Exception):
    """A deterministic validation / contract error with a stable code."""

    def __init__(self, code: str, status: int = 400):
        super().__init__(code)
        self.code = code
        self.status = status


def require(condition: bool, code: str, status: int = 400) -> None:
    if not condition:
        raise Error(code, status)


# --- Canonical JSON / digest ------------------------------------------------
def canonical(value: Any) -> bytes:
    """UTF-8, recursively sorted keys, no whitespace, non-ASCII unescaped.

    ``allow_nan=False`` rejects Infinity/NaN at dump time; integers are emitted
    as integers (request integers-only rule). Raises Error on non-serialisable
    values (e.g. invalid unicode or non-finite floats sneaking through)."""
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8", "strict")
    except (UnicodeError, ValueError, TypeError, RecursionError) as exc:
        raise Error("invalid_canonical_value") from exc


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def _reject_dup_keys(pairs):
    out: dict = {}
    for key, val in pairs:
        if key in out:
            raise Error("duplicate_json_key")
        out[key] = val
    return out


def _reject_constant(_token):
    # Catches literal Infinity / -Infinity / NaN. (1e999 becomes a float inf,
    # handled separately by _reject_nonfinite.)
    raise Error("non_finite_number")


def _reject_nonfinite(value: Any) -> None:
    """Reject any non-finite float at any depth (covers 1e999 -> +inf)."""
    if isinstance(value, bool):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise Error("non_finite_number")
        return
    if isinstance(value, dict):
        for child in value.values():
            _reject_nonfinite(child)
    elif isinstance(value, list):
        for child in value:
            _reject_nonfinite(child)


def strict_json(raw: bytes | str, maximum: int = REQUEST_MAX_BYTES) -> Any:
    """Parse JSON strictly: bounded size, no duplicate keys, no non-finite."""
    if isinstance(raw, str):
        try:
            data = raw.encode("utf-8", "strict")
        except UnicodeError as exc:
            raise Error("invalid_unicode") from exc
    elif isinstance(raw, (bytes, bytearray)):
        data = bytes(raw)
    else:
        raise Error("invalid_json")
    require(len(data) <= maximum, "body_too_large", 413)
    try:
        value = json.loads(
            data.decode("utf-8", "strict"),
            object_pairs_hook=_reject_dup_keys,
            parse_constant=_reject_constant,
        )
    except Error:
        raise
    except (UnicodeError, ValueError, TypeError, RecursionError) as exc:
        raise Error("invalid_json") from exc
    _reject_nonfinite(value)
    return value


# --- Low-level validators ---------------------------------------------------
def _is_int(value: Any) -> bool:
    return type(value) is int and not isinstance(value, bool)


def _int(value: Any, low: int, high: int, code: str = "invalid_request") -> None:
    require(_is_int(value) and low <= value <= high, code)


def _uuid(value: Any, code: str = "invalid_request") -> None:
    require(type(value) is str and UUID_RE.fullmatch(value) is not None, code)


def _enum(value: Any, allowed: Tuple[str, ...], code: str = "invalid_enum") -> None:
    require(type(value) is str and value in allowed, code)


def _object(value: Any, keys: Tuple[str, ...], code: str = "invalid_request") -> None:
    require(type(value) is dict and set(value) == set(keys), code)


def _cell(cell: dict, known: Tuple[str, ...], evidence_revision: int) -> None:
    """Validate a demand/supply cell and ERRATA-01 future-evidence check."""
    _object(cell, ("value", "origin", "status", "evidence_version"), "invalid_cell")
    value, origin, status = cell["value"], cell["origin"], cell["status"]
    ev = cell["evidence_version"]
    require(ev is None or (_is_int(ev) and 1 <= ev <= 1_000_000), "invalid_cell")
    # ERRATA-01: a cell version may never exceed the current evidence_revision.
    if ev is not None:
        require(ev <= evidence_revision, "future_evidence_version")
    if status == "known":
        require(value != "unknown", "invalid_cell")
        require(origin in ("user_explicit", "derived"), "invalid_cell")
        require(status == "known", "invalid_cell")
    elif status == "unknown":
        require(value == "unknown" and origin == "unknown" and ev is None, "invalid_cell")
    elif status == "conflict":
        require(value == "unknown", "invalid_cell")
        require(origin in USER_DERIVED, "invalid_cell")
    else:
        raise Error("invalid_cell")
    _enum(value, tuple(set(known) | {"unknown"}), "invalid_cell")


def _budget(obj: dict, code: str = "invalid_budget") -> None:
    _object(obj, BUDGET_KEYS, code)
    for key in BUDGET_KEYS:
        low = 1 if key in ("max_claims", "max_rounds") else 0
        _int(obj[key], low, BUDGET_MAX[key], code)


# --- Request validation -----------------------------------------------------
def validate_request(req: Any) -> None:
    _object(req, (
        "schema", "request_id", "consumer", "intent_revision", "evidence_revision",
        "brief_digest", "mode", "demand", "supply", "budget", "capabilities",
    ), "invalid_request")
    require(req["schema"] == REQUEST_SCHEMA, "invalid_schema")
    _uuid(req["request_id"])
    _object(req["consumer"], ("product", "version"), "invalid_consumer")
    require(req["consumer"]["product"] == PRODUCT, "invalid_consumer")
    require(req["consumer"]["version"] == VERSION, "invalid_consumer")
    _int(req["intent_revision"], 1, 1_000_000)
    _int(req["evidence_revision"], 1, 1_000_000)
    require(type(req["brief_digest"]) is str and HEX64.fullmatch(req["brief_digest"]) is not None,
            "invalid_digest")
    _enum(req["mode"], MODES)
    # demand
    _object(req["demand"], ("goal", "context", "constraints"), "invalid_demand")
    _cell(req["demand"]["goal"], GOALS, req["evidence_revision"])
    _cell(req["demand"]["context"], CONTEXTS, req["evidence_revision"])
    _cell(req["demand"]["constraints"], CONSTRAINTS, req["evidence_revision"])
    # supply
    _object(req["supply"], ("relation", "evidence", "applicability", "freshness", "conflict"),
            "invalid_supply")
    _cell(req["supply"]["relation"], RELATIONS, req["evidence_revision"])
    _cell(req["supply"]["evidence"], EVIDENCE, req["evidence_revision"])
    _cell(req["supply"]["applicability"], APPLICABILITY, req["evidence_revision"])
    _cell(req["supply"]["freshness"], FRESHNESS, req["evidence_revision"])
    _cell(req["supply"]["conflict"], CONFLICTS, req["evidence_revision"])
    # budget
    _budget(req["budget"])
    # capabilities
    caps = req["capabilities"]
    require(type(caps) is list and len(caps) <= 3
           and all(type(v) is str for v in caps), "invalid_capabilities")
    require(len(set(caps)) == len(caps) and all(v in CAPABILITIES for v in caps),
            "invalid_capabilities")


# --- Catalog validation (ERRATA-02 active_plan_empty) -----------------------
def validate_catalog(catalog: Any) -> dict:
    _object(catalog, ("schema", "templates"), "invalid_catalog")
    require(catalog["schema"] == CATALOG_SCHEMA, "invalid_catalog")
    templates = catalog["templates"]
    require(type(templates) is list and len(templates) <= 16, "invalid_catalog")
    seen = set()
    index = {}
    for item in templates:
        _object(item, ("id", "version", "goal", "active", "plan"), "invalid_template")
        require(type(item["id"]) is str and KEBAB_ID.fullmatch(item["id"]) is not None,
                "invalid_template")
        require(item["id"] not in seen, "duplicate_template")
        seen.add(item["id"])
        _int(item["version"], 1, 1_000_000, "invalid_template")
        _enum(item["goal"], GOALS, "invalid_template")
        require(type(item["active"]) is bool, "invalid_template")
        plan = item["plan"]
        _object(plan, ("query_axes", "source_classes", "checks", "stop_rules", "budget"),
                "invalid_plan")
        # arrays
        for field_name, allowed, mandatory in (
            ("query_axes", AXES, set()),
            ("source_classes", SOURCES, set()),
            ("checks", CHECKS, ESSENTIAL_CHECKS),
            ("stop_rules", STOPS, ESSENTIAL_STOPS),
        ):
            vals = plan[field_name]
            require(type(vals) is list and all(type(v) is str for v in vals), "invalid_plan")
            require(len(vals) <= len(allowed), "invalid_plan")
            require(len(set(vals)) == len(vals), "invalid_plan")
            require(all(v in allowed for v in vals), "invalid_plan")
            require(mandatory.issubset(vals), "invalid_plan")
        _budget(plan["budget"], "invalid_plan")
        # ERRATA-02: an ACTIVE template must have non-empty axes & sources.
        if item["active"]:
            require(len(plan["query_axes"]) >= 1, "active_plan_empty")
            require(len(plan["source_classes"]) >= 1, "active_plan_empty")
        index[item["id"]] = item
    return index


# --- Response validation -----------------------------------------------------
def validate_response(resp: Any, request: Optional[dict] = None,
                      catalog: Optional[dict] = None) -> None:
    if request is not None:
        validate_request(request)
    _object(resp, (
        "schema", "request_id", "intent_revision", "evidence_revision",
        "request_digest", "decision_id", "status", "catalog_revision",
        "strategy", "plan", "reason_codes", "issued_at", "expires_at",
    ), "invalid_response")
    require(resp["schema"] == RESPONSE_SCHEMA, "invalid_schema")
    _uuid(resp["request_id"])
    _int(resp["intent_revision"], 1, 1_000_000)
    _int(resp["evidence_revision"], 1, 1_000_000)
    require(type(resp["request_digest"]) is str and HEX64.fullmatch(resp["request_digest"]) is not None,
            "invalid_digest")
    _uuid(resp["decision_id"])
    _int(resp["catalog_revision"], 1, 2_147_483_647)
    _enum(resp["status"], ("selected", "skipped", "no_match"))
    require(type(resp["reason_codes"]) is list and len(resp["reason_codes"]) <= 6, "invalid_response")
    require(all(type(c) is str and c in REASON_CODES for c in resp["reason_codes"]),
            "invalid_response")
    # issued_at / expires_at are finite numbers (non-finite already rejected by
    # strict_json, but defensively assert here too).
    require(_is_finite_num(resp["issued_at"]), "non_finite_time")
    require(_is_finite_num(resp["expires_at"]), "non_finite_time")

    status = resp["status"]
    if status == "selected":
        _strategy(resp["strategy"])
        _plan(resp["plan"])
        # ERRATA-02: a selected plan must have non-empty axes & sources.
        require(len(resp["plan"]["query_axes"]) >= 1, "selected_plan_empty")
        require(len(resp["plan"]["source_classes"]) >= 1, "selected_plan_empty")
        # A supplied authoritative full catalog is always validated and indexed;
        # an absent ID, version mismatch or altered template digest must reject.
        if catalog is not None:
            index = validate_catalog(catalog)
            tpl = index.get(resp["strategy"]["id"])
            require(tpl is not None, "invalid_strategy")
            require(tpl["version"] == resp["strategy"]["version"], "invalid_strategy")
            require(digest(tpl) == resp["strategy"]["digest"],
                    "strategy_digest_mismatch")
    else:
        require(resp["strategy"] is None, "unexpected_strategy")
        require(resp["plan"] is None, "unexpected_plan")

    # Binding to the originating request (when supplied).
    if request is not None:
        require(resp["request_id"] == request["request_id"], "request_id_mismatch")
        require(resp["intent_revision"] == request["intent_revision"], "intent_revision_mismatch")
        require(resp["evidence_revision"] == request["evidence_revision"], "evidence_revision_mismatch")
        require(resp["request_digest"] == digest(request), "request_digest_mismatch")
        # Shared budget upper limit: response plan budget never exceeds request.
        if status == "selected":
            for key in BUDGET_KEYS:
                require(resp["plan"]["budget"][key] <= request["budget"][key],
                        "budget_exceeds_request")


def _is_finite_num(value: Any) -> bool:
    return (type(value) is int and not isinstance(value, bool)) or (
        type(value) is float and math.isfinite(value)
    )


def _strategy(strategy: Any) -> None:
    require(type(strategy) is dict, "invalid_strategy")
    _object(strategy, ("id", "version", "digest"), "invalid_strategy")
    require(type(strategy["id"]) is str and KEBAB_ID.fullmatch(strategy["id"]) is not None,
            "invalid_strategy")
    _int(strategy["version"], 1, 1_000_000, "invalid_strategy")
    require(type(strategy["digest"]) is str and HEX64.fullmatch(strategy["digest"]) is not None,
            "invalid_strategy")


def _plan(plan: Any) -> None:
    # NOTE: the frozen response schema sets maxItems but NO minItems on
    # query_axes / source_classes, so empty arrays pass JSON Schema. The
    # ERRATA-02 semantic check (selected_plan_empty) rejects empties for a
    # selected response; _plan itself mirrors the schema shape only.
    require(type(plan) is dict, "invalid_plan")
    _object(plan, ("query_axes", "source_classes", "checks", "stop_rules", "budget"),
            "invalid_plan")
    require(type(plan["query_axes"]) is list and len(plan["query_axes"]) <= 8, "invalid_plan")
    require(len(set(plan["query_axes"])) == len(plan["query_axes"]), "invalid_plan")
    require(all(v in AXES for v in plan["query_axes"]), "invalid_plan")
    require(type(plan["source_classes"]) is list and len(plan["source_classes"]) <= 4,
            "invalid_plan")
    require(len(set(plan["source_classes"])) == len(plan["source_classes"]), "invalid_plan")
    require(all(v in SOURCES for v in plan["source_classes"]), "invalid_plan")
    require(type(plan["checks"]) is list and 9 <= len(plan["checks"]) <= 10, "invalid_plan")
    require(ESSENTIAL_CHECKS.issubset(plan["checks"]) and all(v in CHECKS for v in plan["checks"]),
            "invalid_plan")
    require(type(plan["stop_rules"]) is list and len(plan["stop_rules"]) == 5, "invalid_plan")
    require(ESSENTIAL_STOPS.issubset(plan["stop_rules"]) and all(v in STOPS for v in plan["stop_rules"]),
            "invalid_plan")
    _budget(plan["budget"], "invalid_plan")


# --- Feedback validation -----------------------------------------------------
def validate_feedback(fb: Any) -> None:
    _object(fb, ("schema", "feedback_id", "decision_id", "request_digest", "consent", "metrics"),
            "invalid_feedback")
    require(fb["schema"] == FEEDBACK_SCHEMA, "invalid_feedback")
    require(fb["consent"] is True, "consent_required")
    _uuid(fb["feedback_id"], "invalid_feedback")
    _uuid(fb["decision_id"], "invalid_feedback")
    require(type(fb["request_digest"]) is str and HEX64.fullmatch(fb["request_digest"]) is not None,
            "invalid_feedback")
    m = fb["metrics"]
    keys = ("queries", "reads", "claims_total", "claims_checked", "claims_supported",
            "questions_total", "questions_answered", "conditions_total", "conditions_met",
            "conditions_conflict", "conditions_unknown", "counterevidence_required",
            "counterevidence_checked", "out_of_scope_edits", "elapsed_ms", "first_value_ms",
            "user_relevance", "adoption")
    _object(m, keys, "invalid_feedback")
    for key, high in (("queries", 12), ("reads", 20), ("claims_total", 12),
                      ("claims_checked", 12), ("claims_supported", 12),
                      ("questions_total", 100), ("questions_answered", 100),
                      ("conditions_total", 100), ("conditions_met", 100),
                      ("conditions_conflict", 100), ("conditions_unknown", 100),
                      ("counterevidence_required", 12), ("counterevidence_checked", 12),
                      ("out_of_scope_edits", 1000)):
        require(_is_int(m[key]) and 0 <= m[key] <= high, "invalid_feedback")
    # monotonic denominator ordering
    require(m["claims_supported"] <= m["claims_checked"] <= m["claims_total"], "invalid_feedback")
    require(m["questions_answered"] <= m["questions_total"], "invalid_feedback")
    require(m["conditions_met"] + m["conditions_conflict"] + m["conditions_unknown"]
            <= m["conditions_total"], "invalid_feedback")
    require(m["counterevidence_checked"] <= m["counterevidence_required"]
            <= m["claims_total"], "invalid_feedback")
    for key in ("elapsed_ms", "first_value_ms"):
        v = m[key]
        require(v is None or (_is_int(v) and 0 <= v <= 3_600_000), "invalid_feedback")
    if m["first_value_ms"] is not None and m["elapsed_ms"] is not None:
        require(m["first_value_ms"] <= m["elapsed_ms"], "invalid_feedback")
    if m["user_relevance"] is not None:
        _enum(m["user_relevance"], ("relevant", "partial", "not_relevant"), "invalid_feedback")
    if m["adoption"] is not None:
        _enum(m["adoption"], ("reported_planned", "reported_started", "reported_completed"),
              "invalid_feedback")


# --- Local brief + brief digest (BRIEF-DIGEST-v1) ---------------------------
@dataclass
class ResearchSegment:
    """RESERVED EXTENSION POINT (local-only). See RESEARCH_SEGMENT_NOTE.

    Never serialised onto the wire (paper.intent.v1 is closed). Used only to
    annotate the local brief for research field / question / evidence
    applicability / strategy. No group, QR, capacity or upstream/downstream
    linkage is ever introduced here.
    """

    field: Optional[str] = None
    question: Optional[str] = None
    evidence_applicability: Optional[dict] = None
    strategy_hint: Optional[str] = None


def build_local_brief(*, intent_revision: int, evidence_revision: int,
                      accepted_constraints: Optional[dict] = None,
                      known_facts: Optional[list] = None,
                      research_segment: Optional[ResearchSegment] = None) -> dict:
    """Build the effective local brief (local only; never sent on the wire).

    The brief digest is computed from this object. The research segment, if
    supplied, is recorded here ONLY and does not alter the wire request.
    """
    brief: dict = {
        "intent_revision": intent_revision,
        "evidence_revision": evidence_revision,
        "accepted_constraints": accepted_constraints or {},
        "known_facts": known_facts or [],
    }
    if research_segment is not None:
        seg: dict = {}
        if research_segment.field is not None:
            seg["field"] = research_segment.field
        if research_segment.question is not None:
            seg["question"] = research_segment.question
        if research_segment.evidence_applicability is not None:
            seg["evidence_applicability"] = research_segment.evidence_applicability
        if research_segment.strategy_hint is not None:
            seg["strategy_hint"] = research_segment.strategy_hint
        if seg:
            brief["research_segment"] = seg
    return brief


def compute_brief_digest(salt: bytes, brief: dict) -> str:
    """SHA-256( salt(32 raw bytes) || canonical(brief) ). Lowercase hex."""
    require(len(salt) == SALT_BYTES, "bad_salt_length")
    return hashlib.sha256(salt + canonical(brief)).hexdigest()


# --- Request preparation (no network) ---------------------------------------
def prepare_request(*, request_id: str, intent_revision: int,
                    evidence_revision: int, brief_digest: str, mode: str,
                    demand: dict, supply: dict, budget: dict,
                    capabilities: list) -> dict:
    """Construct a canonical paper.intent.v1 request and attach its digest.

    The wire request contains ONLY the closed contract fields. The research
    segment (if any) is NOT added here — it belongs to the local brief only.
    """
    req = {
        "schema": REQUEST_SCHEMA,
        "request_id": request_id,
        "consumer": {"product": PRODUCT, "version": VERSION},
        "intent_revision": intent_revision,
        "evidence_revision": evidence_revision,
        "brief_digest": brief_digest,
        "mode": mode,
        "demand": demand,
        "supply": supply,
        "budget": budget,
        "capabilities": capabilities,
    }
    # NOTE: paper.intent.v1 has NO request_digest field (additionalProperties:false).
    # The digest is computed over this exact body and echoed back by the server
    # inside the *response* for binding; it is never stored on the wire request.
    validate_request(req)  # fail fast on malformed wire content
    return req


# --- Time window (TIME-VALIDATION-v1) ---------------------------------------
def check_time_window(resp: dict, clock: Callable[[], float] = time.time,
                      received_utc: Optional[float] = None) -> None:
    issued = resp["issued_at"]
    expires = resp["expires_at"]
    require(_is_finite_num(issued) and _is_finite_num(expires), "non_finite_time")
    require(issued < expires, "time_invalid")
    require(expires - issued <= MAX_DURATION_SECONDS, "time_duration_exceeded")
    now = clock()
    # Receive window: server issued time within +/-30s of client wall clock.
    require(abs(issued - now) <= MAX_SKEW_SECONDS, "time_skew_exceeded")
    require(expires > now, "expired")
    recv = received_utc if received_utc is not None else now
    # Monotonic local deadline (defensive; never extends cache via wall clock).
    deadline = min(expires - recv, MAX_DURATION_SECONDS)
    require(deadline > 0, "deadline_elapsed")


# --- HTTP transport (fixed endpoint, no redirect, TLS preserved) ------------
# Server self-declared headers that are safe to carry into a sanitized
# diagnostic summary (see contracts/diagnostics-v1/CONTRACT.md). Location,
# Set-Cookie, bodies and every other header never leave the transport layer.
SAFE_RESPONSE_HEADERS = (
    "X-Paper-Feedback-Code", "X-Paper-Event-Ref",
    "X-Paper-Release", "X-Paper-Catalog-Sha256",
)
TRANSPORT_KINDS = ("dns_failure", "tls_verification_failed",
                   "connection_failed", "transport_timeout",
                   "transport_outcome_unknown")
# Frozen copy of the catalog reason_aliases keys (byte-sync is asserted by
# test_paper_diagnostic). Only these exact keys may travel from an error
# body into the worker envelope; everything else stays unknown.
_SERVER_REASON_WHITELIST = frozenset({
    "invalid_request", "invalid_consumer", "invalid_schema", "invalid_json",
    "invalid_uuid", "invalid_enum", "invalid_budget", "invalid_capabilities",
    "sensitive_field", "excluded_key", "unknown_field", "invalid_scope",
    "invalid_track_selection", "invalid_timeout", "invalid_record",
    "invalid_counts", "invalid_time", "invalid_duration",
    "unobserved_mismatch", "privacy_field_refused", "timing_scope_mismatch",
    "input_file_unavailable", "file_not_found", "file_permission_denied",
    "fixed_endpoint_violation", "redirect_rejected",
    "source_fingerprint_mismatch", "source_drift",
    "request_id_mismatch", "request_digest_mismatch",
    "catalog_digest_mismatch", "track_digest_mismatch",
    "response_binding_invalid", "strategy_binding_invalid",
    "transport_failure", "transport_outcome_unknown",
    "write_failed", "record_exists", "record_too_large",
    "local_record_failed", "artifact_readback_failed",
    "invalid_response", "body_too_large", "invalid_content_type",
    "invalid_json_response", "transport_envelope_invalid",
    "expired", "deadline_elapsed", "time_skew_exceeded", "time_invalid",
    "time_duration_exceeded", "budget_exhausted", "query_budget_exhausted",
    "read_budget_exhausted", "claim_budget_exhausted", "round_budget_exhausted",
    "no_match", "track_no_match", "no_active_strategy",
    "needs_selection", "track_selection_required",
    "local_only", "native_short_path", "skipped", "capability_limited",
    "host_permission_blocked", "runtime_unavailable",
    "service_unavailable", "service_not_ready", "catalog_not_ready",
    "decision_feedback_capacity", "metrics_flush_failed",
    "admin_session_required", "admin_session_expired",
    "paper_admin_not_granted", "admin_capability_required",
    "csrf_required", "same_origin_required", "host_not_allowed",
    "route_not_found", "unexpected_query",
    "catalog_revision_conflict", "revision_conflict", "request_id_reused",
    "catalog_changed", "track_catalog_changed", "track_version_mismatch",
})
ERROR_BODY_MAX_BYTES = 4096


def _safe_headers(headers: Any) -> dict:
    """Extract only the four safe self-declared headers, bounded and clean."""
    out: dict = {}
    if headers is None:
        return out
    for name in SAFE_RESPONSE_HEADERS:
        try:
            value = headers.get(name)
        except Exception:  # defensive: header mapping quirks must not leak
            value = None
        if (type(value) is str and 0 < len(value) <= 128
                and "\r" not in value and "\n" not in value):
            out[name] = value
    return out


class HttpRejected(Error):
    """An actual HTTP response with a non-success status was observed.

    ``http_status`` is the real observed status (from HTTPError/redirect);
    the legacy ``Error.status`` stays a client-side classification only.
    """

    def __init__(self, code: str, status: int = 502, *,
                 http_status: Optional[int] = None,
                 server_reason: Optional[str] = None,
                 feedback_code: Optional[str] = None,
                 event_ref: Optional[str] = None,
                 release: Optional[str] = None,
                 catalog_sha256: Optional[str] = None,
                 redirect: bool = False):
        super().__init__(code, status)
        self.http_status = http_status
        # server_reason is the whitelist-parsed error-body reason only; the
        # self-declared feedback-code header rides separately and can never
        # impersonate a reason.
        self.server_reason = server_reason
        self.feedback_code = feedback_code
        self.event_ref = event_ref
        self.release = release
        self.catalog_sha256 = catalog_sha256
        self.redirect = redirect


class _RedirectBlocked(Error):
    """A real redirect response was refused by the fixed-endpoint policy."""

    def __init__(self, observed_status: int, headers: Optional[dict] = None):
        super().__init__("redirect_rejected", 400)
        self.observed_status = observed_status
        self.headers = headers or {}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Keep the real observed redirect status; the target URL never leaves
        # this layer (it would be an unsanitized endpoint detail).
        raise _RedirectBlocked(int(code), _safe_headers(headers))


def _classify_transport_exception(exc: BaseException) -> str:
    """Classify by exception type/errno only; unknown stays honestly unknown.

    Only an actual certificate-verification failure earns the TLS code; a
    generic SSLError (handshake EOF, protocol error, ...) keeps the unknown
    outcome instead of guessing a root cause from error text.
    """
    candidates = [exc]
    reason = getattr(exc, "reason", None)
    if reason is not None and reason is not exc:
        candidates.append(reason)
    for item in candidates:
        if isinstance(item, ssl.SSLCertVerificationError):
            return "tls_verification_failed"
    for item in candidates:
        if isinstance(item, socket.gaierror):
            return "dns_failure"
        if isinstance(item, ConnectionRefusedError):
            return "connection_failed"
        if isinstance(item, (TimeoutError, socket.timeout)):
            return "transport_timeout"
    for item in candidates:
        err = getattr(item, "errno", None)
        if err is None:
            continue
        if err == errno.ECONNREFUSED:
            return "connection_failed"
        if err == getattr(errno, "ETIMEDOUT", None):
            return "transport_timeout"
        if err in (getattr(errno, "EHOSTUNREACH", None),
                   getattr(errno, "ENETUNREACH", None)):
            return "connection_failed"
    return "transport_outcome_unknown"


def _parse_error_body_reason(exc: urllib.error.HTTPError) -> Optional[str]:
    """Extract a whitelisted reason from a bounded error body, or None.

    The body is read within the existing byte bound and a short inactivity
    limit (the parent's absolute subprocess deadline backstops the total);
    only an exact reason_aliases key is returned. The raw body never leaves
    this layer, and any read/parse problem degrades to None (unknown) while
    the real HTTP status is preserved by the caller.
    """
    try:
        _set_response_socket_timeout(exc, 1.0)
    except Exception:
        pass
    try:
        body = exc.read(ERROR_BODY_MAX_BYTES + 1)
    except Exception:
        return None
    if not body or len(body) > ERROR_BODY_MAX_BYTES:
        return None
    try:
        parsed = json.loads(body.decode("utf-8", "strict"))
    except (ValueError, UnicodeError):
        return None
    if type(parsed) is not dict:
        return None
    for key in ("error", "reason"):
        value = parsed.get(key)
        if type(value) is str:
            # Whitelisted keys pass; any other observed reason is reported
            # as unknown - the raw text never enters the envelope.
            return value if value in _SERVER_REASON_WHITELIST else "unknown"
    return None


def _attempt_timeout(timeout: float) -> float:
    require(_is_finite_num(timeout) and timeout > 0, "invalid_timeout")
    return min(float(timeout), DEFAULT_TIMEOUT)


def _validate_fixed_base_url(base_url: str) -> str:
    require(type(base_url) is str, "fixed_endpoint_violation")
    normalized = base_url.rstrip("/")
    require(normalized in (DEV_BASE_URL, PLANNED_PRODUCTION_BASE_URL),
            "fixed_endpoint_violation")
    if normalized == DEV_BASE_URL:
        parsed = urllib.parse.urlparse(normalized)
        require(parsed.scheme == "http" and parsed.netloc == "127.0.0.1:8768" and
                not parsed.path and not parsed.params and not parsed.query and
                not parsed.fragment, "fixed_endpoint_violation")
    return normalized


def _set_response_socket_timeout(response: Any, remaining: float) -> None:
    """Bound each blocking read by the remaining absolute attempt deadline."""
    candidates = [getattr(response, "_sock", None)]
    fp = getattr(response, "fp", None)
    candidates.append(getattr(fp, "_sock", None))
    raw = getattr(fp, "raw", None)
    candidates.append(getattr(raw, "_sock", None))
    connection = getattr(response, "connection", None)
    candidates.append(getattr(connection, "sock", None))
    for sock in candidates:
        if sock is not None and hasattr(sock, "settimeout"):
            sock.settimeout(remaining)
            return


def _read_bounded_response(response: Any, maximum: int, *,
                           deadline_monotonic: float,
                           monotonic: Callable[[], float],
                           status: Optional[int] = None) -> dict:
    # Post-receive contract failures keep the real observed HTTP status;
    # pre-send same-named failures (raised before any response) never do.
    try:
        headers = getattr(response, "headers", None)
        if headers is not None:
            try:
                length = headers.get("Content-Length")
            except AttributeError:
                length = None
            if length is not None:
                try:
                    require(int(length) <= maximum, "body_too_large", 413)
                except ValueError as exc:
                    raise Error("invalid_json") from exc
        body = bytearray()
        while True:
            remaining = deadline_monotonic - monotonic()
            require(remaining > 0, "total_timeout", 504)
            # One millisecond only absorbs floating-point boundary rounding for
            # the socket's inactivity timeout; the absolute check below (and
            # the outer killable worker) still enforces the actual deadline.
            _set_response_socket_timeout(response, remaining + 0.001)
            allowance = maximum + 1 - len(body)
            # BufferedReader.read(amt) may internally collect many packets
            # until it has amt bytes or EOF, hiding the absolute deadline for
            # the whole call. HTTPResponse/BufferedReader.read1 returns after
            # at most one raw read, so this loop rechecks the deadline.
            read_once = getattr(response, "read1", None)
            if read_once is None:
                read_once = response.read
            chunk = read_once(min(READ_CHUNK_BYTES, allowance))
            if not chunk:
                break
            body.extend(chunk)
            require(len(body) <= maximum, "body_too_large", 413)
            require(monotonic() < deadline_monotonic, "total_timeout", 504)
        return strict_json(bytes(body), maximum=maximum)
    except Error as exc:
        if status is not None and getattr(exc, "observed_http_status", None) is None:
            exc.observed_http_status = status
        raise


def _bounded_transport(request: dict, *, base_url: str, timeout: float,
                       request_validator: Callable[[Any], None] = validate_request,
                       response_max_bytes: int = REQUEST_MAX_BYTES,
                       monotonic: Callable[[], float] = time.monotonic,
                       deadline_monotonic: Optional[float] = None,
                       observer: Optional[Callable[[Optional[int], dict], None]] = None
                       ) -> dict:
    """One bounded physical attempt; shared by v1/v2 and direct callers.

    Validation and canonicalization happen before opener creation. No system
    proxy is consulted. The response is read in bounded chunks against an
    absolute monotonic deadline, so a slow trickle cannot extend the call.
    ``observer`` (optional) receives the real response status and the four
    safe self-declared headers the moment the response arrives; it never
    receives the body, the URL or any other header.
    """
    request_validator(request)
    data = canonical(request)
    require(len(data) <= REQUEST_MAX_BYTES, "body_too_large", 413)
    normalized = _validate_fixed_base_url(base_url)
    attempt_cap = _attempt_timeout(timeout)
    start = monotonic()
    deadline = (start + attempt_cap if deadline_monotonic is None
                else min(float(deadline_monotonic), start + attempt_cap))
    remaining = deadline - start
    require(remaining > 0, "total_timeout", 504)
    http_req = urllib.request.Request(
        normalized + DEV_WIRE_PATH, data=data,
        headers={"Content-Type": "application/json"}, method="POST")
    # ProxyHandler({}) forces the fixed direct endpoint; HTTPS keeps the
    # platform's verified default TLS context and redirects are always denied.
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), _NoRedirect())
    with opener.open(http_req, timeout=remaining) as response:
        observed_status = getattr(response, "status", None)
        if observer is not None:
            observer(observed_status,
                     _safe_headers(getattr(response, "headers", None)))
        remaining = deadline - monotonic()
        require(remaining > 0, "total_timeout", 504)
        _set_response_socket_timeout(response, remaining)
        return _read_bounded_response(
            response, response_max_bytes, deadline_monotonic=deadline,
            monotonic=monotonic, status=observed_status)


def _default_transport(request: dict, *, base_url: str, timeout: float,
                       monotonic: Callable[[], float] = time.monotonic,
                       deadline_monotonic: Optional[float] = None) -> dict:
    return _bounded_transport(
        request, base_url=base_url, timeout=timeout,
        request_validator=validate_request, response_max_bytes=REQUEST_MAX_BYTES,
        monotonic=monotonic, deadline_monotonic=deadline_monotonic)


def _transport_worker(protocol: str) -> int:
    """Child-only socket worker; the parent can terminate it at the deadline.

    Envelope kinds written to stdout (all bounded canonical JSON):
      * {"ok": True, "result": ..., "http": {...}}  - success; ``http`` carries
        the real observed status and the four safe self-declared headers.
      * {"ok": False, "kind": "http", ...}          - an actual HTTP rejection
        or refused redirect, with the real status and safe headers only.
      * {"ok": False, "kind": "transport", ...}     - DNS/TLS/connection/
        timeout classification by exception type; unknown stays unknown.
      * {"ok": False, "error": ..., "status": ...}  - deterministic contract
        error (unchanged legacy shape).
    No body text, URL, path, query or raw exception string ever leaves here.
    """
    observation = {"status": None, "headers": {}}
    try:
        envelope = strict_json(sys.stdin.buffer.read(REQUEST_MAX_BYTES + 2049),
                               maximum=REQUEST_MAX_BYTES + 2048)
        if protocol == "v2":
            import strategy_client_v2 as protocol_module
        else:
            protocol_module = sys.modules[__name__]

        def _observe(status: Optional[int], headers: dict) -> None:
            observation["status"] = status
            observation["headers"] = headers

        result = sys.modules[__name__]._bounded_transport(
            envelope["request"], base_url=envelope["base_url"],
            timeout=envelope["timeout"],
            request_validator=protocol_module.validate_request,
            response_max_bytes=envelope["response_max_bytes"],
            observer=_observe)
        sys.stdout.buffer.write(canonical(
            {"ok": True, "result": result, "http": observation}))
        return 0
    except _RedirectBlocked as exc:
        sys.stdout.buffer.write(canonical({
            "ok": False, "kind": "http", "http_status": int(exc.observed_status),
            "redirect": True, "headers": exc.headers}))
        return 0
    except urllib.error.HTTPError as exc:
        # An actual HTTP rejection: keep the real status, the safe headers and
        # a whitelisted reason parsed from the bounded error body. The raw
        # body never leaves the worker; parse failures keep status + unknown.
        envelope_out = {
            "ok": False, "kind": "http", "http_status": int(exc.code),
            "redirect": False,
            "headers": _safe_headers(getattr(exc, "headers", None)),
        }
        body_reason = _parse_error_body_reason(exc)
        if body_reason is not None:
            envelope_out["reason"] = body_reason
        sys.stdout.buffer.write(canonical(envelope_out))
        return 0
    except Error as exc:
        # Post-receive contract errors keep the already-captured observation
        # (real status + safe headers); pre-send ones have none by construction.
        envelope_out = {"ok": False, "error": exc.code, "status": exc.status}
        if observation["status"] is not None:
            envelope_out["http"] = observation
        sys.stdout.buffer.write(canonical(envelope_out))
        return 0
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        sys.stdout.buffer.write(canonical({
            "ok": False, "kind": "transport",
            "transport_kind": _classify_transport_exception(exc)}))
        return 0


def _validate_envelope_http(value: Any) -> dict:
    """Closed validation of the envelope's http observation block.

    Only the exact expected keys are accepted, statuses must be real
    response codes, and only the four safe header names with bounded string
    values pass through; anything else invalidates the envelope.
    """
    require(type(value) is dict, "transport_failure", 502)
    require(set(value) <= {"status", "http_status", "headers"},
            "transport_failure", 502)
    status = value.get("status", value.get("http_status"))
    require(status is None or
            (type(status) is int and 100 <= status <= 599),
            "transport_failure", 502)
    headers = value.get("headers", {})
    require(type(headers) is dict
            and set(headers) <= set(SAFE_RESPONSE_HEADERS)
            and all(type(k) is str and type(v) is str and len(v) <= 128
                    for k, v in headers.items()), "transport_failure", 502)
    return {"status": status, "headers": dict(headers)}


def _isolated_transport(request: dict, *, base_url: str, timeout: float,
                        protocol: str = "v1",
                        response_max_bytes: int = REQUEST_MAX_BYTES,
                        monotonic: Callable[[], float] = time.monotonic,
                        deadline_monotonic: Optional[float] = None,
                        observation_sink: Optional[list] = None) -> dict:
    """Run the complete socket operation in a killable standard-library child.

    Socket timeouts alone are inactivity limits, not absolute DNS/connect/header/
    body deadlines. The child is terminated by communicate/run on expiry; no
    abandoned thread is allowed to continue using the request or connection.
    HTTP rejections come back as HttpRejected with the real observed status and
    are never retried; DNS/TLS/connection/timeout failures keep their own
    classified codes instead of collapsing into a generic transport failure.
    HTTP observations go only into the caller-provided ``observation_sink``
    (one per client instance), never into shared process state.
    """
    if protocol == "v2":
        import strategy_client_v2 as protocol_module
    else:
        protocol_module = sys.modules[__name__]
    protocol_module.validate_request(request)  # closed before spawning a child
    data = canonical(request)
    require(len(data) <= REQUEST_MAX_BYTES, "body_too_large", 413)
    normalized = _validate_fixed_base_url(base_url)
    attempt_cap = _attempt_timeout(timeout)
    start = monotonic()
    deadline = (start + attempt_cap if deadline_monotonic is None
                else min(float(deadline_monotonic), start + attempt_cap))
    remaining = deadline - monotonic()
    require(remaining > 0, "total_timeout", 504)
    envelope = canonical({"request": request, "base_url": normalized,
                          "timeout": remaining,
                          "response_max_bytes": response_max_bytes})
    command = [sys.executable, "-B", os.path.abspath(__file__),
               "_transport-worker", protocol]
    try:
        completed = subprocess.run(
            command, input=envelope, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=remaining, check=False)
    except subprocess.TimeoutExpired as exc:
        raise Error("total_timeout", 504) from exc
    require(monotonic() <= deadline, "total_timeout", 504)
    if completed.returncode != 0:
        # The worker died without reporting: the send outcome is unknown; we
        # must not guess whether the service received anything.
        raise Error("transport_failure", 502)
    result = strict_json(completed.stdout, maximum=CATALOG_MAX_BYTES + 1024)
    require(type(result) is dict and type(result.get("ok")) is bool,
            "transport_failure", 502)
    if result["ok"]:
        require(set(result) == {"ok", "result", "http"}, "transport_failure", 502)
        http_info = _validate_envelope_http(result["http"])
        if observation_sink is not None:
            observation_sink.append({
                "http_status": http_info["status"],
                "headers": http_info["headers"]})
        return result["result"]
    if set(result) in ({"ok", "error", "status"},
                      {"ok", "error", "status", "http"}):
        error = Error(result["error"], result["status"])
        if "http" in result:
            # Post-receive contract error: the real status/safe headers ride
            # on the exception, never in a shared global.
            http_info = _validate_envelope_http(result["http"])
            error.observed_http_status = http_info["status"]
            error.observed_headers = http_info["headers"]
        raise error
    kind = result.get("kind")
    if kind == "http":
        require(set(result) <= {"ok", "kind", "http_status", "redirect",
                                "headers", "reason"}, "transport_failure", 502)
        status = result.get("http_status")
        require(type(status) is int and 100 <= status <= 599,
                "transport_failure", 502)
        headers = _validate_envelope_http(
            {"http_status": status, "headers": result.get("headers", {})}
        )["headers"]
        redirect = result.get("redirect") is True
        body_reason = result.get("reason")
        require(body_reason is None or
                (type(body_reason) is str and
                 (body_reason in _SERVER_REASON_WHITELIST or
                  body_reason == "unknown")),
                "transport_failure", 502)
        raise HttpRejected(
            "redirect_rejected" if redirect else "http_rejected",
            400 if redirect else 502,
            http_status=status,
            # Reason and code are different fields: only the whitelisted
            # error-body reason may be a reason; the header code rides alone.
            server_reason=body_reason,
            feedback_code=headers.get("X-Paper-Feedback-Code"),
            event_ref=headers.get("X-Paper-Event-Ref"),
            release=headers.get("X-Paper-Release"),
            catalog_sha256=headers.get("X-Paper-Catalog-Sha256"),
            redirect=redirect)
    if kind == "transport":
        transport_kind = result.get("transport_kind")
        require(transport_kind in TRANSPORT_KINDS, "transport_failure", 502)
        raise Error(transport_kind, 502)
    raise Error("transport_failure", 502)


def _isolated_v1_transport(request: dict, *, base_url: str, timeout: float,
                           monotonic: Callable[[], float] = time.monotonic,
                           deadline_monotonic: Optional[float] = None,
                           observation_sink: Optional[list] = None) -> dict:
    return _isolated_transport(
        request, base_url=base_url, timeout=timeout, protocol="v1",
        response_max_bytes=REQUEST_MAX_BYTES, monotonic=monotonic,
        deadline_monotonic=deadline_monotonic,
        observation_sink=observation_sink)


# Marks the built-in isolated transports: StrategyClient wraps only these with
# a per-client observation sink; custom transports keep their exact signature.
_isolated_v1_transport._paper_observant = True


# --- Sanitized diagnostics (paper.diagnostic.v1, optional side object) ------
# Diagnostics are built lazily from observed facts only. They are a separate
# object on ResolveResult / CLI output; the closed business wire and the
# paper.local-observation.v2 contract are never modified. A diagnostic
# failure must never change the business outcome, so every build is guarded.
_TRANSPORT_STAGE_CODES = frozenset({
    "total_timeout", "transport_failure", "dns_failure",
    "tls_verification_failed", "connection_failed", "transport_timeout",
    "transport_outcome_unknown",
})
_PRE_SEND_STAGE_CODES = frozenset({
    "fixed_endpoint_violation", "invalid_timeout",
    "source_fingerprint_mismatch", "invalid_canonical_value",
})
# not_called only where a pre-send rejection or an explicit local path
# provably never invoked the transport; anything uncertain stays unknown.
_SEND_STATE_FOR_STAGE = {
    "not_observed": "not_called",
    "pre_send": "not_called",
    "transport": "unknown",
    "http_response": "response_received",
    "response_validation": "response_received",
    "business_response": "response_received",
}


def _stage_for_failure(exc: Optional[BaseException], reason: str,
                       observed: bool = False) -> str:
    if reason in _TRANSPORT_STAGE_CODES:
        return "transport"
    if reason in ("http_rejected", "redirect_rejected"):
        return "http_response"
    if reason in _PRE_SEND_STAGE_CODES:
        return "pre_send"
    if isinstance(exc, urllib.error.HTTPError):
        return "http_response"
    if isinstance(exc, (urllib.error.URLError, TimeoutError, OSError)):
        return "transport"
    # A same-named contract error is response-side only with an actual HTTP
    # observation; without one it happened before any send.
    if observed or getattr(exc, "observed_http_status", None) is not None:
        return "response_validation"
    if reason in ("invalid_json", "body_too_large", "invalid_content_type"):
        return "pre_send"
    return "response_validation"


def _diagnostic_reason(exc: Optional[BaseException], reason: str) -> str:
    """Fine-grained reason for diagnostics without changing ResolveResult.reason."""
    if isinstance(exc, urllib.error.HTTPError):
        return "http_rejected"
    if reason == "transport_failure" and isinstance(
            exc, (urllib.error.URLError, TimeoutError, OSError)):
        return _classify_transport_exception(exc)
    return reason


def build_diagnostic(*, reason: Optional[str], observed_stage: str,
                     transport_attempts: int = 0,
                     request_id: Any = None,
                     exc: Optional[BaseException] = None,
                     observation: Optional[dict] = None,
                     client_platform: Optional[str] = None) -> Optional[dict]:
    """Best-effort paper.diagnostic.v1 summary; None when unavailable.

    Diagnostics never raise into the business path and never add network
    access. ``observation`` is the isolated transport's HTTP observation
    (real status + four safe headers) when one was recorded.
    """
    try:
        import paper_diagnostic as diag
    except ImportError:
        return None
    try:
        http_status: Optional[int] = None
        server_reason = feedback_code = None
        event_ref = release = catalog_sha = None
        if isinstance(exc, HttpRejected):
            http_status = exc.http_status
            server_reason = exc.server_reason
            feedback_code = exc.feedback_code
            event_ref, release = exc.event_ref, exc.release
            catalog_sha = exc.catalog_sha256
        elif isinstance(exc, _RedirectBlocked):
            http_status = exc.observed_status
            feedback_code = exc.headers.get("X-Paper-Feedback-Code")
            event_ref = exc.headers.get("X-Paper-Event-Ref")
            release = exc.headers.get("X-Paper-Release")
            catalog_sha = exc.headers.get("X-Paper-Catalog-Sha256")
        elif isinstance(exc, urllib.error.HTTPError):
            # In-process transport: same rules as the isolated worker - the
            # reason comes only from the bounded whitelist-parsed body, the
            # self-declared code header stays in its own field.
            http_status = exc.code if type(exc.code) is int else None
            headers = _safe_headers(getattr(exc, "headers", None))
            server_reason = _parse_error_body_reason(exc)
            feedback_code = headers.get("X-Paper-Feedback-Code")
            event_ref = headers.get("X-Paper-Event-Ref")
            release = headers.get("X-Paper-Release")
            catalog_sha = headers.get("X-Paper-Catalog-Sha256")
        elif getattr(exc, "observed_http_status", None) is not None:
            # Post-receive contract error carrying its own observation.
            http_status = exc.observed_http_status
            headers = getattr(exc, "observed_headers", None) or {}
            feedback_code = headers.get("X-Paper-Feedback-Code")
            event_ref = headers.get("X-Paper-Event-Ref")
            release = headers.get("X-Paper-Release")
            catalog_sha = headers.get("X-Paper-Catalog-Sha256")
        elif observation:
            status = observation.get("http_status")
            http_status = status if type(status) is int else None
            headers = observation.get("headers") or {}
            feedback_code = headers.get("X-Paper-Feedback-Code")
            event_ref = headers.get("X-Paper-Event-Ref")
            release = headers.get("X-Paper-Release")
            catalog_sha = headers.get("X-Paper-Catalog-Sha256")
        # An allowed server reason is the most specific classification
        # signal for an HTTP rejection (e.g. invalid_consumer -> its own
        # catalog item instead of the generic FBS-PAPER-1500); without one
        # the actual stage decides. The header code never plays this role.
        key_reason = reason
        if (type(server_reason) is str
                and server_reason in _SERVER_REASON_WHITELIST):
            key_reason = server_reason
        send_state = _SEND_STATE_FOR_STAGE[observed_stage]
        return diag.build_diagnostic(
            reason=key_reason, observed_stage=observed_stage,
            send_state=send_state,
            transport_attempts=(transport_attempts
                                if send_state != "not_called" else 0),
            network_sends=None,
            request_id=request_id, http_status=http_status,
            server_reason=server_reason,
            server_feedback_code=feedback_code,
            server_event_ref=event_ref,
            server_release=release, server_catalog_sha256=catalog_sha,
            client_platform=client_platform,
            client_platform_source=("user_reported"
                                    if client_platform else None))
    except Exception:
        return None


def source_fingerprint_status() -> str:
    """Pre-send source self-check: match / mismatch / unknown (fail-open)."""
    try:
        import paper_diagnostic as diag
    except ImportError:
        return "unknown"
    try:
        return diag.source_fingerprint().get("status", "unknown")
    except Exception:
        return "unknown"


# --- Accepted decision and high-level client --------------------------------
@dataclass(frozen=True)
class DecisionGuard:
    """Immutable receive/deadline binding for one exact selected decision."""
    response: dict
    request: dict
    received_utc: float
    received_monotonic: float
    deadline_monotonic: float
    request_digest: str
    response_digest: str

    @classmethod
    def bind(cls, response: dict, request: dict, *, catalog: Optional[dict] = None,
             clock: Callable[[], float] = time.time,
             monotonic: Callable[[], float] = time.monotonic,
             received_utc: Optional[float] = None,
             received_monotonic: Optional[float] = None) -> "DecisionGuard":
        require(response.get("status") == "selected", "decision_not_selected")
        wall = clock() if received_utc is None else received_utc
        mono = monotonic() if received_monotonic is None else received_monotonic
        require(_is_finite_num(wall) and _is_finite_num(mono), "non_finite_time")
        validate_response(response, request=request, catalog=catalog)
        check_time_window(response, clock=lambda: wall, received_utc=wall)
        remaining = min(response["expires_at"] - wall, MAX_DURATION_SECONDS)
        require(remaining > 0, "deadline_elapsed")
        return cls(response=copy.deepcopy(response), request=copy.deepcopy(request),
                   received_utc=wall, received_monotonic=mono,
                   deadline_monotonic=mono + remaining,
                   request_digest=digest(request), response_digest=digest(response))

    def assert_executable(self, *, current_intent_revision: int,
                          current_evidence_revision: int,
                          clock: Callable[[], float] = time.time,
                          monotonic: Callable[[], float] = time.monotonic) -> None:
        require(digest(self.request) == self.request_digest and
                digest(self.response) == self.response_digest, "decision_changed")
        require(monotonic() < self.deadline_monotonic, "deadline_elapsed")
        require(clock() < self.response["expires_at"], "expired")
        require(current_intent_revision == self.request["intent_revision"],
                "intent_revision_mismatch")
        require(current_evidence_revision == self.request["evidence_revision"],
                "evidence_revision_mismatch")


@dataclass
class ResolveResult:
    source: str  # dev_service | native_fallback | native_short_path |
                # capability_limited | local_only
    response: Optional[dict] = None
    reason: Optional[str] = None
    applied_native: bool = False
    network_attempts: int = 0
    guard: Optional[DecisionGuard] = None
    diagnostic: Optional[dict] = None  # separate paper.diagnostic.v1 summary


def _capability_limited(request: dict) -> bool:
    caps = set(request["capabilities"])
    if "web_search" not in caps or "page_read" not in caps:
        return True
    b = request["budget"]
    return b["max_queries"] == 0 or b["max_reads"] == 0


class StrategyClient:
    """Expert-side client with closed sends and a bounded two-attempt budget."""

    def __init__(self, transport: Optional[Callable[..., dict]] = None, *,
                 request_validator: Callable[[Any], None] = validate_request,
                 default_transport: Optional[Callable[..., dict]] = None,
                 response_max_bytes: int = REQUEST_MAX_BYTES):
        self.transport = transport  # callable(request, *, base_url, timeout) -> dict
        self.request_validator = request_validator
        base_transport = default_transport or _isolated_v1_transport
        if getattr(base_transport, "_paper_observant", False):
            # Each client owns its observation sink; interleaved clients can
            # never take each other's HTTP markers, and custom transports keep
            # their exact signature (no TypeError signature probing).
            self._observation_sink: Optional[list] = []

            def _observed_transport(request: dict, *, base_url: str,
                                    timeout: float) -> dict:
                return base_transport(
                    request, base_url=base_url, timeout=timeout,
                    observation_sink=self._observation_sink)

            self.default_transport = _observed_transport
        else:
            self._observation_sink = None
            self.default_transport = base_transport
        self.response_max_bytes = response_max_bytes

    def _pop_observation(self) -> Optional[dict]:
        sink = self._observation_sink
        if sink:
            return sink.pop(0)
        return None

    def prepare_request(self, **kwargs) -> dict:
        return prepare_request(**kwargs)

    def build_local_brief(self, **kwargs) -> dict:
        return build_local_brief(**kwargs)

    def compute_brief_digest(self, salt: bytes, brief: dict) -> str:
        return compute_brief_digest(salt, brief)

    def validate_response(self, resp: dict, request: dict,
                          catalog: Optional[dict] = None,
                          clock: Callable[[], float] = time.time,
                          received_utc: Optional[float] = None) -> Tuple[bool, str]:
        try:
            validate_response(resp, request=request, catalog=catalog)
            check_time_window(resp, clock=clock, received_utc=received_utc)
        except Error as exc:
            return False, exc.code
        return True, "ok"

    def _call_dev(self, request: dict, base_url: str, timeout: float,
                  monotonic: Callable[[], float]):
        self.request_validator(request)  # closed rejection before any transport
        frozen = canonical(request)  # retry bodies derive from these exact bytes
        require(len(frozen) <= REQUEST_MAX_BYTES, "body_too_large", 413)
        _validate_fixed_base_url(base_url)
        attempt_cap = _attempt_timeout(timeout)
        transport = self.transport or self.default_transport
        started = monotonic()
        total_budget = min(MAX_TOTAL_TIMEOUT, 2 * attempt_cap)
        reserve = min(LOCAL_PROCESSING_RESERVE, total_budget * 0.01)
        total_deadline = started + total_budget - reserve
        last_exc: Optional[Exception] = None
        attempts = 0
        for _ in range(2):  # initial + at most one same-id/same-body retry
            remaining = total_deadline - monotonic()
            if remaining <= 0:
                break
            attempt_request = strict_json(frozen, maximum=REQUEST_MAX_BYTES)
            attempts += 1
            try:
                response = transport(attempt_request, base_url=base_url,
                                     timeout=min(attempt_cap, remaining))
                observation = self._pop_observation()
                require(monotonic() <= total_deadline, "total_timeout", 504)
                return response, None, attempts, observation
            except Error as exc:
                # Deterministic contract/HTTP failures are never retried; a
                # post-receive observation (if any) rides along.
                return None, exc, attempts, self._pop_observation()
            except urllib.error.HTTPError as exc:
                # An actual HTTP rejection (in-process transport) is a real
                # response, never a retryable network unknown.
                return None, exc, attempts, self._pop_observation()
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                self._pop_observation()  # discard; nothing usable arrived
                # DNS / TLS-verification / connection failures are
                # classifiable by exception type, and their catalog
                # retry_policy is no_automatic_retry: stop after this single
                # attempt. Only genuinely unknown outcomes and timeouts keep
                # the original at-most-one same-id/same-body retry; HTTP
                # rejections above are never retried. The frozen request
                # bytes are never re-derived or mutated for a retry.
                if _classify_transport_exception(exc) in (
                        "dns_failure", "tls_verification_failed",
                        "connection_failed"):
                    return None, exc, attempts, None
                last_exc = exc
        if last_exc is None:
            last_exc = Error("total_timeout", 504)
        return None, last_exc, attempts, None

    def call_dev(self, request: dict, base_url: str = DEV_BASE_URL,
                 timeout: float = DEFAULT_TIMEOUT,
                 monotonic: Callable[[], float] = time.monotonic
                 ) -> Tuple[Optional[dict], Optional[Exception]]:
        resp, exc, _attempts, _observation = self._call_dev(
            request, base_url, timeout, monotonic)
        return resp, exc

    def call_production(self, request: dict, timeout: float = DEFAULT_TIMEOUT,
                        monotonic: Callable[[], float] = time.monotonic
                        ) -> Tuple[Optional[dict], Optional[Exception]]:
        """Explicit released HTTPS entry; closed validation happens before send."""
        return self.call_dev(request, base_url=PRODUCTION_BASE_URL,
                             timeout=timeout, monotonic=monotonic)

    def resolve_production(self, request: dict, *, timeout: float = DEFAULT_TIMEOUT,
                           catalog: Optional[dict] = None,
                           clock: Callable[[], float] = time.time,
                           monotonic: Callable[[], float] = time.monotonic) -> ResolveResult:
        result = self.resolve(request, dev=True, base_url=PRODUCTION_BASE_URL,
                              timeout=timeout, catalog=catalog, clock=clock,
                              monotonic=monotonic)
        if result.source == "dev_service":
            result.source = "production_service"
        return result

    def resolve(self, request: dict, *, dev: bool = False,
                base_url: str = DEV_BASE_URL, timeout: float = DEFAULT_TIMEOUT,
                catalog: Optional[dict] = None,
                clock: Callable[[], float] = time.time,
                monotonic: Callable[[], float] = time.monotonic,
                client_platform: Optional[str] = None) -> ResolveResult:
        self.request_validator(request)
        request_id = request.get("request_id")

        def _diag(reason, stage, attempts=0, exc=None, observation=None):
            return build_diagnostic(
                reason=reason, observed_stage=stage,
                transport_attempts=attempts, request_id=request_id, exc=exc,
                observation=observation, client_platform=client_platform)

        if request["mode"] in SHORT_PATH_MODES:
            return ResolveResult(
                "native_short_path", reason="native_short_path",
                applied_native=True,
                diagnostic=_diag("native_short_path", "not_observed"))
        if _capability_limited(request):
            return ResolveResult(
                "capability_limited", reason="capability_limited",
                applied_native=True,
                diagnostic=_diag("capability_limited", "not_observed"))
        if not dev:
            return ResolveResult(
                "local_only", reason="local_only", applied_native=True,
                diagnostic=_diag("local_only", "not_observed"))
        # Pre-send source self-check: a mismatch safely returns to the native
        # path with zero network access; unknown never blocks the call.
        if source_fingerprint_status() == "mismatch":
            return ResolveResult(
                "native_fallback", reason="source_fingerprint_mismatch",
                applied_native=True, network_attempts=0,
                diagnostic=_diag("source_fingerprint_mismatch", "pre_send"))
        resp, exc, attempts, observation = self._call_dev(
            request, base_url, timeout, monotonic)
        if resp is None:
            if isinstance(exc, Error):
                reason = exc.code
            elif isinstance(exc, urllib.error.HTTPError):
                reason = "http_rejected"  # real HTTP response, not a network unknown
            else:
                reason = "transport_failure"
            stage = _stage_for_failure(exc, reason, observed=bool(
                observation) or getattr(exc, "observed_http_status", None) is not None)
            return ResolveResult(
                "native_fallback", reason=reason, applied_native=True,
                network_attempts=attempts,
                diagnostic=_diag(_diagnostic_reason(exc, reason), stage,
                                 attempts=attempts, exc=exc,
                                 observation=observation))
        received_wall = clock()
        received_mono = monotonic()
        ok, reason = self.validate_response(
            resp, request, catalog=catalog, clock=lambda: received_wall,
            received_utc=received_wall)
        if not ok:
            return ResolveResult(
                "native_fallback", response=resp, reason=reason,
                applied_native=True, network_attempts=attempts,
                diagnostic=_diag(reason, "response_validation", attempts=attempts,
                                 observation=observation))
        if resp["status"] != "selected":
            return ResolveResult(
                "native_fallback", response=resp, reason=resp["status"],
                applied_native=True, network_attempts=attempts,
                diagnostic=_diag(resp["status"], "business_response",
                                 attempts=attempts, observation=observation))
        try:
            guard = DecisionGuard.bind(
                resp, request, catalog=catalog, clock=lambda: received_wall,
                monotonic=lambda: received_mono, received_utc=received_wall,
                received_monotonic=received_mono)
        except Error as guard_exc:
            return ResolveResult(
                "native_fallback", response=resp, reason=guard_exc.code,
                applied_native=True, network_attempts=attempts,
                diagnostic=_diag(guard_exc.code, "response_validation",
                                 attempts=attempts, observation=observation))
        return ResolveResult(
            "dev_service", response=resp, reason="ok",
            applied_native=False, network_attempts=attempts, guard=guard,
            diagnostic=_diag("completed", "business_response",
                             attempts=attempts, observation=observation))


# --- Minimal CLI for Codex local integration --------------------------------
def _load_json_path(path: str) -> dict:
    # Bounded read first, then format validation; file problems surface as a
    # safe closed code, never as a traceback carrying a private path.
    try:
        with open(path, "rb") as fh:
            data = fh.read(CATALOG_MAX_BYTES + 2)
    except OSError as exc:
        raise Error("input_file_unavailable", 400) from exc
    return strict_json(data, maximum=CATALOG_MAX_BYTES)


def _emit_json(payload: Any, *, indent: Optional[int] = None) -> None:
    """Encoding-independent CLI JSON output.

    ASCII-escaped JSON bytes are written straight to the stdout buffer, so
    the output never depends on the console/PYTHONIOENCODING encoding and a
    safe Chinese diagnostic can never raise UnicodeEncodeError mid-emit
    (which previously blanked stdout and spilled a traceback carrying the
    input path onto stderr). Field semantics and Unicode content are
    unchanged after JSON decoding. No system/encoding settings are touched.
    """
    text = json.dumps(payload, ensure_ascii=True, indent=indent)
    sys.stdout.buffer.write(text.encode("ascii") + b"\n")


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["_transport-worker"] and len(argv) == 2:
        return _transport_worker(argv[1])
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_prep = sub.add_parser("prepare", help="Build a request (no network)")
    p_prep.add_argument("--request-json", required=True)
    p_prep.add_argument("--salt-hex", help="32-byte salt as 64-hex for brief digest")
    p_prep.add_argument("--brief-json", help="local brief JSON for brief digest")

    p_val = sub.add_parser("validate-response", help="Validate a response (no network)")
    p_val.add_argument("--request-json", required=True)
    p_val.add_argument("--response-json", required=True)
    p_val.add_argument("--catalog-json", required=False)
    p_val.add_argument("--now", type=float, required=False)

    p_dev = sub.add_parser("dev-call", help="Explicit dev endpoint call")
    p_dev.add_argument("--request-json", required=True)
    p_dev.add_argument("--base-url", default=DEV_BASE_URL)
    p_dev.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)

    args = parser.parse_args(argv)
    try:
        if args.cmd == "prepare":
            req = _load_json_path(args.request_json)
            if args.salt_hex and args.brief_json:
                salt = bytes.fromhex(args.salt_hex)
                brief = _load_json_path(args.brief_json)
                req["brief_digest"] = compute_brief_digest(salt, brief)
            prepared = prepare_request(
                request_id=req["request_id"], intent_revision=req["intent_revision"],
                evidence_revision=req["evidence_revision"], brief_digest=req["brief_digest"],
                mode=req["mode"], demand=req["demand"], supply=req["supply"],
                budget=req["budget"], capabilities=req["capabilities"],
            )
            _emit_json({
                "request": prepared,
                "request_digest": digest(prepared),
            }, indent=2)
        elif args.cmd == "validate-response":
            request = _load_json_path(args.request_json)
            validate_request(request)
            resp = _load_json_path(args.response_json)
            catalog = _load_json_path(args.catalog_json) if args.catalog_json else None
            clock = (lambda: args.now) if args.now is not None else time.time
            ok, reason = StrategyClient().validate_response(resp, request, catalog=catalog, clock=clock)
            _emit_json({"valid": ok, "reason": reason})
            return 0 if ok else 1
        elif args.cmd == "dev-call":
            request = _load_json_path(args.request_json)
            validate_request(request)
            result = StrategyClient().resolve(request, dev=True, base_url=args.base_url,
                                              timeout=args.timeout)
            _emit_json({
                "source": result.source, "reason": result.reason,
                "response": result.response,
                "diagnostic": result.diagnostic,
            }, indent=2)
            return 0 if result.source == "dev_service" else 2
    except Error as exc:
        # Rejections before resolve (e.g. invalid request JSON, unreadable
        # input file) are pre-send; the diagnostic is separate from the
        # legacy error fields and never carries the offending path/content.
        output = {"error": exc.code, "status": exc.status}
        diagnostic = build_diagnostic(
            reason=exc.code, observed_stage="pre_send",
            transport_attempts=0, exc=exc)
        if diagnostic is not None:
            output["diagnostic"] = diagnostic
        _emit_json(output)
        return 1
    except OSError:
        output = {"error": "input_file_unavailable", "status": 400}
        diagnostic = build_diagnostic(
            reason="input_file_unavailable", observed_stage="pre_send",
            transport_attempts=0)
        if diagnostic is not None:
            output["diagnostic"] = diagnostic
        _emit_json(output)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
