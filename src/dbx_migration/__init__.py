"""
DBX Migration Framework — SSIS → Databricks migration framework (walking skeleton).

Orchestrates deterministic tools (dtsx analyzer, SQL transpiler, medallion writer, reconciliation eval)
and agent-driven steps (contract generation, transpile fixup, migration orchestration) to migrate
SSIS packages onto Databricks with proven row/key/hash-level reconciliation against the SQL Server DW.

See CONTEXT.md for terminology, docs/adr/* for decisions, and docs/framework-structure.md for layout.
"""

__version__ = "0.0.1-skeleton"
__all__ = []
