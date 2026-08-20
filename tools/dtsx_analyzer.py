#!/usr/bin/env python3
"""
dtsx-analyzer — deterministic tool #1 of the migration framework (wayfinder #9 / #13).

Parses one SSIS .dtsx package into the structured metadata the contract-agent (#6)
consumes: connection managers, Execute-SQL-Task SQL, and data-flow source->destination
chains (Oracle OCI / OLE DB sources -> derived-column transforms -> OLE DB destinations).

Deterministic (no LLM). Feeds contract generation, transpilation (#11), and the
thin-slice choice for the walking-skeleton build.

Usage:
    python3 tools/dtsx_analyzer.py "<path/to.dtsx>" [out.json]
"""
from __future__ import annotations
import sys, json
from xml.etree import ElementTree as ET


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _attrs(el) -> dict:
    return {_local(k): v for k, v in el.attrib.items()}


def _iter_local(el, name: str):
    return (e for e in el.iter() if _local(e.tag) == name)


def _parse_conn_string(cs: str) -> dict:
    kv = {}
    for part in cs.split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            kv[k.strip().lower()] = v.strip()
    return {
        "server": kv.get("data source"),
        "database": kv.get("initial catalog"),
        "provider": kv.get("provider"),
        "user": kv.get("user id"),
        "integrated_security": kv.get("integrated security"),
    }


def analyze(path: str) -> dict:
    root = ET.parse(path).getroot()
    pkg = _attrs(root).get("ObjectName") or path.rsplit("/", 1)[-1]

    connections = []
    seen = set()
    for cm in _iter_local(root, "ConnectionManager"):
        name = _attrs(cm).get("ObjectName")
        if not name or name in seen:
            continue
        cs = next((_attrs(i)["ConnectionString"] for i in cm.iter()
                   if "ConnectionString" in _attrs(i)), None)
        seen.add(name)
        connections.append({"name": name,
                            "parsed": _parse_conn_string(cs) if cs else None})

    sql_tasks, dataflows = [], []
    for ex in _iter_local(root, "Executable"):
        a = _attrs(ex)
        etype, ename = a.get("ExecutableType", ""), a.get("ObjectName", "")
        if "ExecuteSQLTask" in etype:
            sql = next((_attrs(sd)["SqlStatementSource"] for sd in ex.iter()
                        if "SqlStatementSource" in _attrs(sd)), None)
            if sql is not None:
                sql_tasks.append({"name": ename, "sql": sql})
        elif "Pipeline" in etype:
            srcs, dests, derived = [], [], 0
            for c in _iter_local(ex, "component"):
                cls = _attrs(c).get("componentClassID", "")
                table = sqlcmd = None
                for p in _iter_local(c, "property"):
                    pn = _attrs(p).get("name")
                    if pn == "OpenRowset":
                        table = (p.text or "").strip() or None
                    elif pn in ("SqlCommand", "SqlCommandVariable"):
                        sqlcmd = (p.text or "").strip() or None
                if "OracleSrc" in cls or "OLEDBSource" in cls:
                    srcs.append({"kind": "oracle" if "Oracle" in cls else "sqlserver",
                                 "table": table, "sql": sqlcmd})
                elif "OLEDBDestination" in cls:
                    dests.append({"table": table})
                elif "DerivedColumn" in cls:
                    derived += 1
            if srcs or dests:
                dataflows.append({"name": ename, "sources": srcs,
                                  "destinations": dests, "derived_columns": derived})

    return {
        "package": pkg,
        "counts": {"connections": len(connections),
                   "sql_tasks": len(sql_tasks), "dataflows": len(dataflows)},
        "connections": connections,
        "sql_tasks": sql_tasks,
        "dataflows": dataflows,
    }


def _summary(d: dict) -> None:
    print(f"package: {d['package']}")
    print(f"counts : {d['counts']}")
    print("connections:")
    for c in d["connections"]:
        p = c.get("parsed") or {}
        print(f"  - {c['name']}: server={p.get('server')} db={p.get('database')} "
              f"provider={p.get('provider')}")
    print("dataflows (source -> destination):")
    for df in d["dataflows"]:
        s = ", ".join(f"{x.get('kind')}:{x.get('table') or ((x.get('sql') or '')[:28] + '…' if x.get('sql') else '?')}"
                      for x in df["sources"]) or "-"
        dst = ", ".join(x.get("table") or "?" for x in df["destinations"]) or "-"
        print(f"  [{df['name']}] {s}  ->  {dst}  (derived={df['derived_columns']})")
    print("sql_tasks:", ", ".join(t["name"] for t in d["sql_tasks"]))


if __name__ == "__main__":
    data = analyze(sys.argv[1])
    if len(sys.argv) > 2:
        with open(sys.argv[2], "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
    _summary(data)
