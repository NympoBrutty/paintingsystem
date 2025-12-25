#!/usr/bin/env python3
"""
test_stageA_contracts.py v2.0 — Comprehensive tests for Stage A contracts

Tests:
- JSON Schema validation
- Lint rules compliance
- Cross-contract consistency
- Catalog synchronization
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List, Set


def _repo_root() -> Path:
    """Get repository root from this file location."""
    return Path(__file__).resolve().parents[2]


def _load_json(path: Path) -> Dict[str, Any]:
    """Load JSON file with UTF-8 encoding."""
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _find_contracts(contracts_dir: Path) -> List[Path]:
    """Find all Stage A contract files."""
    return sorted(contracts_dir.glob("*_contract_stageA*.json"))


class TestStageAContractsStructure(unittest.TestCase):
    """Test contract structure and required fields."""
    
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = _repo_root()
        cls.stageA_dir = cls.repo_root / "stageA"
        cls.contracts_dir = cls.stageA_dir / "contracts"
        cls.contracts = _find_contracts(cls.contracts_dir)
        
        # Load schema
        schema_path = cls.stageA_dir / "schema" / "contract_schema_stageA_v4.json"
        cls.schema = _load_json(schema_path) if schema_path.exists() else {}
        
        # Load glossary
        glossary_path = cls.stageA_dir / "glossary" / "glossary_v1.json"
        cls.glossary = _load_json(glossary_path) if glossary_path.exists() else {}
    
    def test_contracts_exist(self):
        """At least one contract exists."""
        self.assertGreater(len(self.contracts), 0, "No contracts found")
    
    def test_contracts_valid_json(self):
        """All contracts are valid JSON."""
        for path in self.contracts:
            with self.subTest(contract=path.name):
                try:
                    _load_json(path)
                except Exception as e:
                    self.fail(f"Invalid JSON: {e}")
    
    def test_contracts_have_required_fields(self):
        """All contracts have required top-level fields."""
        required = [
            "_schema", "module_id", "module_abbr", "module_type",
            "module_name", "version", "description", "io_contract",
            "parameters", "parameter_groups", "constraints",
            "validation", "error_codes", "algorithm", "relations",
            "test_cases", "policies"
        ]
        
        for path in self.contracts:
            with self.subTest(contract=path.name):
                data = _load_json(path)
                for field in required:
                    self.assertIn(field, data, f"Missing field: {field}")
    
    def test_schema_block_valid(self):
        """All contracts have valid _schema block."""
        for path in self.contracts:
            with self.subTest(contract=path.name):
                data = _load_json(path)
                schema = data.get("_schema", {})
                
                self.assertEqual(schema.get("name"), "A-PRACTICAL.contract")
                self.assertEqual(schema.get("stage"), "A.contract_only")
                self.assertIn(schema.get("maturity_stage"), ["pilot", "draft", "stable"])


class TestStageAContractsValidation(unittest.TestCase):
    """Test contracts with lint validator."""
    
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = _repo_root()
        cls.stageA_dir = cls.repo_root / "stageA"
        
        # Import validator (clean import via package)
        try:
            from stageA.lint import ContractLintValidator
        except ImportError:
            # Fallback for direct execution
            repo_root = _repo_root()
            if str(repo_root) not in sys.path:
                sys.path.insert(0, str(repo_root))
            from stageA.lint import ContractLintValidator
        
        schema_path = cls.stageA_dir / "schema" / "contract_schema_stageA_v4.json"
        glossary_path = cls.stageA_dir / "glossary" / "glossary_v1.json"
        
        cls.validator = ContractLintValidator(
            schema_path=schema_path,
            glossary_path=glossary_path if glossary_path.exists() else None
        )
        
        cls.contracts_dir = cls.stageA_dir / "contracts"
        cls.contracts = _find_contracts(cls.contracts_dir)
    
    def test_all_contracts_pass_validation(self):
        """All contracts pass lint validation."""
        for path in self.contracts:
            with self.subTest(contract=path.name):
                result = self.validator.validate_contract(path)
                
                if not result.passed:
                    errors = [f"{e.code}: {e.message}" for e in result.errors]
                    self.fail(f"Validation failed:\n" + "\n".join(errors))
    
    def test_all_contracts_score_above_90(self):
        """All contracts score at least 90/100."""
        for path in self.contracts:
            with self.subTest(contract=path.name):
                result = self.validator.validate_contract(path)
                self.assertGreaterEqual(
                    result.score, 90,
                    f"Score {result.score} below threshold"
                )


class TestStageACatalogSync(unittest.TestCase):
    """Test catalog synchronization with contracts."""
    
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = _repo_root()
        cls.stageA_dir = cls.repo_root / "stageA"
        
        # Load catalog
        katalog_path = cls.stageA_dir / "katalog" / "katalog_4_0.json"
        cls.katalog = _load_json(katalog_path) if katalog_path.exists() else {}
        
        # Load contracts
        cls.contracts_dir = cls.stageA_dir / "contracts"
        cls.contracts: Dict[str, Dict[str, Any]] = {}
        for path in _find_contracts(cls.contracts_dir):
            data = _load_json(path)
            cls.contracts[data.get("module_id", "")] = data
    
    def test_catalog_modules_exist(self):
        """All catalog modules have corresponding contracts."""
        for module in self.katalog.get("modules", []):
            module_id = module.get("module_id")
            with self.subTest(module_id=module_id):
                self.assertIn(
                    module_id, self.contracts,
                    f"Contract not found for catalog entry"
                )
    
    def test_catalog_versions_match(self):
        """Catalog versions match contract versions."""
        for module in self.katalog.get("modules", []):
            module_id = module.get("module_id")
            if module_id in self.contracts:
                with self.subTest(module_id=module_id):
                    self.assertEqual(
                        module.get("version"),
                        self.contracts[module_id].get("version"),
                        "Version mismatch"
                    )
    
    def test_catalog_abbr_match(self):
        """Catalog abbreviations match contract abbreviations."""
        for module in self.katalog.get("modules", []):
            module_id = module.get("module_id")
            if module_id in self.contracts:
                with self.subTest(module_id=module_id):
                    self.assertEqual(
                        module.get("module_abbr"),
                        self.contracts[module_id].get("module_abbr"),
                        "Abbreviation mismatch"
                    )


class TestStageAGlossaryCoverage(unittest.TestCase):
    """Test glossary coverage."""
    
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = _repo_root()
        cls.stageA_dir = cls.repo_root / "stageA"
        
        # Load glossary
        glossary_path = cls.stageA_dir / "glossary" / "glossary_v1.json"
        cls.glossary = _load_json(glossary_path) if glossary_path.exists() else {}
        cls.terms = set(cls.glossary.get("terms", {}).keys())
        
        # Load contracts
        cls.contracts_dir = cls.stageA_dir / "contracts"
        cls.contracts = [_load_json(p) for p in _find_contracts(cls.contracts_dir)]
    
    def test_module_abbrs_in_glossary(self):
        """All module abbreviations are defined in glossary."""
        for contract in self.contracts:
            abbr = contract.get("module_abbr")
            with self.subTest(abbr=abbr):
                self.assertIn(
                    abbr, self.terms,
                    f"Module abbreviation not in glossary"
                )


class TestStageAErrorCodeConsistency(unittest.TestCase):
    """Test error code consistency across contracts."""
    
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = _repo_root()
        cls.contracts_dir = cls.repo_root / "stageA" / "contracts"
        cls.contracts = [_load_json(p) for p in _find_contracts(cls.contracts_dir)]
    
    def test_error_codes_unique_within_contract(self):
        """Error codes are unique within each contract."""
        for contract in self.contracts:
            with self.subTest(module_id=contract.get("module_id")):
                codes = [ec.get("code") for ec in contract.get("error_codes", [])]
                self.assertEqual(
                    len(codes), len(set(codes)),
                    "Duplicate error codes found"
                )
    
    def test_constraints_reference_defined_codes(self):
        """All constraint error codes are defined."""
        for contract in self.contracts:
            with self.subTest(module_id=contract.get("module_id")):
                defined = {ec.get("code") for ec in contract.get("error_codes", [])}
                for c in contract.get("constraints", []):
                    code = c.get("error_code")
                    self.assertIn(
                        code, defined,
                        f"Constraint references undefined code: {code}"
                    )
    
    def test_validation_rules_reference_defined_codes(self):
        """All validation rule codes are defined."""
        for contract in self.contracts:
            with self.subTest(module_id=contract.get("module_id")):
                defined = {ec.get("code") for ec in contract.get("error_codes", [])}
                for rule in contract.get("validation", {}).get("rules", []):
                    code = rule.get("error_code")
                    self.assertIn(
                        code, defined,
                        f"Validation rule references undefined code: {code}"
                    )


if __name__ == "__main__":
    unittest.main(verbosity=2)
