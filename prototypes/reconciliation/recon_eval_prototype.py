#!/usr/bin/env python3
"""
PROTOTYPE (wayfinder #7) — reconciliation eval harness. Spike, not production.

Goal: "validate the validator." Prove that an eval built from the #6 lineage-contract
ReconSpec (grain_keys / hash_columns / aggregate_metrics / thresholds) catches
row-count, key-level, and hash-level discrepancies — and specifically that an
AGGREGATE-ONLY check is fooled by a value corruption that preserves row counts and
sums, while the hash-level check catches it. That is the whole reason the map insists
on row/key/hash granularity, not just aggregates.

The real harness compiles this same ReconSpec to SQL Server (HASHBYTES('SHA2_256', ...))
on the DW reference side and Spark SQL (sha2(concat_ws(...), 256)) on the migrated
(silver/gold) candidate side, using the SAME canonicalization so hashes match across
engines. Here we run it in pure Python over synthetic rows to prove the LOGIC.
"""
from __future__ import annotations
import hashlib
from dataclasses import dataclass, field

# A single canonicalization, mirrored on every engine, so a row's hash is identical
# regardless of where it is computed. Cross-engine hash parity lives or dies here.
NULL_TOKEN = "\x00NULL\x00"
SEP = "\x1f"  # unit separator — cannot appear in normal data


def canon(v) -> str:
    if v is None:
        return NULL_TOKEN
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, float):
        return format(v, ".6f")        # fixed scale: kills float-format drift
    return str(v).strip()               # trim: trailing-space noise is not a diff


def row_hash(row: dict, cols: list[str]) -> str:
    return hashlib.sha256(SEP.join(canon(row.get(c)) for c in cols).encode()).hexdigest()


@dataclass
class ReconSpec:
    grain_keys: list[str]
    hash_columns: list[str]
    aggregate_metrics: list[tuple[str, str]]           # (column, fn)
    thresholds: dict = field(default_factory=lambda: {
        "row_count": "exact", "key_match": "exact", "hash_match": "exact"})


def _index(rows, keys):
    return {tuple(r[k] for k in keys): r for r in rows}


def _agg(rows, column, fn):
    if fn == "count":
        return len(rows)
    vals = [r[column] for r in rows if r.get(column) is not None]
    if fn == "sum":
        return sum(vals)
    if fn == "count_distinct":
        return len(set(vals))
    raise ValueError(f"unknown agg fn: {fn}")


def reconcile(reference, candidate, spec: ReconSpec) -> dict:
    """reference = source of truth (SQL Server DW); candidate = migrated UC table."""
    rep = {"checks": {}}

    rc_ref, rc_cand = len(reference), len(candidate)
    rc_ok = rc_ref == rc_cand
    rep["checks"]["row_count"] = {"ref": rc_ref, "cand": rc_cand, "pass": rc_ok}

    ref_i, cand_i = _index(reference, spec.grain_keys), _index(candidate, spec.grain_keys)
    missing = sorted(set(ref_i) - set(cand_i))   # in DW, absent from migrated
    extra = sorted(set(cand_i) - set(ref_i))     # in migrated, absent from DW
    key_ok = not missing and not extra
    rep["checks"]["key_match"] = {
        "missing_in_candidate": missing, "extra_in_candidate": extra, "pass": key_ok}

    common = sorted(set(ref_i) & set(cand_i))
    mism = [k for k in common
            if row_hash(ref_i[k], spec.hash_columns) != row_hash(cand_i[k], spec.hash_columns)]
    hash_ok = not mism
    rep["checks"]["hash_match"] = {"mismatched_keys": mism, "pass": hash_ok}

    agg_ok, metrics = True, []
    for col, fn in spec.aggregate_metrics:
        a, b = _agg(reference, col, fn), _agg(candidate, col, fn)
        ok = a == b
        agg_ok &= ok
        metrics.append({"metric": f"{fn}({col})", "ref": a, "cand": b, "pass": ok})
    rep["checks"]["aggregates"] = {"metrics": metrics, "pass": agg_ok}

    rep["passed"] = rc_ok and key_ok and hash_ok and agg_ok
    # What a naive checker that only looks at counts+aggregates would conclude:
    rep["aggregate_only_verdict"] = rc_ok and agg_ok
    return rep


