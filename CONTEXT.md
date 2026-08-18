# SSIS → Databricks Migration Framework

The agent-driven framework that migrates Rede D'Or's SSIS-loaded SQL Server data warehouse onto Databricks, one package at a time, and proves parity against the current DW output before trusting the migration.

## Language

**Package**:
One SSIS `.dtsx` unit — the granularity a Lineage Contract covers. The corpus is 16, across four source groups (Moderna, MV, Tasy, WPD).
_Avoid_: job, pipeline (a *pipeline* is the migrated Databricks output, not the SSIS input)

**Lineage Contract**:
The machine-readable, package-scoped record of how one Package's sources map to its Targets, plus the reconciliation checks for each Target. It is what the migration agent works *from* and what gives reconciliation its column-level parity targets.
_Avoid_: mapping doc, manifest, spec

**Target**:
A data-warehouse table a Package loads — staging (`STG_`), dimension (`DIM_`), or fact (`FAT_`/`FACT_`). Reconciliation runs per Target.
_Avoid_: destination, sink, output table

**Column Mapping**:
An explicit source-column → target-column edge, carried when the SSIS step is a mechanical 1:1 OLE DB data flow (e.g. Stage). The lineage is structurally extractable.
_Avoid_: field map

**SQL-Task Transform**:
A Target whose transform lives as opaque T-SQL inside an Execute SQL Task (e.g. dimension/fact loads with JOINs, `CASE`, UDF calls). The lineage is implicit in the SQL, not column-mapped.
_Avoid_: query transform

**Reconciliation Spec**:
The declarative, dialect-agnostic description of a Target's parity checks — grain keys, hash columns, aggregate metrics, thresholds. It states *what* to compare; the reconciliation eval decides *how* to run it.
_Avoid_: recon query, validation query

**Grain Key**:
The business key(s) identifying one row of a Target, at which key-level and hash comparison is performed. An aggregate-only check can be fooled by a bug that preserves totals but corrupts rows; the Grain Key is what makes the hash-level check possible.
_Avoid_: primary key, natural key

**Source Hash**:
The content hash of the source `.dtsx`, stored in the Lineage Contract as the drift detector: when the Package changes, the hash mismatches and the framework regenerates the contract.
_Avoid_: checksum, version hash

**Adjudication Gate**:
The human review where an agent-generated Lineage Contract's mappings (and later, the first reconciliation diffs) are ratified — recorded per mapping as a confidence score and a verified-by identity. One of the two human gates that earn hands-off migration of the remaining packages.
_Avoid_: sign-off, approval step
