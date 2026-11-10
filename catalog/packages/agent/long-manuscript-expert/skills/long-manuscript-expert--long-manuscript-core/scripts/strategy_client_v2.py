#!/usr/bin/env python3
"""Deterministic paper.*.v2 client (contract revision 2, smart hardware).

Authoritative source: contracts/v2r2/ including CLIENT-SEMANTICS-01.md.
The predecessor contracts/v2 directory is not used. v1 remains the base-only
compatibility path; this module is required for research-track tasks.

Research tracks cover only sector, scenario, evidence applicability and research
strategy. They never represent groups, QR/admission/capacity, upstream/downstream
spaces or identities. Full topics, private materials and author judgements stay
local. Standard library only; the transport is injectable for hermetic tests.
"""
from __future__ import annotations

import argparse
import copy
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Optional, Tuple

import strategy_client as v1
from strategy_client import (
    Error, require, canonical, digest, strict_json, compute_brief_digest,
    DEV_BASE_URL, PLANNED_PRODUCTION_BASE_URL, DEFAULT_TIMEOUT,
    MAX_DURATION_SECONDS, BUDGET_KEYS, KEBAB_ID, HEX64,
    _object, _int, _uuid, _enum, _cell, _budget, _is_finite_num,
)

__all__ = [
    "Error", "StrategyClientV2", "DecisionGuard", "validate_request",
    "validate_catalog", "validate_response", "validate_feedback",
    "prepare_request", "build_local_brief", "check_time_window",
    "map_scope_text", "canonical", "digest", "strict_json",
    "DEV_BASE_URL", "PLANNED_PRODUCTION_BASE_URL",
]

REQUEST_SCHEMA = "paper.intent.v2"
RESPONSE_SCHEMA = "paper.strategy-decision.v2"
FEEDBACK_SCHEMA = "paper.feedback.v2"
CATALOG_SCHEMA = "paper.catalog.v2"
CONTRACT_REVISION = 2

SECTORS = ("smart_hardware", "manufacturing", "enterprise_software",
           "cross_industry", "other", "unknown")
SCENARIOS = ("product_feasibility", "aftersales_ai", "competitive_comparison",
             "knowledge_qa", "other", "unknown")
DOMAIN_CHECKS = (
    "aftersales_manual_dispatch", "escalation_route", "ticket_data_boundary",
    "competitor_identity_version", "license_entitlements", "benchmark_task_alignment",
    "qa_citation_grounding", "retrieval_access_scope", "stale_knowledge",
    "device_test_conditions", "edge_cloud_boundary", "power_latency_connectivity",
    "bom_manufacturing_support",
)
TRACK_REASONS = (
    "track_selected", "track_selection_required", "track_no_match",
    "track_catalog_unavailable", "track_catalog_changed", "track_not_found",
    "track_version_mismatch", "track_paused", "track_unreviewed",
    "track_not_yet_effective", "track_review_expired", "track_goal_mismatch",
    "sector_unknown_not_supported", "scenario_unknown_not_supported",
    "scope_conflict", "sector_mismatch", "scenario_mismatch",
)
REASON_CODES = v1.REASON_CODES + TRACK_REASONS
NON_REJECTION_REASONS = {"track_selected", "track_selection_required"}
EXCLUDED_KEYS = {
    "group", "groups", "group_id", "group_qr", "qr", "qr_code", "capacity",
    "admission", "membership", "upstream", "downstream", "space", "space_id",
}
DISPLAY_MAX = 80
MAX_TRACKS = 12


