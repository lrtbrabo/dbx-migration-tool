---
status: accepted
---

# UC target layout: bronze/silver/gold medallion in the existing `platfin_hml` catalog

The migrated pipeline output lands in a **bronze/silver/gold medallion** built inside the **existing `platfin_hml` catalog** (one catalog, three schemas: `bronze`, `silver`, `gold`), following Rede D'Or's corporate Data Lake standard **IND.GD.DOR-0001 v01.003** for bronze/silver/gold table nomenclature. This fills the Lineage Contract's `target_table.uc` slot (ADR-0001 / #6).

## SSIS layer → medallion mapping

| SSIS layer | Medallion | Naming (per IND.GD.DOR-0001) | Reconciled vs DW |
|---|---|---|---|
| source operational table | **bronze** | `bronze_<sistemaOrigem>_<baseOrigem>_<tabelaOrigem>` | — (new raw layer; no DW counterpart) |
| `STG_*` (truncate+reload current snapshot, source format) | **silver** | `silver_<sistemaOrigem>_<tabelaOrigem>` | DW `STG_*` |
| `DIM_*` / `FAT_*`·`FATO_*` (business-modeled) | **gold** | `<tb\|vw>_gold_<tipoCamada>_<assunto>` (`tipoCamada` ∈ cad/mov/fat/dim/dom/esp) | DW `DIM_*`/`FAT_*` |

Pilot slice (Moderna): `SMESPEC` → bronze `platfin_hml.bronze.bronze_moderna_simah_smespec`; `STG_SMESPEC` → silver `platfin_hml.silver.silver_moderna_smespec`; `DIM_ESPECIALIDADE` → gold `platfin_hml.gold.tb_gold_dim_especialidade`. (`SIMAH_SQL` is the source database on server `10.133.109.5`; the DW target is `Orthoservice_Moderna` on `BIDB01`.)

## Considered Options

- **Single existing catalog `platfin_hml` + `bronze`/`silver`/`gold` schemas** — chosen. Uses the catalog the platform team designated for this (financial-platform, homologation) effort; layer-schemas keep the medallion cohesive and easy to grant/rebuild while iterating the skeleton.
- **The standard's own catalog scheme** (bronze+silver in a per-source-system catalog, gold in `gold_<corporativo>`) — **deviated from** for this effort; we consolidate into `platfin_hml` and revisit alignment at production cutover. This deviation is the main thing a future reader will question — hence this ADR.
- **New dedicated catalog (e.g. `bi_dw`)** — rejected in favour of the existing designated catalog.
- **`STG_ → bronze`** (with silver as an added dedupe step) — rejected. SSIS `STG_` is a truncate+reload *current snapshot in source format*, which matches the standard's **silver** definition; **bronze** is the genuinely-raw-from-source layer the DW never had.

## Consequences

- **Reconciliation gates** are **silver ↔ DW `STG_`** and **gold ↔ DW `DIM_/FAT_`**. **Bronze has no DW counterpart** (reconcile against source row-count, if at all) — it is a new raw layer; history/CDC is deferred (see the map's load-semantics fog).
- The `target_table.uc` slot in each contract is filled by this convention: `STG_` Targets → silver FQN, `DIM_/FAT_` Targets → gold FQN.
- **Deviation from IND.GD.DOR-0001's catalog rule** (single `platfin_hml` vs the standard's split) is deliberate for HML; flag for the Architecture/Governance team at production cutover.
- **Casing-collision Target names** (e.g. `Fact_Table` vs `fact_table` in one package, seen in WPD/MV) need a disambiguation rule before those packages migrate; the Moderna pilot is clean, so deferred.
- Gold uses a **single `gold` schema** for the skeleton; the standard's subject/`<assunto>` schemas can be adopted once gold subjects are defined.
