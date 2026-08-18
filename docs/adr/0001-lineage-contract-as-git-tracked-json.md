---
status: accepted
---

# Lineage contracts are git-tracked JSON, one file per package

The Lineage Contract is the framework's central artifact (source → transform → target mappings + per-target reconciliation specs). We store it as **one JSON document per package** (`contracts/<group>/<package>.contract.json`), governed by a JSON Schema and **git-tracked as the source of truth** — *not* in the pre-existing `mdm.diamond_lakebase`, nor a Delta/UC table. The contract is a generated, human-reviewed, static-per-version artifact whose lifecycle (generate → adjudicate → consume) maps exactly onto git: the Adjudication Gate is a pull-request review of a contract diff, versioning is git history, and the contract stays co-versioned with the framework code that produced it — and the framework, not any one pilot, is the product.

## Considered Options

- **Lakebase (`mdm.diamond_lakebase`)** — rejected as source of truth. Its only pull was "reuse existing infra," but that is an MDM *data* store; putting migration-framework metadata there couples two unrelated domains. Reuse-of-infra is not reuse-of-domain.
- **Delta table in UC** — rejected as source of truth. Heavy for ~16 small documents, awkward for single-record read/write and human diff review. Its real strength (UC-native lineage) is unaffected by this choice: UC-native lineage is produced at *runtime* when the migrated pipeline runs, as a derived cross-check, independent of where the contract text lives.
- **git JSON files** — chosen. The core migration loop is a per-package key fetch ("load the contract for package X"), which files serve trivially.

## Consequences

- No live cross-contract SQL query without a **derived** projection (a Delta/Lakebase index built by scanning the files). That projection's value is fleet-scale, so it is out of scope for the walking-skeleton map and rides with the packages-2–16 effort; the JSON Schema is designed to flatten into rows trivially when it is built.
- Contract writes go through git rather than concurrent OLTP — acceptable for a generate-once / review-once artifact.
- A *live registry of migration run-state* (status, last reconciliation result, adjudicated diffs) is dynamic and is **not** this artifact; if needed, it belongs to the framework decomposition, separate from the contract.
