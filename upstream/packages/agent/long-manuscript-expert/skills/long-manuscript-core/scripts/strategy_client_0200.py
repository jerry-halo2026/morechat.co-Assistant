#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Closed v2 + exact 2026.11.5 strategy client / receipt consumer (rev 2).

Standard library only. Selected minimum wire:
  POST /v1/strategies/resolve   paper.intent.v2
  POST /v1/feedback             paper.feedback.v2 (default off)
  POST /v1/strategies/receipt   paper.strategy-receipt-query.v1 (READ ONLY)

NOT enabled: v3, foundation preview, feedback.v3, private project lookup,
paid provider, global manuscript storage. Five-form/v3 fields never enter the
v2 wire. 270/300 are never impersonated: the compat shape used ONLY to reuse
the complete predecessor validator is never persisted or transmitted.

Rev 2 fixes (independently reproduced NC01..NC08 + pairing C01..C05):
  NC01 every remote exit (resolve, query, feedback) obeys the default-off gate;
  NC02 send_started/action states are DURABLE immutable events, with a
       read-only restore-by-original-id path; persistence failure => 0 calls;
  NC03 wire receipt stays a CLOSED 7-field envelope; local metadata is separate;
  NC04 the COMPLETE v2 request validator is reused, not a weak reimplementation;
  NC05 the COMPLETE v2 response validator plus exact current budget/capability
       binding, candidate/track consistency and one-shot action gating;
  NC06 finite, ordered, bounded, non-boolean timestamps; 60s-old recovery is
       valid, fresh-response 30s path is separate, exact expiry refuses;
  NC07 feedback is honestly unsupported until a real confirmed send exists;
  NC08 a small bounded HTTPS transport exists but is never used by default.

Rev 3 fixes (second-round independent review R2-01..R2-05 + probe02):
  R2-01 the complete v2 RESPONSE validator now receives the persisted ORIGINAL
       request (validation-only compat copy), activating candidate scope,
       selection-mode vs track_selection, digest/revision and request budget
       semantics; the current local context is MANDATORY (no fallback to the
       original capabilities);
  R2-02 observed expiry is permanent: in-process monotonic clock floor plus a
       durable expired_rejected event; wall-clock rollback cannot revive a
       decision that was already observed expired;
  R2-03 execution permission is granted ONLY after the exclusive durable
       recovered event is successfully written AND read back; a collision (a
       second instance) or persistence failure stays non-executable, and a
       same-id read-only query never upgrades into a second execution grant;
  R2-04 restore binds the whole identity chain: filename == requested id ==
       record.operation_id == record.request_id == wire request_id; consumer,
       schema, revisions, canonical length and digest must all agree; an edited
       outer record with a substituted id is refused before any query;
  R2-05 the bounded HTTPS transport now enforces a true TOTAL deadline
       (monotonic), STRICT JSON (duplicate keys / NaN / Infinity refused) and
       preserves the ACTUAL redirect status;
  probe02 every CURRENT budget cap is bound per key with spent budget; a
       current cap of 0 blocks the plan even when the original request allowed
       more; a missing current cap is unknown and never infinity.

The service is NOT deployed in this revision. remote_enabled defaults to False.
No real network call is made by this module unless a caller explicitly opts in
AND supplies/creates a real transport. Loopback pairing evidence belongs to the
service lane; this client does not claim HTTP consumption from local mocks.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import ssl
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import strategy_client as v1
import strategy_client_v2 as v2

VERSION = "2026.11.5"
# Legal predecessor product version. Bounded read-only compatibility only:
# old pending records / receipts keep their ORIGINAL version, id and digest;
# nothing is migrated, re-labelled or re-sent. The module name
# strategy_client_0200 and the paper.client0200.* schema names are compat
# identifiers and intentionally do not change with the release version.
LEGACY_VERSION_0200 = "2026.11.0200"
PRODUCT = "long-manuscript-expert"
RESOLVE_SCHEMA = "paper.intent.v2"
FEEDBACK_SCHEMA = "paper.feedback.v2"
RECEIPT_QUERY_SCHEMA = "paper.strategy-receipt-query.v1"
RECEIPT_RESULT_SCHEMA = "paper.strategy-receipt.v1"
DECISION_SCHEMA = "paper.strategy-decision.v2"

RESOLVE_PATH = "/v1/strategies/resolve"
FEEDBACK_PATH = "/v1/feedback"
RECEIPT_PATH = "/v1/strategies/receipt"
BASE_URL = "https://api2.u3w.com/working-paper"
MAX_REQUEST_BYTES = 16384
MAX_RESPONSE_BYTES = 65536
HTTP_TIMEOUT_SECONDS = 3.0
TOTAL_TIMEOUT_SECONDS = 6.0
MAX_FUTURE_SKEW_SECONDS = 30.0
DECISION_LIFETIME_SECONDS = 600.0

CANONICALIZATION = "json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')"
CONTRACT_SAMPLE_DIGEST = "860d5f2086c83102634b0dc629068361ea1069dd95d9e2fd4a51b617bbd09f5f"
CONTRACT_SAMPLE_CANONICAL_BYTES = 1464

INTENT_V2_FIELDS = frozenset({
    "schema", "consumer", "request_id", "intent_revision", "evidence_revision",
    "mode", "demand", "supply", "research_scope", "track_selection",
    "brief_digest", "capabilities", "budget",
})
CONSUMER_FIELDS = frozenset({"product", "version"})
RECEIPT_QUERY_FIELDS = frozenset({"schema", "consumer", "request_id", "request_digest"})
RECEIPT_RESULT_FIELDS = frozenset({
    "schema", "request_id", "request_digest", "state", "response",
    "executable", "retry_permitted",
})
DECISION_FIELDS = frozenset({
    "schema", "request_id", "intent_revision", "evidence_revision", "request_digest",
    "decision_id", "status", "catalog_revision", "strategy", "plan", "reason_codes",
    "issued_at", "expires_at", "track", "candidates", "track_evaluations", "selection_mode",
})
RECEIPT_STATES = frozenset({"recorded", "expired", "catalog_changed", "unknown"})
ALLOWED_CAPABILITIES = frozenset({"web_search", "page_read", "file_read"})
BUDGET_KEYS = ("max_queries", "max_reads", "max_claims", "max_rounds")
HEX64 = re.compile(r"^[0-9a-f]{64}$")

# enterprise-r4 C: the only two CLOSED business outcomes a real v2 feedback
# response can report. An HTTP 200 by itself (or an empty/unknown body) is NOT
# a confirmation; the service's own accepted/duplicate shapes must be checked.
VERIFIED_DECISION_SCHEMA = "paper.client0200.verified-decision.v1"
FEEDBACK_ACCEPTED_PROVENANCE = "anonymous_client_report_unverified"
FEEDBACK_ACCEPTED_SHAPE = {"status", "provenance"}
FEEDBACK_DUPLICATE_SHAPE = {"status"}


def feedback_receipt_status(status, body) -> str | None:
    """Return the CLOSED business outcome of a real v2 feedback response.

    Only the two shapes the frozen service actually emits are confirmations:
      accepted  -> {"status":"accepted",
                    "provenance":"anonymous_client_report_unverified"}
      duplicate -> {"status":"duplicate"}
    An HTTP 200 with an empty body, a malformed object, a partial shape or an
    unknown status is NOT a confirmation: the caller must keep the original
    id and the already-started state as unknown and never resend. No new
    response schema is introduced.
    """
    if type(status) is not int or not 200 <= status < 300:
        return None
    if not isinstance(body, dict):
        return None
    kind = body.get("status")
    if kind == "accepted":
        if (set(body) == FEEDBACK_ACCEPTED_SHAPE
                and body.get("provenance") == FEEDBACK_ACCEPTED_PROVENANCE):
            return "accepted"
        return None
    if kind == "duplicate" and set(body) == FEEDBACK_DUPLICATE_SHAPE:
        return "duplicate"
    return None


def _loopback_controlled_base_ok(url) -> bool:
    """enterprise-r4 B (loopback hook parsing fix): accept a controlled base
    URL only when its REAL parsed hostname is bare loopback.

    A prefix check lets userinfo forge a loopback-looking string
    (``http://127.0.0.1@attacker.example/``); ``urlsplit`` resolves the actual
    host, and any userinfo, non-loopback host, non-http scheme, or attached
    path/query/fragment is refused. Both the parent (before ANY spawn) and
    the child (before ANY network call) call this, so a forged target is
    rejected at the earliest possible boundary.
    """
    from urllib.parse import urlsplit

    if not isinstance(url, str):
        return False
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    if parts.scheme != "http":
        return False
    if parts.username is not None or parts.password is not None:
        return False  # userinfo can fake a loopback prefix
    if parts.path not in ("", "/") or parts.query or parts.fragment:
        return False  # the base URL must be a bare origin
    host = parts.hostname
    if host not in ("127.0.0.1", "localhost"):
        return False
    try:
        port = parts.port
    except ValueError:
        return False
    if port is not None and not (1 <= port <= 65535):
        return False
    return True


class ContractError(ValueError):
    pass


class SendRefused(RuntimeError):
    pass


