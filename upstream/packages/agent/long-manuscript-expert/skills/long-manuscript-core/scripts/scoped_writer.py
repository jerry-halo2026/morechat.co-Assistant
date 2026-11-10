#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Portable guarded writer for long-manuscript-expert 2026.11.5 (rev 2).

Standard library only. Fixes the independently reproduced P1 boundaries:

* claim-before-write: the operation id is EXCLUSIVELY claimed before any product
  byte is written; same id + identical body/target/baselines is a read-only
  lookup, any different target/body/baselines is refused with ZERO new writes.
* safe operation ids: no separators, absolute paths, dot segments or overlength.
  Every derived path (including receipts) is real-root checked with symlink
  boundary checks.
* receipts use exclusive creation only (no exists()+write_text race).
* the registered writer is the ONLY callable that writes product bytes; its
  identity and CURRENT full source bytes are rechecked before every write.
* atomic publication: complete bytes go into a private temp file first, then a
  hard link atomically publishes the fully written content under the target
  name. A collision refuses; no visible zero-byte product file is produced.
* query separates historical write success from CURRENT byte integrity and
  never writes.
* editorial scope is a separate, explicit validator (a path guard is not an
  author-scope guard).

This is a NEW portable reconstruction, not byte-equivalent to any predecessor.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import types
import uuid
from datetime import datetime, timezone
from pathlib import Path

VERSION = "2026.11.5"
# Bounded read-only compatibility: a legal old 2026.11.0200 claim+receipt
# pair may reconcile READ-ONLY with the ORIGINAL ids/paths/digests preserved.
# Cross-version splicing is refused: an old receipt never binds to a new
# claim and vice versa. New claims/receipts always stamp the new version.
LEGACY_WRITE_VERSION = "2026.11.0200"
GUARD_SCHEMA = "paper.scoped-write-guard.v2"
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
MAX_ID_LEN = 64


class GuardError(RuntimeError):
    pass


class SourceChanged(GuardError):
    pass


class Collision(GuardError):
    pass


class OutsideScope(GuardError):
    pass


class UnsafeOperationId(GuardError):
    pass


class OperationConflict(GuardError):
    pass


