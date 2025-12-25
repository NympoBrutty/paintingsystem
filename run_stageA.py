#!/usr/bin/env python3
"""
run_stageA.py — One-click local validation

Usage:
    python run_stageA.py           # Run all checks
    python run_stageA.py --quick   # Skip tests, only validate
    python run_stageA.py --verbose # Detailed output

This script:
1. Validates all Stage A contracts
2. Runs unit tests
3. Generates reports in stageA/_reports/
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_command(cmd: list[str], description: str, verbose: bool = False) -> bool:
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"▶ {description}")
    print(f"{'='*60}")
    
    if verbose:
        print(f"  Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=not verbose,
            text=True,
            cwd=Path(__file__).parent
        )
        
        if result.returncode == 0:
            print(f"✅ {description} — PASSED")
            if verbose and result.stdout:
                print(result.stdout)
            return True
        else:
            print(f"❌ {description} — FAILED")
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            return False
            
    except Exception as e:
        print(f"❌ {description} — ERROR: {e}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="One-click Stage A validation"
    )
    parser.add_argument(
        "--quick", "-q",
        action="store_true",
        help="Quick mode: skip tests, only validate contracts"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--no-reports",
        action="store_true",
        help="Skip report generation"
    )
    
    args = parser.parse_args()
    
    repo_root = Path(__file__).parent
    reports_dir = repo_root / "stageA" / "_reports"
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║              Stage A — Local Validation Suite                ║
║                      {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                       ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    results = []
    
    # Step 1: Validate contracts
    validate_cmd = [
        sys.executable,
        "stageA/tools/batch_validator.py",
        "stageA/contracts",
        "--glossary", "stageA/glossary/glossary_v1.json",
        "--schema", "stageA/schema/contract_schema_stageA_v4.json",
    ]
    
    if not args.no_reports:
        reports_dir.mkdir(parents=True, exist_ok=True)
        validate_cmd.extend(["--out", str(reports_dir)])
    
    if args.verbose:
        validate_cmd.append("--verbose")
    
    results.append(run_command(
        validate_cmd,
        "Contract Validation",
        verbose=args.verbose
    ))
    
    # Step 2: Run tests (unless --quick)
    if not args.quick:
        test_cmd = [
            sys.executable, "-m", "unittest",
            "discover", "-s", "stageA/tests",
            "-p", "test_*.py",
            "-v" if args.verbose else "-q"
        ]
        
        results.append(run_command(
            test_cmd,
            "Unit Tests",
            verbose=args.verbose
        ))
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(results)
    total = len(results)
    
    if all(results):
        print(f"""
✅ ALL CHECKS PASSED ({passed}/{total})

Reports saved to: {reports_dir if not args.no_reports else 'N/A'}
        """)
        return 0
    else:
        print(f"""
❌ SOME CHECKS FAILED ({passed}/{total} passed)

Please fix the issues above before committing.
        """)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
