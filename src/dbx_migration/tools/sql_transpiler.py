"""
sql_transpiler — convert SQL Server / Oracle SQL to Spark SQL via Lakebridge.

Deterministic tool #11: Lakebridge-assisted hybrid transpilation strategy.

Lakebridge does deterministic conversion (TRUNCATE, DELETE, DB_NAME() → current_database(),
DELETE…JOIN → MERGE, index-DDL removal); agent (transpile_fixup_agent) handles ~5–10/task
(SSIS ? → job/widget param, broken IF EXISTS/FILLFACTOR blocks, 3-part → UC catalog.schema).

Consumes: T-SQL or Oracle SQL from Lineage Contract.
Produces: Spark SQL (validated by reconciliation_harness before commit).
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class TranspileRequest:
    """Input to a transpilation pass."""
    sql: str
    source_dialect: str  # 'sqlserver' or 'oracle'
    target_dialect: str = "spark"
    package_name: str | None = None


@dataclass
class TranspileResult:
    """Output of a transpilation pass."""
    original_sql: str
    transpiled_sql: str
    source_dialect: str
    target_dialect: str
    errors: list[str]
    warnings: list[str]
    requires_fixup: bool


def transpile(request: TranspileRequest) -> TranspileResult:
    """
    Transpile SQL from source (SQL Server or Oracle) to Spark SQL via Lakebridge.

    Handles deterministic transformations (TRUNCATE, DELETE, DB_NAME(), DELETE…JOIN→MERGE,
    index-DDL removal). Agent (transpile_fixup_agent) addresses remaining issues.

    Args:
        request: Source SQL + dialect metadata.

    Returns:
        TranspileResult with transpiled SQL, any errors/warnings, and fixup flag.

    Raises:
        NotImplementedError: Stub — Lakebridge integration pending (#11).

    See Also:
        transpile_fixup_agent: Handles post-Lakebridge corrections.
    """
    raise NotImplementedError("sql_transpiler.transpile: Lakebridge integration pending (#11)")


def estimate_fixup_effort(result: TranspileResult) -> int:
    """
    Estimate the number of manual fixup interventions likely needed (from #11: ~5–10/task).

    Args:
        result: Output from transpile().

    Returns:
        Estimated count of issues requiring agent intervention.
    """
    raise NotImplementedError("sql_transpiler.estimate_fixup_effort: Stub pending Lakebridge assessment (#11)")
