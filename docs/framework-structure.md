# Framework Structure

The SSIS → Databricks migration framework decomposes into **deterministic tools**, **agents**, and **reusable skills** per Issue #9. This document maps the architecture to the codebase layout.

## High-Level Decomposition

```
┌─────────────────────────────────────────────────────────────────┐
│  Walking Skeleton Loop (migration_driver)                       │
│  ┌─────────────┐ ┌──────────────┐ ┌──────────────┐ ┌─────────┐ │
│  │ Analyze     │ │ Contract Gen │ │ Transpile    │ │ Write   │ │
│  │ (SSIS dtsx) │ │ & Adjudicate │ │ & Fixup      │ │ Medallion│ │
│  └─────────────┘ └──────────────┘ └──────────────┘ └─────────┘ │
│                                                                   │
│  ┌──────────────────────────────────┐ ┌──────────────────────┐  │
│  │ Reconcile                        │ │ Adjudicate Diffs     │  │
│  │ (row/key/hash + agg)             │ │ & Escalate           │  │
│  └──────────────────────────────────┘ └──────────────────────┘  │
│                                                                   │
│  Two Human Gates:                                                │
│    • Gate 1: Adjudicate contract (mappings, reconciliation spec) │
│    • Gate 2: Adjudicate diffs (accept / fix / escalate)          │
└─────────────────────────────────────────────────────────────────┘

Deterministic Tools        Agents                      Skills
├── dtsx_analyzer          ├── contract_agent          ├── /migrate-package
├── source_reader          ├── transpile_fixup_agent   ├── /extract-contract
├── sql_transpiler         └── migration_driver        ├── /transpile-package
├── medallion_writer                                   ├── /run-reconciliation
└── reconciliation_harness                             └── /adjudicate-diffs
```

---

## Directory Layout

```
dbx-migration-tool/
├── src/dbx_migration/              # Python package (scaffolding)
│   ├── __init__.py                 # Package root
│   ├── tools/                      # Deterministic tools (stubs, #10–#11, #8, #7)
│   │   ├── __init__.py
│   │   ├── source_reader.py        # JDBC + OPENQUERY reader (#10)
│   │   ├── sql_transpiler.py       # Lakebridge wrapper (#11)
│   │   ├── medallion_writer.py     # UC bronze/silver/gold writer (#8)
│   │   └── reconciliation_harness.py # row/key/hash eval (#7)
│   ├── agents/                     # Claude-driven agents (stubs, #6, #11, #9)
│   │   ├── __init__.py
│   │   ├── contract_agent.py       # Lineage contract generator (#6)
│   │   ├── transpile_fixup_agent.py # Post-Lakebridge fixer (#11)
│   │   └── migration_driver.py     # Loop orchestrator (#9)
│   └── skills/                     # Reusable Claude Code skills (#9)
│       ├── __init__.py
│       └── README.md               # Skill documentation + workflows
│
├── contract.schema.json            # JSON Schema for Lineage Contracts (ADR-0001)
├── docs/
│   ├── adr/                        # Architectural Decision Records
│   │   ├── 0001-lineage-contract-as-git-tracked-json.md
│   │   └── 0002-uc-target-layout-medallion.md
│   ├── agents/                     # Agent-specific docs
│   │   ├── domain.md
│   │   ├── issue-tracker.md
│   │   └── triage-labels.md
│   └── framework-structure.md      # This file
│
├── prototypes/                     # Validation & design spikes
│   └── reconciliation/
│       └── recon_eval_prototype.py # Reconciliation validator (proven logic)
│
├── tools/
│   └── dtsx_analyzer.py            # SSIS parser (existing, not in src/)
│
├── CONTEXT.md                      # Domain terminology & concepts
├── CLAUDE.md                        # Project instructions
└── contract.schema.json            # JSON Schema (symlink or copy at root)
```

---

## Mapping to Issue #9 Decisions

### 1. Deterministic Tools (`src/dbx_migration/tools/`)

**Decision**: Five core deterministic tools form the scaffolding; each maps to one framework sub-decision.

| Tool | Issue | Purpose | Input | Output |
|---|---|---|---|---|
| `source_reader` | #10 | Read from SSIS sources (SQL Server, Oracle via OPENQUERY) | Connection metadata, query | Rows (for reconciliation, staging, audit) |
| `sql_transpiler` | #11 | Convert SQL Server / Oracle SQL to Spark via Lakebridge | T-SQL / Oracle SQL | Spark SQL + transpilation report |
| `medallion_writer` | #8 | Write migrated data to UC bronze/silver/gold layers | Transpiled SQL, target FQN | UC delta tables in `platfin_hml` |
| `reconciliation_harness` | #7 | Reconciliation eval (row/key/hash + aggregates) | Reference rows, candidate rows, ReconSpec | Reconciliation report (pass/fail per check + diffs) |
| dtsx_analyzer (existing) | #2 | Parse SSIS package structure (not owned by scaffold) | .dtsx file | Connections, SQL tasks, data flows (JSON) |

