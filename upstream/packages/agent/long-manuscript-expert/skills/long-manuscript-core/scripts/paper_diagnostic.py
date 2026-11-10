#!/usr/bin/env python3
"""Sanitized diagnostic summaries for long-manuscript-expert (paper.diagnostic.v1).

This module is the ONLY client-side implementation of the frozen contract
``contracts/diagnostics-v1/CONTRACT.md``. The byte-identical catalog copy at
``skills/long-manuscript-core/references/diagnostics-catalog.json`` (SHA-256
9467080d5007c7e837d009fcd0e3d0de65d1d590b93393758f54f86f85701471) is the sole
truth source for feedback codes, kinds, phases, safe texts and retry postures.

Hard rules implemented here (see CONTRACT.md):
  * Diagnostic output is metadata only: no user content, no raw error text, no
    URLs, no paths, no request bodies, no original request ids, no headers
    beyond the four safe server self-declarations.
  * ``http_status`` is recorded ONLY when an actual HTTPResponse/HTTPError was
    observed. The legacy ``Error.status`` field is never copied into it.
  * ``server_reason`` accepts exact keys of the catalog ``reason_aliases`` only;
    anything else observed is reported as ``unknown``, never echoed. It comes
    from the whitelist-parsed error body only - never from a header.
  * ``server_feedback_code`` is the server's self-declared feedback-code
    header kept in its own closed field (exact ``FBS-PAPER-NNNN`` shape);
    a code can never impersonate a reason.
  * ``request_ref`` = SHA256(UTF8("paper-request-ref.v1\\0" + str(UUID))); the
    original request_id never appears. ``short_ref`` is a display hint only.
  * ``transport_attempts`` counts calls into the transport layer; it is NOT a
    network-send count. ``network_sends`` stays null unless actually measured.
  * ``execution_platform`` is this process's sys.platform classification;
    ``client_platform`` defaults to ``unknown`` and is only set when the user
    explicitly reports it (``client_platform_source=user_reported``).
  * ``source_fingerprint`` covers only the explicitly scoped executed modules
    and the catalog, using package-relative paths against a fixed manifest.
    It proves only the files that were read - never which copy the host chose,
    and never another installed copy. This module and the manifest itself are
    excluded to avoid self-circular hashing.
  * Same-named failures before send and after receive are classified by their
    actual stage (e.g. invalid_json input vs invalid_json_response).

Standard library only. This module never performs network access.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import uuid as _uuid_mod
from datetime import datetime, timezone
from typing import Any, Dict, Optional

__all__ = [
    "DiagnosticError", "SCHEMA", "PRODUCT_ID", "CONSUMER_VERSION",
    "OBSERVED_STAGES", "SEND_STATES", "EXECUTION_PLATFORMS",
    "package_root", "load_catalog", "catalog_integrity",
    "feedback_key_for", "sanitize_server_reason", "request_ref",
    "execution_platform", "source_fingerprint", "build_diagnostic",
]

SCHEMA = "paper.diagnostic.v1"
PRODUCT_ID = "long-manuscript-expert"
# Current producer label for self-produced diagnostics. New records must not
# be mislabelled with the predecessor 2026.10.300 tag.
CONSUMER_VERSION = "2026.11.5"

OBSERVED_STAGES = (
    "not_observed", "pre_send", "transport", "http_response",
    "response_validation", "business_response", "local_io", "host_tool",
    "operation_receipt",
)
# Frozen contract enum: not_called only when the transport was provably never
# invoked (pre-send rejection or an explicit local path); anything uncertain
# stays unknown.
SEND_STATES = ("not_called", "unknown", "response_received")
EXECUTION_PLATFORMS = ("win32", "darwin", "linux", "other")

CATALOG_RELATIVE_PATH = (
    "skills/long-manuscript-core/references/diagnostics-catalog.json")
MANIFEST_RELATIVE_PATH = (
    "skills/long-manuscript-core/scripts/source-manifest.json")

REQUEST_REF_DOMAIN = b"paper-request-ref.v1\x00"
EVENT_REF_RE = re.compile(r"^[0-9a-f]{32}$")
RELEASE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,127}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
# The server's self-declared feedback code header is a CODE, never a reason:
# it travels in its own closed field and only in this exact frozen shape.
FEEDBACK_CODE_RE = re.compile(r"^FBS-PAPER-[0-9]{4}$")

# Stage-appropriate fallback when a reason is not a catalog item key and not
# an exact reason_aliases key. Classification is not root-cause proof: an
# unsupported validation reason falls back to the generic, observable
# response_invalid, never to a specific binding claim.
_STAGE_FALLBACK = {
    "not_observed": "not_started",
    "pre_send": "input_invalid",
    "transport": "outcome_unknown",
    "http_response": "http_rejected",
    "response_validation": "response_invalid",
    "business_response": "response_invalid",
    "local_io": "local_record_failed",
    "host_tool": "host_blocked",
    "operation_receipt": "write_result_unconfirmed",
}

# Same-named codes whose catalog alias targets the pre-send item, mapped to
# their response-side item when they actually happened after receive.
_RESPONSE_SIDE_REASONS = {
    "invalid_json": "invalid_json_response",
}

# Codes whose catalog alias targets a response-side item, mapped back to the
# pre-send item when they provably happened before any send.
_PRE_SEND_REASON_OVERRIDES = {
    "body_too_large": "input_invalid",
}

# Client-internal codes that are not in reason_aliases but have a well-defined
# catalog item.
_SUPPLEMENTARY_REASONS = {
    "total_timeout": "transport_timeout",
}

_STAGE_DEFAULT_EVIDENCE = {
    "not_observed": "not_observed",
    "pre_send": "pre_send_validation",
    "transport": "transport_exception",
    "http_response": "http_response",
    "response_validation": "response_validation",
    "business_response": "validated_business_response",
    "local_io": "local_io",
    "host_tool": "host_tool_observation",
    "operation_receipt": "operation_receipt",
}

_CATALOG_CACHE: Dict[str, Dict[str, Any]] = {}


class DiagnosticError(Exception):
    """The diagnostic contract cannot be honoured (catalog/manifest problem)."""


def package_root() -> str:
    """Absolute expert-package root derived from this file's location.

    Layout: <root>/skills/long-manuscript-core/scripts/paper_diagnostic.py
    """
    here = os.path.abspath(os.path.dirname(__file__))
    return os.path.abspath(os.path.join(here, os.pardir, os.pardir, os.pardir))


def _read_bytes(path: str, maximum: int) -> bytes:
    with open(path, "rb") as handle:
        data = handle.read(maximum + 1)
    if len(data) > maximum:
        raise DiagnosticError("catalog_too_large")
    return data


def load_catalog(root: Optional[str] = None) -> Dict[str, Any]:
    """Load the embedded catalog copy; raises DiagnosticError on any problem."""
    base = os.path.abspath(root) if root else package_root()
    path = os.path.join(base, *CATALOG_RELATIVE_PATH.split("/"))
    cached = _CATALOG_CACHE.get(path)
    if cached is not None:
        return cached
    try:
        raw = _read_bytes(path, 256 * 1024)
        catalog = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError, UnicodeError) as exc:
        raise DiagnosticError("catalog_unavailable") from exc
    if (type(catalog) is not dict
            or catalog.get("schema") != "paper.feedback-catalog.v1"
            or type(catalog.get("items")) is not dict
            or type(catalog.get("reason_aliases")) is not dict):
        raise DiagnosticError("catalog_invalid")
    _CATALOG_CACHE[path] = catalog
    return catalog


def catalog_integrity(root: Optional[str] = None) -> Optional[str]:
    """SHA-256 of the embedded catalog copy; None when unreadable."""
    base = os.path.abspath(root) if root else package_root()
    path = os.path.join(base, *CATALOG_RELATIVE_PATH.split("/"))
    try:
        return hashlib.sha256(_read_bytes(path, 256 * 1024)).hexdigest()
    except (OSError, DiagnosticError):
        return None


def feedback_key_for(reason: Optional[str], observed_stage: str,
                     catalog: Dict[str, Any]) -> str:
    """Resolve a client reason to a catalog item key; stage-aware, closed."""
    items = catalog["items"]
    aliases = catalog["reason_aliases"]
    mapped = reason
    if (observed_stage in ("response_validation", "business_response")
            and mapped in _RESPONSE_SIDE_REASONS):
        mapped = _RESPONSE_SIDE_REASONS[mapped]
    if observed_stage == "pre_send" and mapped in _PRE_SEND_REASON_OVERRIDES:
        mapped = _PRE_SEND_REASON_OVERRIDES[mapped]
    if mapped in items:
        return mapped
    if mapped in aliases:
        target = aliases[mapped]
        if target in items:
            return target
    if mapped in _SUPPLEMENTARY_REASONS:
        return _SUPPLEMENTARY_REASONS[mapped]
    return _STAGE_FALLBACK.get(observed_stage, "not_started")


def sanitize_server_reason(value: Optional[str], catalog: Dict[str, Any]) -> Optional[str]:
    """Exact reason_aliases keys pass; anything else observed becomes unknown.

    None means no server reason was observed at all (stays null)."""
    if value is None:
        return None
    if type(value) is str and value in catalog["reason_aliases"]:
        return value
    return "unknown"


def request_ref(request_id: Any) -> Optional[str]:
    """SHA256("paper-request-ref.v1\\0" + str(UUID(request_id))); None if invalid."""
    if type(request_id) is not str:
        return None
    try:
        normalized = str(_uuid_mod.UUID(request_id))
    except (ValueError, AttributeError, TypeError):
        return None
    return hashlib.sha256(REQUEST_REF_DOMAIN + normalized.encode("utf-8")).hexdigest()


def execution_platform() -> str:
    """This process's platform classification; never the client platform."""
    platform = sys.platform
    if platform.startswith("win"):
        return "win32"
    if platform == "darwin":
        return "darwin"
    if platform.startswith("linux"):
        return "linux"
    return "other"


