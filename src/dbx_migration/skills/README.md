# Migration Framework Skills

Reusable Claude Code skills for the SSIS → Databricks migration framework. Each skill wraps one or more agents/tools and exposes a high-level workflow intent.

## Available Skills

### `/migrate-package`

**Purpose**: Run the full migration loop on one package end-to-end.

**Workflow**:
1. Analyze SSIS package (`dtsx_analyzer`).
2. Generate Lineage Contract (`contract_agent`) → **Gate 1: adjudicate contract**.
3. Transpile SQL (`sql_transpiler` + `transpile_fixup_agent`).
4. Write to medallion (`medallion_writer`).
5. Run reconciliation (`reconciliation_harness`) → **Gate 2: adjudicate diffs**.
6. Finalize or escalate.

**Usage**: `/migrate-package <package_name> --source-group <group> --dtsx-path <path>`

**Output**: Migrated UC tables + reconciliation report + (optional) escalation summary.

**Human Gates**:
- **Gate 1** (contract adjudication): Verify source → target mappings, column-level parity.
- **Gate 2** (diff adjudication): Accept diffs / codify tolerance / escalate.

---

### `/extract-contract`

**Purpose**: Extract and review the Lineage Contract for a package (shallow → deep analysis).

**Workflow**:
1. Analyze SSIS package (`dtsx_analyzer`).
2. Generate contract (`contract_agent`).
3. Validate schema (`contract_agent.validate_contract`).
4. Return contract for review (does not execute write/reconcile).

**Usage**: `/extract-contract <package_name> --source-group <group> --dtsx-path <path>`

**Output**: Contract JSON + validation errors (if any).

**Use case**: Pre-flight check before full migration; contract review without commitment.

---

### `/transpile-package`

**Purpose**: Transpile and review SQL for one package without migration.

**Workflow**:
1. Analyze SSIS package (`dtsx_analyzer`).
2. Extract SQL tasks (from Lineage Contract if available, else from dtsx_analyzer).
3. Transpile each task (`sql_transpiler` + `transpile_fixup_agent`).
4. Return transpiled SQL + fixup log (does not write/reconcile).

**Usage**: `/transpile-package <package_name> --source-group <group> --dtsx-path <path>`

**Output**: Transpiled SQL per target + fixup summary.

**Use case**: Validation of transpilation strategy before reconciliation; isolated SQL review.

---

### `/run-reconciliation`

**Purpose**: Run reconciliation eval for one target (DW reference vs. UC candidate).

**Workflow**:
1. Fetch reference rows from DW (`source_reader.reconciliation_reference_rows`).
2. Fetch candidate rows from UC.
3. Run eval (`reconciliation_harness.reconcile`).
4. Return report (row count, key match, hash match, aggregates + diffs).

**Usage**: `/run-reconciliation --target-uc <uc_fqn> --target-legacy <legacy_name> --spec <json>`

**Output**: Reconciliation report (pass/fail per check) + diff details.

**Use case**: Validation of reconciliation eval; per-target deep dive during debugging.

---

### `/adjudicate-diffs`

**Purpose**: Human adjudication of reconciliation diffs (Gate 2).

**Workflow**:
1. Present diff summary (row-level mismatches, aggregates, hash diffs).
2. Collect human decision: accept (codify tolerance), fix (escalate), or escalate.
3. Record decision + notes (for audit + next-package learning).
4. Update codified tolerance rules (Lakebase run-state, deferred Q1).

**Usage**: `/adjudicate-diffs --report <json> [--action approve|fix|escalate] [--tolerance-rules <json>]`

**Output**: Adjudication record + updated rules (if any).

**Use case**: Final gate before committing migrated tables; establishes acceptable-difference baselines.

---

## Framework Map

