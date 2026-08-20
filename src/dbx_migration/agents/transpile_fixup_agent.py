"""
transpile_fixup_agent — Claude-driven post-Lakebridge SQL fixup.

Agent #11: Consumes Lakebridge transpilation output and fixes ~5–10 issues per task:
  - SSIS ? → Databricks job/widget parameter.
  - Broken IF EXISTS(sys.indexes) / FILLFACTOR blocks (not valid in Spark).
  - 3-part name references (server.db.schema.table) → UC (catalog.schema.table).
  - MERGE semantics verification.
  - Oracle syntax quirks (hierarchical queries, etc.) → Spark idioms.

Produces: Corrected Spark SQL validated by reconciliation_harness before commit.

Deterministic transpilation (Lakebridge) + agent fixup = pragmatic hybrid (#11).
Non-interactive transpile requires --transpiler-config-path for parameterization.
"""
from __future__ import annotations
from typing import Any
from dataclasses import dataclass


@dataclass
class TranspileFixupRequest:
    """Input to transpile fixup."""
    transpiled_sql: str  # Lakebridge output (Spark SQL, but may have issues)
    original_sql: str  # Pre-transpilation SQL (for reference)
    source_dialect: str  # 'sqlserver' or 'oracle'
    target_table_uc: str  # UC FQN where this SQL will load (e.g., 'platfin_hml.silver.silver_mv_atendimento')
    lineage_context: dict[str, Any] | None = None  # optional: package, connections, schema hints


@dataclass
class TranspileFixupResult:
    """Output of fixup."""
    fixed_sql: str
    fixes_applied: list[str]  # human-readable list of corrections
    requires_validation: bool  # gated by reconciliation_harness before commit
    confidence: float  # 0–1 estimate of correctness


def fixup_transpiled_sql(request: TranspileFixupRequest) -> TranspileFixupResult:
    """
    Post-Lakebridge fixup: correct the ~5–10 common issues per task.

    Agent-driven workflow:
      1. Parse the transpiled SQL and identify common issues.
      2. Apply fixes:
         - Parameter markers (?) → Databricks widget/job parameter names.
         - IF EXISTS(sys.indexes) / FILLFACTOR → remove or replace.
         - 3-part references → UC catalog.schema.table.
         - MERGE semantics → verify WHEN MATCHED/NOT MATCHED clauses.
         - Oracle hierachical → CTE or lateral joins.
      3. Return fixed SQL + list of applied fixes.

    Args:
        request: Transpiled SQL + context.

    Returns:
        TranspileFixupResult with corrected SQL + fixes + validation flag.

    Raises:
        NotImplementedError: Stub — agent implementation pending (#11).
    """
    raise NotImplementedError("transpile_fixup_agent.fixup_transpiled_sql: Agent implementation pending (#11)")


def parameter_substitution_hints(sql: str, lineage_context: dict[str, Any] | None = None) -> list[tuple[str, str]]:
    """
    Infer parameter substitution suggestions for ? markers in SQL.

    Looks at query context (package metadata, source definitions) to suggest
    what each ? should map to (e.g., run_date, batch_id, etc.).

    Args:
        sql: SQL with ? placeholders.
        lineage_context: Optional package metadata.

    Returns:
        List of (? index or placeholder, suggested_parameter_name) tuples.
    """
    raise NotImplementedError("transpile_fixup_agent.parameter_substitution_hints: Context analysis pending (#11)")


def validate_spark_syntax(sql: str) -> tuple[bool, str | None]:
    """
    Quick syntax validation of Spark SQL (not execution, just parsing).

    Args:
        sql: Spark SQL to validate.

    Returns:
        (is_valid, error_message_or_none).
    """
    raise NotImplementedError("transpile_fixup_agent.validate_spark_syntax: Spark SQL validator pending (#11)")
