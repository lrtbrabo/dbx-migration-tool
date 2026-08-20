"""
Agents — Claude-driven steps in the migration loop.

The framework decomposes into three agent responsibilities:
  - contract_agent: Generates Lineage Contracts from SSIS package analysis (#6).
  - transpile_fixup_agent: Fixes Lakebridge transpilation output (~5–10 issues/task, #11).
  - migration_driver: Orchestrates the full loop (end-to-end, gated by reconciliation #7).

Two human gates: validate-the-validator + adjudicate-first-diffs → codified tolerance rules.
"""

__all__ = []
