"""
medallion_writer — write migrated data to UC bronze/silver/gold layers.

Deterministic tool #8: bronze/silver/gold medallion in platfin_hml catalog (IND.GD.DOR-0001).

SSIS → UC mapping:
  - source operational table → bronze: bronze_<sistemaOrigem>_<baseOrigem>_<tabelaOrigem>
  - STG_* → silver: silver_<sistemaOrigem>_<tabelaOrigem>
  - DIM_* / FAT_* → gold: <tb|vw>_gold_<tipoCamada>_<assunto>

Example (pilot MV/Bartira):
  - SMESPEC (source) → platfin_hml.bronze.bronze_mv_bartira_smespec
  - STG_SMESPEC → platfin_hml.silver.silver_mv_smespec
  - DIM_ESPECIALIDADE → platfin_hml.gold.tb_gold_dim_especialidade

Reconciliation gates: silver ↔ DW STG_*, gold ↔ DW DIM_/FAT_*.
Bronze has no DW counterpart (new raw layer; reconcile against source row-count only if at all).

Consumes: Transpiled SQL + reconciliation metadata from Lineage Contract.
Produces: UC delta tables in the medallion.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class MedallionLayer(Enum):
    """Medallion layer designation."""
    BRONZE = "bronze"  # raw operational source (no DW counterpart)
    SILVER = "silver"  # SSIS STG_ layer (reconciles vs DW STG_*)
    GOLD = "gold"      # SSIS DIM_/FAT_ layer (reconciles vs DW DIM_/FAT_*)


class LoadSemantics(Enum):
    """Load strategy for the target."""
    FULL_REFRESH = "full_refresh"  # TRUNCATE + reload (skeleton default)
    INCREMENTAL = "incremental"   # CDC, partition append, etc. (deferred to #13)


@dataclass
class MedallionTarget:
    """Target table in the bronze/silver/gold medallion."""
    catalog: str = "platfin_hml"
    layer: MedallionLayer = MedallionLayer.GOLD
    schema: str | None = None  # set by layer
    table_name: str = ""
    legacy_source_name: str | None = None  # e.g., 'DIM_ESPECIALIDADE' (for audit)


def uc_fqn_from_legacy(
    legacy_table_name: str,
    source_system: str,
    source_database: str = "",
    layer_hint: str = "",
) -> str:
    """
    Map a legacy SSIS target name to a UC FQN per IND.GD.DOR-0001.

    Args:
        legacy_table_name: SSIS target (e.g., 'STG_SMESPEC', 'DIM_ESPECIALIDADE').
        source_system: Source system code (e.g., 'mv', 'moderna', 'tasy').
        source_database: Source database/connection (e.g., 'bartira', 'simah').
        layer_hint: Optional hint (used if legacy name is ambiguous; default='gold').

    Returns:
        UC FQN: 'platfin_hml.<layer>.<table_name>' per standard.

    Raises:
        NotImplementedError: Stub — naming logic and UC table creation pending (#8).
    """
    raise NotImplementedError("medallion_writer.uc_fqn_from_legacy: UC naming + table creation pending (#8)")


def write_target(
    uc_target: MedallionTarget,
    spark_sql: str,
    load_semantics: LoadSemantics = LoadSemantics.FULL_REFRESH,
) -> None:
    """
    Execute the transpiled SQL to load the UC target table.

    For skeleton (full-refresh): truncate and insert. Later (#13): add incremental logic.

    Args:
        uc_target: Target table metadata.
        spark_sql: Transpiled Spark SQL (ready to execute).
        load_semantics: Load strategy (default: full_refresh).

    Raises:
        NotImplementedError: Stub — Databricks SQL execution pending.
    """
    raise NotImplementedError("medallion_writer.write_target: Databricks SQL execution pending (#8)")


def audit_trail_columns() -> dict[str, str]:
    """
    Standard audit columns appended to every migrated target (framework-wide pattern).

    Returns:
        Dict mapping column name to Spark SQL expression (e.g., '_migrated_at' → 'current_timestamp()').
    """
    raise NotImplementedError("medallion_writer.audit_trail_columns: Audit schema design pending (#8)")