### 2. Agents (`src/dbx_migration/agents/`)

**Decision**: Three agent responsibilities orchestrate the loop and handle decision-making.

| Agent | Issue | Purpose | Inputs | Outputs |
|---|---|---|---|---|
| `contract_agent` | #6 | Generate Lineage Contracts from SSIS analysis | dtsx_analyzer output, package metadata | LineageContract (JSON) + validation errors |
| `transpile_fixup_agent` | #11 | Fix post-Lakebridge SQL (~5–10 issues/task) | Transpiled SQL, source dialect, context | Fixed Spark SQL + fixup log |
| `migration_driver` | #9 | Orchestrate end-to-end loop (analyze → contract → transpile → write → reconcile → adjudicate) | Package metadata, dtsx path, flags | MigrationContext (status, artifacts, errors) |

### 3. Reusable Skills (`src/dbx_migration/skills/`)

**Decision**: Five high-level workflows wrap agents + tools for user-facing intent.

| Skill | Use Case | Agents | Tools |
|---|---|---|---|
| `/migrate-package` | Full migration end-to-end | contract_agent, transpile_fixup_agent, migration_driver | all |
| `/extract-contract` | Contract review (shallow) | contract_agent | dtsx_analyzer |
| `/transpile-package` | SQL transpilation review (isolated) | transpile_fixup_agent | sql_transpiler |
| `/run-reconciliation` | Reconciliation eval per target | — | reconciliation_harness, source_reader |
| `/adjudicate-diffs` | Gate 2: diff adjudication | — | — |

### 4. Data Model (`contract.schema.json`)

**Decision**: Lineage Contracts are **git-tracked JSON** (ADR-0001) per package, governed by a JSON Schema (draft 2020-12).

**File Path**: `contract.schema.json` (repo root)

**Key Sections**:
- `package`: Source SSIS metadata (name, group, path, source hash for drift detection).
- `connections[]`: SSIS connection managers (source systems, databases).
- `targets[]`: Each target table, with:
  - `target_table`: Legacy name + UC FQN (per ADR-0002).
  - `load_semantics`: full_refresh (skeleton) or incremental (deferred).
  - `transform_type`: column_mapping (1:1 OLE DB) or sql_task (Execute-SQL-Task).
  - `column_mappings[]` or `sql`: Explicit edges or opaque SQL.
  - `reconciliation`: ReconSpec (grain_keys, hash_columns, aggregates, thresholds).
  - `confidence`: Adjudication metadata (score, verifier, notes).

---

## Lifecycle & Gates

### Walking Skeleton Loop (end-to-end per package)

```
1. Analyze SSIS package
   └→ dtsx_analyzer → connections, SQL tasks, data flows

2. Generate Lineage Contract
   └→ contract_agent + dtsx_analyzer → LineageContract JSON

   ⚠️  Gate 1: Contract Adjudication
       Human operator reviews mappings, column parity, reconciliation spec.
       Decision: approve (confidence scores recorded) / reject / escalate.
       Output: Adjudicated contract (git-tracked).

3. Transpile SQL
   └→ sql_transpiler (Lakebridge) → Spark SQL
   └→ transpile_fixup_agent → Fixed Spark SQL

4. Write to Medallion
   └→ medallion_writer → UC bronze/silver/gold in platfin_hml

5. Run Reconciliation
   └→ reconciliation_harness (row/key/hash + agg) → Reconciliation report

   ⚠️  Gate 2: Diff Adjudication
       Human operator reviews diffs (missing/extra rows, hash mismatches, agg gaps).
       Decision: accept (codify tolerance) / fix (escalate) / escalate.
       Output: Adjudication record + tolerance rules (Lakebase, deferred Q1).

6. Finalize
   └→ Migrated tables committed; next package or end.
```

### Two Human Gates

**Gate 1: Contract Adjudication** (Post-Contract Generation)
- **Decision**: Verify source → target mappings, column-level parity, reconciliation specs.
- **Input**: Generated Lineage Contract (JSON).
- **Actions**:
  - ✅ **Approve**: Record confidence per target + verifier identity → proceed to transpilation.
  - ❌ **Reject**: Request fixes (escalates to code review / manual contract edit).
  - ⚠️ **Escalate**: Flag ambiguous / unresolvable → defer to later rounds.
- **Output**: Adjudicated contract (git-tracked, adjudication metadata recorded).