Each skill maps to one or more components from the decomposition (#9):

| Skill | Agents | Tools | Decision(s) |
|---|---|---|---|
| `/migrate-package` | `contract_agent` + `transpile_fixup_agent` + `migration_driver` | all | #6–#11 |
| `/extract-contract` | `contract_agent` | `dtsx_analyzer` | #6 |
| `/transpile-package` | `transpile_fixup_agent` | `sql_transpiler`, `dtsx_analyzer` | #11 |
| `/run-reconciliation` | — | `reconciliation_harness`, `source_reader` | #7 |
| `/adjudicate-diffs` | — | — | #9 (Gate 2) |

## Gate Integration

### Gate 1: Contract Adjudication

Triggered by `/migrate-package` after contract generation. Human operator:
1. Reviews contract JSON (`targets[]`, `source`, `column_mappings`, `reconciliation`).
2. Verifies mappings against domain knowledge (package docs, DW schema).
3. **Approves**: Records confidence per target; pipeline proceeds to transpilation.
4. **Rejects**: Requests fixes (escalates to codebase review / manual contract edit).
5. **Escalates**: Flags as ambiguous / unresolvable; deferred to later rounds.

Output: Adjudicated contract (confidence scores, verifier identity, timestamp) → committed to git.

### Gate 2: Diff Adjudication

Triggered by `/migrate-package` after reconciliation. Human operator:
1. Reviews reconciliation report (per check: row_count, key_match, hash_match, aggregates).
2. Examines diffs (missing rows, extra rows, value mismatches, aggregate gaps).
3. **Accepts**: Diffs are acceptable (e.g., known tolerance, new audit columns). Codify rule: `column → tolerance % or explicit list`.
4. **Fixes**: Bug in transpiled SQL or reconciliation spec; escalate for code review.
5. **Escalates**: Unresolved; flag for manual investigation (Lakebase run-state records this).

Output: Adjudication record (decision, tolerance rules) → committed to Lakebase (deferred Q1).

---

## Assumptions & Deferred

- **Run-state storage** (Gate 2 tolerance rules): Deferred to Q1 (Lakebase run-state).
- **Orchestration** (per-package scheduling): Deferred to Q2 (Databricks Workflows, one parameterized job/package).
- **Incremental load semantics**: Deferred to #13 (packages 2–16); skeleton uses full-refresh (TRUNCATE + reload).
- **Cross-contract projection**: Queryable index over JSON contracts (fleet-scale feature); deferred to packages 2–16.

---

## Example Walkthrough: Pilot (MV/Bartira)

**Goal**: Migrate one package end-to-end, prove reconciliation, unlock hands-off for packages 2–16.

**Command**: `dbt invoke skill migrate-package carga_hospital_mv --source-group mv --dtsx-path extracted_dtsx/MV/Carga_Hospital_MV.dtsx`

**Steps**:
1. **Analyze**: dtsx_analyzer parses SSIS (connections, SQL tasks, data flows) → SIMAH_SQL (Oracle) source + Bartira (DW) targets (Atendimento, Guia, etc.).
2. **Contract**: contract_agent generates mappings (STG_ATENDIMENTO → silver_mv_atendimento, DIM_GUIA → tb_gold_dim_guia, etc.). Reconciliation spec: grain_keys=[ID_ATENDIMENTO], hash_columns=[*], agg=[COUNT(*), SUM(STATUS)].
3. **Gate 1**: Human approves mappings, confidence scores recorded.
4. **Transpile**: sql_transpiler (Lakebridge) converts T-SQL → Spark. transpile_fixup_agent fixes ? parameters, 3-part names (dbo.table → platfin_hml.silver.table).
5. **Write**: medallion_writer loads bronze_mv_bartira_* (raw), silver_mv_* (STG_ equivalent), tb_gold_dim_* (DIM_/FAT_).
6. **Reconcile**: reconciliation_harness compares UC vs. DW (JDBC OPENQUERY). Row count ✓, keys ✓, hash ✓, aggregates ✓ → PASSED.
7. **Gate 2**: Human approves. Diffs recorded (empty for pilot) → codified tolerance = exact.
8. **Commit**: Git commit (contract, metadata). Next package.

---

## See Also

- `CONTEXT.md` — terminology & concepts.
- `docs/adr/*` — architectural decisions.
- `docs/framework-structure.md` — layout & mapping to #9.
- `prototypes/reconciliation/recon_eval_prototype.py` — reconciliation validation.
- Issue #1 (walking skeleton) + #9 (framework decomposition) for full context.
