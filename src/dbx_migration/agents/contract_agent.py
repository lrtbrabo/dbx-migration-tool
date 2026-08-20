"""
contract_agent — Claude-driven generation of Lineage Contracts from SSIS packages.

Agent #6: Consumes dtsx_analyzer output (connections, SQL tasks, data flows) and generates
a Lineage Contract per package (source → transform → target + reconciliation specs).

The contract captures:
  - Connections (source systems, databases).
  - For each Target:
    - Legacy name + UC FQN (via medallion_writer per ADR-0002).
    - Load semantics (full-refresh for skeleton, incremental deferred to #13).
    - Transform type (discriminator: 'column_mapping' for 1:1 OLE DB flows, 'sql_task' for Execute-SQL-Task).
    - Source details (connection, query, via source_reader).
    - Column mappings (for 'column_mapping' type) or transpiled SQL (for 'sql_task' type).
    - Reconciliation spec (grain_keys, hash_columns, aggregate_metrics, thresholds).
    - Confidence score + adjudication status (per ADR-0001 Adjudication Gate).

Contract lives at contracts/<group>/<package>.contract.json, git-tracked (ADR-0001).
Source hash (dtsx_analyzer) enables drift detection.

Human gate: Adjudication → verify mappings, ratify or escalate.
"""
from __future__ import annotations
from typing import Any
from dataclasses import dataclass


@dataclass
class ContractGenerationRequest:
    """Input to contract generation."""
    package_name: str
    source_group: str  # 'moderna', 'mv', 'tasy', 'wpd'
    dtsx_path: str  # path to .dtsx file
    dtsx_analyzer_output: dict[str, Any]  # from tools/dtsx_analyzer.py
    uc_target_layout: str = "platfin_hml"  # catalog (per ADR-0002)


@dataclass
class LineageContract:
    """Generated Lineage Contract (JSON-serializable, one per package)."""
    schema_version: str  # e.g., '1.0'
    package: dict[str, Any]  # {name, group, source_dtsx_path, source_hash}
    provenance: dict[str, Any]  # {generated_at, generator ('contract_agent'), model}
    connections: list[dict[str, Any]]  # from dtsx_analyzer
    targets: list[dict[str, Any]]  # each: target_table, load_semantics, transform_type, source, column_mappings, sql, reconciliation, confidence


def generate_contract(request: ContractGenerationRequest) -> LineageContract:
    """
    Generate a Lineage Contract from package analysis.

    High-level workflow (agent-driven):
      1. Parse dtsx_analyzer output (connections, SQL tasks, data flows).
      2. For each target (destination in data flows or Execute-SQL-Task result):
         a. Determine UC FQN via medallion_writer (silver for STG_, gold for DIM_/FAT_).
         b. Extract transform (column mapping for OLE DB flows, SQL for Execute-SQL-Task).
         c. Infer reconciliation spec (grain keys from source or data model hints).
         d. Assign confidence (high for 1:1 flows, medium for inferred grain keys, low for ambiguous).
      3. Emit contract structure.

    Args:
        request: Package path + dtsx_analyzer output.

    Returns:
        LineageContract ready for JSON serialization and adjudication review.

    Raises:
        NotImplementedError: Stub — agent implementation pending.

    See Also:
        ADR-0001 (git-tracked JSON contracts).
        ADR-0002 (UC target layout).
        prototypes/reconciliation/recon_eval_prototype.py (ReconSpec structure).
    """
    raise NotImplementedError("contract_agent.generate_contract: Agent implementation pending (#6)")


def validate_contract(contract: LineageContract) -> tuple[bool, list[str]]:
    """
    Validate contract against schema and business rules.

    Checks:
      - Required fields present (schema_version, package, targets[]).
      - UC FQN format (platfin_hml.bronze|silver|gold.*).
      - Reconciliation specs have grain_keys + hash_columns + aggregate_metrics.
      - No duplicate targets by UC FQN.
      - Confidence scores 0–1.

    Args:
        contract: Generated contract.

    Returns:
        (is_valid, list of validation errors).
    """
    raise NotImplementedError("contract_agent.validate_contract: Validation logic pending (#6)")