**Gate 2: Diff Adjudication** (Post-Reconciliation)
- **Decision**: Accept reconciliation diffs / codify tolerance / escalate for investigation.
- **Input**: Reconciliation report (row count, key match, hash match, aggregates + diffs).
- **Actions**:
  - ✅ **Accept**: Diffs are acceptable (known tolerance, new audit columns). Codify rule: `column → tolerance % or explicit list`.
  - 🔧 **Fix**: Bug in transpiled SQL or reconciliation spec → escalate for code review.
  - ⚠️ **Escalate**: Unresolved / ambiguous → flag for manual investigation (Lakebase run-state records decision).
- **Output**: Adjudication record (decision, tolerance rules) → committed (Lakebase, deferred Q1).

---

## Per-Package State & Versioning

### Lineage Contracts (git-tracked, per #9)

**Location**: `contracts/<group>/<package>.contract.json`

**Lifecycle**:
1. Generated by `contract_agent` (post-analysis).
2. Adjudicated via Gate 1 (human approval + confidence scores).
3. Committed to git (versioned alongside framework code).
4. Source hash (from .dtsx) enables drift detection (re-generate if .dtsx changes).

### Run-State (deferred to Q1, per #9)

**Intended Location**: Lakebase table (dynamic, not git-tracked).

**Contents**:
- Per-package status (not_started, in_progress, completed, failed, escalated).
- Adjudication records (Gate 1 + Gate 2 decisions + tolerance rules).
- Last reconciliation result (pass/fail per check, diffs, timestamp).

**Deferred**: Q1 effort (outside skeleton scope).

### Orchestration (deferred to Q2, per #9)

**Intended Mechanism**: Databricks Workflows (one parameterized job per package).

**Deferred**: Q2 effort (outside skeleton scope). Skeleton runs via `/migrate-package` skill (interactive).

---

## Framework Assumptions & Constraints

### Skeleton Scope

✅ **Included**:
- Full migration loop on one pilot package (MV/Bartira).
- Reconciliation eval proven to catch discrepancies (validate-the-validator, #7).
- Adjudicate first diffs (Gate 2) to unlock hands-off for packages 2–16.
- Lineage contracts (git-tracked) + UC medallion layout (ADR-0002) + transpilation strategy (ADR-0001, #11).

❌ **Deferred (Packages 2–16)**:
- Incremental load semantics (full-refresh only for skeleton).
- Lakebase run-state storage (Gate 2 tolerance rules, Q1).
- Databricks Workflows orchestration (per-package scheduling, Q2).
- Cross-contract queryable projection (fleet-scale feature).

### Design Constraints

1. **Generality**: Framework applied to one package must generalize to all 16 (no bespoke one-offs).
2. **Minimal Human Interaction**: Two gates (contract + diffs), then hands-off for remaining packages.
3. **Determinism**: Tools are deterministic (no LLM, reproducible); agents are decision-drivers (LLM-backed).
4. **Parity Proof**: Reconciliation eval must be proven (prototype validated) before production use.

---

## Calling Conventions

### To Run the Full Migration Loop (Pilot / Test)

```bash
# Via Claude Code skill
/migrate-package carga_hospital_mv \
  --source-group mv \
  --dtsx-path extracted_dtsx/MV/Carga_Hospital_MV.dtsx \
  [--dry-run]
```

### To Extract & Review Contract (Shallow Analysis)

```bash
/extract-contract carga_hospital_mv \
  --source-group mv \
  --dtsx-path extracted_dtsx/MV/Carga_Hospital_MV.dtsx
```

### To Review Transpilation (SQL Only)

```bash
/transpile-package carga_hospital_mv \
  --source-group mv \
  --dtsx-path extracted_dtsx/MV/Carga_Hospital_MV.dtsx
```

### To Run Reconciliation (Per-Target Deep Dive)

```bash
/run-reconciliation \
  --target-uc platfin_hml.silver.silver_mv_atendimento \
  --target-legacy STG_ATENDIMENTO \
  --spec '{"grain_keys": ["ID_ATENDIMENTO"], "hash_columns": ["*"], "aggregate_metrics": [["count", "count"]]}'
```

### To Adjudicate Diffs (Gate 2)

```bash
/adjudicate-diffs \
  --report <reconciliation_report.json> \
  [--action approve|fix|escalate] \
  [--tolerance-rules <tolerance_spec.json>]
```

---

## See Also

- **CONTEXT.md**: Domain terminology & core concepts.
- **ADR-0001**: Lineage contracts are git-tracked JSON.
- **ADR-0002**: UC target layout (bronze/silver/gold in `platfin_hml`).
- **prototypes/reconciliation/recon_eval_prototype.py**: Reconciliation validator (proven logic).
- **Issue #1**: Walking skeleton map (end-to-end destination).
- **Issue #9**: Framework decomposition (this architecture).
- **src/dbx_migration/skills/README.md**: Skill workflows & gate integration.