# The fingerprint scope is a fixed allowlist of executed modules and the
# catalog - never whatever paths a manifest happens to contain. Only the
# manifest file itself is excluded (including it would be self-circular).
FINGERPRINT_SCOPE = (
    "skills/long-manuscript-core/references/diagnostics-catalog.json",
    "skills/long-manuscript-core/scripts/paper_diagnostic.py",
    "skills/long-manuscript-core/scripts/strategy_client.py",
    "skills/long-manuscript-core/scripts/strategy_client_v2.py",
)
MANIFEST_SCHEMA = "paper.source-manifest.v1"
MANIFEST_REVISION = 1


def _unknown_fingerprint(detail: str) -> Dict[str, Any]:
    # A fixed, closed unknown shape: no manifest-derived keys or values can
    # leak into the summary, whatever the malformed input contained.
    return {"scope": [], "status": "unknown", "detail": detail}


def _read_bounded_file(path: str, maximum: int) -> Optional[bytes]:
    """Read one scoped file without following escapes outside the package."""
    try:
        if os.path.islink(path) or not os.path.isfile(path):
            return None
        with open(path, "rb") as handle:
            data = handle.read(maximum + 1)
    except OSError:
        return None
    if len(data) > maximum:
        return None
    return data


def source_fingerprint(root: Optional[str] = None) -> Dict[str, Any]:
    """Compare the fixed scoped modules/catalog against the manifest baseline.

    The manifest's structure, revision, exact member set and SHA types are
    validated before any file is read; entries outside the fixed scope are
    never read. Symlink/reparse escapes outside the package root count as
    mismatch. Without a usable baseline the result is a fixed ``unknown``
    shape - never ``match`` and never an echo of the invalid input.
    """
    base = os.path.realpath(os.path.abspath(root) if root else package_root())
    manifest_path = os.path.join(base, *MANIFEST_RELATIVE_PATH.split("/"))
    raw = _read_bounded_file(manifest_path, 256 * 1024)
    if raw is None:
        return _unknown_fingerprint("manifest_unavailable")
    try:
        manifest = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError):
        return _unknown_fingerprint("manifest_invalid")
    if (type(manifest) is not dict
            or manifest.get("schema") != MANIFEST_SCHEMA
            or manifest.get("revision") != MANIFEST_REVISION
            or type(manifest.get("files")) is not dict):
        return _unknown_fingerprint("manifest_invalid")
    files = manifest["files"]
    expected_scope = sorted(FINGERPRINT_SCOPE)
    if sorted(files.keys()) != expected_scope:
        return _unknown_fingerprint("manifest_scope_mismatch")
    for rel in expected_scope:
        expected = files[rel]
        if type(expected) is not str or HEX64_RE.fullmatch(expected) is None:
            return _unknown_fingerprint("manifest_invalid")
    details: Dict[str, str] = {}
    status = "match"
    for rel in expected_scope:
        candidate = os.path.realpath(os.path.join(base, *rel.split("/")))
        inside = (candidate == base or
                  candidate.startswith(base + os.sep))
        data = (_read_bounded_file(candidate, 4 * 1024 * 1024)
                if inside else None)
        if data is not None and hashlib.sha256(data).hexdigest() == files[rel]:
            details[rel] = "match"
        else:
            details[rel] = "mismatch"
            status = "mismatch"
    return {
        "scope": expected_scope,
        "status": status,
        "files": details,
        "manifest_revision": MANIFEST_REVISION,
    }


