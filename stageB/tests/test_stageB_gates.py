"""Stage B — B-Gate Tests.

Goals:
    - Module skeletons are generated and importable
    - Generator is idempotent: 2nd run produces identical *_autogen.* tree
    - Generator writes ONLY *_autogen.* files
    - Autogen files have proper structure (ClassVar, from_contract_dict, etc.)
    - Autogen files carry traceability markers (header + runtime constants)
    - Manual files (if present) are NOT overwritten by generator

These tests do NOT check Stage C logic; only Stage B guarantees.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Dict, List, Set

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = REPO_ROOT / "stageA" / "contracts"
MODULES_DIR = REPO_ROOT / "stageB" / "modules"

REQUIRED_AUTOGEN_FILES = [
    "config_autogen.py",
    "io_types_autogen.py",
    "validators_autogen.py",
    "pipeline_autogen.py",
    "cli_autogen.py",
    "README_autogen.md",
]

MANUAL_FILES = [
    "pipeline.py",
    "__manual__.py",
    "__init__.py",
]


def _discover_contract_abbrs() -> List[str]:
    """Discover module_abbr list from Stage A contracts."""
    abbrs: List[str] = []
    for p in sorted(CONTRACTS_DIR.glob("*_contract_stageA_FINAL.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            abbr = str(data.get("module_abbr") or "").strip().upper()
            if abbr:
                abbrs.append(abbr)
        except Exception:
            continue

    seen: Set[str] = set()
    out: List[str] = []
    for a in abbrs:
        if a not in seen:
            out.append(a)
            seen.add(a)
    return out


def _autogen_files_tree_hash() -> Dict[str, str]:
    """Return mapping relpath -> sha256 for all *_autogen.* files."""
    out: Dict[str, str] = {}
    if not MODULES_DIR.exists():
        return out

    for p in sorted(MODULES_DIR.rglob("*_autogen.*")):
        if p.is_file():
            rel = p.relative_to(REPO_ROOT).as_posix()
            out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def _manual_files_hash_if_exist() -> Dict[str, str]:
    """Return mapping relpath -> sha256 for manual files that already exist."""
    out: Dict[str, str] = {}
    if not MODULES_DIR.exists():
        return out

    for p in sorted(MODULES_DIR.rglob("*")):
        if not p.is_file():
            continue
        if p.name not in MANUAL_FILES:
            continue
        rel = p.relative_to(REPO_ROOT).as_posix()
        out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def _run_generator() -> subprocess.CompletedProcess:
    """Run the Stage B generator."""
    return subprocess.run(
        [sys.executable, "-m", "stageB.generator.generate_module", "--all"],
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
    )


class TestStageBGateGeneration(unittest.TestCase):
    """B-Gate: Generator produces valid output."""

    @classmethod
    def setUpClass(cls) -> None:
        proc = _run_generator()
        if proc.returncode != 0:
            raise RuntimeError(
                f"Stage B generator failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
            )

    def test_contracts_discovered(self) -> None:
        abbrs = _discover_contract_abbrs()
        self.assertTrue(abbrs, "No Stage A contracts discovered")

    def test_module_directories_exist(self) -> None:
        abbrs = _discover_contract_abbrs()
        for abbr in abbrs:
            mod_dir = MODULES_DIR / abbr
            self.assertTrue(
                mod_dir.exists() and mod_dir.is_dir(),
                f"Missing module directory: {mod_dir}"
            )

    def test_all_autogen_files_exist(self) -> None:
        abbrs = _discover_contract_abbrs()
        for abbr in abbrs:
            mod_dir = MODULES_DIR / abbr
            for fname in REQUIRED_AUTOGEN_FILES:
                fpath = mod_dir / fname
                self.assertTrue(
                    fpath.exists(),
                    f"Missing autogen file: {abbr}/{fname}"
                )


class TestStageBGateImports(unittest.TestCase):
    """B-Gate: All generated modules are importable."""

    @classmethod
    def setUpClass(cls) -> None:
        proc = _run_generator()
        if proc.returncode != 0:
            raise RuntimeError(f"Generator failed: {proc.stderr}")

    def test_autogen_modules_importable(self) -> None:
        abbrs = _discover_contract_abbrs()
        for abbr in abbrs:
            for mod_name in [
                f"stageB.modules.{abbr}.config_autogen",
                f"stageB.modules.{abbr}.io_types_autogen",
                f"stageB.modules.{abbr}.validators_autogen",
                f"stageB.modules.{abbr}.pipeline_autogen",
                f"stageB.modules.{abbr}.cli_autogen",
            ]:
                with self.subTest(module=mod_name):
                    __import__(mod_name)


class TestStageBGateIdempotency(unittest.TestCase):
    """B-Gate: Generator is idempotent (autogen outputs)."""

    def test_idempotency(self) -> None:
        proc1 = _run_generator()
        self.assertEqual(proc1.returncode, 0, f"First run failed: {proc1.stderr}")
        before = _autogen_files_tree_hash()
        self.assertTrue(before, "No *_autogen.* files found after first run")

        proc2 = _run_generator()
        self.assertEqual(proc2.returncode, 0, f"Second run failed: {proc2.stderr}")
        after = _autogen_files_tree_hash()

        self.assertEqual(
            before, after,
            "Idempotency violated: *_autogen.* outputs changed on second run"
        )


class TestStageBGateSafety(unittest.TestCase):
    """B-Gate: Generator only writes allowed file set."""

    @classmethod
    def setUpClass(cls) -> None:
        _run_generator()

    def test_no_unexpected_files(self) -> None:
        allowed_names = {
            "config_autogen.py",
            "io_types_autogen.py",
            "validators_autogen.py",
            "pipeline_autogen.py",
            "cli_autogen.py",
            "README_autogen.md",
            "pipeline.py",
            "__manual__.py",
            "__init__.py",
        }

        unexpected: List[str] = []
        for p in MODULES_DIR.rglob("*"):
            if not p.is_file():
                continue
            if "__pycache__" in p.parts or p.suffix == ".pyc":
                continue
            if p.name not in allowed_names:
                unexpected.append(p.relative_to(REPO_ROOT).as_posix())

        self.assertFalse(
            unexpected,
            f"Unexpected files in modules tree: {unexpected}"
        )


class TestStageBGateTraceability(unittest.TestCase):
    """B-Gate: Traceability markers exist (header + runtime constants)."""

    @classmethod
    def setUpClass(cls) -> None:
        _run_generator()

    def test_autogen_headers_contain_sha(self) -> None:
        abbrs = _discover_contract_abbrs()
        for abbr in abbrs:
            mod_dir = MODULES_DIR / abbr
            for fname in [
                "config_autogen.py",
                "io_types_autogen.py",
                "validators_autogen.py",
                "pipeline_autogen.py",
                "cli_autogen.py",
            ]:
                p = mod_dir / fname
                with self.subTest(file=p.as_posix()):
                    txt = p.read_text(encoding="utf-8", errors="replace")
                    self.assertIn("contract_sha256:", txt)

    def test_runtime_constants_exist(self) -> None:
        abbrs = _discover_contract_abbrs()
        for abbr in abbrs:
            mod = __import__(
                f"stageB.modules.{abbr}.config_autogen",
                fromlist=["__contract_id__", "__contract_sha256__", "__schema_version__"]
            )
            for attr in [
                "__contract_id__",
                "__contract_version__",
                "__schema_version__",
                "__contract_sha256__",
            ]:
                self.assertTrue(
                    hasattr(mod, attr),
                    f"{abbr}.config_autogen missing {attr}"
                )


class TestStageBGateManualNotOverwritten(unittest.TestCase):
    """B-Gate: Manual files are not overwritten (if they already exist)."""

    def test_manual_files_not_modified(self) -> None:
        # Hash manual files that exist BEFORE generator
        before = _manual_files_hash_if_exist()

        proc = _run_generator()
        self.assertEqual(proc.returncode, 0, f"Generator failed: {proc.stderr}")

        after = _manual_files_hash_if_exist()

        # Only compare keys that existed before (do not care about new manual files)
        for rel, h in before.items():
            self.assertEqual(
                h, after.get(rel),
                f"Manual file was modified by generator: {rel}"
            )


class TestStageBGateStructure(unittest.TestCase):
    """B-Gate: Autogen files have proper structure."""

    @classmethod
    def setUpClass(cls) -> None:
        _run_generator()

    def test_config_has_classvar_mapping(self) -> None:
        abbrs = _discover_contract_abbrs()
        for abbr in abbrs:
            with self.subTest(module=abbr):
                mod = __import__(
                    f"stageB.modules.{abbr}.config_autogen",
                    fromlist=["Parameters"]
                )
                params_cls = mod.Parameters
                self.assertTrue(
                    hasattr(params_cls, "__contract_field_map__"),
                    f"{abbr}.Parameters missing __contract_field_map__"
                )

    def test_config_has_validate_ranges(self) -> None:
        abbrs = _discover_contract_abbrs()
        for abbr in abbrs:
            with self.subTest(module=abbr):
                mod = __import__(
                    f"stageB.modules.{abbr}.config_autogen",
                    fromlist=["Parameters"]
                )
                params_cls = mod.Parameters
                self.assertTrue(
                    callable(getattr(params_cls, "validate_ranges", None)),
                    f"{abbr}.Parameters missing validate_ranges method"
                )

    def test_config_has_from_contract_dict(self) -> None:
        abbrs = _discover_contract_abbrs()
        for abbr in abbrs:
            with self.subTest(module=abbr):
                mod = __import__(
                    f"stageB.modules.{abbr}.config_autogen",
                    fromlist=["Parameters"]
                )
                params_cls = mod.Parameters
                self.assertTrue(
                    callable(getattr(params_cls, "from_contract_dict", None)),
                    f"{abbr}.Parameters missing from_contract_dict method"
                )

    def test_io_types_have_from_contract_dict(self) -> None:
        abbrs = _discover_contract_abbrs()
        for abbr in abbrs:
            with self.subTest(module=abbr):
                mod = __import__(
                    f"stageB.modules.{abbr}.io_types_autogen",
                    fromlist=["Inputs", "Outputs"]
                )
                for cls_name in ["Inputs", "Outputs"]:
                    cls = getattr(mod, cls_name)
                    self.assertTrue(
                        callable(getattr(cls, "from_contract_dict", None)),
                        f"{abbr}.{cls_name} missing from_contract_dict method"
                    )


class TestStageBGateFunctionality(unittest.TestCase):
    """B-Gate: Basic functionality works."""

    @classmethod
    def setUpClass(cls) -> None:
        _run_generator()

    def test_parameters_instantiate_with_defaults(self) -> None:
        abbrs = _discover_contract_abbrs()
        for abbr in abbrs:
            with self.subTest(module=abbr):
                mod = __import__(
                    f"stageB.modules.{abbr}.config_autogen",
                    fromlist=["Parameters"]
                )
                params = mod.Parameters()
                self.assertIsNotNone(params)

    def test_validate_ranges_returns_list(self) -> None:
        abbrs = _discover_contract_abbrs()
        for abbr in abbrs:
            with self.subTest(module=abbr):
                mod = __import__(
                    f"stageB.modules.{abbr}.config_autogen",
                    fromlist=["Parameters"]
                )
                params = mod.Parameters()
                result = params.validate_ranges()
                self.assertIsInstance(result, list)

    def test_from_contract_dict_works(self) -> None:
        abbrs = _discover_contract_abbrs()
        for abbr in abbrs:
            with self.subTest(module=abbr):
                mod = __import__(
                    f"stageB.modules.{abbr}.config_autogen",
                    fromlist=["Parameters"]
                )
                params = mod.Parameters.from_contract_dict({})
                self.assertIsNotNone(params)

    def test_is_valid_returns_bool(self) -> None:
        """is_valid() returns boolean."""
        abbrs = _discover_contract_abbrs()
        for abbr in abbrs:
            with self.subTest(module=abbr):
                mod = __import__(
                    f"stageB.modules.{abbr}.validators_autogen",
                    fromlist=["is_valid"]
                )
                from importlib import import_module
                config = import_module(f"stageB.modules.{abbr}.config_autogen")
                params = config.Parameters()
                result = mod.is_valid(params)
                self.assertIsInstance(result, bool)


if __name__ == "__main__":
    unittest.main(verbosity=2)