# --------------------------------------------------------------------------- demo
# Reference = the DW's DIM_ESPECIALIDADE (pilot slice), the source of truth.
REFERENCE = [
    {"SMESPEC_ID": 1, "SMESPEC_DESCR": "Cardiologia", "ATIVO": 1},
    {"SMESPEC_ID": 2, "SMESPEC_DESCR": "Ortopedia",   "ATIVO": 1},
    {"SMESPEC_ID": 3, "SMESPEC_DESCR": "Pediatria",   "ATIVO": 1},
    {"SMESPEC_ID": 4, "SMESPEC_DESCR": "Neurologia",  "ATIVO": 0},
]
SPEC = ReconSpec(
    grain_keys=["SMESPEC_ID"],
    hash_columns=["SMESPEC_ID", "SMESPEC_DESCR", "ATIVO"],
    aggregate_metrics=[("SMESPEC_ID", "count"), ("ATIVO", "sum")],
)


def clone(rows):
    return [dict(r) for r in rows]


def variants():
    v = {}

    v["identical"] = clone(REFERENCE)

    dropped = clone(REFERENCE); dropped.pop()                     # lose id=4
    v["dropped_row"] = dropped

    added = clone(REFERENCE); added.append(
        {"SMESPEC_ID": 5, "SMESPEC_DESCR": "Dermatologia", "ATIVO": 1})
    v["added_row"] = added

    # THE dangerous one: swap two descriptions. Row count unchanged (4),
    # count(SMESPEC_ID)=4 unchanged, sum(ATIVO)=3 unchanged — aggregate-only PASSES,
    # but rows 1 and 2 now hold each other's names. Hash-level MUST catch it.
    swapped = clone(REFERENCE)
    swapped[0]["SMESPEC_DESCR"], swapped[1]["SMESPEC_DESCR"] = (
        swapped[1]["SMESPEC_DESCR"], swapped[0]["SMESPEC_DESCR"])
    v["value_swap_agg_preserving"] = swapped

    # Cosmetic-only: trailing whitespace. Canonicalization must NOT flag this.
    ws = clone(REFERENCE); ws[0]["SMESPEC_DESCR"] = "Cardiologia   "
    v["whitespace_only_no_diff"] = ws

    return v


def fmt(rep):
    c = rep["checks"]
    def mark(b): return "PASS" if b else "FAIL"
    lines = [
        f"    row_count : {mark(c['row_count']['pass'])}  (ref={c['row_count']['ref']} cand={c['row_count']['cand']})",
        f"    key_match : {mark(c['key_match']['pass'])}  (missing={c['key_match']['missing_in_candidate']} extra={c['key_match']['extra_in_candidate']})",
        f"    hash_match: {mark(c['hash_match']['pass'])}  (mismatched_keys={c['hash_match']['mismatched_keys']})",
        f"    aggregates: {mark(c['aggregates']['pass'])}  ({', '.join(m['metric']+'='+str(m['ref'])+'/'+str(m['cand']) for m in c['aggregates']['metrics'])})",
        f"    -> OVERALL: {mark(rep['passed'])}   | aggregate-only checker would say: {mark(rep['aggregate_only_verdict'])}",
    ]
    return "\n".join(lines)


def main():
    print("Reconciliation eval prototype — validating the validator (wayfinder #7)\n")
    print(f"ReconSpec: grain_keys={SPEC.grain_keys} hash_columns={SPEC.hash_columns} "
          f"aggregates={[f'{fn}({c})' for c, fn in SPEC.aggregate_metrics]}\n")

    expectations = {
        "identical": True,
        "dropped_row": False,
        "added_row": False,
        "value_swap_agg_preserving": False,
        "whitespace_only_no_diff": True,
    }

    all_correct = True
    fooled_case = None
    for name, cand in variants().items():
        rep = reconcile(REFERENCE, cand, SPEC)
        correct = rep["passed"] == expectations[name]
        all_correct &= correct
        if name == "value_swap_agg_preserving" and rep["aggregate_only_verdict"] and not rep["passed"]:
            fooled_case = name
        print(f"[{name}]  (expected {'PASS' if expectations[name] else 'FAIL'}, "
              f"validator {'CORRECT' if correct else 'WRONG'})")
        print(fmt(rep))
        print()

    print("=" * 72)
    print(f"Validator verdict on all {len(expectations)} seeded cases: "
          f"{'ALL CORRECT ✓' if all_correct else 'INCORRECT ✗'}")
    if fooled_case:
        print(f"Linchpin proven: '{fooled_case}' — an aggregate-only check PASSES it "
              f"(counts+sums intact), but the hash-level check FAILS it. "
              f"This is why the eval must compare at row/key/hash granularity.")
    raise SystemExit(0 if all_correct and fooled_case else 1)


if __name__ == "__main__":
    main()