# Bounded legal observation instants: 2000-01-01 .. 2100-01-01 UTC.
_OBSERVED_AT_MIN = 946684800.0
_OBSERVED_AT_MAX = 4102444800.0


def _iso8601_utc(observed_at: Any) -> str:
    """Normalise to a canonical UTC ISO8601 string; reject anything else.

    Arbitrary strings are never passed through (a summary is a closed safe
    output); only a bounded finite number or a parseable ISO8601 datetime
    with an explicit UTC offset is accepted.
    """
    if observed_at is None:
        moment = datetime.now(tz=timezone.utc)
    elif type(observed_at) in (int, float) and not isinstance(observed_at, bool):
        value = float(observed_at)
        if not (_OBSERVED_AT_MIN <= value <= _OBSERVED_AT_MAX):
            raise DiagnosticError("invalid_observed_at")
        moment = datetime.fromtimestamp(value, tz=timezone.utc)
    elif type(observed_at) is str and observed_at:
        text = observed_at
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise DiagnosticError("invalid_observed_at") from exc
        if (parsed.tzinfo is None
                or parsed.utcoffset() != timezone.utc.utcoffset(None)):
            raise DiagnosticError("invalid_observed_at")
        moment = parsed.astimezone(timezone.utc)
    else:
        raise DiagnosticError("invalid_observed_at")
    return moment.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _optional_hex(value: Any, pattern) -> Optional[str]:
    # fullmatch: a trailing newline must not smuggle a value past the pattern.
    if type(value) is str and pattern.fullmatch(value):
        return value
    return None


