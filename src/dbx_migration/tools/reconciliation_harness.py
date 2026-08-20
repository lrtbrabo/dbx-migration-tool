"""
reconciliation_harness — row/key/hash + aggregate reconciliation eval.

Deterministic tool #7: Reconciliation eval design proven by prototype (prototypes/reconciliation/recon_eval_prototype.py).

Four checks off the Lineage Contract's ReconSpec:
  1. row_count: DW reference row count vs. UC candidate.
  2. key_match: Grain-key set membership (missing_in_candidate, extra_in_candidate).
  3. hash_match: Row-level content hash (Spark SHA2) for common keys (catches value corruption).
  4. aggregates: Metrics (sum, count, count_distinct) over business columns.

Hash canonicalization: NULL_TOKEN + SEP across engines, float fixed-scale, trim whitespace.

Threshold policy: Start 'exact' (exact/0.00), codified per-column tolerance via adjudication gate.

Consumes: Reference rows (from DW via source_reader) + candidate rows (from UC).
          ReconSpec from Lineage Contract (grain_keys, hash_columns, aggregate_metrics).
Produces: Reconciliation report (pass/fail per check, diffs).
"""
from __future__ import annotations
import hashlib
from dataclasses import dataclass, field
from typing import Any


# Cross-engine canonicalization (SQL Server HASHBYTES, Spark sha2 — same logic on both sides)
NULL_TOKEN = "\x00NULL\x00"
SEP = "\x1f"  # unit separator — cannot appear in normal data


def canonicalize_value(v: Any) -> str:
    """
    Canonicalize a single value for hashing (cross-engine consistent).

    Handles: None → NULL_TOKEN, bool → '0'/'1', float → 6-decimal fixed, str → trim.

    Args:
        v: Python value from row dict.

    Returns:
        Canonicalized string suitable for hash input.
    """
    if v is None:
        return NULL_TOKEN
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, float):
        return format(v, ".6f")  # fixed scale: kills float-format drift
    return str(v).strip()  # trim: trailing-space noise is not a diff


def row_hash(row: dict[str, Any], columns: list[str]) -> str:
    """
    Compute row-level SHA256 hash over specified columns (cross-engine).

    Args:
        row: Dict mapping column name → value.
        columns: Column names to include in hash (in order).

    Returns:
        Hex-encoded SHA256 hash.
    """
    content = SEP.join(canonicalize_value(row.get(c)) for c in columns)
    return hashlib.sha256(content.encode()).hexdigest()


@dataclass
class ReconSpec:
    """Declarative reconciliation spec for one Target (per Lineage Contract #6)."""
    grain_keys: list[str]  # business keys identifying one row
    hash_columns: list[str]  # columns to hash (excl. audit columns; all business cols)
    aggregate_metrics: list[tuple[str, str]]  # (column_name, fn) where fn ∈ ['count', 'sum', 'count_distinct']
    thresholds: dict[str, str] = field(default_factory=lambda: {
        "row_count": "exact",      # 'exact' or tolerance '%'
        "key_match": "exact",      # 'exact' or tolerance '%'
        "hash_match": "exact",     # 'exact' or tolerance '%'
        "aggregates": "exact",     # per-metric tolerance (advanced)
    })


@dataclass
class ReconCheck:
    """Single reconciliation check result."""
    name: str  # 'row_count', 'key_match', 'hash_match', 'aggregates'
    passed: bool
    reference_value: Any = None
    candidate_value: Any = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReconReport:
    """Full reconciliation report for one Target."""
    target_name: str
    spec: ReconSpec
    checks: list[ReconCheck] = field(default_factory=list)
    passed: bool = False  # overall verdict
    aggregate_only_verdict: bool = False  # what naive checker (count+agg only) concludes


def reconcile(
    reference_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    spec: ReconSpec,
    target_name: str = "target",
) -> ReconReport:
    """
    Run reconciliation eval: row count, key match, hash match, aggregates.

    The eval catches:
      - Missing/extra rows (key_match).
      - Value corruption preserving counts (hash_match catches; agg-only fooled).
      - Different aggregate totals.

    Args:
        reference_rows: Reference (DW) rows (source of truth).
        candidate_rows: Candidate (UC) rows (migrated output).
        spec: ReconSpec from Lineage Contract.
        target_name: Target table name (for reporting).

    Returns:
        ReconReport with per-check pass/fail and overall verdict.

    See Also:
        prototypes/reconciliation/recon_eval_prototype.py for validation logic + demo.
    """
    raise NotImplementedError("reconciliation_harness.reconcile: Cross-engine reconciliation eval pending (#7)")


def threshold_check(
    reference_value: Any,
    candidate_value: Any,
    threshold_spec: str,
) -> bool:
    """
    Evaluate a single metric against a threshold spec.

    Args:
        reference_value: Reference (DW) value.
        candidate_value: Candidate (UC) value.
        threshold_spec: 'exact' or tolerance string (e.g., '5.0%', '±10').

    Returns:
        True if within threshold.
    """
    raise NotImplementedError("reconciliation_harness.threshold_check: Tolerance eval pending (#7)")


def agg_metric(rows: list[dict[str, Any]], column: str, fn: str) -> Any:
    """
    Compute aggregate metric over rows.

    Args:
        rows: List of row dicts.
        column: Column to aggregate (ignored for fn='count').
        fn: Aggregation function ('count', 'sum', 'count_distinct').

    Returns:
        Aggregate result.
    """
    raise NotImplementedError("reconciliation_harness.agg_metric: Aggregate computation pending (#7)")
