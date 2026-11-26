"""Compare selected installed specialist source files against pinned upstream Git blobs.

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
_OTHER_BLOBS = {
    "rdagent": {
        "rdagent/app/cli.py": "52bdbcce1b69f811eeda88b06667acf35c2b89d9",
        "rdagent/app/data_science/conf.py": "2d8ec6262f6d8ea2f80be0968817795665f3c46f",
        "rdagent/app/data_science/loop.py": "b2d08abf038aa7d4d3fca28fd2aa23153ba11d89",
        "rdagent/scenarios/data_science/dev/runner/eval.py": "269bb61e8a1174ecef0c8aa23442dfc5095c557f",
        "rdagent/scenarios/data_science/scen/__init__.py": "b6f60a3af1bcbcdcd09e6f299d702f669dae4c07",
        "rdagent/scenarios/data_science/test_eval.py": "d91fcd57eef8be8f8a802abcc323a7662bf7da05",
    },
    "tooluniverse": {
        "tooluniverse/__init__.py": "d4ffc14b1f17e6cd7ee152390c7da2ecccbe472d",
        "tooluniverse/crossref_tool.py": "70e2c1bf13d91f99577a04cdb33aed6dab92497b",
        "tooluniverse/base_rest_tool.py": "cbbe567098a88df61d9daf098b506663ab82d114",
        "tooluniverse/base_tool.py": "d3f214df5b924fc24510464544d8caad362e1d51",
        "tooluniverse/data/crossref_tools.json": "60ebf250c806eb5ad247fc583d18b3e1e8d2307d",
        "tooluniverse/zenodo_tool.py": "592ffd3cdab41407f8e59b84d680e1ab6cd0df82",
        "tooluniverse/data/zenodo_tools.json": "066257ca8e58674ffe382dd11f15ec6a31815411",
    },
    "arc": {
        "researchclaw/cli.py": "4c272dd8ae24b2f7cf579c9d057d9af25d689cc2",
        "researchclaw/config.py": "04bd7309746d65b5c83b902c9531f7a917c3184a",
        "researchclaw/pipeline/runner.py": "2e5883557b373e9bbf6a4227c6afb08914188a1f",
        "researchclaw/pipeline/stage_impls/_literature.py": "1ffb46e171a83c3afc663ddc3ff50f8878df2be4",
        "researchclaw/pipeline/stage_impls/_topic.py": "993127467a2ed31b93ab84f10296ef87d841bc32",
        "researchclaw/pipeline/stages.py": "6b7fee006c23e07280a4612f2f743fcd2ba3c332",
    },
}
_MAX = 2 * 1024 * 1024


def _git_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def inspect_aide_install(root):
    return inspect_specialist_install("aide", root)


def inspect_specialist_install(provider, root):
    if provider not in ("aide", "rdagent", "arc", "tooluniverse"):
        raise ValueError("UNKNOWN_SPECIALIST_PROVIDER")
    blobs = _BLOBS if provider == "aide" else _OTHER_BLOBS[provider]
    root = Path(root)
    if not root.is_absolute() or ".." in root.parts:
        raise ValueError("AIDE_SOURCE_ROOT_ABSOLUTE_REQUIRED")
    for part in reversed((root, *root.parents)):
        _plain(part, directory=True)
    results = []
    for ref, expected in blobs.items():
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
            "upstream_revision": next(row["revision"] for row in candidates()["candidates"] if row["id"] == provider),
            "files": results, "installed_version_authenticated": False,
            "dependencies_verified": False, "executable_binding_verified": False,
            "capability_accepted": False, "execution_authorized": False,
            "model_calls_requested": 0}
