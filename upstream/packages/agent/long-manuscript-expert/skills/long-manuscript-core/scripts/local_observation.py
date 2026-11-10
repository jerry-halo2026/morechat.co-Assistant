#!/usr/bin/env python3
"""paper.local-observation.v2 local execution summary (stdlib only, deterministic).

Records what one local task actually did: phases, an explicit timing scope
with UTC start/end and measured durations where honestly available, tool /
source-read / load-bearing claim-verification counts, the selected strategy
client, result and actual catalog/strategy/track binding, deliverable
read-back status, failure categories, a local run-category declaration and
the fields left unobserved.

Timing honesty (v2): ``timing_scope`` is a closed declaration, not an
independent certification. "unknown" (default) forbids every timing value.
"observed_interval" records an actually measured mid-task interval; it may
carry started/ended/elapsed but first_value_ms must stay null, and the
interval must never be passed off as a whole-task duration or a
first-usable-result latency. "task_total" is reserved for a genuinely
complete host event or user-provided/verified start-end evidence; it must
never be filled from mid-task sampling or post-hoc file timestamps.

Count honesty (v2): tools_used counts actual tool CALLS (not distinct tool
kinds) and only with a complete verifiable call record, else null; never
scan other sessions or private logs to invent a number. sources_read counts
research-evidence sources actually read (method docs and scripts do not
count). claims_checked is recorded only with a corresponding verifiable
checklist basis, else null. Counts are checkpoint observations - they never
claim calls that have not happened yet, and call counts, tool-kind counts,
input-file counts and evidence-source counts are not interchangeable.

Unmeasured strategy use is recorded as "unknown", never as a proven non-use;
"none"/"not_used" is reserved for explicit non-use. A known protocol with an
unconfirmed result (client=v1/v2, result=unknown) is allowed and is not the
same as not knowing the protocol. A selected result must carry the real
catalog/strategy binding (plus track binding for v2); a real non-selected
response (no_match / needs_selection / skipped / native_fallback) may keep
its observed catalog_revision while method and track fields stay null;
local-only paths keep every binding field null. The record is local-only
and is never uploaded by this module. v1 records are never silently read as
v2 and never overwritten.
It accepts only closed fields with bounded enums and non-negative integers;
unknown stays null or "unknown" and is never filled with 0. Titles, topics,
body text, full file contents, absolute private paths, accounts, URLs, raw
queries, cookies/tokens and whole conversations are rejected. Records are
written under a dedicated new filename and never overwrite an existing file.
Fill only from actual execution evidence; a model's own narration is not
execution evidence. See templates/local-observation-record.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
from typing import Any, Optional

SCHEMA = "paper.local-observation.v2"
# Current producer label. New self-produced records must NOT be mislabelled
# with the old 2026.10.300 tag the predecessor line used.
PACKAGE_VERSION = "2026.11.5"
# Explicit read boundary: records produced by the predecessor lines (old
# producer tag 2026.10.300, and 2026.11.0200 where present) remain LEGAL to
# READ/validate as-is. Reading an old record never re-labels or rewrites it.
LEGACY_PACKAGE_VERSIONS = ("2026.10.300", "2026.11.0200")
_READABLE_PACKAGE_VERSIONS = frozenset({PACKAGE_VERSION} | set(LEGACY_PACKAGE_VERSIONS))
MAX_RECORD_BYTES = 16 * 1024
MAX_EPOCH = 4_102_444_800          # 2100-01-01T00:00:00Z, mirrors strategy client
MAX_DURATION_MS = 86_400_000       # one local task record is bounded to 24 h
MAX_COUNT = 100_000

TASK_KINDS = ("research", "revision", "recovery", "material_review",
              "light_task", "other")
RUN_CATEGORIES = ("unknown", "synthetic", "user_task")
TIMING_SCOPES = ("unknown", "observed_interval", "task_total")
PHASES = ("intake", "evidence_review", "external_research", "extraction",
          "judgment", "drafting", "revision", "verification", "delivery",
          "recovery")
STRATEGY_CLIENTS = ("unknown", "none", "v1", "v2")
STRATEGY_RESULTS = ("selected", "skipped", "no_match", "needs_selection",
                    "native_short_path", "native_fallback",
                    "capability_limited", "local_only", "not_used", "unknown")
STRATEGY_BINDING_KEYS = ("catalog_revision", "strategy_id", "strategy_version",
                         "track_id", "track_version")
MAX_CATALOG_REVISION = 2_147_483_647
MAX_TEMPLATE_VERSION = 1_000_000
READBACK_STATES = ("read_back_verified", "generated_not_read_back",
                   "not_generated", "unknown")
FAILURE_CATEGORIES = ("transport_failure", "invalid_response",
                      "decision_expired", "timeout", "budget_exhausted",
                      "capability_limited", "permission_denied",
                      "parse_failure", "user_stop", "other")
COUNT_KEYS = ("tools_used", "sources_read", "claims_checked")
UNOBSERVED_FIELDS = ("started_at_utc", "ended_at_utc", "elapsed_ms",
                     "first_value_ms", "counts.tools_used",
                     "counts.sources_read", "counts.claims_checked",
                     "strategy.result", "deliverable_readback")

# Privacy: these keys are refused at any depth, in addition to the closed key
# sets. The record carries no titles, topics, body text, file contents,
# absolute private paths, accounts, URLs, raw queries, cookies/tokens or
# conversations.
DENIED_KEYS = frozenset({
    "title", "topic", "subject", "query", "raw_query", "search_query",
    "url", "uri", "link", "href", "path", "file_path", "filepath",
    "absolute_path", "dir", "directory", "folder",
    "account", "username", "user", "user_id", "email",
    "cookie", "token", "secret", "password", "credential", "api_key",
    "apikey", "auth", "authorization",
    "conversation", "message", "messages", "chat", "transcript",
    "content", "body", "text", "full_text", "file_content", "draft",
    "manuscript", "excerpt",
})

_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z")
_SAFE_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,62}[a-z0-9]\Z")
_FILENAME = re.compile(r"paper\.local-observation\.v2-[0-9a-f-]{36}\.json\Z")


class Error(Exception):
    """A deterministic rejection with a stable machine-readable code."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def require(condition: bool, code: str) -> None:
    if not condition:
        raise Error(code)


