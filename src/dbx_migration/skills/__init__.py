"""
Reusable Claude Code skills for the migration framework.

Skills are high-level workflows (agents + tools) that can be invoked via Claude Code `/skill` commands.
They wrap the lower-level agent orchestration (migration_driver, etc.) with user-facing intent.

Available skills (see README.md for details):
  - /migrate-package: Run full migration loop on one package (analyze → contract → transpile → write → reconcile → adjudicate).
  - /extract-contract: Extract and review the Lineage Contract for a package (contract_agent).
  - /transpile-package: Transpile SQL tasks for a package (sql_transpiler + transpile_fixup_agent).
  - /run-reconciliation: Run reconciliation eval for one target (reconciliation_harness + review).
  - /adjudicate-diffs: Human adjudication of reconciliation diffs (gate 2).
"""

__all__ = []