def build_diagnostic(*, reason: Optional[str] = None,
                     feedback_key: Optional[str] = None,
                     observed_stage: str = "not_observed",
                     send_state: str = "unknown",
                     evidence_basis: Optional[str] = None,
                     transport_attempts: Optional[int] = None,
                     network_sends: Optional[int] = None,
                     request_id: Any = None,
                     http_status: Optional[int] = None,
                     server_reason: Optional[str] = None,
                     server_feedback_code: Optional[str] = None,
                     server_event_ref: Optional[str] = None,
                     server_release: Optional[str] = None,
                     server_catalog_sha256: Optional[str] = None,
                     client_platform: Optional[str] = None,
                     client_platform_source: Optional[str] = None,
                     observed_at: Any = None,
                     root: Optional[str] = None,
                     include_fingerprint: bool = True) -> Dict[str, Any]:
    """Build one closed paper.diagnostic.v1 summary from observed facts only.

    Raises DiagnosticError when the catalog is unavailable or a parameter
    violates the contract; callers must treat diagnostics as best-effort and
    never let a diagnostic failure change the business outcome.
    """
    if observed_stage not in OBSERVED_STAGES:
        raise DiagnosticError("invalid_observed_stage")
    if send_state not in SEND_STATES:
        raise DiagnosticError("invalid_send_state")
    if transport_attempts is not None and (
            type(transport_attempts) is not int or transport_attempts < 0):
        raise DiagnosticError("invalid_transport_attempts")
    if send_state == "not_called" and transport_attempts not in (None, 0):
        raise DiagnosticError("send_state_conflict")
    if network_sends is not None and (
            type(network_sends) is not int or network_sends < 0):
        raise DiagnosticError("invalid_network_sends")
    if http_status is not None and (
            type(http_status) is not int or not 100 <= http_status <= 599):
        raise DiagnosticError("invalid_http_status")

    catalog = load_catalog(root)
    items = catalog["items"]
    if feedback_key is not None:
        if feedback_key not in items:
            raise DiagnosticError("unknown_feedback_key")
        key = feedback_key
    else:
        key = feedback_key_for(reason, observed_stage, catalog)
    item = items[key]

    if evidence_basis is None:
        evidence_basis = _STAGE_DEFAULT_EVIDENCE[observed_stage]
    if evidence_basis not in catalog["evidence_basis"]:
        raise DiagnosticError("invalid_evidence_basis")

    if client_platform is not None:
        if (client_platform in catalog["client_platforms"]
                and client_platform_source == "user_reported"):
            reported_platform = client_platform
            platform_source = "user_reported"
        else:
            reported_platform = "unknown"
            platform_source = None
    else:
        reported_platform = "unknown"
        platform_source = None

    fingerprint = (source_fingerprint(root) if include_fingerprint
                   else {"scope": [], "status": "unknown",
                         "detail": "not_checked"})

    ref = request_ref(request_id)
    return {
        "schema": SCHEMA,
        "product_id": PRODUCT_ID,
        "consumer_version": CONSUMER_VERSION,
        "feedback_key": key,
        "feedback_code": item["code"],
        "kind": item["kind"],
        "phase": item["phase"],
        "message": item["message"],
        "next_action": item["next_action"],
        "retry_policy": item["retry_policy"],
        "observed_stage": observed_stage,
        "observed_at": _iso8601_utc(observed_at),
        "evidence_basis": evidence_basis,
        "transport_attempts": transport_attempts,
        "network_sends": network_sends,
        "send_state": send_state,
        "http_status": http_status,
        "server_reason": sanitize_server_reason(server_reason, catalog),
        "server_feedback_code": _optional_hex(server_feedback_code,
                                              FEEDBACK_CODE_RE),
        "request_ref": ref,
        "short_ref": ref[:12] if ref is not None else None,
        "server_event_ref": _optional_hex(server_event_ref, EVENT_REF_RE),
        "server_release": _optional_hex(server_release, RELEASE_RE),
        "server_catalog_sha256": _optional_hex(server_catalog_sha256, HEX64_RE),
        "execution_platform": execution_platform(),
        "client_platform": reported_platform,
        "client_platform_source": platform_source,
        "source_fingerprint": fingerprint,
    }


if __name__ == "__main__":
    # Maintainer-facing self check: prints catalog integrity and the source
    # fingerprint of this exact package copy. No network access.
    print(json.dumps({
        "catalog_sha256": catalog_integrity(),
        "source_fingerprint": source_fingerprint(),
        "execution_platform": execution_platform(),
    }, ensure_ascii=False, indent=2))