def _is_int(value: Any) -> bool:
    return type(value) is int


def _is_finite_num(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def _reject_denied_keys(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            require(isinstance(key, str) and key.lower() not in DENIED_KEYS,
                    "privacy_field_refused")
            _reject_denied_keys(child)
    elif isinstance(value, list):
        for child in value:
            _reject_denied_keys(child)


def _exact_keys(obj: Any, keys: tuple, code: str) -> None:
    require(type(obj) is dict, code)
    require(set(obj.keys()) == set(keys), code)


def _nullable_int(value: Any, low: int, high: int, code: str) -> None:
    if value is None:
        return
    require(_is_int(value) and low <= value <= high, code)


def _enum_list(value: Any, allowed: tuple, high: int, code: str) -> None:
    require(type(value) is list and len(value) <= high, code)
    require(all(type(item) is str for item in value), code)
    require(len(set(value)) == len(value), code)
    require(all(item in allowed for item in value), code)


def validate_record(record: Any) -> None:
    """Validate one paper.local-observation.v2 record; raise Error otherwise."""
    _reject_denied_keys(record)
    # Schema first: a v1 (or any foreign) record is never silently read as
    # v2; it is rejected by identity before any structural comparison.
    require(type(record) is dict and record.get("schema") == SCHEMA,
            "invalid_schema")
    _exact_keys(record, ("schema", "observation_id", "package_version",
                         "task_kind", "run_category", "timing_scope",
                         "phases", "started_at_utc", "ended_at_utc",
                         "elapsed_ms", "first_value_ms", "counts", "strategy",
                         "deliverable_readback", "failure_categories",
                         "feedback", "unobserved_fields"), "invalid_record")
    require(type(record["observation_id"]) is str and
            _UUID.fullmatch(record["observation_id"]) is not None,
            "invalid_observation_id")
    require(record["package_version"] in _READABLE_PACKAGE_VERSIONS,
            "invalid_package_version")
    require(record["task_kind"] in TASK_KINDS, "invalid_task_kind")
    # Local declaration only: never a trusted user identity or an adoption
    # proof. Default is "unknown".
    require(record["run_category"] in RUN_CATEGORIES, "invalid_run_category")
    _enum_list(record["phases"], PHASES, len(PHASES), "invalid_phases")

    # Timing scope (v2): a closed declaration, not an independent
    # certification. "unknown" forbids every timing value. "observed_interval"
    # is an actually measured mid-task interval and must never masquerade as
    # a task total or a first-usable-result latency. "task_total" is reserved
    # for a complete host event or user-verified start/end evidence.
    timing_scope = record["timing_scope"]
    require(timing_scope in TIMING_SCOPES, "invalid_timing_scope")
    started, ended = record["started_at_utc"], record["ended_at_utc"]
    _nullable_int(started, 0, MAX_EPOCH, "invalid_time")
    _nullable_int(ended, 0, MAX_EPOCH, "invalid_time")
    if started is not None and ended is not None:
        require(ended >= started, "invalid_time")
    elapsed, first_value = record["elapsed_ms"], record["first_value_ms"]
    _nullable_int(elapsed, 0, MAX_DURATION_MS, "invalid_duration")
    _nullable_int(first_value, 0, MAX_DURATION_MS, "invalid_duration")
    if elapsed is not None and first_value is not None:
        require(first_value <= elapsed, "invalid_duration")
    if timing_scope == "unknown":
        require(started is None and ended is None and elapsed is None
                and first_value is None, "timing_scope_mismatch")
    elif timing_scope == "observed_interval":
        require(first_value is None, "timing_scope_mismatch")

    counts = record["counts"]
    _exact_keys(counts, COUNT_KEYS, "invalid_counts")
    for key in COUNT_KEYS:
        _nullable_int(counts[key], 0, MAX_COUNT, "invalid_counts")

    strategy = record["strategy"]
    _exact_keys(strategy, ("client", "result") + STRATEGY_BINDING_KEYS,
                "invalid_strategy")
    client, result = strategy["client"], strategy["result"]
    require(client in STRATEGY_CLIENTS, "invalid_strategy")
    require(result in STRATEGY_RESULTS, "invalid_strategy")
    # Honest defaults: unmeasured strategy use is "unknown", not a proven
    # non-use. none/not_used is reserved for explicit non-use. A known
    # protocol with an unconfirmed result (client=v2, result=unknown) is
    # valid and is not the same as not knowing the protocol.
    if client == "unknown":
        require(result == "unknown", "invalid_strategy")
    require((client == "none") == (result == "not_used"), "invalid_strategy")
    if client in ("v1", "v2"):
        require(result != "not_used", "invalid_strategy")
    # Binding fields: safe named ids and bounded positive integers, or null.
    _nullable_int(strategy["catalog_revision"], 1, MAX_CATALOG_REVISION,
                  "invalid_strategy_binding")
    for key in ("strategy_version", "track_version"):
        _nullable_int(strategy[key], 1, MAX_TEMPLATE_VERSION,
                      "invalid_strategy_binding")
    for key in ("strategy_id", "track_id"):
        value = strategy[key]
        require(value is None or
                (type(value) is str and _SAFE_ID.fullmatch(value) is not None),
                "invalid_strategy_binding")
    bound = {key: strategy[key] is not None for key in STRATEGY_BINDING_KEYS}
    method_bound = any(bound[key] for key in
                       ("strategy_id", "strategy_version",
                        "track_id", "track_version"))
    if result == "selected":
        # A selected decision must carry the real method and catalog binding.
        require(bound["catalog_revision"] and bound["strategy_id"]
                and bound["strategy_version"], "invalid_strategy_binding")
        if client == "v2":
            require(bound["track_id"] and bound["track_version"],
                    "invalid_strategy_binding")
        else:
            require(not bound["track_id"] and not bound["track_version"],
                    "invalid_strategy_binding")
    elif result in ("no_match", "needs_selection", "skipped",
                    "native_fallback"):
        # A real non-selected response still carries its catalog_revision;
        # a known catalog version may be kept. Method and track bindings
        # stay null: no selection is ever fabricated. Fallbacks without an
        # actual receipt simply leave the catalog null.
        require(not method_bound, "invalid_strategy_binding")
    else:
        # not_used / unknown / local-only paths: no service receipt exists,
        # so every binding field stays null. Never fabricate a binding and
        # never re-request just to fill the record.
        require(not any(bound.values()), "invalid_strategy_binding")

    require(record["deliverable_readback"] in READBACK_STATES,
            "invalid_readback")
    _enum_list(record["failure_categories"], FAILURE_CATEGORIES,
               len(FAILURE_CATEGORIES), "invalid_failure_categories")

    feedback = record["feedback"]
    _exact_keys(feedback, ("consent", "sent"), "invalid_feedback")
    require(type(feedback["consent"]) is bool and
            type(feedback["sent"]) is bool, "invalid_feedback")
    require(not feedback["sent"] or feedback["consent"],
            "feedback_without_consent")

    unobserved = record["unobserved_fields"]
    _enum_list(unobserved, UNOBSERVED_FIELDS, len(UNOBSERVED_FIELDS),
               "invalid_unobserved_fields")
    listed = set(unobserved)
    # Unknown is explicit: a null / "unknown" field must be listed as
    # unobserved, and an observed field must not be listed. Nothing is
    # zero-filled.
    nullables = {
        "started_at_utc": started, "ended_at_utc": ended,
        "elapsed_ms": elapsed, "first_value_ms": first_value,
        "counts.tools_used": counts["tools_used"],
        "counts.sources_read": counts["sources_read"],
        "counts.claims_checked": counts["claims_checked"],
    }
    for field_name, value in nullables.items():
        require((value is None) == (field_name in listed), "unobserved_mismatch")
    require(("unknown" == record["deliverable_readback"])
            == ("deliverable_readback" in listed), "unobserved_mismatch")
    require(("unknown" == strategy["result"])
            == ("strategy.result" in listed), "unobserved_mismatch")


def build_record(*, observation_id: str, task_kind: str,
                 run_category: str = "unknown",
                 timing_scope: str = "unknown",
                 phases: Optional[list] = None,
                 started_at_utc: Optional[int] = None,
                 ended_at_utc: Optional[int] = None,
                 elapsed_ms: Optional[int] = None,
                 first_value_ms: Optional[int] = None,
                 tools_used: Optional[int] = None,
                 sources_read: Optional[int] = None,
                 claims_checked: Optional[int] = None,
                 strategy_client: str = "unknown",
                 strategy_result: str = "unknown",
                 catalog_revision: Optional[int] = None,
                 strategy_id: Optional[str] = None,
                 strategy_version: Optional[int] = None,
                 track_id: Optional[str] = None,
                 track_version: Optional[int] = None,
                 deliverable_readback: str = "unknown",
                 failure_categories: Optional[list] = None,
                 feedback_consent: bool = False,
                 feedback_sent: bool = False,
                 unobserved_fields: Optional[list] = None) -> dict:
    """Assemble and validate a record. Defaults keep everything unobserved.

    When ``unobserved_fields`` is not provided it is derived deterministically
    from the fields actually left null / "unknown" (never zero-filled, never
    guessed). An explicitly supplied list is validated strictly as before.
    """
    if unobserved_fields is None:
        derived = []
        for field_name, value in (
                ("started_at_utc", started_at_utc),
                ("ended_at_utc", ended_at_utc),
                ("elapsed_ms", elapsed_ms),
                ("first_value_ms", first_value_ms),
                ("counts.tools_used", tools_used),
                ("counts.sources_read", sources_read),
                ("counts.claims_checked", claims_checked)):
            if value is None:
                derived.append(field_name)
        if strategy_result == "unknown":
            derived.append("strategy.result")
        if deliverable_readback == "unknown":
            derived.append("deliverable_readback")
        unobserved_fields = derived
    record = {
        "schema": SCHEMA,
        "observation_id": observation_id,
        "package_version": PACKAGE_VERSION,
        "task_kind": task_kind,
        "run_category": run_category,
        "timing_scope": timing_scope,
        "phases": list(phases) if phases else [],
        "started_at_utc": started_at_utc,
        "ended_at_utc": ended_at_utc,
        "elapsed_ms": elapsed_ms,
        "first_value_ms": first_value_ms,
        "counts": {"tools_used": tools_used, "sources_read": sources_read,
                   "claims_checked": claims_checked},
        "strategy": {"client": strategy_client, "result": strategy_result,
                     "catalog_revision": catalog_revision,
                     "strategy_id": strategy_id,
                     "strategy_version": strategy_version,
                     "track_id": track_id,
                     "track_version": track_version},
        "deliverable_readback": deliverable_readback,
        "failure_categories": list(failure_categories) if failure_categories else [],
        "feedback": {"consent": feedback_consent, "sent": feedback_sent},
        "unobserved_fields": list(unobserved_fields),
    }
    validate_record(record)
    return record


def record_filename(record: dict) -> str:
    """Dedicated per-record filename; never a user-chosen original name."""
    return "paper.local-observation.v2-%s.json" % record["observation_id"]


def canonical_bytes(record: dict) -> bytes:
    """Deterministic serialisation: same record always yields same bytes."""
    text = json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True)
    return (text + "\n").encode("utf-8")


def record_digest(record: dict) -> str:
    return hashlib.sha256(canonical_bytes(record)).hexdigest()


def write_record(record: dict, output_dir: str) -> str:
    """Validate and exclusively create the record file. Never overwrites."""
    validate_record(record)
    require(type(output_dir) is str and output_dir.strip() != "",
            "invalid_output_dir")
    os.makedirs(output_dir, exist_ok=True)
    target = os.path.join(output_dir, record_filename(record))
    data = canonical_bytes(record)
    try:
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    except FileExistsError:
        raise Error("record_exists")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
    except OSError:
        try:
            os.unlink(target)
        except OSError:
            pass
        raise Error("write_failed")
    return target


def _strict_loads(raw: bytes) -> Any:
    require(len(raw) <= MAX_RECORD_BYTES, "record_too_large")
    pairs_seen = []

    def _hook(pairs):
        keys = [key for key, _ in pairs]
        require(len(set(keys)) == len(keys), "duplicate_key")
        pairs_seen.append(True)
        return dict(pairs)

    try:
        text = raw.decode("utf-8")
        require(all(ord(ch) >= 32 or ch in "\r\n\t" for ch in text),
                "invalid_unicode")
        value = json.loads(text, object_pairs_hook=_hook)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise Error("invalid_json")
    _reject_non_finite(value)
    return value


def _reject_non_finite(value: Any) -> None:
    if isinstance(value, dict):
        for child in value.values():
            _reject_non_finite(child)
    elif isinstance(value, list):
        for child in value:
            _reject_non_finite(child)
    elif type(value) is float:
        require(math.isfinite(value), "non_finite_number")


def load_record(path: str) -> dict:
    """Read and validate an existing record file (read-only)."""
    try:
        with open(path, "rb") as handle:
            raw = handle.read(MAX_RECORD_BYTES + 1)
    except OSError:
        raise Error("read_failed")
    record = _strict_loads(raw)
    validate_record(record)
    return record


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    val = sub.add_parser("validate", help="Validate a local observation record")
    val.add_argument("--record-json", required=True)
    wr = sub.add_parser("write", help="Validate and exclusively write a record")
    wr.add_argument("--record-json", required=True)
    wr.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    try:
        if args.cmd == "validate":
            record = load_record(args.record_json)
            print(json.dumps({"valid": True, "digest": record_digest(record)},
                             ensure_ascii=False))
        else:
            candidate = _strict_loads(open(args.record_json, "rb").read())
            path = write_record(candidate, args.output_dir)
            print(json.dumps({"written": True, "file": os.path.basename(path),
                              "digest": record_digest(candidate)},
                             ensure_ascii=False))
    except Error as exc:
        print(json.dumps({"error": exc.code}, ensure_ascii=False))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