def _reject_excluded(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            require(isinstance(key, str) and key.lower() not in EXCLUDED_KEYS,
                    "excluded_field")
            _reject_excluded(child, path + "." + str(key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_excluded(child, "%s[%d]" % (path, index))


def _array(value: Any, allowed: Tuple[str, ...], low: int, high: int,
           code: str) -> None:
    require(type(value) is list and low <= len(value) <= high, code)
    require(all(type(item) is str for item in value), code)
    require(len(set(value)) == len(value), code)
    require(all(item in allowed for item in value), code)


def _display(value: Any, code: str) -> None:
    require(type(value) is str and 1 <= len(value) <= DISPLAY_MAX, code)
    require(not any(ord(ch) < 32 or ord(ch) == 127 for ch in value), code)


def _id(value: Any, code: str) -> None:
    require(type(value) is str and KEBAB_ID.fullmatch(value) is not None, code)


def _time_int(value: Any, code: str, nullable: bool = False) -> None:
    if nullable and value is None:
        return
    _int(value, 0, 4_102_444_800, code)


def unknown_cell() -> dict:
    return {"value": "unknown", "origin": "unknown", "status": "unknown",
            "evidence_version": None}


def known_cell(value: str, origin: str = "user_explicit", evidence_version: Optional[int] = None) -> dict:
    return {"value": value, "origin": origin, "status": "known",
            "evidence_version": evidence_version}


def conflict_cell(origin: str = "derived", evidence_version: Optional[int] = None) -> dict:
    return {"value": "unknown", "origin": origin, "status": "conflict",
            "evidence_version": evidence_version}


def map_scope_text(sector_text: Optional[str], scenario_text: Optional[str], *,
                   origin: str = "user_explicit", evidence_revision: int = 1) -> dict:
    """Map explicit wording to closed enums; never infer a missing value as known.

    ``origin='derived'`` is for an explicitly labelled inference and therefore
    still requires explicit selection. Unmapped text remains unknown.
    """
    require(origin in ("user_explicit", "derived"), "invalid_scope_origin")
    sector_map = {
        "智能硬件": "smart_hardware", "硬件": "smart_hardware",
        "smart hardware": "smart_hardware", "制造业": "manufacturing",
        "manufacturing": "manufacturing", "企业软件": "enterprise_software",
        "enterprise software": "enterprise_software", "跨行业": "cross_industry",
        "其他": "other",
    }
    scenario_map = {
        "产品可行性": "product_feasibility", "产品验证": "product_feasibility",
        "product feasibility": "product_feasibility", "售后ai": "aftersales_ai",
        "售后AI": "aftersales_ai", "aftersales ai": "aftersales_ai",
        "竞品比较": "competitive_comparison", "竞争比较": "competitive_comparison",
        "知识问答": "knowledge_qa", "knowledge qa": "knowledge_qa", "其他": "other",
    }
    def lookup(text: Optional[str], mapping: dict) -> Optional[str]:
        if text is None:
            return None
        stripped = text.strip()
        return mapping.get(stripped) or mapping.get(stripped.lower())
    sector = lookup(sector_text, sector_map)
    scenario = lookup(scenario_text, scenario_map)
    return {
        "sector": known_cell(sector, origin, evidence_revision) if sector else unknown_cell(),
        "scenario": known_cell(scenario, origin, evidence_revision) if scenario else unknown_cell(),
    }


def build_local_brief(*, intent_revision: int, evidence_revision: int,
                      accepted_constraints: Optional[dict] = None,
                      known_facts: Optional[list] = None,
                      research_scope: Optional[dict] = None,
                      source_states: Optional[dict] = None,
                      local_context: Optional[dict] = None) -> dict:
    """Build the local bilateral brief. This object is never sent on the wire."""
    brief = {
        "intent_revision": intent_revision,
        "evidence_revision": evidence_revision,
        "accepted_constraints": accepted_constraints or {},
        "known_facts": known_facts or [],
        "research_scope": research_scope or {"sector": unknown_cell(), "scenario": unknown_cell()},
        "source_states": source_states or {},
        "local_context": local_context or {},
    }
    _reject_excluded(brief)
    return brief


def prepare_request(*, request_id: str, intent_revision: int,
                    evidence_revision: int, brief_digest: str, mode: str,
                    demand: dict, supply: dict, budget: dict, capabilities: list,
                    research_scope: dict, track_selection: Optional[dict] = None) -> dict:
    req = {
        "schema": REQUEST_SCHEMA, "request_id": request_id,
        "consumer": {"product": v1.PRODUCT, "version": v1.VERSION},
        "intent_revision": intent_revision, "evidence_revision": evidence_revision,
        "brief_digest": brief_digest, "mode": mode, "demand": demand,
        "supply": supply, "budget": budget, "capabilities": capabilities,
        "research_scope": research_scope, "track_selection": track_selection,
    }
    validate_request(req)
    return req


def validate_request(req: Any) -> None:
    _reject_excluded(req)
    _object(req, (
        "schema", "request_id", "consumer", "intent_revision", "evidence_revision",
        "brief_digest", "mode", "demand", "supply", "budget", "capabilities",
        "research_scope", "track_selection",
    ), "invalid_request")
    base = {key: value for key, value in req.items()
            if key not in ("research_scope", "track_selection")}
    base["schema"] = v1.REQUEST_SCHEMA
    v1.validate_request(base)
    require(req["schema"] == REQUEST_SCHEMA, "invalid_schema")
    _object(req["research_scope"], ("sector", "scenario"), "invalid_research_scope")
    _cell(req["research_scope"]["sector"], SECTORS, req["evidence_revision"])
    _cell(req["research_scope"]["scenario"], SCENARIOS, req["evidence_revision"])
    selection = req["track_selection"]
    if selection is not None:
        _object(selection, ("id", "version", "catalog_revision"), "invalid_track_selection")
        _id(selection["id"], "invalid_track_selection")
        _int(selection["version"], 1, 1_000_000, "invalid_track_selection")
        _int(selection["catalog_revision"], 1, 2_147_483_647, "invalid_track_selection")


def validate_catalog(catalog: Any) -> dict:
    _reject_excluded(catalog)
    _object(catalog, ("schema", "templates", "research_tracks"), "invalid_catalog")
    require(catalog["schema"] == CATALOG_SCHEMA, "invalid_catalog")
    templates = v1.validate_catalog({"schema": v1.CATALOG_SCHEMA,
                                     "templates": catalog["templates"]})
    tracks_raw = catalog["research_tracks"]
    require(type(tracks_raw) is list and len(tracks_raw) <= MAX_TRACKS, "invalid_catalog")
    require(not (set(templates) & {t.get("id") for t in tracks_raw if isinstance(t, dict)}),
            "duplicate_template")
    tracks = {}
    for track in tracks_raw:
        _object(track, ("id", "version", "display_name", "sector_ids", "scenario_ids",
                        "allowed_goals", "active", "review", "adjustment"), "invalid_track")
        _id(track["id"], "invalid_track")
        require(track["id"] not in tracks, "duplicate_template")
        _int(track["version"], 1, 1_000_000, "invalid_track")
        _display(track["display_name"], "invalid_track")
        _array(track["sector_ids"], SECTORS, 1, 6, "invalid_track")
        _array(track["scenario_ids"], SCENARIOS, 1, 6, "invalid_track")
        _array(track["allowed_goals"], v1.GOALS, 1, 5, "invalid_track")
        require(type(track["active"]) is bool, "invalid_track")
        review = track["review"]
        _object(review, ("status", "basis", "reviewed_at", "valid_from", "expires_at"),
                "invalid_review")
        _enum(review["status"], ("draft", "approved"), "invalid_review")
        _enum(review["basis"], ("synthetic_method_seed", "manual_review"), "invalid_review")
        for key in ("reviewed_at", "valid_from", "expires_at"):
            _time_int(review[key], "invalid_review", nullable=True)
        if review["status"] == "draft":
            require(all(review[key] is None for key in ("reviewed_at", "valid_from", "expires_at")),
                    "invalid_review")
            require(track["active"] is False, "invalid_track")
        else:
            require(all(_is_finite_num(review[key]) for key in ("reviewed_at", "valid_from", "expires_at")),
                    "invalid_review")
            require(review["reviewed_at"] <= review["valid_from"] < review["expires_at"],
                    "invalid_review")
        adjustment = track["adjustment"]
        _object(adjustment, ("query_order", "source_order", "check_order",
                             "domain_checks", "budget_caps"), "invalid_adjustment")
        _array(adjustment["query_order"], v1.AXES, 0, 8, "invalid_adjustment")
        _array(adjustment["source_order"], v1.SOURCES, 0, 4, "invalid_adjustment")
        _array(adjustment["check_order"], v1.CHECKS, 0, 10, "invalid_adjustment")
        _array(adjustment["domain_checks"], DOMAIN_CHECKS, 1, 13, "invalid_adjustment")
        _budget(adjustment["budget_caps"], "invalid_adjustment")
        tracks[track["id"]] = track
    return {"templates": templates, "tracks": tracks}


def _plan_v2(plan: Any) -> None:
    require(type(plan) is dict, "invalid_plan")
    _object(plan, ("query_axes", "source_classes", "checks", "stop_rules", "budget",
                   "domain_checks"), "invalid_plan")
    base = {key: value for key, value in plan.items() if key != "domain_checks"}
    v1._plan(base)
    require(len(plan["query_axes"]) >= 1 and len(plan["source_classes"]) >= 1,
            "selected_plan_empty")
    _array(plan["domain_checks"], DOMAIN_CHECKS, 1, 13, "selected_plan_empty")


def _candidate(candidate: Any) -> None:
    _object(candidate, ("id", "version", "display_name", "sector_ids", "scenario_ids",
                        "allowed_goals", "expires_at"), "invalid_candidate")
    _id(candidate["id"], "invalid_candidate")
    _int(candidate["version"], 1, 1_000_000, "invalid_candidate")
    _display(candidate["display_name"], "invalid_candidate")
    _array(candidate["sector_ids"], SECTORS, 1, 6, "invalid_candidate")
    _array(candidate["scenario_ids"], SCENARIOS, 1, 6, "invalid_candidate")
    _array(candidate["allowed_goals"], v1.GOALS, 1, 5, "invalid_candidate")
    _time_int(candidate["expires_at"], "invalid_candidate")


def _evaluation(evaluation: Any) -> None:
    _object(evaluation, ("id", "version", "display_name", "eligible", "reasons", "expires_at"),
            "invalid_evaluation")
    _id(evaluation["id"], "invalid_evaluation")
    _int(evaluation["version"], 1, 1_000_000, "invalid_evaluation")
    _display(evaluation["display_name"], "invalid_evaluation")
    require(type(evaluation["eligible"]) is bool, "invalid_evaluation")
    _array(evaluation["reasons"], TRACK_REASONS, 0, 17, "invalid_evaluation")
    _time_int(evaluation["expires_at"], "invalid_evaluation", nullable=True)
    reasons = set(evaluation["reasons"])
    if evaluation["eligible"]:
        require(not (reasons - NON_REJECTION_REASONS), "contradictory_evaluation")
    else:
        require(bool(reasons) and "track_selected" not in reasons,
                "contradictory_evaluation")


def _scope_matches(ids: list, cell: dict) -> bool:
    if cell["status"] == "conflict":
        return False
    if cell["status"] == "unknown":
        return "unknown" in ids
    return cell["value"] in ids


def _candidate_covers(candidate: dict, request: dict) -> bool:
    goal = request["demand"]["goal"]
    return (
        goal["status"] != "conflict" and goal["value"] in candidate["allowed_goals"]
        and _scope_matches(candidate["sector_ids"], request["research_scope"]["sector"])
        and _scope_matches(candidate["scenario_ids"], request["research_scope"]["scenario"])
    )


def _unique_index(items: list, validator: Callable[[Any], None], code: str) -> dict:
    require(type(items) is list and len(items) <= MAX_TRACKS, code)
    result = {}
    for item in items:
        validator(item)
        require(item["id"] not in result, "duplicate_track_id")
        result[item["id"]] = item
    return result


def validate_response(resp: Any, request: Optional[dict] = None,
                      catalog: Optional[dict] = None) -> None:
    _reject_excluded(resp)
    if request is not None:
        validate_request(request)
    _object(resp, (
        "schema", "request_id", "intent_revision", "evidence_revision", "request_digest",
        "decision_id", "status", "catalog_revision", "strategy", "plan", "reason_codes",
        "issued_at", "expires_at", "track", "candidates", "track_evaluations", "selection_mode",
    ), "invalid_response")
    require(resp["schema"] == RESPONSE_SCHEMA, "invalid_schema")
    _uuid(resp["request_id"])
    _int(resp["intent_revision"], 1, 1_000_000)
    _int(resp["evidence_revision"], 1, 1_000_000)
    require(type(resp["request_digest"]) is str and HEX64.fullmatch(resp["request_digest"]),
            "invalid_digest")
    _uuid(resp["decision_id"])
    _int(resp["catalog_revision"], 1, 2_147_483_647)
    _enum(resp["status"], ("selected", "skipped", "no_match", "needs_selection"), "invalid_response")
    _array(resp["reason_codes"], REASON_CODES, 0, 23, "invalid_response")
    require(_is_finite_num(resp["issued_at"]) and _is_finite_num(resp["expires_at"]),
            "non_finite_time")
    _enum(resp["selection_mode"], ("automatic_unique", "explicit", "none"), "invalid_response")

    candidates = _unique_index(resp["candidates"], _candidate, "invalid_response")
    evaluations = _unique_index(resp["track_evaluations"], _evaluation, "invalid_response")
    for track_id, evaluation in evaluations.items():
        if track_id in candidates:
            require(evaluation["version"] == candidates[track_id]["version"],
                    "track_version_inconsistent")
            require(evaluation["expires_at"] == candidates[track_id]["expires_at"],
                    "track_expiry_inconsistent")
    for track_id, candidate in candidates.items():
        evaluation = evaluations.get(track_id)
        require(evaluation is not None and evaluation["eligible"], "candidate_not_eligible")
        require(evaluation["expires_at"] == candidate["expires_at"], "track_expiry_inconsistent")
        if request is not None:
            require(_candidate_covers(candidate, request), "candidate_out_of_scope")

    status = resp["status"]
    if status == "selected":
        v1._strategy(resp["strategy"])
        _plan_v2(resp["plan"])
        track = resp["track"]
        require(type(track) is dict, "invalid_track")
        _object(track, ("id", "version", "display_name", "digest", "expires_at"), "invalid_track")
        _id(track["id"], "invalid_track")
        _int(track["version"], 1, 1_000_000, "invalid_track")
        _display(track["display_name"], "invalid_track")
        require(type(track["digest"]) is str and HEX64.fullmatch(track["digest"]), "invalid_digest")
        _time_int(track["expires_at"], "invalid_track")
        require(resp["selection_mode"] in ("automatic_unique", "explicit"), "invalid_selection_mode")
        require("track_selected" in resp["reason_codes"], "invalid_response")
        candidate = candidates.get(track["id"])
        evaluation = evaluations.get(track["id"])
        require(candidate is not None and candidate["version"] == track["version"],
                "selected_track_candidate_mismatch")
        require(evaluation is not None and evaluation["eligible"] and
                not (set(evaluation["reasons"]) - NON_REJECTION_REASONS),
                "selected_track_not_eligible")
        require(candidate["expires_at"] == track["expires_at"] and
                evaluation["expires_at"] == track["expires_at"], "track_expiry_inconsistent")
        if resp["selection_mode"] == "automatic_unique":
            require(len(candidates) == 1, "automatic_selection_not_unique")
    else:
        require(resp["strategy"] is None, "unexpected_strategy")
        require(resp["plan"] is None, "unexpected_plan")
        require(resp["track"] is None, "unexpected_track")
        require(resp["selection_mode"] == "none", "invalid_selection_mode")
        if status == "needs_selection":
            require(len(candidates) >= 1, "needs_selection_without_candidates")
            require("track_selection_required" in resp["reason_codes"], "invalid_response")
        # no_match/skipped may retain eligible, in-scope candidates to explain
        # the rejection and support a later explicit local choice. The null
        # execution objects and selection_mode=none above still forbid adoption.

    if request is not None:
        validate_request(request)
        require(resp["request_id"] == request["request_id"], "request_id_mismatch")
        require(resp["intent_revision"] == request["intent_revision"], "intent_revision_mismatch")
        require(resp["evidence_revision"] == request["evidence_revision"], "evidence_revision_mismatch")
        require(resp["request_digest"] == digest(request), "request_digest_mismatch")
        selection = request["track_selection"]
        if status == "selected":
            if selection is None:
                require(resp["selection_mode"] == "automatic_unique", "invalid_selection_mode")
                for key in ("sector", "scenario"):
                    cell = request["research_scope"][key]
                    require(cell["status"] in ("known", "unknown"),
                            "automatic_scope_not_explicit")
                    if cell["status"] == "known":
                        require(cell["origin"] == "user_explicit",
                                "automatic_scope_not_explicit")
                    # Unknown remains unknown. It is eligible only when the
                    # selected candidate explicitly covers unknown, as already
                    # enforced by _candidate_covers for every candidate.
            else:
                require(resp["selection_mode"] == "explicit", "invalid_selection_mode")
                require(resp["track"]["id"] == selection["id"] and
                        resp["track"]["version"] == selection["version"] and
                        resp["catalog_revision"] == selection["catalog_revision"],
                        "explicit_track_binding_mismatch")
            for key in BUDGET_KEYS:
                require(resp["plan"]["budget"][key] <= request["budget"][key],
                        "budget_exceeds_request")
        else:
            # A changed catalog or an old response must never be silently rebound.
            if selection is not None and resp["catalog_revision"] != selection["catalog_revision"]:
                require("track_catalog_changed" in resp["reason_codes"], "catalog_revision_mismatch")

    if catalog is not None:
        index = validate_catalog(catalog)
        if status == "selected":
            track_obj = index["tracks"].get(resp["track"]["id"])
            require(track_obj is not None, "track_not_found")
            require(track_obj["version"] == resp["track"]["version"], "track_version_mismatch")
            require(track_obj["active"] is True, "track_paused")
            require(track_obj["review"]["status"] == "approved", "track_unreviewed")
            require(digest(track_obj) == resp["track"]["digest"], "track_digest_mismatch")
            require(track_obj["review"]["expires_at"] == resp["track"]["expires_at"],
                    "track_expiry_inconsistent")
            template = index["templates"].get(resp["strategy"]["id"])
            require(template is not None, "invalid_strategy")
            require(template["version"] == resp["strategy"]["version"], "invalid_strategy")
            require(digest(template) == resp["strategy"]["digest"], "strategy_digest_mismatch")
            for field_name in ("query_axes", "source_classes", "checks", "stop_rules"):
                require(set(resp["plan"][field_name]) == set(template["plan"][field_name]),
                        "plan_not_base_reorder")
            require(set(resp["plan"]["domain_checks"]) ==
                    set(track_obj["adjustment"]["domain_checks"]), "domain_checks_mismatch")
            for key in BUDGET_KEYS:
                require(resp["plan"]["budget"][key] <= template["plan"]["budget"][key] and
                        resp["plan"]["budget"][key] <= track_obj["adjustment"]["budget_caps"][key],
                        "budget_exceeds_cap")


def check_time_window(resp: dict, clock: Callable[[], float] = time.time,
                      received_utc: Optional[float] = None,
                      catalog: Optional[dict] = None) -> None:
    v1.check_time_window(resp, clock=clock, received_utc=received_utc)
    if resp.get("track") is not None:
        require(resp["expires_at"] <= resp["track"]["expires_at"], "decision_outlives_track")
        require(clock() < resp["track"]["expires_at"], "track_review_expired")
        if catalog is not None:
            track_obj = validate_catalog(catalog)["tracks"].get(resp["track"]["id"])
            require(track_obj is not None, "track_not_found")
            require(track_obj["review"]["valid_from"] <= clock(), "track_not_yet_effective")


@dataclass(frozen=True)
class DecisionGuard:
    """Exact selected response plus immutable wall/monotonic receive binding."""
    response: dict
    request: dict
    received_utc: float
    received_monotonic: float
    deadline_monotonic: float
    track_expires_at: Optional[float]
    request_digest: str
    response_digest: str

    @classmethod
    def bind(cls, response: dict, request: dict, *, catalog: Optional[dict] = None,
             clock: Callable[[], float] = time.time,
             monotonic: Callable[[], float] = time.monotonic,
             received_utc: Optional[float] = None,
             received_monotonic: Optional[float] = None) -> "DecisionGuard":
        require(response.get("status") == "selected", "decision_not_selected")
        now = clock() if received_utc is None else received_utc
        mono = monotonic() if received_monotonic is None else received_monotonic
        require(v1._is_finite_num(now) and v1._is_finite_num(mono), "non_finite_time")
        validate_response(response, request=request, catalog=catalog)
        check_time_window(response, clock=lambda: now, received_utc=now, catalog=catalog)
        remaining = min(response["expires_at"] - now, MAX_DURATION_SECONDS)
        track_expiry = response["track"]["expires_at"] if response.get("track") else None
        if track_expiry is not None:
            remaining = min(remaining, track_expiry - now)
        require(remaining > 0, "deadline_elapsed")
        return cls(response=copy.deepcopy(response), request=copy.deepcopy(request),
                   received_utc=now, received_monotonic=mono,
                   deadline_monotonic=mono + remaining, track_expires_at=track_expiry,
                   request_digest=digest(request), response_digest=digest(response))

    def assert_executable(self, *, current_intent_revision: int,
                          current_evidence_revision: int,
                          clock: Callable[[], float] = time.time,
                          monotonic: Callable[[], float] = time.monotonic) -> None:
        require(digest(self.request) == self.request_digest and
                digest(self.response) == self.response_digest, "decision_changed")
        require(monotonic() < self.deadline_monotonic, "deadline_elapsed")
        if self.track_expires_at is not None:
            require(clock() < self.track_expires_at, "track_review_expired")
        require(clock() < self.response["expires_at"], "expired")
        require(current_intent_revision == self.request["intent_revision"], "intent_revision_mismatch")
        require(current_evidence_revision == self.request["evidence_revision"], "evidence_revision_mismatch")


def validate_feedback(fb: Any, *, decision: dict, request: Optional[dict] = None) -> None:
    _reject_excluded(fb)
    require(fb.get("schema") == FEEDBACK_SCHEMA, "invalid_feedback")
    require(decision.get("schema") == RESPONSE_SCHEMA and decision.get("status") == "selected",
            "feedback_requires_selected_decision")
    base = dict(fb)
    base["schema"] = v1.FEEDBACK_SCHEMA
    v1.validate_feedback(base)
    require(fb["decision_id"] == decision["decision_id"], "feedback_decision_mismatch")
    require(fb["request_digest"] == decision["request_digest"], "feedback_request_digest_mismatch")
    if request is not None:
        require(fb["request_digest"] == digest(request), "feedback_request_digest_mismatch")
        require(decision["request_id"] == request["request_id"], "request_id_mismatch")


def _default_transport(request: dict, *, base_url: str, timeout: float,
                       monotonic: Callable[[], float] = time.monotonic,
                       deadline_monotonic: Optional[float] = None) -> dict:
    """Fixed direct endpoint with v2's independent 64 KiB response ceiling."""
    return v1._bounded_transport(
        request, base_url=base_url, timeout=timeout,
        request_validator=validate_request, response_max_bytes=v1.CATALOG_MAX_BYTES,
        monotonic=monotonic, deadline_monotonic=deadline_monotonic)


def _isolated_v2_transport(request: dict, *, base_url: str, timeout: float,
                           monotonic: Callable[[], float] = time.monotonic,
                           deadline_monotonic: Optional[float] = None,
                           observation_sink: Optional[list] = None) -> dict:
    """Killable full-chain deadline plus v2's closed schema and 64 KiB limit."""
    return v1._isolated_transport(
        request, base_url=base_url, timeout=timeout, protocol="v2",
        response_max_bytes=v1.CATALOG_MAX_BYTES, monotonic=monotonic,
        deadline_monotonic=deadline_monotonic,
        observation_sink=observation_sink)


# Marks the built-in isolated transport: v1.StrategyClient wraps only marked
# transports with a per-client observation sink; custom ones keep signature.
_isolated_v2_transport._paper_observant = True


@dataclass
class ResolveResult:
    source: str
    response: Optional[dict] = None
    reason: Optional[str] = None
    applied_native: bool = False
    network_attempts: int = 0
    guard: Optional[DecisionGuard] = None
    diagnostic: Optional[dict] = None  # separate paper.diagnostic.v1 summary


class StrategyClientV2:
    """Real v2 client; every send path shares the closed bounded v1 transport."""

    def __init__(self, transport: Optional[Callable[..., dict]] = None):
        self.transport = transport
        self._v1 = v1.StrategyClient(
            transport=transport, request_validator=validate_request,
            default_transport=_isolated_v2_transport, response_max_bytes=v1.CATALOG_MAX_BYTES)

    def prepare_request(self, **kwargs) -> dict:
        return prepare_request(**kwargs)

    def build_local_brief(self, **kwargs) -> dict:
        return build_local_brief(**kwargs)

    def compute_brief_digest(self, salt: bytes, brief: dict) -> str:
        return compute_brief_digest(salt, brief)

    def validate_response(self, resp: dict, request: dict, *, catalog: Optional[dict] = None,
                          clock: Callable[[], float] = time.time,
                          received_utc: Optional[float] = None) -> Tuple[bool, str]:
        try:
            validate_response(resp, request=request, catalog=catalog)
            check_time_window(resp, clock=clock, received_utc=received_utc, catalog=catalog)
        except Error as exc:
            return False, exc.code
        return True, "ok"

    def call_dev(self, request: dict, base_url: str = DEV_BASE_URL,
                 timeout: float = DEFAULT_TIMEOUT,
                 monotonic: Callable[[], float] = time.monotonic):
        validate_request(request)
        return self._v1.call_dev(request, base_url=base_url, timeout=timeout,
                                 monotonic=monotonic)

    def call_production(self, request: dict, timeout: float = DEFAULT_TIMEOUT,
                        monotonic: Callable[[], float] = time.monotonic):
        """Explicit released HTTPS entry; never sends feedback or local briefs."""
        validate_request(request)
        return self._v1.call_dev(request, base_url=v1.PRODUCTION_BASE_URL,
                                 timeout=timeout, monotonic=monotonic)

    def resolve_production(self, request: dict, *, timeout: float = DEFAULT_TIMEOUT,
                           catalog: Optional[dict] = None,
                           clock: Callable[[], float] = time.time,
                           monotonic: Callable[[], float] = time.monotonic) -> ResolveResult:
        result = self.resolve(request, dev=True, base_url=v1.PRODUCTION_BASE_URL,
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
        validate_request(request)
        request_id = request.get("request_id")

        def _diag(reason, stage, attempts=0, exc=None, observation=None):
            return v1.build_diagnostic(
                reason=reason, observed_stage=stage,
                transport_attempts=attempts, request_id=request_id, exc=exc,
                observation=observation, client_platform=client_platform)

        if request["mode"] in v1.SHORT_PATH_MODES:
            return ResolveResult(
                "native_short_path", reason="native_short_path",
                applied_native=True,
                diagnostic=_diag("native_short_path", "not_observed"))
        if v1._capability_limited(request):
            return ResolveResult(
                "capability_limited", reason="capability_limited",
                applied_native=True,
                diagnostic=_diag("capability_limited", "not_observed"))
        if not dev:
            return ResolveResult(
                "local_only", reason="local_only", applied_native=True,
                diagnostic=_diag("local_only", "not_observed"))
        # Pre-send source self-check: mismatch returns natively, zero network.
        if v1.source_fingerprint_status() == "mismatch":
            return ResolveResult(
                "native_fallback", reason="source_fingerprint_mismatch",
                applied_native=True, network_attempts=0,
                diagnostic=_diag("source_fingerprint_mismatch", "pre_send"))
        resp, exc, attempts, observation = self._v1._call_dev(
            request, base_url, timeout, monotonic)
        if resp is None:
            if isinstance(exc, Error):
                reason = exc.code
            elif isinstance(exc, urllib.error.HTTPError):
                reason = "http_rejected"  # real HTTP response, not a network unknown
            else:
                reason = "transport_failure"
            stage = v1._stage_for_failure(exc, reason, observed=bool(
                observation) or getattr(exc, "observed_http_status", None) is not None)
            return ResolveResult(
                "native_fallback", reason=reason, applied_native=True,
                network_attempts=attempts,
                diagnostic=_diag(v1._diagnostic_reason(exc, reason), stage,
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
        if resp["status"] == "needs_selection":
            return ResolveResult(
                "native_selection_required", response=resp,
                reason="needs_selection", applied_native=True,
                network_attempts=attempts,
                diagnostic=_diag("needs_selection", "business_response",
                                 attempts=attempts, observation=observation))
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


def _load_json_path(path: str) -> dict:
    # Bounded read first, then format validation; file problems surface as a
    # safe closed code, never as a traceback carrying a private path.
    try:
        with open(path, "rb") as handle:
            data = handle.read(v1.CATALOG_MAX_BYTES + 2)
    except OSError as exc:
        raise Error("input_file_unavailable", 400) from exc
    return strict_json(data, maximum=v1.CATALOG_MAX_BYTES)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    prep = sub.add_parser("prepare", help="Prepare a paper.intent.v2 request without network")
    prep.add_argument("--request-json", required=True)
    val = sub.add_parser("validate-response", help="Validate a v2 response without network")
    val.add_argument("--request-json", required=True)
    val.add_argument("--response-json", required=True)
    val.add_argument("--catalog-json")
    val.add_argument("--now", type=float)
    dev = sub.add_parser("dev-call", help="Explicit localhost:8768 integration call")
    dev.add_argument("--request-json", required=True)
    dev.add_argument("--base-url", default=DEV_BASE_URL)
    dev.add_argument("--catalog-json")
    dev.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    prod = sub.add_parser("production-call", help="Explicit released HTTPS strategy call")
    prod.add_argument("--request-json", required=True)
    prod.add_argument("--catalog-json")
    prod.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    args = parser.parse_args(argv)
    try:
        if args.cmd == "prepare":
            raw = _load_json_path(args.request_json)
            prepared = prepare_request(
                request_id=raw["request_id"], intent_revision=raw["intent_revision"],
                evidence_revision=raw["evidence_revision"], brief_digest=raw["brief_digest"],
                mode=raw["mode"], demand=raw["demand"], supply=raw["supply"],
                budget=raw["budget"], capabilities=raw["capabilities"],
                research_scope=raw["research_scope"], track_selection=raw["track_selection"],
            )
            v1._emit_json({"request": prepared,
                           "request_digest": digest(prepared)}, indent=2)
        elif args.cmd == "validate-response":
            request = _load_json_path(args.request_json)
            response = _load_json_path(args.response_json)
            catalog = _load_json_path(args.catalog_json) if args.catalog_json else None
            clock = (lambda: args.now) if args.now is not None else time.time
            ok, reason = StrategyClientV2().validate_response(response, request, catalog=catalog, clock=clock)
            v1._emit_json({"valid": ok, "reason": reason})
            return 0 if ok else 1
        else:
            request = _load_json_path(args.request_json)
            catalog = _load_json_path(args.catalog_json) if args.catalog_json else None
            if args.cmd == "production-call":
                result = StrategyClientV2().resolve_production(
                    request, timeout=args.timeout, catalog=catalog)
            else:
                result = StrategyClientV2().resolve(
                    request, dev=True, base_url=args.base_url,
                    timeout=args.timeout, catalog=catalog)
            v1._emit_json({"source": result.source, "reason": result.reason,
                           "applied_native": result.applied_native,
                           "network_attempts": result.network_attempts,
                           "guard_present": result.guard is not None,
                           "response": result.response,
                           "diagnostic": result.diagnostic}, indent=2)
            return 0 if result.source in ("dev_service", "production_service") else 2
    except Error as exc:
        # Rejections before resolve are pre-send; diagnostic stays separate
        # and never carries the offending path/content.
        output = {"error": exc.code, "status": exc.status}
        diagnostic = v1.build_diagnostic(
            reason=exc.code, observed_stage="pre_send",
            transport_attempts=0, exc=exc)
        if diagnostic is not None:
            output["diagnostic"] = diagnostic
        v1._emit_json(output)
        return 1
    except OSError:
        output = {"error": "input_file_unavailable", "status": 400}
        diagnostic = v1.build_diagnostic(
            reason="input_file_unavailable", observed_stage="pre_send",
            transport_attempts=0)
        if diagnostic is not None:
            output["diagnostic"] = diagnostic
        v1._emit_json(output)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