def canonical_bytes(value) -> bytes:
    """Exact copy of the selected service contract canonicalization."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def request_digest(value) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _is_uuid(value) -> bool:
    if not isinstance(value, str) or len(value) != 36:
        return False
    try:
        return str(uuid.UUID(value)) == value.lower()
    except (ValueError, AttributeError):
        return False


def _finite_number(value) -> bool:
    return (type(value) in (int, float)) and math.isfinite(value)


def validate_wire(intent: dict) -> dict:
    """Closed v2 validation BEFORE any journaling or transport.

    Reuses the COMPLETE predecessor v2 validator (nested closed keys/types,
    enums, budgets, finite values, revisions, excluded fields, demand/supply
    cells, research scope, track selection) via a compat-shaped COPY that is
    used for validation only. The exact 2026.11.5 consumer is enforced on
    the real object; 270/300 are never impersonated on the wire.
    """
    if not isinstance(intent, dict):
        raise ContractError("intent must be an object")
    extra = set(intent) - INTENT_V2_FIELDS
    if extra:
        raise ContractError(f"closed v2 wire refuses extra fields: {sorted(extra)}")
    missing = INTENT_V2_FIELDS - set(intent)
    if missing:
        raise ContractError(f"missing closed v2 fields: {sorted(missing)}")
    if intent["schema"] != RESOLVE_SCHEMA:
        raise ContractError("schema must be paper.intent.v2")
    consumer = intent["consumer"]
    if not isinstance(consumer, dict) or set(consumer) != CONSUMER_FIELDS:
        raise ContractError("consumer must have exactly product/version")
    if consumer["product"] != PRODUCT or consumer["version"] != VERSION:
        raise ContractError("consumer must be exactly long-manuscript-expert / 2026.11.5")
    if not _is_uuid(intent["request_id"]):
        raise ContractError("request_id must be a lowercase UUID string")
    for key in ("intent_revision", "evidence_revision"):
        if type(intent[key]) is not int or intent[key] < 1:
            raise ContractError(f"{key} must be a positive integer")
    caps = intent["capabilities"]
    if (type(caps) is not list or not caps or
            any(type(c) is not str or c not in ALLOWED_CAPABILITIES for c in caps)
            or len(set(caps)) != len(caps)):
        raise ContractError("capabilities must be a non-empty closed enum subset")
    budget = intent["budget"]
    if type(budget) is not dict or set(budget) != set(BUDGET_KEYS):
        raise ContractError("budget keys must be closed")
    for key in BUDGET_KEYS:
        if type(budget[key]) is not int or budget[key] < 0:
            raise ContractError(f"budget.{key} must be a non-negative integer")
    if not (isinstance(intent["brief_digest"], str)
            and HEX64.fullmatch(intent["brief_digest"])):
        raise ContractError("brief_digest must be 64 lowercase hex")
    # COMPLETE predecessor validator, on a validation-only compat copy.
    compat = json.loads(json.dumps(intent))
    compat["consumer"] = {"product": v1.PRODUCT, "version": v1.VERSION}
    try:
        v2.validate_request(compat)
    except Exception as exc:
        raise ContractError(f"complete v2 request validation failed: {type(exc).__name__}: {exc}")
    raw = canonical_bytes(intent)
    if len(raw) > MAX_REQUEST_BYTES:
        raise ContractError("request exceeds 16 KiB v2 limit")
    return {"valid": True, "canonical_bytes": len(raw),
            "request_digest": request_digest(intent),
            "validator": "strategy_client_v2.validate_request (reused, compat-shape only)"}


def validate_decision_shape(decision: dict, *, request: dict | None = None) -> dict:
    """COMPLETE v2 response validator reused WITH the original request.

    Passing the original request activates every request-dependent semantic:
    candidate scope coverage, selection mode vs the requested track_selection
    (explicit binding / automatic uniqueness / explicit-scope origin), digest,
    revisions and per-request budget ceilings. The request handed to the legacy
    validator is a validation-only compat copy (consumer swapped); the real
    0200 wire object is never mutated, persisted or transmitted in compat form.
    """
    if not isinstance(decision, dict) or set(decision) != DECISION_FIELDS:
        raise ContractError("decision fields not closed")
    if decision["schema"] != DECISION_SCHEMA:
        raise ContractError("decision schema mismatch")
    for key in ("issued_at", "expires_at"):
        if not _finite_number(decision[key]):
            raise ContractError(f"{key} must be a finite non-boolean number")
    try:
        v2.validate_response(decision, request=request, catalog=None)
    except Exception as exc:
        raise ContractError(f"complete v2 response validation failed: {type(exc).__name__}: {exc}")
    return {"valid": True,
            "request_bound": request is not None,
            "validator": "strategy_client_v2.validate_response (reused, request-bound)"}


def _reject_nonfinite(value) -> None:
    """Reject any non-finite float at any depth (covers 1e999 -> +inf)."""
    if isinstance(value, bool):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ContractError("non-finite JSON number refused")
        return
    if isinstance(value, dict):
        for child in value.values():
            _reject_nonfinite(child)
    elif isinstance(value, list):
        for child in value:
            _reject_nonfinite(child)


def _strict_json_loads(raw: bytes) -> dict:
    """Strict JSON: duplicate keys, non-finite constants AND non-finite
    numbers (including exponent overflow such as 1e999 -> +inf) are refused.

    parse_constant alone only catches the literal NaN/Infinity tokens; a
    number like 1e999 parses to float('inf') through the default float()
    conversion, so the conversion itself is hooked and a full recursive
    finite-value check runs afterwards."""
    def _pairs(pairs):
        seen = {}
        for k, v in pairs:
            if k in seen:
                raise ContractError(f"duplicate JSON key refused: {k}")
            seen[k] = v
        return seen

    def _constant(name):
        raise ContractError(f"non-finite JSON constant refused: {name}")

    def _finite_float(token: str) -> float:
        value = float(token)
        if not math.isfinite(value):
            raise ContractError(
                f"non-finite JSON number refused (exponent overflow: {token[:32]})")
        return value

    try:
        parsed = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                            parse_constant=_constant, parse_float=_finite_float)
    except ContractError:
        raise
    except (UnicodeDecodeError, ValueError) as exc:
        raise ContractError(f"strict JSON parse failed: {type(exc).__name__}: {exc}")
    _reject_nonfinite(parsed)
    return parsed


def _child_socket_operation(envelope: dict) -> dict:
    """CHILD-ONLY: perform the ENTIRE DNS/connect/TLS/headers/body operation.

    enterprise-r4 B. A socket inactivity timeout is NOT an absolute deadline:
    a peer that drips valid headers every 0.8s keeps ``opener.open`` alive well
    past the declared total deadline. Here the whole operation lives in ONE
    killable child process; the parent's monotonic subprocess timeout is the
    authoritative hard cutoff for the header phase, so the child (and its
    socket) is terminated AT the deadline — no abandoned background thread is
    left sending. The body loop additionally re-checks the absolute deadline
    between raw reads. Strict JSON and exact size limits are unchanged.

    Only a bounded canonical envelope is returned; the request body, URL and
    raw exception text never leave the child.
    """
    import time

    # The child re-validates the closed envelope itself; it never trusts the
    # parent to have checked. Only the three exact 0200 paths and bounded
    # bodies are accepted, and a controlled target must be loopback HTTP.
    if envelope.get("schema") != "paper.client0200.transport-envelope.v1":
        return {"ok": False, "kind": "contract", "reason": "invalid_transport_envelope"}
    path = envelope["path"]
    if path not in (RESOLVE_PATH, RECEIPT_PATH, FEEDBACK_PATH):
        return {"ok": False, "kind": "contract", "reason": "unsupported path"}
    body = bytes.fromhex(envelope["body_hex"])
    if len(body) > MAX_REQUEST_BYTES:
        return {"ok": False, "kind": "contract", "reason": "request exceeds 16 KiB"}
    controlled = envelope.get("controlled_base_url")
    if controlled is not None and not _loopback_controlled_base_ok(controlled):
        return {"ok": False, "kind": "contract",
                "reason": "controlled target must be loopback HTTP"}
    started = time.monotonic()
    deadline = started + float(envelope["remaining_seconds"])
    url = (controlled or BASE_URL) + path
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"})

    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            # Preserve the ACTUAL redirect status code in the refusal.
            raise urllib.error.HTTPError(url, code, f"redirect refused: {code}", headers, None)

    ctx = ssl.create_default_context()
    opener = urllib.request.build_opener(
        _NoRedirect, urllib.request.HTTPSHandler(context=ctx))
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return {"ok": False, "kind": "contract", "reason": "total_deadline_exceeded"}
    try:
        resp_ctx = opener.open(req, timeout=min(HTTP_TIMEOUT_SECONDS, remaining))
    except urllib.error.HTTPError as exc:
        return {"ok": False, "kind": "http",
                "http_status": int(exc.code) if isinstance(getattr(exc, "code", None), int) else None}
    except (TimeoutError, OSError) as exc:
        return {"ok": False, "kind": "transport", "reason": type(exc).__name__}
    with resp_ctx as resp:
        status = resp.status
        if time.monotonic() >= deadline:
            return {"ok": False, "kind": "contract", "reason": "total_deadline_exceeded"}
        headers = getattr(resp, "headers", None)
        length = headers.get("Content-Length") if headers is not None else None
        if length is not None:
            try:
                if int(length) > MAX_RESPONSE_BYTES:
                    return {"ok": False, "kind": "contract",
                            "reason": "response exceeds 64 KiB"}
            except ValueError:
                pass
        buf = bytearray()
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return {"ok": False, "kind": "contract", "reason": "total_deadline_exceeded"}
            sock = None
            fp = getattr(resp, "fp", None)
            for candidate in (getattr(resp, "_sock", None),
                              getattr(fp, "_sock", None),
                              getattr(getattr(fp, "raw", None), "_sock", None),
                              getattr(getattr(resp, "connection", None), "sock", None)):
                if candidate is not None and hasattr(candidate, "settimeout"):
                    sock = candidate
                    break
            if sock is not None:
                sock.settimeout(remaining + 0.001)
            allowance = MAX_RESPONSE_BYTES + 1 - len(buf)
            if allowance <= 0:
                return {"ok": False, "kind": "contract", "reason": "response exceeds 64 KiB"}
            read_once = getattr(resp, "read1", None) or resp.read
            try:
                chunk = read_once(min(8192, allowance))
            except (TimeoutError, OSError):
                return {"ok": False, "kind": "contract", "reason": "total_deadline_exceeded"}
            if not chunk:
                break
            buf.extend(chunk)
            if len(buf) > MAX_RESPONSE_BYTES:
                return {"ok": False, "kind": "contract", "reason": "response exceeds 64 KiB"}
            if time.monotonic() >= deadline:
                return {"ok": False, "kind": "contract", "reason": "total_deadline_exceeded"}
    try:
        parsed = _strict_json_loads(bytes(buf))
    except ContractError as exc:
        return {"ok": False, "kind": "contract", "reason": str(exc)}
    return {"ok": True, "status": status, "body": parsed}


def bounded_https_transport(path: str, body: bytes, *,
                            _controlled_base_url: str | None = None) -> dict:
    """Bounded HTTPS transport for the exact 0200 / receipt / feedback wire.
    Never called by default (remote_enabled defaults to False).

    enterprise-r4 B: the COMPLETE call — DNS, connect, TLS, response HEADERS
    and BODY — runs in ONE killable child process. The parent applies the
    monotonic TOTAL_TIMEOUT_SECONDS as an absolute subprocess deadline and
    terminates the child AT that deadline. Slow-drip headers can no longer
    outlive the deadline while ``opener.open`` blocks; no timeout background
    thread is left sending. This reuses the SINGLE-KILLABLE-SUBPROCESS design
    of the packaged predecessor client (strategy_client._isolated_transport)
    but is written directly for the 0200 closed paths and canonical bytes: it
    does NOT attach the old retry/compat layer and never impersonates 300/v3.

    ``_controlled_base_url`` is a PRIVATE local-verification hook: only a
    loopback HTTP target is accepted, so this development transport cannot be
    pointed at a production origin. It never changes the request body or any
    wire field. Loopback pairing evidence remains owned by the service lane.
    """
    import subprocess
    import sys
    import time

    if path not in (RESOLVE_PATH, RECEIPT_PATH, FEEDBACK_PATH):
        raise ContractError("unsupported path")
    if len(body) > MAX_REQUEST_BYTES:
        raise ContractError("request exceeds 16 KiB")
    if _controlled_base_url is not None:
        if not _loopback_controlled_base_ok(_controlled_base_url):
            raise ContractError("controlled target must be loopback HTTP")
    start = time.monotonic()
    deadline = start + TOTAL_TIMEOUT_SECONDS
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise ContractError("total_deadline_exceeded")
    envelope: dict = {"schema": "paper.client0200.transport-envelope.v1",
                      "path": path, "body_hex": body.hex(),
                      "remaining_seconds": remaining}
    if _controlled_base_url is not None:
        envelope["controlled_base_url"] = _controlled_base_url
    wire = canonical_bytes(envelope)
    command = [sys.executable, "-B", os.path.abspath(__file__),
               "_transport-worker-0200"]
    try:
        completed = subprocess.run(
            command, input=wire, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=remaining, check=False)
    except subprocess.TimeoutExpired as exc:
        # subprocess.run killed and reaped the child; no worker stays alive.
        raise ContractError("total_deadline_exceeded") from exc
    # Absolute deadline is authoritative even when the child returned in time.
    if time.monotonic() > deadline:
        raise ContractError("total_deadline_exceeded")
    if completed.returncode != 0:
        raise ContractError("transport_failure")
    result = _strict_json_loads(completed.stdout)
    if not isinstance(result, dict) or type(result.get("ok")) is not bool:
        raise ContractError("transport_failure")
    if result["ok"]:
        if (set(result) != {"ok", "status", "body"}
                or type(result["status"]) is not int):
            raise ContractError("transport_failure")
        return {"status": result["status"], "body": result["body"]}
    kind = result.get("kind")
    if kind == "http":
        code = result.get("http_status")
        raise urllib.error.HTTPError(
            BASE_URL + path, code if type(code) is int else 500,
            f"http rejection {code}", {}, None)
    if kind == "contract":
        raise ContractError(str(result.get("reason") or "transport_failure"))
    if kind == "transport":
        # A DNS/TLS/connect/timeout failure is unknown, never a confirmed send.
        raise ContractError("total_deadline_exceeded"
                            if result.get("reason") in ("TimeoutError", "timed out")
                            else "transport_failure")
    raise ContractError("transport_failure")


class Client0200:
    """One-shot, consent-first, durable, recovery-safe client."""

    def __init__(self, project_dir: str | Path, *, remote_enabled: bool = False,
                 feedback_enabled: bool = False,
                 transport: Callable[[str, bytes], dict] | None = None,
                 clock: Callable[[], float | None] | None = None) -> None:
        self.project_dir = Path(project_dir).resolve()
        self.remote_enabled = bool(remote_enabled)
        self.feedback_enabled = bool(feedback_enabled)
        self.transport = transport
        self.clock = clock or (lambda: datetime.now(timezone.utc).timestamp())
        self.resolve_calls = 0
        self.feedback_calls = 0
        self.receipt_query_calls = 0
        self.network_calls = 0
        self.send_started = False
        self.prepared = None
        self.action_ledger: dict[str, dict] = {}
        self.feedback_eligible = False
        self.feedback_eligibility_source = None
        self.decision_from_receipt = False
        self._restored = False
        # Monotonic wall-clock floor: a decision already observed unusable at a
        # LATER now must never become usable again when the clock rolls back.
        self._clock_floor = None
        # op -> expires_at of decisions whose expiry was OBSERVED (persisted).
        self._observed_expired: dict[str, float] = {}
        # Decision verified IN THIS PROCESS (never restored-from-receipt):
        # the only basis for the explicit v2 feedback entry.
        self._verified_decision = None

    # ---- durable immutable event journal -----------------------------------
    def _strategy_dir(self) -> Path:
        d = self.project_dir / "strategy"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _exclusive_event(self, name: str, payload: dict) -> bool:
        """Exclusive creation; never truncates a competing record."""
        path = self._strategy_dir() / name
        data = (json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        try:
            fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            with os.fdopen(fd, "wb") as fh:
                fh.write(data)
                fh.flush()
                os.fsync(fh.fileno())
            return True
        except FileExistsError:
            return False  # an existing event wins; never overwrite/truncate

    def _read_events(self, op: str) -> list[dict]:
        d = self._strategy_dir()
        out = []
        for p in sorted(d.glob(f"event-{op}-*.json")):
            out.append(json.loads(p.read_text(encoding="utf-8")))
        return out

    def _persist_action(self, op: str, seq: int, state: str, **extra) -> bool:
        return self._exclusive_event(
            f"event-{op}-{seq:03d}-{state}.json",
            {"schema": "paper.strategy-action-event.v1", "version": VERSION,
             "operation_id": op, "state": state, "budget_spent": 1 if seq else 0,
             **extra})

    # ---- 1. persist first, then send ----------------------------------------
    def prepare(self, intent: dict, *, intent_revision: int, evidence_revision: int,
                contract_source: str = "SERVICE-CLIENT-CONTRACT.json#local-01-r1") -> dict:
        try:
            check = validate_wire(intent)
        except ContractError as exc:
            return {"state": "input_invalid", "reason": str(exc),
                    "network_calls": self.network_calls, "send_permitted": False,
                    "native_continue": True}
        op = intent["request_id"]
        raw = canonical_bytes(intent)
        # Directory creation is part of persistence: any failure here must also
        # produce ZERO network calls (an illegal path raises ValueError).
        try:
            target = self._strategy_dir() / f"pending-{op}.json"
        except Exception as exc:
            return {"schema": "paper.strategy-pending.v1", "version": VERSION,
                    "state": "save_failed", "network_calls": self.network_calls,
                    "send_permitted": False, "reason": type(exc).__name__,
                    "note": "保存目录创建失败时零网络；不凭缺响应断言没有发送"}
        record = {
            "schema": "paper.strategy-pending.v1", "version": VERSION,
            "operation_id": op, "request_id": op,
            "canonical_bytes_len": len(raw), "request_digest": check["request_digest"],
            "canonical_hex": raw.hex(),
            "intent_revision": intent_revision, "evidence_revision": evidence_revision,
            "consumer": {"product": PRODUCT, "version": VERSION},
            "contract_source": contract_source,
            "send_started": False, "state": "prepared_no_send",
        }
        try:
            ok = self._exclusive_event(target.name, record)
            if not ok:
                return {"state": "save_failed", "reason": "pending_record_already_exists",
                        "network_calls": self.network_calls, "send_permitted": False,
                        "native_continue": True,
                        "note": "排他创建失败时不覆盖原记录；零发送"}
        except Exception as exc:
            return {"schema": "paper.strategy-pending.v1", "version": VERSION,
                    "state": "save_failed", "network_calls": self.network_calls,
                    "send_permitted": False, "reason": type(exc).__name__,
                    "note": "保存失败时网络调用必须为零"}
        rb = json.loads(target.read_text(encoding="utf-8"))
        if bytes.fromhex(rb["canonical_hex"]) != raw:
            return {"state": "save_readback_mismatch", "network_calls": self.network_calls,
                    "send_permitted": False}
        self.prepared = {"record": record, "path": target, "raw": raw, "check": check}
        self._persist_action(op, 0, "prepared")
        self.action_ledger[op] = {"state": "prepared", "budget_spent": 0,
                                  "local_work_allowed": False}
        return {"state": "prepared", "operation_id": op,
                "request_digest": check["request_digest"],
                "canonical_bytes": len(raw), "persisted_path": str(target).replace("\\", "/"),
                "readback_verified": True, "network_calls": self.network_calls,
                "native_continue": True}

    # ---- read-only restore by ORIGINAL id (cross-process) ------------------
    def restore(self, operation_id: str) -> dict:
        """Fresh process reopens the ORIGINAL pending record and action events.

        Read-only. Never re-resolves, never creates a new id, never replays.

        The persisted record, its canonical wire, the filename and the events
        must agree on the ORIGINAL operation identity: rec.operation_id ==
        rec.request_id == requested id == filename id == embedded wire
        request_id; the embedded consumer/schema/revisions must match the
        record; the digest must cover the exact canonical bytes. Any mismatch
        (e.g. an edited outer record with a substituted operation_id) is
        refused BEFORE this instance can query with a wrong id; the record on
        disk is never modified by a refusal.
        """
        try:
            target = self._strategy_dir() / f"pending-{operation_id}.json"
        except Exception as exc:
            return {"state": "save_failed", "restored": False, "network_calls": 0,
                    "reason": type(exc).__name__}
        if not target.is_file():
            return {"state": "unknown", "restored": False, "network_calls": 0,
                    "note": "缺原号记录保持 unknown；不换号重做"}
        try:
            rec = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            return {"state": "unknown", "restored": False, "network_calls": 0,
                    "reason": f"record_unreadable:{type(exc).__name__}"}
        if not isinstance(rec, dict):
            return {"state": "refused", "restored": False,
                    "reason": "record_not_object"}
        try:
            rec_version = rec.get("version")
            if (rec.get("schema") != "paper.strategy-pending.v1"
                    or rec_version not in (VERSION, LEGACY_VERSION_0200)):
                return {"state": "refused", "restored": False,
                        "reason": "record_schema_version_mismatch"}
            if rec_version == LEGACY_VERSION_0200:
                # Bounded legacy boundary (version 2026.11.5): a legal old
                # 0200 pending record (outer record AND wire consumer both at
                # the original 2026.11.0200) is preserved AS-IS — original
                # consumer, UUID, digest and canonical bytes. It is never
                # re-labelled as the new version, never given a new digest
                # and never re-sent by this client. Read-only receipt
                # queries for it must use the preserved old-version client
                # path. Refusal happens BEFORE any event processing or
                # network call; the record on disk is never modified.
                return {"state": "refused", "restored": False,
                        "network_calls": 0,
                        "reason": "legacy_0200_pending_preserved_readonly",
                        "legacy_version": LEGACY_VERSION_0200,
                        "note": "旧 0200 pending 原样保留（原 consumer/原号/原摘要/原字节）；"
                                "不改写为新版 consumer 或新 digest、不重发；"
                                "只读回执查询请使用保留的 0200 版客户端路径"}
            if (rec.get("operation_id") != operation_id
                    or rec.get("request_id") != operation_id):
                return {"state": "refused", "restored": False,
                        "reason": "record_operation_identity_mismatch",
                        "note": "外层改号不授予新身份；拒绝且不改记录、不按错误号查询"}
            if not _is_uuid(operation_id):
                return {"state": "refused", "restored": False,
                        "reason": "operation_id_not_uuid"}
            raw = bytes.fromhex(rec["canonical_hex"])
            if hashlib.sha256(raw).hexdigest() != rec.get("request_digest"):
                return {"state": "unknown", "restored": False,
                        "reason": "persisted_canonical_digest_mismatch"}
            wire = json.loads(raw.decode("utf-8"))
            if not isinstance(wire, dict):
                return {"state": "refused", "restored": False,
                        "reason": "canonical_wire_not_object"}
            if wire.get("schema") != RESOLVE_SCHEMA:
                return {"state": "refused", "restored": False,
                        "reason": "wire_schema_mismatch"}
            if wire.get("request_id") != operation_id:
                return {"state": "refused", "restored": False,
                        "reason": "wire_request_id_mismatch"}
            if wire.get("consumer") != {"product": PRODUCT, "version": VERSION}:
                # A NEW outer record version with an OLD wire consumer (or any
                # other mismatch) is cross-version splicing: neither client
                # generation ever wrote it. Genuine old records were already
                # handled read-only at the outer record version check above.
                return {"state": "refused", "restored": False,
                        "reason": "wire_consumer_mismatch",
                        "note": "外层与 wire consumer 版本不一致视为跨版本拼接；"
                                "拒绝且零写、不重发"}
            if (wire.get("intent_revision") != rec.get("intent_revision")
                    or wire.get("evidence_revision") != rec.get("evidence_revision")):
                return {"state": "refused", "restored": False,
                        "reason": "record_revision_binding_mismatch"}
            if rec.get("canonical_bytes_len") != len(raw):
                return {"state": "refused", "restored": False,
                        "reason": "canonical_length_mismatch"}
            if request_digest(wire) != rec.get("request_digest"):
                return {"state": "refused", "restored": False,
                        "reason": "canonical_wire_digest_mismatch"}
        except (KeyError, TypeError, ValueError, UnicodeDecodeError) as exc:
            return {"state": "refused", "restored": False,
                    "reason": f"record malformed: {type(exc).__name__}"}
        events = self._read_events(operation_id)
        for e in events:
            if not isinstance(e, dict) or e.get("operation_id") != operation_id:
                return {"state": "refused", "restored": False,
                        "reason": "event_identity_mismatch",
                        "note": "事件原号与请求原号不符；拒绝恢复"}
        # Persisted observed-expiry / clock-floor state survives restart.
        for e in events:
            if e.get("state") == "expired_rejected" and _finite_number(e.get("expires_at")):
                self._observed_expired[operation_id] = e["expires_at"]
                if _finite_number(e.get("observed_now")):
                    self._clock_floor = (max(self._clock_floor, e["observed_now"])
                                         if self._clock_floor is not None else e["observed_now"])
        self.prepared = {"record": rec, "path": target, "raw": raw,
                         "check": {"request_digest": rec["request_digest"],
                                   "canonical_bytes": len(raw)}}
        self.send_started = any(e.get("state") in ("send_started", "completed", "unknown")
                                for e in events) or bool(rec.get("send_started"))
        state = "prepared"
        for e in events:
            if e.get("state") in ("completed", "unknown", "recovered", "started", "send_started"):
                state = e["state"]
        self.action_ledger[operation_id] = {"state": state, "budget_spent": len(events),
                                            "local_work_allowed": False}
        # A restored operation is NEVER eligible for a new resolve.
        self.resolve_calls = 1 if self.send_started else 0
        self._restored = True
        self.decision_from_receipt = True
        self.feedback_eligible = False
        self.feedback_eligibility_source = None
        return {"state": "restored", "restored": True, "operation_id": operation_id,
                "send_started": self.send_started, "action_state": state,
                "events": len(events), "resolve_resend_permitted": False,
                "new_id_created": False, "replay_permitted": False,
                "network_calls": 0, "read_only": True,
                "identity_binding": {"record_request_file_event_agree": True,
                                     "consumer_schema_revisions_digest_bound": True},
                "note": "中断后仅按原号只读重开；不重新 resolve、不恢复反馈资格"}

    # ---- unified default-off gate ------------------------------------------
    def _gate(self, purpose: str) -> dict | None:
        if not self.remote_enabled:
            return {"state": "remote_disabled", "purpose": purpose,
                    "network_calls": self.network_calls, "retry_permitted": False,
                    "native_continue": True,
                    "note": "所有远端出口（含查询与反馈）默认关闭；本地恢复不联网"}
        if self.transport is None:
            return {"state": "transport_unavailable", "purpose": purpose,
                    "network_calls": self.network_calls, "retry_permitted": False,
                    "native_continue": True,
                    "note": "无真实 transport，不宣称线上通过"}
        return None

    # ---- 2. exactly one resolve --------------------------------------------
    def resolve_once(self) -> dict:
        if self.prepared is None:
            return {"state": "not_prepared", "network_calls": self.network_calls,
                    "native_continue": True, "note": "未先保存不发；保存失败零网络"}
        if self.resolve_calls >= 1 or self._restored:
            return {"state": "resolve_already_attempted_or_restored",
                    "network_calls": self.network_calls, "retry_permitted": False,
                    "native_continue": True,
                    "note": "0200 关闭旧客户端同号自动 resolve 重试；恢复实例不重发"}
        gate = self._gate("resolve")
        if gate:
            return gate
        op = self.prepared["record"]["operation_id"]
        # Persist send_started BEFORE transport; failure means ZERO calls.
        if not self._persist_action(op, 1, "send_started"):
            return {"state": "save_failed", "network_calls": self.network_calls,
                    "retry_permitted": False, "native_continue": True,
                    "note": "发送前状态持久化失败=>零网络；记录转换排他且不可变"}
        self.send_started = True
        self.action_ledger[op] = {"state": "started", "budget_spent": 1,
                                  "local_work_allowed": False}
        self.resolve_calls += 1
        self.network_calls += 1
        try:
            response = self.transport(RESOLVE_PATH, self.prepared["raw"])
        except urllib.error.HTTPError as exc:
            # A KNOWN HTTP status is preserved together with a safe error
            # category. Nothing is inferred about whether the business side
            # recorded the request; the state stays unknown under the ORIGINAL
            # id, resolve is never auto-resent, and the raw exception body,
            # URL or credentials are never echoed.
            code = exc.code if isinstance(getattr(exc, "code", None), int) else None
            if code is None:
                reason = "http_error"
            elif 300 <= code < 400:
                reason = f"http_{code}_redirect_refused"
            elif 400 <= code < 500:
                reason = f"http_{code}_client_error"
            elif 500 <= code < 600:
                reason = f"http_{code}_server_error"
            else:
                reason = f"http_{code}_http_error"
            self._persist_action(op, 2, "unknown", reason=reason,
                                 http_status=code)
            self.action_ledger[op]["state"] = "unknown"
            return {"state": "unknown", "reason": reason, "http_status": code,
                    "network_calls": self.network_calls, "retry_permitted": False,
                    "native_continue": True,
                    "note": "已知 HTTP 状态按原号 unknown；不重发、不换号、不从状态码推断业务落库；"
                            "不输出原始异常正文/URL/凭据"}
        except Exception as exc:
            self._persist_action(op, 2, "unknown", reason=type(exc).__name__)
            self.action_ledger[op]["state"] = "unknown"
            return {"state": "unknown", "reason": type(exc).__name__,
                    "network_calls": self.network_calls, "retry_permitted": False,
                    "native_continue": True,
                    "note": "响应未知只按原号查 receipt；不重发、不换号、不沿旧诊断码自动重试"}
        if not isinstance(response, dict):
            self._persist_action(op, 2, "unknown", reason="invalid_response_shape")
            self.action_ledger[op]["state"] = "unknown"
            return {"state": "unknown", "reason": "invalid_response_shape",
                    "network_calls": self.network_calls, "retry_permitted": False,
                    "native_continue": True}
        self._persist_action(op, 2, "completed")
        self.action_ledger[op]["state"] = "completed"
        # enterprise-r4 C (FB01): a NORMAL resolve that returned a verified
        # selected decision durably binds the COMPLETE original decision
        # (exclusive + read back) BEFORE any later feedback attempt can
        # depend on an in-process memory copy alone.
        if self._verify_decision_for_feedback(response) is not None:
            self._persist_verified_decision_binding(response)
        return {"state": "response_received", "response": response,
                "network_calls": self.network_calls, "native_continue": True}

    # ---- receipt query: closed wire + separate local metadata --------------
    def query_receipt(self) -> dict:
        if self.prepared is None:
            return self._local_envelope({"state": "unknown", "writes": 0,
                                         "reason": "not_prepared"})
        gate = self._gate("receipt_query")
        if gate:
            return self._local_envelope({**gate, "writes": 0})
        op = self.prepared["record"]["operation_id"]
        digest = self.prepared["check"]["request_digest"]
        query = {"schema": RECEIPT_QUERY_SCHEMA,
                 "consumer": {"product": PRODUCT, "version": VERSION},
                 "request_id": op, "request_digest": digest}
        self.receipt_query_calls += 1
        self.network_calls += 1
        try:
            result = self.transport(RECEIPT_PATH, canonical_bytes(query))
        except Exception as exc:
            return self._local_envelope({"state": "unknown", "reason": type(exc).__name__})
        if not isinstance(result, dict):
            return self._local_envelope({"state": "unknown", "reason": "invalid_receipt_shape"})
        body = result.get("body", result) if "body" in result else result
        body = body.get("body", body) if isinstance(body, dict) and "body" in body else body
        # The server envelope stays CLOSED: no local keys are injected.
        wire = dict(body) if isinstance(body, dict) else None
        return {"wire_receipt": wire,
                "local": {"schema": "paper.strategy-receipt-query.local.v1",
                          "operation_id": op, "writes": 0, "new_id_created": False,
                          "replay_permitted": False, "resolve_retry_permitted": False,
                          "query_is_read_only": True,
                          "note": "wire 七字段封套与本地元数据分离；外层/内层校验消费原封套"}}

    def _local_envelope(self, extra: dict) -> dict:
        return {"wire_receipt": None,
                "local": {"schema": "paper.strategy-receipt-query.local.v1",
                          "writes": 0, "new_id_created": False,
                          "replay_permitted": False, "resolve_retry_permitted": False,
                          "query_is_read_only": True, **extra}}

    def query_and_validate(self, *, local: dict | None = None) -> dict:
        """Public query->validate flow; consumes the ORIGINAL closed envelope."""
        q = self.query_receipt()
        wire = q.get("wire_receipt")
        if not isinstance(wire, dict):
            return {"validated": False, "executable": False, "state": "unknown",
                    "reason": (q.get("local") or {}).get("state", "no_wire_receipt"),
                    "native_continue": True, "wire_fields_closed": None,
                    "local": q.get("local")}
        v = self.validate_receipt(wire, local=local)
        return {**v, "local": q["local"], "wire_fields_closed":
                set(wire) == RECEIPT_RESULT_FIELDS}

    # ---- 3/4. two-layer validation -----------------------------------------
    def _compat_request(self) -> dict:
        """Validation-only projection of the PERSISTED original request.

        The consumer field is swapped for the legacy validator's expectations.
        This copy is never persisted and never transmitted; the real 0200 wire
        object stays untouched.
        """
        original = json.loads(bytes.fromhex(
            self.prepared["record"]["canonical_hex"]).decode("utf-8"))
        compat = json.loads(json.dumps(original))
        compat["consumer"] = {"product": v1.PRODUCT, "version": v1.VERSION}
        return compat

    def _validate_decision_with_request(self, decision: dict) -> None:
        """Complete v2 response validation bound to the ORIGINAL request.

        The compat projections (request consumer + the decision's
        request_digest field) exist ONLY for the legacy validator; the exact
        0200 digest binding is enforced separately and FIRST (receipt digest
        and inner digest must equal the 0200 canonical digest).
        """
        compat_req = self._compat_request()
        compat_dec = json.loads(json.dumps(decision))
        compat_dec["request_digest"] = v1.digest(compat_req)
        validate_decision_shape(compat_dec, request=compat_req)

    def validate_receipt(self, receipt: dict, *, local: dict | None = None) -> dict:
        local = local or {}
        if self.prepared is None:
            raise ContractError("no prepared operation to bind")
        expected_id = self.prepared["record"]["operation_id"]
        expected_digest = self.prepared["check"]["request_digest"]
        if not isinstance(receipt, dict) or set(receipt) != RECEIPT_RESULT_FIELDS:
            return self._refuse("receipt_fields_not_closed")
        if receipt["schema"] != RECEIPT_RESULT_SCHEMA:
            return self._refuse("receipt_schema_mismatch")
        if receipt["request_id"] != expected_id:
            return self._refuse("request_id_mismatch")
        if receipt["request_digest"] != expected_digest:
            return self._refuse("same_uuid_different_digest")
        for key in ("executable", "retry_permitted"):
            if type(receipt[key]) is not bool:
                return self._refuse(f"{key}_not_real_boolean")
        if receipt["retry_permitted"] is not False:
            return self._refuse("retry_must_be_false")
        state = receipt["state"]
        if state not in RECEIPT_STATES:
            return self._refuse("state_not_in_enum")
        if state == "unknown":
            if receipt["response"] is not None or receipt["executable"] is not False:
                return self._refuse("unknown_state_combination_invalid")
            return self._refuse("unknown_no_replay", state="unknown")
        if not isinstance(receipt["response"], dict):
            return self._refuse("non_unknown_state_needs_original_response")
        if state in ("expired", "catalog_changed"):
            if receipt["executable"] is not False:
                return self._refuse("expired_or_catalog_changed_must_not_execute")
            return {"validated": True, "executable": False, "state": state,
                    "reason": "readable_but_not_executable", "native_continue": True}
        # state == recorded -> COMPLETE v2 response validation WITH the
        # persisted ORIGINAL request (scope/selection/digest/revisions/budget).
        try:
            self._validate_decision_with_request(receipt["response"])
        except ContractError as exc:
            return self._refuse(str(exc))
        inner = self._bind_decision(receipt["response"], expected_id,
                                    expected_digest, local)
        if not inner["valid"]:
            return self._refuse(inner["reason"])
        # enterprise-r4 C (FB01): once the receipt decision passes the FULL
        # v2 validation + binding for THIS original request, the durable
        # verified-decision binding is persisted BEFORE any later early exit
        # (timing, action state, recovery collision) can drop it.
        if inner["status"] == "selected":
            self._persist_verified_decision_binding(receipt["response"])
        op = expected_id
        timing = self._recovery_timing(receipt["response"], op)
        if not timing["usable"]:
            if timing["reason"] in ("exactly_or_past_expiry", "clock_regression",
                                    "expiry_already_observed_permanent"):
                self._persist_observed_expiry(op, receipt["response"], self.clock()
                                              if _finite_number(self.clock()) else 0.0)
            return {"validated": True, "executable": False, "state": "recorded",
                    "reason": timing["reason"], "timing": timing, "native_continue": True,
                    "note": "已观测过期/时钟回退对该原决定永久不可执行；不刷新签发或寿命"}
        # DURABLE action state is authoritative: reread events from disk so a
        # stale in-memory instance cannot authorize over a newer durable state.
        events = self._read_events(op)
        durable = {"prepared", "started", "send_started", "unknown", "completed", "recovered"}
        durable_state = None
        for e in events:
            if isinstance(e, dict) and e.get("state") in durable:
                durable_state = e["state"]
        action = self.action_ledger.get(op)
        if action is None:
            action = {"state": durable_state or "unknown",
                      "budget_spent": len(events), "local_work_allowed": False}
            self.action_ledger[op] = action
        if action["state"] in ("completed", "unknown", "recovered") or durable_state in (
                "completed", "unknown", "recovered"):
            return {"validated": True, "executable": False, "state": "recorded",
                    "reason": "local_action_already_" + (
                        durable_state or action["state"]),
                    "local_action": action, "native_continue": True,
                    "note": "重复读 receipt 不重做已完成/结果未知/已恢复的动作"}
        if inner["status"] != "selected":
            return {"validated": True, "executable": False, "state": "recorded",
                    "reason": "non_selected_decision_not_executed", "native_continue": True}
        if receipt["executable"] is not True:
            return {"validated": True, "executable": False, "state": "recorded",
                    "reason": "executable_flag_false", "native_continue": True}
        # R2-03: execution permission requires the EXCLUSIVE durable recovered
        # event to be successfully created AND read back. A collision means
        # another instance already transitioned; this instance stays
        # non-executable. A no-write same-id query can never upgrade into a
        # second execution permission.
        persisted = self._persist_action(op, 3, "recovered")
        if not persisted:
            ev = self._read_events(op)
            recovered_by_other = any(
                isinstance(e, dict) and e.get("state") == "recovered" and
                e.get("operation_id") == op for e in ev)
            self.action_ledger[op] = {"state": "recovered", "budget_spent": len(ev),
                                      "local_work_allowed": False,
                                      "recovered_by": "other_instance_or_unreadable"}
            return {"validated": True, "executable": False, "state": "recorded",
                    "reason": ("recovered_event_collision_not_executable"
                               if recovered_by_other else "recovered_event_persist_failed"),
                    "local_action": self.action_ledger[op], "native_continue": True,
                    "retry_permitted": False, "replay_permitted": False,
                    "note": "排他持久事件未落盘/碰撞即不授权执行；保持unknown约束、不重发"}
        # Read back the durable transition before granting permission.
        event_path = self._strategy_dir() / f"event-{op}-003-recovered.json"
        try:
            rb = json.loads(event_path.read_text(encoding="utf-8"))
            if not (isinstance(rb, dict) and rb.get("operation_id") == op
                    and rb.get("state") == "recovered"):
                return {"validated": True, "executable": False, "state": "recorded",
                        "reason": "recovered_event_readback_invalid",
                        "native_continue": True, "retry_permitted": False}
        except (OSError, ValueError):
            return {"validated": True, "executable": False, "state": "recorded",
                    "reason": "recovered_event_readback_unreadable",
                    "native_continue": True, "retry_permitted": False}
        self.action_ledger[op] = {"state": "recovered", "budget_spent": action["budget_spent"],
                                  "local_work_allowed": True, "recovered_once": True}
        # A receipt read in a RESTORED process never restores feedback
        # eligibility; only a decision verified in THIS process does.
        self._verified_decision = receipt["response"] if not self._restored else None
        return {"validated": True, "executable": True, "state": "recorded",
                "decision": receipt["response"], "timing": timing,
                "local_action": self.action_ledger[op], "native_continue": True,
                "note": "完整 v2 语义（带原请求）+ 当前能力/预算/轨道绑定 + 排他持久恢复事件已落盘读回；"
                        "重复读不再可执行"}

    def _bind_decision(self, d: dict, expected_id: str, expected_digest: str,
                       local: dict) -> dict:
        """Exact binding against the immutable original request and MANDATORY
        CURRENT local context; the complete v2 shape was already validated
        above WITH the original request (scope/selection/digest semantics).

        The current local context is REQUIRED: intent/evidence revisions, a
        non-empty closed capability subset, and a CURRENT cap for EVERY budget
        key. A missing current cap is unknown, and unknown is never infinity:
        the plan must be re-decided, not silently executed under the original
        request budget. Spent budget, when supplied, is subtracted from the cap.
        """
        if d["request_id"] != expected_id or d["request_digest"] != expected_digest:
            return {"valid": False, "reason": "inner_binding_mismatch"}
        status = d["status"]
        rec = self.prepared["record"]
        if d["intent_revision"] != rec["intent_revision"]:
            return {"valid": False, "reason": "intent_revision_mismatch"}
        if d["evidence_revision"] != rec["evidence_revision"]:
            return {"valid": False, "reason": "evidence_revision_mismatch"}
        # MANDATORY current local state (never a fallback to original caps).
        for key in ("intent_revision", "evidence_revision", "capabilities"):
            if local.get(key) is None:
                return {"valid": False, "reason": f"local_context_required:{key}"}
        if local["intent_revision"] != d["intent_revision"]:
            return {"valid": False, "reason": "local_intent_revision_changed"}
        if local["evidence_revision"] != d["evidence_revision"]:
            return {"valid": False, "reason": "local_evidence_revision_changed"}
        current_caps = local["capabilities"]
        if (not isinstance(current_caps, list) or not current_caps
                or any(c not in ALLOWED_CAPABILITIES for c in current_caps)
                or len(set(current_caps)) != len(current_caps)):
            return {"valid": False, "reason": "no_valid_current_capability"}
        current_caps = set(current_caps)
        # Original request budget/capability binding (never a weak subset).
        original = json.loads(bytes.fromhex(rec["canonical_hex"]).decode("utf-8"))
        orig_budget = original["budget"]
        if status != "selected":
            if d["strategy"] is not None or d["plan"] is not None or d["track"] is not None:
                return {"valid": False, "reason": "non_selected_must_have_null_plan"}
            return {"valid": True, "status": status}
        plan = d["plan"]
        plan_budget = plan["budget"]
        # CURRENT budget caps may be supplied flat (max_queries=..., etc.) or
        # as an explicit budget_caps object; both are merged. A key with NO
        # current cap is unknown, and unknown is never infinity.
        caps_local = local.get("budget_caps")
        if caps_local is None:
            caps_local = {}
        if not isinstance(caps_local, dict):
            return {"valid": False, "reason": "local_budget_caps_invalid"}
        merged_caps = {}
        for key in BUDGET_KEYS:
            if key in caps_local:
                merged_caps[key] = caps_local[key]
            elif key in local:
                merged_caps[key] = local[key]
        unknown_keys = [k for k in BUDGET_KEYS if k not in merged_caps]
        spent = local.get("budget_spent", {})
        if not isinstance(spent, dict):
            return {"valid": False, "reason": "local_budget_spent_invalid"}
        # Bind every key that HAS a current cap first: budget 0 IS 0.
        for key in BUDGET_KEYS:
            if key not in merged_caps:
                continue
            if type(plan_budget[key]) is not int or plan_budget[key] < 0:
                return {"valid": False, "reason": "plan_budget_invalid"}
            if plan_budget[key] > orig_budget[key]:
                return {"valid": False, "reason": "plan_budget_exceeds_original_request"}
            cap = merged_caps[key]
            if type(cap) is not int or cap < 0:
                return {"valid": False, "reason": f"local_cap_invalid:{key}"}
            already = spent.get(key, 0)
            if type(already) is not int or already < 0:
                return {"valid": False, "reason": f"local_spent_invalid:{key}"}
            # Plan usage plus already-spent must fit the CURRENT cap.
            if plan_budget[key] + already > cap:
                return {"valid": False, "reason": "budget_exceeds_current_local_cap",
                        "key": key, "plan": plan_budget[key], "spent": already, "cap": cap}
        if unknown_keys:
            return {"valid": False, "reason": "local_budget_caps_required_all_keys",
                    "missing": sorted(unknown_keys)}
        for key in BUDGET_KEYS:
            if type(plan_budget[key]) is not int or plan_budget[key] < 0:
                return {"valid": False, "reason": "plan_budget_invalid"}
            if plan_budget[key] > orig_budget[key]:
                return {"valid": False, "reason": "plan_budget_exceeds_original_request"}
        # A plan that needs search/read cannot run without those capabilities.
        if plan.get("query_axes") and "web_search" not in current_caps:
            return {"valid": False, "reason": "search_capability_unavailable"}
        if plan.get("source_classes") and "page_read" not in current_caps:
            return {"valid": False, "reason": "read_capability_unavailable"}
        if not d["candidates"] or not d["track_evaluations"]:
            return {"valid": False, "reason": "candidates_or_track_evaluations_missing"}
        track = d["track"]
        eligible = {e["id"] for e in d["track_evaluations"] if e["eligible"]}
        if track["id"] not in eligible or track["id"] not in {c["id"] for c in d["candidates"]}:
            return {"valid": False, "reason": "selected_track_not_eligible_or_not_candidate"}
        return {"valid": True, "status": status}

    def _persist_observed_expiry(self, op: str, d: dict, now: float) -> None:
        """Persist the OBSERVED expiry for the original decision id.

        An expiry once observed stays non-executable for that decision even
        after a wall-clock rollback or a process restart. The event is
        exclusive; a competing record wins and is never truncated.
        """
        try:
            self._exclusive_event(
                f"event-{op}-expired-rejected.json",
                {"schema": "paper.strategy-action-event.v1", "version": VERSION,
                 "operation_id": op, "state": "expired_rejected",
                 "expires_at": d["expires_at"], "observed_now": now,
                 "budget_spent": 0})
        except OSError:
            pass  # persistence failure is conservative: in-memory floor still applies
        self._observed_expired[op] = d["expires_at"]

    def _recovery_timing(self, d: dict, op: str | None = None) -> dict:
        """Finite, ordered, bounded timestamps; observed expiry is FINAL.

        Guards, in order:
        * clock must be finite;
        * in-process monotonic floor: `now` may never go backwards for decision
          usability (a rollback after an unusable observation cannot revive it);
        * an expiry OBSERVED for this original id (in memory or persisted) is
          permanently unusable regardless of the current clock reading;
        * lifetime was never refreshed; issued/expires stay original.
        """
        now = self.clock()
        if not _finite_number(now):
            return {"usable": False, "reason": "clock_untrusted"}
        if self._clock_floor is not None and now < self._clock_floor:
            return {"usable": False, "reason": "clock_regression",
                    "floor": self._clock_floor, "now": now}
        if _finite_number(now):
            self._clock_floor = now if self._clock_floor is None else max(self._clock_floor, now)
        if op is not None and op in self._observed_expired:
            return {"usable": False, "reason": "expiry_already_observed_permanent",
                    "expires_at": self._observed_expired[op]}
        issued, expires = d["issued_at"], d["expires_at"]
        if not (_finite_number(issued) and _finite_number(expires)):
            return {"usable": False, "reason": "non_finite_or_boolean_timestamp"}
        if issued >= expires:
            return {"usable": False, "reason": "reversed_lifetime"}
        if expires - issued > DECISION_LIFETIME_SECONDS:
            return {"usable": False, "reason": "lifetime_was_refreshed"}
        if now < issued - MAX_FUTURE_SKEW_SECONDS:
            return {"usable": False, "reason": "future_issued_beyond_skew"}
        if now >= expires:
            return {"usable": False, "reason": "exactly_or_past_expiry",
                    "age_seconds": now - issued}
        return {"usable": True, "issued_at": issued, "expires_at": expires,
                "age_seconds": now - issued, "age_over_30s_allowed": (now - issued) > 30,
                "lifetime_refreshed": False,
                "monotonic_floor": self._clock_floor,
                "reason": "within_original_lifetime"}

    def fresh_response_timing(self, d: dict) -> dict:
        """Separate path for a brand-new response: issued_at must be recent
        (<=30s old). Recovery NEVER uses this check."""
        now = self.clock()
        if not (_finite_number(now) and _finite_number(d.get("issued_at"))
                and _finite_number(d.get("expires_at"))):
            return {"usable": False, "reason": "non_finite_or_clock_untrusted"}
        age = now - d["issued_at"]
        if age < -MAX_FUTURE_SKEW_SECONDS:
            return {"usable": False, "reason": "future_issued"}
        if age > 30.0:
            return {"usable": False, "reason": "fresh_response_older_than_30s"}
        if d["expires_at"] <= now:
            return {"usable": False, "reason": "exactly_or_past_expiry"}
        return {"usable": True, "age_seconds": age,
                "note": "新响应 30 秒签发路径；恢复路径恒定不刷新寿命"}

    def _refuse(self, reason: str, *, state: str | None = None) -> dict:
        return {"validated": False, "executable": False, "state": state or "unknown",
                "reason": reason, "native_continue": True, "retry_permitted": False,
                "new_id_created": False, "replay_permitted": False}

    # ---- 7. feedback: honest, not simulated --------------------------------
    # ---- enterprise-r4 C: durable verified-decision binding (FB01/FB04) ----
    def _binding_path(self, op: str) -> Path:
        # Deliberately NOT event-* prefixed: the action-event glob in
        # _read_events/restore must stay untouched (r3 named passes bind it).
        return self._strategy_dir() / f"decision-{op}-verified.json"

    def _original_request(self) -> dict:
        return json.loads(bytes.fromhex(
            self.prepared["record"]["canonical_hex"]).decode("utf-8"))

    def _verify_decision_for_feedback(self, decision) -> dict | None:
        """FULL verification of a decision as the feedback basis: the COMPLETE
        v2 response validator bound to the persisted ORIGINAL request, plus the
        exact 0200 digest/id binding and a SELECTED plan with integer budget
        caps. Returns the verified decision object or None; never raises."""
        if self.prepared is None or not isinstance(decision, dict):
            return None
        try:
            op = self.prepared["record"]["operation_id"]
            digest = self.prepared["check"]["request_digest"]
            if decision.get("schema") != DECISION_SCHEMA:
                return None
            if decision.get("request_id") != op:
                return None
            if decision.get("request_digest") != digest:
                return None
            if decision.get("status") != "selected":
                return None
            plan = decision.get("plan")
            if not isinstance(plan, dict) or not isinstance(plan.get("budget"), dict):
                return None
            for key in BUDGET_KEYS:
                cap = plan["budget"].get(key)
                if type(cap) is not int or cap < 0:
                    return None
            self._validate_decision_with_request(decision)
        except Exception:
            return None
        return decision

    def _persist_verified_decision_binding(self, decision) -> bool:
        """FB01: EXCLUSIVELY persist the binding of the COMPLETE verified
        original decision to this operation and READ IT BACK. The record
        carries the original request canonical bytes, its digest and the full
        decision object; nothing is ever overwritten. Returns True only when
        the durable copy matches byte-for-byte semantics."""
        if self.prepared is None or not isinstance(decision, dict):
            return False
        op = self.prepared["record"]["operation_id"]
        record = {
            "schema": VERIFIED_DECISION_SCHEMA, "version": VERSION,
            "operation_id": op, "request_id": op,
            "request_digest": self.prepared["check"]["request_digest"],
            "canonical_hex": self.prepared["raw"].hex(),
            "decision": decision,
        }
        payload = (json.dumps(record, ensure_ascii=False, sort_keys=True,
                              allow_nan=False) + "\n").encode("utf-8")
        path = self._binding_path(op)
        try:
            fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            with os.fdopen(fd, "wb") as fh:
                fh.write(payload)
                fh.flush()
                os.fsync(fh.fileno())
        except (FileExistsError, OSError):
            return False
        try:
            rb = json.loads(path.read_text(encoding="utf-8"))
            if (isinstance(rb, dict)
                    and rb.get("schema") == VERIFIED_DECISION_SCHEMA
                    and rb.get("operation_id") == op
                    and rb.get("request_digest") == self.prepared["check"]["request_digest"]
                    and rb.get("canonical_hex") == record["canonical_hex"]
                    and rb.get("decision") == decision):
                return True
        except (OSError, ValueError):
            pass
        return False

    def _load_verified_decision_binding(self) -> dict | None:
        """FB04: reload and FULLY re-verify the durable binding. The binding
        survives a CLIENT restart (restore by original id); a service restart
        never destroys the LOCAL copy, and 24h/eligibility adjudication
        belongs to the SERVICE (accepted vs duplicate), never to this client.
        A strategy receipt alone never re-creates this binding."""
        if self.prepared is None:
            return None
        op = self.prepared["record"]["operation_id"]
        path = self._binding_path(op)
        if not path.is_file():
            return None
        try:
            rec = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(rec, dict) or rec.get("schema") != VERIFIED_DECISION_SCHEMA:
            return None
        if rec.get("operation_id") != op or rec.get("request_id") != op:
            return None
        if not isinstance(rec.get("canonical_hex"), str):
            return None
        try:
            raw = bytes.fromhex(rec["canonical_hex"])
            wire = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None
        if raw != self.prepared["raw"]:
            return None
        if request_digest(wire) != rec.get("request_digest"):
            return None
        if rec.get("request_digest") != self.prepared["check"]["request_digest"]:
            return None
        return self._verify_decision_for_feedback(rec.get("decision"))

    def _feedback_start_event_path(self, op: str) -> Path:
        return self._strategy_dir() / f"event-{op}-F01-feedback-started.json"

    def _feedback_start_exists(self) -> bool:
        if self.prepared is None:
            return False
        return self._feedback_start_event_path(
            self.prepared["record"]["operation_id"]).is_file()

    def mark_in_process_decision(self, *, consent: bool, metrics_observed: bool) -> dict:
        """enterprise-r4 C (FB04): eligibility is grounded in the DURABLE local
        verified-decision binding, not an in-process boolean.

        A CLIENT restart (restore by original id) with an intact binding and
        NO feedback start event keeps the single first attempt; a SERVICE
        restart never destroys the local binding, and 24h/eligibility is
        adjudicated by the service (accepted vs duplicate closed receipts).
        Booleans alone never grant eligibility; a strategy receipt alone
        never re-creates it; no re-resolve ever fabricates it."""
        binding = self._load_verified_decision_binding()
        never_sent = not self._feedback_start_exists()
        eligible = bool(self.feedback_enabled and consent and metrics_observed
                        and binding is not None and never_sent)
        self.feedback_eligible = eligible
        self.feedback_eligibility_source = (
            "durable_verified_decision_binding_never_sent" if eligible else None)
        return {"eligible": self.feedback_eligible,
                "source": self.feedback_eligibility_source,
                "binding_present": binding is not None,
                "feedback_start_event_present": not never_sent,
                "reason": None if self.feedback_eligible else
                ("feedback_start_event_already_exists" if not never_sent
                 else "no_durable_verified_decision_binding"),
                "note": "客户端重启≠服务重启：资格来自完整本地绑定且从未发送；"
                        "24 小时资格由服务裁决（accepted/duplicate）"}

    def simulate_restart(self) -> dict:
        self.decision_from_receipt = True
        self.feedback_eligible = False
        self.feedback_eligibility_source = None
        self._verified_decision = None
        for v in self.action_ledger.values():
            v["local_work_allowed"] = False
        return {"feedback_eligible_after_restart": False,
                "feedback_calls": self.feedback_calls,
                "note": "服务/会话重启后 receipt 不恢复反馈资格；不重新 resolve 造资格"}

    def maybe_feedback(self, *, consent: bool = False, metrics_observed: bool = False) -> dict:
        """PASSIVE observation only: never sends. The explicit positive entry
        is submit_feedback (default OFF). This method never fabricates a
        success and never counts a send."""
        gate = self._gate("feedback")
        if gate:
            return {"sent": False, "state": "disabled", "reason": gate["state"],
                    "feedback_calls": self.feedback_calls,
                    "note": "默认关闭；被动观察不发送，正向入口为 submit_feedback"}
        return {"sent": False, "state": "not_requested",
                "reason": "passive_observation_only",
                "feedback_calls": self.feedback_calls,
                "positive_entry": "submit_feedback",
                "requires": ["feedback_enabled", "remote_enabled", "real transport",
                             "verified in-process selected decision",
                             "complete v2 feedback payload (full metrics, consent true)"],
                "note": "maybe_feedback 本身不发送；只有 submit_feedback 在全部前提满足时单次发送"}

    def submit_feedback(self, feedback: dict) -> dict:
        """EXPLICIT positive v2 feedback entry. Default OFF; ONE send only.

        enterprise-r4 C closes the five reproduced gaps FB01..FB05:
          * FB01 the decision basis is the DURABLE verified binding of the
            COMPLETE original decision (persisted exclusively + read back at
            resolve/receipt validation time), re-verified NOW against the
            persisted ORIGINAL request — an in-process memory copy alone or
            a strategy receipt alone is never a basis;
          * FB02 observed usage (queries/reads/claims_total) is checked
            against the ORIGINAL selected plan budget BEFORE any send;
          * FB04 a CLIENT restore with an intact binding and NO feedback
            start event keeps the single first attempt; 24h/eligibility is
            adjudicated by the SERVICE via its closed receipts;
          * FB05 the COMPLETE six-field canonical payload, its
            payload_sha256 AND an INDEPENDENT body_digest (sha256 of the
            exact wire bytes) are saved EXCLUSIVELY in the F01 event and READ
            BACK before the send is considered started;
          * FB03 ONLY the two CLOSED business receipts confirm: accepted
            (exact provenance) or duplicate. HTTP 200 with an empty/unknown
            body stays unknown and is NEVER resent.

        The send start is persisted FIRST as an exclusive immutable event; a
        persistence failure (or an already-existing same-op feedback start)
        means ZERO network. Exactly ONE transport call follows. Unknown
        remains unknown.
        """
        gate = self._gate("feedback")
        if gate:
            return {"sent": False, "state": "disabled", "reason": gate["state"],
                    "feedback_calls": self.feedback_calls,
                    "note": "默认关闭：feedback_enabled/remote_enabled/transport 缺一即零发送"}
        if not isinstance(feedback, dict):
            return {"sent": False, "state": "refused", "reason": "invalid_feedback_shape",
                    "feedback_calls": self.feedback_calls,
                    "note": "payload 必须是完整 v2 反馈对象"}
        consent = feedback.get("consent") is True
        metrics = feedback.get("metrics")
        self.mark_in_process_decision(consent=consent,
                                      metrics_observed=isinstance(metrics, dict)
                                      and bool(metrics))
        unmet = []
        if not consent:
            unmet.append("explicit_consent_true")
        if not isinstance(metrics, dict) or not metrics:
            unmet.append("complete_observed_metrics_object")
        # FB01/FB04: durable binding re-verified now.
        decision = self._load_verified_decision_binding()
        if decision is None:
            unmet.append("durable_verified_decision_binding")
        if not self.feedback_eligible:
            unmet.append("feedback_eligibility")
        if unmet:
            return {"sent": False, "state": "refused", "reason": "prerequisites_not_met",
                    "unmet_prerequisites": sorted(set(unmet)),
                    "feedback_calls": self.feedback_calls,
                    "note": "具名列出未闭前提；未知保持未知；不重新 resolve 造资格"}
        try:
            # Reuse the COMPLETE v2 feedback validator, bound to the durable
            # verified decision AND the persisted ORIGINAL request.
            v2.validate_feedback(feedback, decision=decision,
                                 request=self._original_request())
        except Exception as exc:  # v2 raises its own Error types
            return {"sent": False, "state": "refused", "reason": "invalid_feedback",
                    "validator": "strategy_client_v2.validate_feedback",
                    "validator_error": f"{type(exc).__name__}: {exc}"[:200],
                    "feedback_calls": self.feedback_calls,
                    "note": "复用完整 v2 反馈校验；缺完整 payload/同意/真实指标即零发送，"
                            "不编造指标、不把 unsupported 当功能完成"}
        # FB02: observed usage must fit the ORIGINAL selected plan budget.
        plan_budget = decision["plan"]["budget"]
        budget_over = {}
        for metric_key, budget_key in (("queries", "max_queries"),
                                       ("reads", "max_reads"),
                                       ("claims_total", "max_claims")):
            used = metrics.get(metric_key)
            if type(used) is not int or used < 0 or used > plan_budget[budget_key]:
                budget_over[metric_key] = {"observed": used,
                                           "plan_max": plan_budget[budget_key]}
        if budget_over:
            return {"sent": False, "state": "refused",
                    "reason": "metrics_exceed_plan_budget",
                    "budget_exceeded": budget_over,
                    "feedback_calls": self.feedback_calls,
                    "note": "发送前按原 selected plan 预算核对反馈指标；超限即零发送"}
        op = self.prepared["record"]["operation_id"]
        # FB05: canonical six-field payload bytes, payload digest AND an
        # independent digest of the exact wire bytes sent.
        payload_bytes = canonical_bytes(feedback)
        wire = payload_bytes + b"\n"
        if len(wire) > MAX_REQUEST_BYTES:
            return {"sent": False, "state": "refused", "reason": "feedback_exceeds_16KiB",
                    "feedback_calls": self.feedback_calls}
        # F01 exclusive guard FIRST: once a start event exists (send started
        # or outcome unknown), ZERO automatic resend — the original id and
        # the unknown state are kept.
        f01_path = self._feedback_start_event_path(op)
        if f01_path.is_file():
            return {"sent": False, "state": "refused",
                    "reason": "feedback_start_event_exists_no_resend",
                    "feedback_calls": self.feedback_calls, "resend_permitted": False,
                    "note": "F01 排他守卫：已开始/未知不重发；保持原号与 unknown"}
        payload_sha256 = hashlib.sha256(payload_bytes).hexdigest()
        body_digest = hashlib.sha256(wire).hexdigest()
        started = self._exclusive_event(
            f"event-{op}-F01-feedback-started.json",
            {"schema": "paper.feedback-event.v1", "version": VERSION,
             "consumer": {"product": PRODUCT, "version": VERSION},
             "operation_id": op, "feedback_id": feedback.get("feedback_id"),
             "decision_id": feedback.get("decision_id"),
             "request_digest": feedback.get("request_digest"),
             "payload": feedback, "payload_sha256": payload_sha256,
             "body_digest": body_digest, "budget_spent": 0})
        if not started:
            return {"sent": False, "state": "save_failed",
                    "reason": "feedback_start_event_exists_or_unwritable",
                    "feedback_calls": self.feedback_calls, "resend_permitted": False,
                    "note": "同号反馈开始事件不可变排他：已存在即不重发"}
        # FB05: READ BACK the complete six-field payload and both digests
        # BEFORE the send counts as started; a mismatch means zero network.
        try:
            rb = json.loads(f01_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            rb = None
        if not (isinstance(rb, dict)
                and rb.get("operation_id") == op
                and rb.get("feedback_id") == feedback.get("feedback_id")
                and rb.get("decision_id") == feedback.get("decision_id")
                and rb.get("request_digest") == feedback.get("request_digest")
                and rb.get("payload") == feedback
                and rb.get("payload_sha256") == payload_sha256
                and rb.get("body_digest") == body_digest):
            return {"sent": False, "state": "save_failed",
                    "reason": "feedback_start_readback_invalid",
                    "feedback_calls": self.feedback_calls, "resend_permitted": False,
                    "note": "F01 读回不完整即不标开始、零网络、不重发"}
        self.feedback_calls += 1
        self.network_calls += 1
        try:
            response = self.transport(FEEDBACK_PATH, wire)
        except urllib.error.HTTPError as exc:
            code = exc.code if isinstance(getattr(exc, "code", None), int) else None
            reason = (f"http_{code}_client_error" if code is not None and 400 <= code < 500
                      else f"http_{code}_server_error" if code is not None and 500 <= code < 600
                      else "http_error")
            self._exclusive_event(
                f"event-{op}-F02-feedback-unknown.json",
                {"schema": "paper.feedback-event.v1", "version": VERSION,
                 "operation_id": op, "state": "unknown", "reason": reason,
                 "http_status": code, "budget_spent": 0})
            return {"sent": False, "state": "unknown", "reason": reason,
                    "http_status": code, "feedback_calls": self.feedback_calls,
                    "resend_permitted": False,
                    "note": "反馈未知保持未知：不自动重发、不重新 resolve 造资格；"
                            "不输出原始异常正文/URL/凭据"}
        except Exception as exc:
            self._exclusive_event(
                f"event-{op}-F02-feedback-unknown.json",
                {"schema": "paper.feedback-event.v1", "version": VERSION,
                 "operation_id": op, "state": "unknown",
                 "reason": type(exc).__name__, "budget_spent": 0})
            return {"sent": False, "state": "unknown", "reason": type(exc).__name__,
                    "feedback_calls": self.feedback_calls, "resend_permitted": False,
                    "note": "反馈未知保持未知：不自动重发"}
        status = response.get("status") if isinstance(response, dict) else None
        body = response.get("body") if isinstance(response, dict) else None
        # FB03: ONLY the two CLOSED business outcomes confirm.
        outcome = feedback_receipt_status(status, body)
        if outcome is not None:
            self._exclusive_event(
                f"event-{op}-F03-feedback-confirmed.json",
                {"schema": "paper.feedback-event.v1", "version": VERSION,
                 "operation_id": op, "state": "confirmed",
                 "feedback_id": feedback.get("feedback_id"),
                 "outcome": outcome, "http_status": status, "budget_spent": 0})
            return {"sent": True, "state": "confirmed", "outcome": outcome,
                    "http_status": status,
                    "feedback_calls": self.feedback_calls,
                    "note": "仅 accepted（精确 provenance）或 duplicate 闭合回执才确认；"
                            "单次发送；duplicate 表示服务已裁决；反馈接受不等于真人采用"}
        self._exclusive_event(
            f"event-{op}-F02-feedback-unknown.json",
            {"schema": "paper.feedback-event.v1", "version": VERSION,
             "operation_id": op, "state": "unknown",
             "reason": "receipt_not_confirmed", "http_status": status,
             "budget_spent": 0})
        return {"sent": False, "state": "unknown", "reason": "receipt_not_confirmed",
                "http_status": status,
                "feedback_calls": self.feedback_calls, "resend_permitted": False,
                "note": "HTTP 200 空 body/未知形状不是确认：仅 accepted/duplicate 闭合回执确认；"
                        "其余保持 unknown，不重发"}

    def report(self) -> dict:
        return {"schema": "paper.strategy-client-0200.report.v2", "version": VERSION,
                "consumer": {"product": PRODUCT, "version": VERSION},
                "remote_enabled": self.remote_enabled, "feedback_enabled": self.feedback_enabled,
                "resolve_calls": self.resolve_calls, "feedback_calls": self.feedback_calls,
                "receipt_query_calls": self.receipt_query_calls,
                "network_calls": self.network_calls, "send_started": self.send_started,
                "feedback_eligible": self.feedback_eligible,
                "feedback_eligibility_source": self.feedback_eligibility_source,
                "decision_from_receipt": self.decision_from_receipt,
                "restored_read_only": self._restored,
                "action_ledger": dict(self.action_ledger),
                "complete_v2_validator_reused": True,
                "wire_fields_frozen": True, "v3_and_five_forms_in_wire": False,
                "old_versions_impersonated": False,
                "bounded_https_transport_available": True,
                "http_verified": False, "production_deployed": False,
                "loopback_pairing_claimed": False,
                "feedback_positive_entry": "submit_feedback (default OFF, single send, "
                                           "durable start event, v2 validator reused)",
                "feedback_v3_enabled": False}


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 2 and sys.argv[1] == "_transport-worker-0200":
        # Child-only transport worker. Bounded stdin, one canonical envelope
        # on stdout; nothing else is emitted and no retry layer is attached.
        raw = sys.stdin.buffer.read(MAX_REQUEST_BYTES * 2 + 8192)
        try:
            env = _strict_json_loads(raw)
            out = _child_socket_operation(env)
        except Exception as exc:  # never leak raw text; keep the outcome unknown
            out = {"ok": False, "kind": "transport",
                   "reason": type(exc).__name__}
        sys.stdout.buffer.write(canonical_bytes(out))
