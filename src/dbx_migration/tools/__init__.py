"""
Deterministic tools — the scaffolding layer.

Each tool maps to one of the locked framework decisions:
  - source_reader: #10 (DW host + Oracle bridge via OPENQUERY/linked servers)
  - sql_transpiler: #11 (Lakebridge-assisted transpilation strategy)
  - medallion_writer: #8 (bronze/silver/gold in platfin_hml per IND.GD.DOR-0001)
  - reconciliation_harness: #7 (row/key/hash + agg eval, proven by prototype)
"""

__all__ = []
