#!/usr/bin/env python3
"""Bound automatic preview attempts with a JSON state file.

This guard authorizes calls; it does not invoke a browser, create screenshots,
inspect artifacts, or certify visual quality. Only an authorized record permits
the caller to start the corresponding preview invocation.
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys


SCHEMA_VERSION = 1
OUTCOMES = ("returned", "failed", "unknown")
ARTIFACT_STATES = ("generated", "missing", "unknown")
CONFIRMED_OUTCOMES = ("returned", "failed")
CONFIRMED_ARTIFACT_STATES = ("generated", "missing")


class GuardError(Exception):
    """An expected validation or budget denial."""


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def emit(payload, stream=sys.stdout):
    print(json.dumps(payload, ensure_ascii=False, indent=2), file=stream)


def load_state(path):
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise GuardError("State file does not exist; run init first") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise GuardError("Cannot read valid state JSON: %s" % exc) from exc
    if state.get("schema_version") != SCHEMA_VERSION:
        raise GuardError("Unsupported state schema")
    if not isinstance(state.get("attempts"), list):
        raise GuardError("State attempts must be a list")
    return state


def save_state(path, state):
    temp_path = path.with_name(path.name + ".tmp")
    try:
        temp_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temp_path, path)
    except OSError as exc:
        raise GuardError("Cannot save state: %s" % exc) from exc


def find_attempt(state, attempt_id):
    for attempt in state["attempts"]:
        if attempt.get("attempt_id") == attempt_id:
            return attempt
    raise GuardError("Unknown attempt_id: %s" % attempt_id)


def unknown_resolution(attempt):
    if attempt.get("outcome") != "unknown":
        return None
    resolution = attempt.get("resolution")
    if not isinstance(resolution, dict):
        return None
    if resolution.get("outcome") not in CONFIRMED_OUTCOMES:
        return None
    if resolution.get("artifact_state") not in CONFIRMED_ARTIFACT_STATES:
        return None
    evidence = resolution.get("evidence")
    if not isinstance(evidence, str) or not evidence.strip():
        return None
    return resolution


def is_unresolved_unknown(attempt):
    return attempt.get("outcome") == "unknown" and unknown_resolution(attempt) is None


def effective_result(attempt):
    resolution = unknown_resolution(attempt)
    if resolution is not None:
        return resolution["outcome"], resolution["artifact_state"]
    return attempt.get("outcome"), attempt.get("artifact_state")


def retryable(attempt):
    outcome, artifact_state = effective_result(attempt)
    if outcome == "failed":
        return True
    return outcome == "returned" and artifact_state == "missing"


def command_init(args):
    path = Path(args.state)
    if path.exists():
        raise GuardError("State file already exists; use status, not init")
    units = list(dict.fromkeys(args.unit))
    if not units or any(not unit.strip() for unit in units):
        raise GuardError("At least one non-empty planned unit is required")
    if not args.route.strip():
        raise GuardError("Route must be non-empty")
    state = {
        "schema_version": SCHEMA_VERSION,
        "route": args.route,
        "planned_units": units,
        "max_retries": args.max_retries,
        "created_at": now_utc(),
        "stopped": None,
        "attempts": [],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    save_state(path, state)
    emit({
        "status": "initialized",
        "route": state["route"],
        "planned_units": units,
        "max_retries": state["max_retries"],
    })


def command_authorize(args):
    path = Path(args.state)
    state = load_state(path)
    if state["stopped"] is not None:
        raise GuardError("Route is stopped; no further preview is authorized")
    if any(is_unresolved_unknown(item) for item in state["attempts"]):
        raise GuardError(
            "Resolve the unknown attempt with evidence or stop the route first"
        )
    if any(item.get("outcome") == "authorized" for item in state["attempts"]):
        raise GuardError("Complete the pending authorized attempt first")
    if args.unit not in state["planned_units"]:
        raise GuardError("Unit was not declared during init")

    retries_used = sum(
        item.get("retry_of") is not None for item in state["attempts"]
    )
    retry_of = args.retry_of
    if retry_of is None:
        if any(
            item.get("unit") == args.unit and item.get("retry_of") is None
            for item in state["attempts"]
        ):
            raise GuardError("Initial attempt for this unit was already authorized")
        kind = "planned_initial"
        reason = None
    else:
        if retries_used >= state["max_retries"]:
            raise GuardError("Route retry budget exhausted")
        if not args.reason or not args.reason.strip():
            raise GuardError("A retry requires an evidence-based reason")
        original = find_attempt(state, retry_of)
        if original.get("unit") != args.unit:
            raise GuardError("Retry must keep the original unit")
        if original.get("retry_of") is not None:
            raise GuardError("Retry the initial attempt, not another retry")
        if any(item.get("retry_of") == retry_of for item in state["attempts"]):
            raise GuardError("This initial attempt already has a retry")
        if not retryable(original):
            raise GuardError(
                "Retry requires failed outcome or returned outcome with missing artifact"
            )
        kind = "failure_retry"
        reason = args.reason.strip()

    attempt_id = max(
        [item.get("attempt_id", 0) for item in state["attempts"]] or [0]
    ) + 1
    attempt = {
        "attempt_id": attempt_id,
        "unit": args.unit,
        "kind": kind,
        "retry_of": retry_of,
        "retry_reason": reason,
        "authorized_at": now_utc(),
        "outcome": "authorized",
        "artifact_state": "not-recorded",
    }
    state["attempts"].append(attempt)
    save_state(path, state)
    emit({
        "status": "authorized",
        "attempt_id": attempt_id,
        "kind": kind,
        "authorized_invocations": len(state["attempts"]),
        "retries_remaining": state["max_retries"] - retries_used
        - (1 if retry_of is not None else 0),
    })


def command_complete(args):
    path = Path(args.state)
    state = load_state(path)
    attempt = find_attempt(state, args.attempt_id)
    if attempt.get("outcome") != "authorized":
        raise GuardError("Only a pending authorized attempt can be completed")
    attempt["outcome"] = args.outcome
    attempt["artifact_state"] = args.artifact_state
    attempt["result_note"] = args.note.strip()
    attempt["completed_at"] = now_utc()
    save_state(path, state)
    emit({
        "status": "recorded",
        "attempt_id": args.attempt_id,
        "outcome": args.outcome,
        "artifact_state": args.artifact_state,
    })


def command_resolve(args):
    path = Path(args.state)
    state = load_state(path)
    attempt = find_attempt(state, args.attempt_id)
    if attempt.get("outcome") != "unknown":
        raise GuardError("Only an unknown attempt can be resolved")
    if attempt.get("resolution") is not None:
        raise GuardError("This unknown attempt already has a resolution")
    evidence = args.evidence.strip()
    if not evidence:
        raise GuardError("Resolving an unknown attempt requires evidence")
    attempt["resolution"] = {
        "outcome": args.outcome,
        "artifact_state": args.artifact_state,
        "evidence": evidence,
        "resolved_at": now_utc(),
    }
    save_state(path, state)
    emit({
        "status": "resolved",
        "attempt_id": args.attempt_id,
        "original_outcome": "unknown",
        "confirmed_outcome": args.outcome,
        "confirmed_artifact_state": args.artifact_state,
    })


def command_stop(args):
    path = Path(args.state)
    state = load_state(path)
    if state["stopped"] is not None:
        raise GuardError("Route is already stopped")
    state["stopped"] = {"at": now_utc(), "reason": args.reason.strip()}
    save_state(path, state)
    emit({"status": "stopped", "route": state["route"]})


def command_status(args):
    state = load_state(Path(args.state))
    attempts = state["attempts"]
    summary = {
        "route": state["route"],
        "authorized_invocations": len(attempts),
        "planned_initials": sum(
            item.get("retry_of") is None for item in attempts
        ),
        "failure_retries": sum(
            item.get("retry_of") is not None for item in attempts
        ),
        "pending_completion": sum(
            item.get("outcome") == "authorized" for item in attempts
        ),
        "unresolved_unknown": sum(
            is_unresolved_unknown(item) for item in attempts
        ),
        "resolved_unknown": sum(
            unknown_resolution(item) is not None for item in attempts
        ),
        "stopped": state["stopped"] is not None,
    }
    emit({"summary": summary, "state": state})


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("--state", required=True)
    init_parser.add_argument("--route", required=True)
    init_parser.add_argument("--unit", action="append", required=True)
    init_parser.add_argument("--max-retries", type=int, choices=(0, 1), default=1)
    init_parser.set_defaults(handler=command_init)

    authorize_parser = subparsers.add_parser("authorize")
    authorize_parser.add_argument("--state", required=True)
    authorize_parser.add_argument("--unit", required=True)
    authorize_parser.add_argument("--retry-of", type=int)
    authorize_parser.add_argument("--reason")
    authorize_parser.set_defaults(handler=command_authorize)

    complete_parser = subparsers.add_parser("complete")
    complete_parser.add_argument("--state", required=True)
    complete_parser.add_argument("--attempt-id", type=int, required=True)
    complete_parser.add_argument("--outcome", choices=OUTCOMES, required=True)
    complete_parser.add_argument(
        "--artifact-state", choices=ARTIFACT_STATES, required=True
    )
    complete_parser.add_argument("--note", required=True)
    complete_parser.set_defaults(handler=command_complete)

    resolve_parser = subparsers.add_parser("resolve")
    resolve_parser.add_argument("--state", required=True)
    resolve_parser.add_argument("--attempt-id", type=int, required=True)
    resolve_parser.add_argument(
        "--outcome", choices=CONFIRMED_OUTCOMES, required=True
    )
    resolve_parser.add_argument(
        "--artifact-state", choices=CONFIRMED_ARTIFACT_STATES, required=True
    )
    resolve_parser.add_argument("--evidence", required=True)
    resolve_parser.set_defaults(handler=command_resolve)

    stop_parser = subparsers.add_parser("stop")
    stop_parser.add_argument("--state", required=True)
    stop_parser.add_argument("--reason", required=True)
    stop_parser.set_defaults(handler=command_stop)

    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--state", required=True)
    status_parser.set_defaults(handler=command_status)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        args.handler(args)
    except GuardError as exc:
        emit({"status": "denied", "reason": str(exc)}, stream=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
