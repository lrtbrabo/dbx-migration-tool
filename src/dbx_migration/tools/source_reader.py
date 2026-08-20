"""
source_reader — read package sources from SSIS-connected databases.

Deterministic tool #10: DW host (RDRJ2BIDB01, reachable via dbricks-keyvault-secrets)
and Oracle bridge via OPENQUERY/linked servers (proven notebooks in ops-001/sqlserver_oracle_query).

Consumes: Lineage Contract's source definitions (connection name, query).
Produces: Row data (for reconciliation, staging, audit).
"""
from __future__ import annotations
from typing import Iterator, Any
from dataclasses import dataclass


@dataclass
class SourceConnection:
    """Metadata for a source connection (SQL Server, Oracle via linked server, etc.)."""
    name: str
    connection_type: str  # 'sqlserver', 'oracle', 'linked_server_query'
    host: str | None = None
    port: int | None = None
    database: str | None = None
    user: str | None = None


def read_from_connection(
    connection: SourceConnection,
    query: str,
    credentials_scope: str = "dbricks-keyvault-secrets",
) -> Iterator[dict[str, Any]]:
    """
    Read rows from a source database via JDBC (SQL Server) or OPENQUERY (Oracle via linked server).

    Args:
        connection: Source connection metadata (from Lineage Contract).
        query: SQL query to execute against the source (original T-SQL or Oracle SQL).
        credentials_scope: Keyvault scope for credentials (e.g., 'dbricks-keyvault-secrets').

    Yields:
        Row dictionaries with column names as keys.

    Raises:
        NotImplementedError: Stub — actual JDBC/OPENQUERY binding in progress (#10).
    """
    raise NotImplementedError("source_reader.read_from_connection: JDBC/OPENQUERY integration pending (#10)")


def reconciliation_reference_rows(
    dw_connection: SourceConnection,
    target_table: str,
    grain_keys: list[str],
) -> list[dict[str, Any]]:
    """
    Fetch reference rows from the SQL Server DW target table.

    Reconciliation uses this as the source of truth to compare against migrated (UC) output.
    Canonicalization happens in reconciliation_harness.

    Args:
        dw_connection: DW connection (e.g., RDRJ2BIDB01).
        target_table: Fully-qualified legacy DW table name (e.g., 'Bartira.dbo.DIM_ESPECIALIDADE').
        grain_keys: Business key column names (used for indexing by reconciliation_harness).

    Returns:
        List of row dicts. Columns include grain_keys + all columns in the target's hash_columns.

    Raises:
        NotImplementedError: Stub — JDBC binding pending.
    """
    raise NotImplementedError("source_reader.reconciliation_reference_rows: JDBC integration pending (#10)")
