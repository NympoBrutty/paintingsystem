"""Stage B Generator Package.

Entry point:
    python -m stageB.generator.generate_module --all
    python -m stageB.generator.generate_module --module SPS
"""

from .generate_module import (
    GENERATOR_VERSION,
    discover_contracts,
    generate_for_contract_path,
    main,
)

__all__ = [
    "GENERATOR_VERSION",
    "discover_contracts",
    "generate_for_contract_path",
    "main",
]
