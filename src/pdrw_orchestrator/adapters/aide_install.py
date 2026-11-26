"""Compare selected installed AIDE source files against pinned upstream Git blobs.

No interpreter startup, imports, installation or model calls. This is a
partial byte comparison, not package authenticity or dependency acceptance.
"""
from pathlib import Path
import hashlib

from .aide import _plain
from ..specialists import candidates

_BLOBS = {
    "aide/run.py": "22f48a9e2b334ba76254009d36c85f2f7ad03820",
    "aide/agent.py": "512368205265b75d5cfdaf777f03db0245e1631e",
    "aide/interpreter.py": "e1e880e3e0a3c738a6b4e16ce83d14fe52e461eb",
    "aide/utils/config.py": "68dec057e02e68df300c3ed384c8ff672bddcdb5",
    "aide/utils/config.yaml": "77ecfb5ecee7675acf8ad2132923514e92b6fbc2",
    "aide/journal.py": "88d44a4e84d014febdbe259ba13bdaf826ebe83e",
}
_MAX = 2 * 1024 * 1024


def _git_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def inspect_aide_install(root):
    root = Path(root)
    if not root.is_absolute() or ".." in root.parts:
        raise ValueError("AIDE_SOURCE_ROOT_ABSOLUTE_REQUIRED")
    for part in reversed((root, *root.parents)):
        _plain(part, directory=True)
    results = []
    for ref, expected in _BLOBS.items():
        path = root / ref
        result = {"ref": ref, "expected_git_blob": expected}
        try:
            for folder in reversed(tuple(p for p in path.parents if p != root and root in p.parents)):
                _plain(folder, directory=True)
            _plain(path, directory=False)
            with path.open("rb") as stream:
                raw = stream.read(_MAX + 1)
            if not raw or len(raw) > _MAX:
                raise ValueError("SOURCE_SIZE_INVALID")
            actual = _git_blob(raw)
            result.update({"observed_git_blob": actual,
                           "status": "MATCH" if actual == expected else "MISMATCH"})
        except (OSError, ValueError):
            result["status"] = "UNAVAILABLE_OR_UNSAFE"
        results.append(result)
    return {"status": "PINNED_SELECTED_BYTES_MATCH" if all(x["status"] == "MATCH" for x in results)
            else "PINNED_SELECTED_BYTES_NOT_MATCHED",
            "upstream_revision": candidates("optimization")["candidates"][0]["revision"],
            "files": results, "installed_version_authenticated": False,
            "dependencies_verified": False, "executable_binding_verified": False,
            "capability_accepted": False, "execution_authorized": False,
            "model_calls_requested": 0}
