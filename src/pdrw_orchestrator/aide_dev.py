"""Bind AIDE native task to an operator-staged, explicitly scoped DEV snapshot.

No source project traversal, data copy, model call or authorization. The
operator is responsible for actual data classification, permissions and
isolation. Only flat, finite local snapshots and exact manifests are supported.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from . import aide_pilot
from .adapters.aide import _plain, preview_aide

_MAX_FILES = 64
_MAX_FILE = 128 * 1024 * 1024
_MAX_TOTAL = 512 * 1024 * 1024
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,119}\Z")
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_EXT = {".csv", ".tsv", ".json", ".jsonl", ".npy", ".npz", ".parquet", ".txt"}
_RESERVED = re.compile(r"(?:^|[_.-])(?:sealed|confirmation|holdout|reserved|secret|credential)(?:$|[_.-])", re.I)


def _check_snapshot(root, plan):
    preview = preview_aide(plan)
    if plan["project_id"] == "PUBLIC-SYNTHETIC":
        raise ValueError("USE_FIXED_PILOT_FOR_SYNTHETIC_ID")
    root = aide_pilot._check_root(root, exists=True)
    worker, review, data = root / "worker", root / "review", root / "worker" / "data"
    for path in (worker, review, data):
        _plain(path, directory=True)
    count, total = check_manifest_files(review, data, plan)
    return root, preview, count, total


def check_manifest_files(review, data, plan, *, extra_names=()):
    """Shared flat DEV manifest check, not a data-scope proof."""
    _plain(review, directory=True)
    _plain(data, directory=True)
    raw = aide_pilot._read(review / "manifest.json", 64 * 1024)
    if hashlib.sha256(raw).hexdigest() != plan["data_manifest_sha256"]:
        raise ValueError("AIDE_DEV_MANIFEST_DIGEST_MISMATCH")
    manifest = json.loads(raw)
    if (not isinstance(manifest, dict) or set(manifest) != {"schema_version", "project_id", "task_id", "scope", "files"}
            or manifest["schema_version"] != "aide-dev-snapshot-v1"
            or manifest["project_id"] != plan["project_id"] or manifest["task_id"] != plan["task_id"]
            or manifest["scope"] != "DEV_ONLY_DECLARED"
            or not isinstance(manifest["files"], list) or not 1 <= len(manifest["files"]) <= _MAX_FILES):
        raise ValueError("AIDE_DEV_MANIFEST_INVALID")
    expected = {}
    total = 0
    for item in manifest["files"]:
        if not isinstance(item, dict) or set(item) != {"name", "sha256", "bytes"}:
            raise ValueError("AIDE_DEV_FILE_RECORD_INVALID")
        name, size, digest = item["name"], item["bytes"], item["sha256"]
        if (not isinstance(name, str) or not _NAME.fullmatch(name)
                or _RESERVED.search(name) or name.casefold() in {"submission_test.csv", "grade.py", "description.md"} or Path(name).suffix.lower() not in _EXT
                or name.casefold() in expected
                or type(size) is not int or not 1 <= size <= _MAX_FILE
                or not isinstance(digest, str) or not _SHA.fullmatch(digest)):
            raise ValueError("AIDE_DEV_FILE_RECORD_INVALID")
        expected[name.casefold()] = item
        total += size
    if total > _MAX_TOTAL or {p.name for p in data.iterdir()} != ({x["name"] for x in expected.values()} | set(extra_names)):
        raise ValueError("AIDE_DEV_DATA_SET_OR_SIZE_MISMATCH")
    # Reject unsafe metadata before reading any snapshot file contents.
    for item in expected.values():
        path = data / item["name"]
        _plain(path, directory=False)
        st = path.stat()
        if st.st_nlink != 1 or st.st_size != item["bytes"]:
            raise ValueError("AIDE_DEV_DATA_FILE_TYPE_OR_SIZE_MISMATCH")
    for item in expected.values():
        path = data / item["name"]
        h = hashlib.sha256()
        remaining = item["bytes"]
        with path.open("rb") as stream:
            while remaining:
                chunk = stream.read(min(remaining, 1024 * 1024))
                if not chunk:
                    raise ValueError("AIDE_DEV_DATA_BYTES_MISMATCH")
                remaining -= len(chunk)
                h.update(chunk)
            if stream.read(1) or h.hexdigest() != item["sha256"]:
                raise ValueError("AIDE_DEV_DATA_BYTES_MISMATCH")
    return len(expected), total


def stage(root, plan):
    root, preview, _, _ = _check_snapshot(root, plan)
    worker = root / "worker"
    if {p.name for p in worker.iterdir()} != {"data"}:
        raise ValueError("AIDE_DEV_WORKER_NOT_FRESH")
    aide_pilot._write(worker / "task.md", preview["task_file_preview"].encode("utf-8"))
    return verify(root, plan)


def verify(root, plan):
    root, preview, count, total = _check_snapshot(root, plan)
    task_bytes = aide_pilot._read(root / "worker" / "task.md", 32 * 1024)
    if task_bytes != preview["task_file_preview"].encode("utf-8"):
        raise ValueError("AIDE_DEV_TASK_BYTES_MISMATCH")
    return {**preview, "status": "DECLARED_DEV_SNAPSHOT_BYTES_MATCH_ONLY",
            "snapshot_file_count": count, "snapshot_bytes": total,
            "scope_declared": "DEV_ONLY_DECLARED", "actual_data_scope_verified": False,
            "original_grant_verified": False, "external_transfer_authorized": False,
            "scientific_validity_verified": False}