class WriterUnbound(GuardError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def validate_operation_id(operation_id: str) -> str:
    """Strict, path-safe operation id. No traversal, no separators, no dot segments."""
    if not isinstance(operation_id, str) or not SAFE_ID.fullmatch(operation_id):
        raise UnsafeOperationId("operation_id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
    if len(operation_id) > MAX_ID_LEN or operation_id in (".", ".."):
        raise UnsafeOperationId("operation_id length or dot segment rejected")
    if ".." in operation_id:
        raise UnsafeOperationId("dot segment rejected")
    return operation_id


def default_writer(path: Path, data: bytes) -> int:
    """The concrete, registered writer: writes COMPLETE bytes exclusively.

    This function is the only product-byte writer; the guard calls it by
    identity. Its source is inside the trusted code root.
    """
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    return len(data)


def _contains_path(root: Path, candidate: Path) -> bool:
    """Platform-independent resolved path relation (no string prefix)."""
    try:
        r = Path(root).resolve(strict=True)
        c = Path(candidate).resolve()
        return c == r or c.is_relative_to(r)
    except (OSError, ValueError):
        return False


def _assert_safe_target(root: Path, target: Path) -> Path:
    """Real root relation + symlink boundary for ANY derived path."""
    resolved = Path(target).resolve()
    if not _contains_path(root, resolved):
        raise OutsideScope(f"derived path outside guard root: {target}")
    # Reject symlinks in the parent chain itself.
    cur = Path(target).parent
    while True:
        if cur.is_symlink():
            raise OutsideScope(f"symlink parent in derived path: {cur}")
        if cur == root.resolve() or cur.parent == cur:
            break
        cur = cur.parent
    return resolved


def _exclusive_write(path: Path, data: bytes) -> None:
    """Exclusive creation with complete bytes and fsync; never overwrite."""
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
    except BaseException:
        try:
            path.unlink()
        except OSError:
            pass
        raise


class ScopedWriter:
    def __init__(self, root: str | Path, *, code_root: str | Path | None = None) -> None:
        self.root = Path(root).resolve(strict=True)
        # Trusted code root is separate from the user project root.
        self.code_root = (Path(code_root).resolve(strict=True) if code_root
                          else Path(__file__).resolve().parent)
        self.receipts_dir = _assert_safe_target(self.root, self.root / "receipts")
        self.receipts_dir.mkdir(parents=True, exist_ok=True)
        self._writer_fn = None
        self._writer_entry = None
        self._writer_obj = None          # the exact registered function OBJECT
        self._writer_code = None         # its exact code object
        self.events: list[dict] = []
        self.stats = {
            "write_attempts": 0, "claims_created": 0, "product_writes": 0,
            "registered_writer_calls": 0, "before_write_checks_started": 0,
            "before_write_checks_succeeded": 0, "full_byte_rechecks": 0,
            "atomic_publications": 0, "collisions_refused": 0,
            "source_changes_refused": 0, "operation_conflicts_refused": 0,
            "unsafe_ids_refused": 0, "writer_source_changes_refused": 0,
            "closure_checks": 0, "closure_changes_refused": 0,
            "same_id_queries": 0, "query_writes": 0, "readbacks": 0,
        }
        self.register_writer(default_writer, name="scoped_writer.default_writer")

    # ---- real writer binding ------------------------------------------------
    def register_writer(self, func, name: str | None = None) -> dict:
        if not callable(func) or not isinstance(func, types.FunctionType):
            raise WriterUnbound("writer must be a plain function")
        code = getattr(func, "__code__", None)
        if code is None:
            raise WriterUnbound("writer has no __code__")
        source = Path(code.co_filename).resolve()
        if not _contains_path(self.code_root, source):
            raise OutsideScope(f"writer source outside trusted code root: {source}")
        data = source.read_bytes()
        self._writer_fn = func
        self._writer_obj = func
        self._writer_code = code
        self._writer_entry = {
            "function": name or func.__qualname__,
            "module": func.__module__,
            "source": str(source).replace("\\", "/"),
            "source_sha256": sha256_bytes(data),
            "code_filename": code.co_filename,
            "registered_after_initialization": True,
        }
        return dict(self._writer_entry)

    def writer_registry(self) -> list[dict]:
        return [dict(self._writer_entry)] if self._writer_entry else []

    def _assert_writer_current(self) -> dict:
        """Exact callable identity + code origin + CURRENT full source bytes.

        The function that will ACTUALLY be invoked must be the very same object
        that was registered (`is`), carry the registered code object, and its
        `__code__.co_filename` must resolve to the registered source file whose
        CURRENT bytes still hash to the registered digest. Type checks alone
        never prove identity.
        """
        if self._writer_fn is None or self._writer_entry is None:
            raise WriterUnbound("no writer registered")
        if self._writer_obj is None or self._writer_code is None:
            raise WriterUnbound("writer registry incomplete; refuse to write")
        if self._writer_fn is not self._writer_obj:
            self.stats["writer_identity_refused"] = self.stats.get("writer_identity_refused", 0) + 1
            raise WriterUnbound(
                "bound writer object differs from the registered function object; refuse")
        if getattr(self._writer_fn, "__code__", None) is not self._writer_code:
            self.stats["writer_identity_refused"] = self.stats.get("writer_identity_refused", 0) + 1
            raise WriterUnbound("writer code object differs from registered code; refuse")
        try:
            code_filename = Path(self._writer_fn.__code__.co_filename).resolve()
        except (OSError, ValueError) as exc:
            raise WriterUnbound(f"writer code origin unresolvable: {exc}") from exc
        registered_source = Path(self._writer_entry["source"])
        if code_filename != registered_source:
            self.stats["writer_identity_refused"] = self.stats.get("writer_identity_refused", 0) + 1
            raise WriterUnbound(
                "actual callable co_filename does not match registered source; refuse")
        current = registered_source.read_bytes()
        current_sha = sha256_bytes(current)
        if current_sha != self._writer_entry["source_sha256"]:
            self.stats["writer_source_changes_refused"] += 1
            raise SourceChanged("registered writer source bytes changed before write")
        return {"function": self._writer_entry["function"],
                "called": False, "source_sha256_current": current_sha,
                "source_bytes": len(current)}

    # ---- pre-write full byte recheck ---------------------------------------
    def check_baselines(self, baselines: dict[str, dict]) -> list[dict]:
        checks = []
        for rel, expected in sorted(baselines.items()):
            target = _assert_safe_target(self.root, self.root / rel)
            self.stats["before_write_checks_started"] += 1
            data = target.read_bytes()  # COMPLETE bytes, not metadata/slice
            self.stats["full_byte_rechecks"] += 1
            actual_sha = sha256_bytes(data)
            if actual_sha != expected["sha256"] or len(data) != expected["bytes"]:
                self.stats["source_changes_refused"] += 1
                raise SourceChanged(
                    f"source changed before write: {rel} expected {expected['sha256']} got {actual_sha}")
            checks.append({"path": rel, "bytes": len(data), "sha256": actual_sha, "matched": True})
        return checks

    # ---- frozen closure (source-guard): NON-writer dependencies ------------
    def _check_closure(self, closure: dict[str, str]) -> list[dict]:
        """Verify the FROZEN closure immediately before publication.

        ``closure`` maps absolute path (forward slashes) -> sha256 for every
        NON-writer dependency the caller actually consumed (product modules,
        packaged library manifest). This is a READ-ONLY digest check: the
        closure never influences WHAT is written, so its paths grant no write
        authority. Any byte change refuses with ZERO product writes — the
        registered writer source itself is separately enforced by
        ``_assert_writer_current``.
        """
        if not closure:
            return []
        checks = []
        for path_key, expected in sorted(closure.items()):
            if not isinstance(path_key, str) or not path_key or not isinstance(expected, str):
                raise GuardError(f"closure entry malformed: {path_key!r}")
            p = Path(path_key)
            try:
                resolved = p.resolve(strict=True)
            except (OSError, ValueError) as exc:
                raise GuardError(f"closure path unresolvable: {path_key}") from exc
            if not resolved.is_file():
                self.stats["closure_changes_refused"] = (
                    self.stats.get("closure_changes_refused", 0) + 1)
                raise SourceChanged(
                    f"frozen closure member missing before write: {path_key}")
            data = resolved.read_bytes()
            self.stats["closure_checks"] = self.stats.get("closure_checks", 0) + 1
            actual = sha256_bytes(data)
            if actual != expected:
                self.stats["closure_changes_refused"] = (
                    self.stats.get("closure_changes_refused", 0) + 1)
                raise SourceChanged(
                    f"frozen closure changed before write: {path_key} "
                    f"expected {expected} got {actual}")
            checks.append({"path": path_key, "bytes": len(data),
                           "sha256": actual, "matched": True})
        return checks

    # ---- atomic publication -------------------------------------------------
    def _publish(self, target: Path, data: bytes, writer_state: dict) -> dict:
        """Complete bytes in a private temp, then ATOMIC hard-link publication.

        The target name never appears with partial content. A pre-existing
        target makes the link fail, so collisions never overwrite.
        """
        target.parent.mkdir(parents=True, exist_ok=True)
        _assert_safe_target(self.root, target.parent)
        tmp = target.parent / (".tmp-" + uuid.uuid4().hex)
        _assert_safe_target(self.root, tmp)
        writer_state["called"] = True
        self.stats["registered_writer_calls"] += 1
        self._writer_fn(tmp, data)          # the registered writer really writes
        if tmp.read_bytes() != data:
            tmp.unlink(missing_ok=True)
            raise GuardError("registered writer produced incomplete bytes")
        _assert_safe_target(self.root, target)
        if target.exists():
            tmp.unlink(missing_ok=True)
            self.stats["collisions_refused"] += 1
            raise Collision(f"target already exists, refusing overwrite: {target}")
        try:
            os.link(tmp, target)            # atomic, refuse-on-existing publish
            atomic = True
        except (OSError, NotImplementedError) as exc:
            # Honest capability boundary: no atomic publication on this FS.
            tmp.unlink(missing_ok=True)
            raise GuardError(f"atomic_publication_unavailable: {type(exc).__name__}")
        finally:
            if tmp.exists():
                tmp.unlink()
        self.stats["atomic_publications"] += 1
        self.stats["product_writes"] += 1
        return {"atomic_publication": atomic, "overwrite": False,
                "visible_zero_byte_product_file": False}

    # ---- claim-before-write -------------------------------------------------
    # ---- shared CURRENT byte state (query and same-id early return) --------
    def _current_state(self, receipt: dict) -> dict:
        current_path = _assert_safe_target(self.root, self.root / receipt["path"])
        if not current_path.is_file():
            return {"state": "missing", "readback_verified": False,
                    "reason": "product file no longer present; user edits preserved"}
        actual = current_path.read_bytes()
        actual_sha = sha256_bytes(actual)
        changed = (actual_sha != receipt["sha256"] or len(actual) != receipt["bytes"])
        return {"state": "changed" if changed else "verified",
                "readback_verified": not changed,
                "sha256": actual_sha, "bytes": len(actual),
                "reason": "current bytes match historical receipt" if not changed
                          else "current bytes differ (possible user hand edit); do not claim verified"}

    # ---- strict read-only receipt<->claim binding (R2-03) -------------------
    def _load_json(self, path: Path, *, what: str) -> dict:
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise GuardError(f"{what} unreadable/corrupt: {type(exc).__name__}") from exc
        if not isinstance(obj, dict):
            raise GuardError(f"{what} has non-object shape; refuse")
        return obj

    def _validate_receipt_for(self, oid: str, claim: dict) -> tuple[dict, dict | None, str | None]:
        """Strictly reconcile claim and receipt for the REQUESTED original id.

        Returns (receipt, reason). reason is None only when every binding
        agrees: schema, version, kind, receipt.operation_id == claim id ==
        requested id, canonical target path, content sha256/bytes and the
        claim's declared receipt filename. Any mismatch -> reason string; the
        caller returns unknown/conflict with ZERO writes.
        """
        receipt_path = _assert_safe_target(self.receipts_dir,
                                           self.receipts_dir / f"write-{oid}.json")
        if not receipt_path.is_file():
            return None, None  # no receipt at all is not a binding failure
        receipt = self._load_json(receipt_path, what="receipt")
        receipt_version = receipt.get("version")
        # Same-version pairing only: new receipt+new claim, or legacy
        # 2026.11.0200 receipt+legacy claim (read-only reconciliation with
        # original bytes preserved). A mixed pair is cross-version splicing
        # and stays a binding failure with ZERO writes.
        if (receipt.get("schema") != GUARD_SCHEMA
                or receipt_version not in (VERSION, LEGACY_WRITE_VERSION)
                or receipt_version != claim.get("version")):
            return receipt, "receipt_schema_version_mismatch"
        if receipt.get("operation_id") != oid or claim.get("operation_id") != oid:
            return receipt, "receipt_operation_id_mismatch"
        if claim.get("receipt") != receipt_path.name:
            return receipt, "claim_receipt_filename_mismatch"
        if receipt.get("path") != claim.get("path"):
            return receipt, "receipt_target_path_mismatch"
        if (receipt.get("sha256") != claim.get("content_sha256")
                or receipt.get("bytes") != claim.get("content_bytes")):
            return receipt, "receipt_content_digest_mismatch"
        for key in ("state", "label", "completed_at", "publication", "registered_writer"):
            if key not in receipt:
                return receipt, f"receipt_missing_field:{key}"
        return receipt, None

    # ---- claim-before-write -------------------------------------------------
    def _claim(self, operation_id: str, rel_path: str, data: bytes,
               baselines: dict[str, dict]) -> tuple[Path, dict]:
        claim_path = _assert_safe_target(self.receipts_dir,
                                        self.receipts_dir / f"claim-{operation_id}.json")
        receipt_path = _assert_safe_target(self.receipts_dir,
                                          self.receipts_dir / f"write-{operation_id}.json")
        body = {
            "schema": GUARD_SCHEMA, "version": VERSION, "kind": "operation_claim",
            "operation_id": operation_id, "path": rel_path.replace("\\", "/"),
            "content_sha256": sha256_bytes(data), "content_bytes": len(data),
            "baselines": {k: v["sha256"] for k, v in sorted(baselines.items())},
            "receipt": receipt_path.name, "state": "claimed", "at": utc_now(),
        }
        encoded = (json.dumps(body, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        try:
            _exclusive_write(claim_path, encoded)   # EXCLUSIVE, no exists()+write_text
        except FileExistsError:
            self.stats["operation_conflicts_refused"] += 1
            raise OperationConflict(
                "operation id already claimed; compare with existing claim before any write")
        self.stats["claims_created"] += 1
        return receipt_path, body

    def _existing_same_operation(self, operation_id: str, rel_path: str, data: bytes,
                                 baselines: dict[str, dict]) -> dict | None:
        """Same id + identical target/body/baselines -> read-only lookup.
        Any difference -> refuse. Never writes a second product file."""
        claim_path = self.receipts_dir / f"claim-{operation_id}.json"
        receipt_path = self.receipts_dir / f"write-{operation_id}.json"
        if not claim_path.is_file():
            return None
        try:
            claim = json.loads(claim_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            # A competitor/corrupt claim is an existing, unparsed occupancy:
            # refuse safely, never crash and never truncate it.
            self.stats["operation_conflicts_refused"] += 1
            raise OperationConflict("existing claim is unreadable; refuse before any write")
        if not isinstance(claim, dict) or claim.get("kind") != "operation_claim" or not all(
                k in claim for k in ("path", "content_sha256", "content_bytes", "baselines")):
            self.stats["operation_conflicts_refused"] += 1
            raise OperationConflict("existing claim has foreign/incomplete shape; refuse before any write")
        same = (claim["path"] == rel_path.replace("\\", "/")
                and claim["content_sha256"] == sha256_bytes(data)
                and claim["content_bytes"] == len(data)
                and claim["baselines"] == {k: v["sha256"] for k, v in sorted(baselines.items())})
        if not same:
            self.stats["operation_conflicts_refused"] += 1
            raise OperationConflict(
                "same operation id with different target/body/baselines refused before any write")
        if not receipt_path.is_file():
            return {"state": "unknown", "reason": "prior_claim_without_receipt",
                    "receipt": None, "writes": 0, "new_id_created": False,
                    "replay_permitted": False, "claim": claim}
        # R2-03: a receipt under this id must be THIS operation's receipt.
        receipt, reason = self._validate_receipt_for(operation_id, claim)
        if reason is not None:
            self.stats["operation_conflicts_refused"] += 1
            return {"state": "unknown", "reason": f"receipt_binding_conflict:{reason}",
                    "receipt": None, "receipt_observed_foreign": True,
                    "writes": 0, "new_id_created": False,
                    "replay_permitted": False, "claim": claim,
                    "note": "回执与claim原号/目标/摘要不一致；按unknown处理，零写、不重放、不改写他人回执"}
        current = self._current_state(receipt)
        return {"state": receipt["state"], "reason": "same_operation_read_only",
                "receipt": receipt, "current": current,
                "writes": 0, "new_id_created": False,
                "replay_permitted": False, "claim": claim,
                "note": "同号同体只读查询；历史完成与当前字节分别核验"}

    def write_new(self, rel_path: str, data: bytes, *, baselines: dict[str, dict],
                  operation_id: str, label: str = "write_new",
                  closure: dict[str, str] | None = None) -> dict:
        """One guarded product write. Claims the id BEFORE any product byte.

        ``closure`` (source-guard): absolute path -> sha256 for every
        non-writer dependency the caller consumed. All members are re-read and
        byte-compared AFTER the writer identity check and BEFORE publication;
        any change refuses with zero product writes.
        """
        self.stats["write_attempts"] += 1
        try:
            oid = validate_operation_id(operation_id)
        except UnsafeOperationId:
            self.stats["unsafe_ids_refused"] += 1
            raise
        target = _assert_safe_target(self.root, self.root / rel_path)
        self.events.append({"event": "write_attempt", "operation_id": oid,
                            "label": label, "path": rel_path, "at": utc_now()})

        # 1) claim / reconcile the ORIGINAL id first (zero product writes)
        prior = self._existing_same_operation(oid, rel_path, data, baselines)
        if prior is not None:
            self.events.append({"event": "same_operation_read_only",
                                "operation_id": oid, "at": utc_now(), "writes": 0})
            return prior
        receipt_path, claim = self._claim(oid, rel_path, data, baselines)

        # 1b) R2-01/R2-03: a receipt already present under a FRESHLY claimed id
        # is a conflict. Refuse BEFORE any product byte is written; keep claim,
        # keep the foreign receipt, zero product writes, no replay.
        if receipt_path.is_file():
            foreign, reason = self._validate_receipt_for(oid, claim)
            self.stats["collisions_refused"] += 1
            return {"state": "unknown",
                    "reason": "receipt_present_before_product_write",
                    "receipt_binding": reason or "unvalidated_foreign_receipt",
                    "receipt": None, "receipt_observed_foreign": True,
                    "writes": 0, "product_writes": 0, "new_id_created": False,
                    "replay_permitted": False, "claim": claim,
                    "note": "新claim下已存在回执：写前拒绝，不盲删、不改写他人回执、不重放"}

        # 2) full-byte pre-write recheck of every selected source/original
        checks = self.check_baselines(baselines)
        self.stats["before_write_checks_succeeded"] += 1
        if len(checks) != len(baselines):
            raise GuardError("incomplete observed byte recheck")

        # 3) verify the ACTUAL writer identity and its current source bytes
        writer_state = self._assert_writer_current()

        # 3b) frozen closure: every non-writer dependency the caller bound
        #     must still be byte-identical IMMEDIATELY before publication.
        closure_checks = self._check_closure(closure or {})

        # 4) atomic publication through the registered writer
        publication = self._publish(target, data, writer_state)

        # 5) read back what is now visible
        rb = target.read_bytes()
        if rb != data:
            raise GuardError("readback mismatch after publication")
        self.stats["readbacks"] += 1

        receipt = {
            "schema": GUARD_SCHEMA, "version": VERSION,
            "operation_id": oid, "label": label,
            "path": rel_path.replace("\\", "/"),
            "bytes": len(data), "sha256": sha256_bytes(data),
            "before_write_checks": checks, "before_write_check_count": len(checks),
            "full_byte_recheck_count": len(checks),
            "frozen_closure": {"enforced": bool(closure),
                                "checked": len(closure_checks),
                                "members": closure_checks},
            "registered_writer": {**writer_state, **self._writer_entry},
            "publication": publication,
            "readback_verified_at_write_time": True,
            "state": "completed", "completed_at": utc_now(),
        }
        # Receipt itself is EXCLUSIVE: a competing receipt is never overwritten.
        encoded = (json.dumps(receipt, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        try:
            _exclusive_write(receipt_path, encoded)
        except FileExistsError:
            # R2-01/r3: the PRODUCT has already been published by THIS call. The
            # `writes` field reports THIS call's actual product writes (= 1) so
            # a caller can never read a partially completed operation as zero
            # product writes. Query-style zero-write accounting is reported
            # separately (`query_writes`). The new product is NOT deleted, the
            # competing receipt is NOT overwritten, and replay is forbidden.
            self.stats["collisions_refused"] += 1
            self.stats["receipt_collision_partial_writes"] = (
                self.stats.get("receipt_collision_partial_writes", 0) + 1)
            return {"state": "unknown", "reason": "receipt_collision_product_already_published",
                    "receipt": None, "receipt_observed_foreign": True,
                    "writes": 1, "product_writes": 1,
                    "writes_definition": "product bytes published by THIS call",
                    "query_writes": 0, "receipt_overwritten": False,
                    "product_deleted": False,
                    "published": {"path": rel_path.replace("\\", "/"),
                                  "sha256": sha256_bytes(data), "bytes": len(data),
                                  "readback_verified_at_write_time": True,
                                  "atomic_publication": publication},
                    "new_id_created": True, "replay_permitted": False,
                    "claim": claim,
                    "note": "回执竞争失败但产品已原子发布一次：本调用产品写=1、查询写=0；"
                            "不盲删新产物、不改写他人回执、不重放、不换号"}
        return receipt

    # ---- read-only query: historical vs CURRENT ----------------------------
    def query(self, operation_id: str) -> dict:
        self.stats["same_id_queries"] += 1
        try:
            oid = validate_operation_id(operation_id)
        except UnsafeOperationId:
            self.stats["unsafe_ids_refused"] += 1
            raise
        claim_path = _assert_safe_target(self.receipts_dir,
                                        self.receipts_dir / f"claim-{oid}.json")
        receipt_path = _assert_safe_target(self.receipts_dir,
                                          self.receipts_dir / f"write-{oid}.json")
        self.events.append({"event": "same_id_query", "operation_id": oid,
                            "at": utc_now(), "writes": 0})
        if not receipt_path.is_file():
            return {"schema": GUARD_SCHEMA, "version": VERSION,
                    "operation_id": oid, "historical": {"state": "unknown"},
                    "current": {"state": "unknown"}, "writes": 0,
                    "new_id_created": False, "replay_permitted": False,
                    "note": "缺回执保持 unknown；零写、不换号、不重放"}
        # R2-03: load the claim and strictly reconcile it with the receipt.
        # A receipt from ANOTHER operation copied under this id must never be
        # accepted as this operation's confirmation.
        if not claim_path.is_file():
            return {"schema": GUARD_SCHEMA, "version": VERSION,
                    "operation_id": oid, "historical": {"state": "unknown"},
                    "current": {"state": "unknown"},
                    "reason": "receipt_without_claim",
                    "writes": 0, "new_id_created": False, "replay_permitted": False,
                    "note": "无claim的回执不作为本号确认；unknown、零写"}
        try:
            claim = self._load_json(claim_path, what="claim")
        except GuardError:
            return {"schema": GUARD_SCHEMA, "version": VERSION,
                    "operation_id": oid, "historical": {"state": "unknown"},
                    "current": {"state": "unknown"},
                    "reason": "claim_unreadable",
                    "writes": 0, "new_id_created": False, "replay_permitted": False}
        receipt, reason = self._validate_receipt_for(oid, claim)
        if reason is not None:
            # Wrong id / wrong body / foreign receipt: unknown + conflict, ZERO
            # writes, and the foreign receipt bytes are left untouched.
            self.stats["operation_conflicts_refused"] += 1
            return {"schema": GUARD_SCHEMA, "version": VERSION,
                    "operation_id": oid,
                    "historical": {"state": "unknown"},
                    "current": {"state": "unknown"},
                    "reason": f"receipt_binding_conflict:{reason}",
                    "receipt": None, "receipt_observed_foreign": True,
                    "writes": 0, "new_id_created": False, "replay_permitted": False,
                    "claim_present": True,
                    "note": "回执与claim原号/目标/摘要不一致；另一操作的成功不冒充本号确认；零写不改写"}
        historical = {"state": receipt["state"],
                      "path": receipt["path"], "sha256": receipt["sha256"],
                      "bytes": receipt["bytes"],
                      "readback_verified_at_write_time": receipt["readback_verified_at_write_time"]}
        # CURRENT integrity is a separate fact, never implied by history.
        current = self._current_state(receipt)
        return {"schema": GUARD_SCHEMA, "version": VERSION,
                "operation_id": oid, "historical": historical, "current": current,
                "receipt": receipt, "writes": 0, "new_id_created": False,
                "replay_permitted": False, "claim_present": True,
                "note": "历史写成功与当前字节读回分列；当前缺失/变化不冒充确认"}

    def report(self) -> dict:
        s = dict(self.stats)
        s["writer_calls_protected"] = (s["registered_writer_calls"] == s["product_writes"])
        s["query_is_zero_write"] = (s["query_writes"] == 0)
        return {"schema": GUARD_SCHEMA, "version": VERSION,
                "root": str(self.root).replace("\\", "/"),
                "code_root": str(self.code_root).replace("\\", "/"),
                "stats": s, "events": list(self.events),
                "writer_registry": self.writer_registry(),
                "zero_calls_are_not_writer_coverage": True,
                "platform_independent_path_relation": True}


# ---- editorial scope: a path guard is NOT an author-scope guard ------------
def validate_scoped_revision(*, original: bytes, revised: bytes,
                             protected_texts: list[bytes],
                             authorized_sections: list[str],
                             out_of_scope_expected_unchanged: bool = True) -> dict:
    """Explicit, bounded editorial check used by the real revision entry point.

    * every protected hand note must survive byte-for-byte;
    * only authorized section markers may change;
    * outside authorized spans, bytes must be identical.
    """
    missing = [t.decode("utf-8", "replace") for t in protected_texts if t not in revised]
    if missing:
        return {"valid": False, "reason": "protected_hand_edit_removed",
                "missing": missing, "scope_enforced": True}
    # Protected hand notes must survive at the SAME occurrence count, not merely
    # appear somewhere else in the revised draft.
    for t in protected_texts:
        if original.count(t) != revised.count(t):
            return {"valid": False, "reason": "protected_hand_edit_occurrence_changed",
                    "text": t.decode("utf-8", "replace"),
                    "original_count": original.count(t), "revised_count": revised.count(t),
                    "scope_enforced": True}

    def split_spans(data: bytes) -> list[tuple[str, bytes]]:
        """Ordered (name, bytes) spans. Duplicate headings get #n suffixes so
        they never collapse over each other. The first span is __prefix__ (all
        author content before the first H2) and is read-only by default."""
        text = data.decode("utf-8")
        parts = re.split(r"(?m)^(## .+)$", text)
        spans: list[tuple[str, bytes]] = [("__prefix__", parts[0].encode("utf-8"))]
        seen: dict[str, int] = {}
        for i in range(1, len(parts) - 1, 2):
            title = parts[i].strip()
            seen[title] = seen.get(title, 0) + 1
            name = title if seen[title] == 1 else f"{title}#{seen[title]}"
            spans.append((name, (parts[i] + parts[i + 1]).encode("utf-8")))
        return spans

    a, b = split_spans(original), split_spans(revised)
    a_map, b_map = dict(a), dict(b)
    changed = [k for k in a_map.keys() | b_map.keys() if a_map.get(k) != b_map.get(k)]
    added = [k for k in b_map if k not in a_map]
    removed = [k for k in a_map if k not in b_map]
    # Authorization is EXACT span-name membership; no substring matching.
    authorized = set(authorized_sections)
    unauthorized = [k for k in changed if k not in authorized]
    # __prefix__ (author content before the first H2) is read-only unless it is
    # EXPLICITLY authorized by the exact name "__prefix__".
    if unauthorized and out_of_scope_expected_unchanged:
        return {"valid": False, "reason": "out_of_scope_span_changed",
                "unauthorized": sorted(unauthorized), "added": sorted(added),
                "removed": sorted(removed), "scope_enforced": True,
                "note": "首个二级标题之前的作者前缀默认只读；授权按精确标题名匹配，不做子串匹配"}
    return {"valid": True, "protected_texts_preserved": True,
            "protected_texts_occurrence_preserved": True,
            "changed_sections": sorted(changed),
            "added_sections": sorted(added), "removed_sections": sorted(removed),
            "out_of_scope_sections_unchanged": not unauthorized,
            "out_of_scope_sync_pending": [],
            "scope_enforced": True,
            "note": "仅路径守卫不能证明编辑范围；本验证器由实际局改入口调用"}
