#!/usr/bin/env python3
"""扫描 pipelines/ → 生成 registry.json（站点数据源）+ INDEX.md（人看总目录）。

用法：
    python3 tools/build_registry.py

规则：
  · 每个子目录 = 一个管线；必须先过 validate.py 的全部检查才收录
  · 只有 meta.status == "published" 会进 registry
  · 不过的目录记进 registry.skipped[]（附原因），方便修，不会静默丢
  · registry.json 绝不手写 —— 手写必然漂移
"""
import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate import ROOT, PIPELINES_DIR, check_dir, load_json, schema_errors  # noqa: E402

OUT_JSON = ROOT / "registry.json"
OUT_MD = ROOT / "INDEX.md"
REGISTRY_VERSION = "1.0.0"


def stats_of(flow):
    nodes = flow["nodes"]
    models = set()
    for n in nodes:
        pid = (n.get("config", {}).get("provider") or {}).get("id")
        if pid:
            models.add(pid)
    edges = sum(len(o.get("to", [])) for n in nodes for o in n.get("outputs", []))
    return {
        "nodes": len(nodes),
        "edges": edges,
        "notes": sum(1 for n in nodes if n["type"] == "note"),
        "models": len(models),
    }


def entry_of(d, flow, meta):
    ident, about = flow["identity"], flow.get("about", {})
    rel = "pipelines/%s/" % d.name
    return {
        "id": ident["id"],
        "name": ident["name"],
        "summary": about.get("summary", ""),
        "version": ident["version"],
        "author": ident.get("author"),
        "license": ident.get("license"),
        "created": ident.get("created"),
        "category": meta["category"],
        "tags": meta.get("tags", []),
        "featured": bool(meta.get("featured", False)),
        "order": int(meta.get("order", 100)),
        "cover": meta.get("cover"),
        "stats": stats_of(flow),
        "requires": about.get("requires", []),
        "produces": about.get("produces", []),
        "path": rel,
        "flow": rel + "pipeline.flow.json",
        "readme": rel + "README.md",
        "updated": None,
    }


def render_index(entries, skipped, gen):
    L = []
    L.append("# 流谱管线库 · 总目录\n")
    L.append("> 本文件由 `tools/build_registry.py` 自动生成，**请勿手改**。\n")
    L.append("生成时间：%s ｜ 收录 **%d** 条 ｜ 跳过 %d 条\n" % (gen, len(entries), len(skipped)))
    if entries:
        L.append("| # | 管线 | 一句话 | 分类 | 版本 | 节点 | 边 | 模型 |")
        L.append("|---|---|---|---|---|---|---|---|")
        for i, e in enumerate(entries, 1):
            s = e["stats"]
            L.append("| %d | [%s](%s) | %s | %s | %s | %d | %d | %d |"
                     % (i, e["name"], e["path"], e["summary"], e["category"],
                        e["version"], s["nodes"], s["edges"], s["models"]))
        L.append("")
    else:
        L.append("_（暂无收录）_\n")
    if skipped:
        L.append("## 未收录（校验未过）\n")
        for s in skipped:
            L.append("- `%s` —— %s" % (s["dir"], s["reason"]))
        L.append("")
    return "\n".join(L)


def main():
    if not PIPELINES_DIR.exists():
        print("找不到 %s" % PIPELINES_DIR)
        return 1

    entries, skipped = [], []
    for d in sorted(p for p in PIPELINES_DIR.iterdir() if p.is_dir()):
        if d.name.startswith(".") or d.name.startswith("_"):
            continue
        errs, _warns, _info = check_dir(d)
        if errs:
            skipped.append({"dir": d.name, "reason": "校验未过（%d 处）：%s"
                            % (len(errs), errs[0])})
            print("  跳过 %-24s %s" % (d.name, errs[0]))
            continue
        meta = load_json(d / "meta.json")
        if meta.get("status") != "published":
            print("  略过 %-24s status=%s" % (d.name, meta.get("status")))
            continue
        flow = load_json(d / "pipeline.flow.json")
        entries.append(entry_of(d, flow, meta))
        print("  收录 %-24s %s" % (d.name, flow["identity"]["name"]))

    entries.sort(key=lambda e: (0 if e["featured"] else 1, e["order"], e["id"]))
    cats = {}
    for e in entries:
        cats[e["category"]] = cats.get(e["category"], 0) + 1
    gen = datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()

    reg = {
        "registry_version": REGISTRY_VERSION,
        "generated": gen,
        "count": len(entries),
        "pipelines": entries,
        "categories": [{"name": k, "count": v} for k, v in sorted(cats.items())],
        "skipped": skipped,
    }

    errs, warns = schema_errors(reg, "registry.schema.json")
    for w in warns:
        print("  ! %s" % w)
    if errs:
        print("\n生成的 registry.json 不符合 schema（这是个 bug，请修 build_registry.py）：")
        for e in errs[:8]:
            print("  X %s" % e)
        return 1

    # 幂等：内容（除 generated 外）没变就沿用旧时间戳，避免每次构建都产生无意义 diff
    if OUT_JSON.exists():
        try:
            old = load_json(OUT_JSON)
            a, b = dict(old), dict(reg)
            a.pop("generated", None)
            b.pop("generated", None)
            if a == b:
                reg["generated"] = old.get("generated", reg["generated"])
                print("\n  · 内容未变，沿用上次时间戳 %s" % reg["generated"])
        except (json.JSONDecodeError, OSError):
            pass
        if OUT_MD.exists() and OUT_MD.read_text(encoding="utf-8") == render_index(
                entries, skipped, reg["generated"]):
            print("  · INDEX.md 未变")

    OUT_JSON.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(render_index(entries, skipped, reg["generated"]), encoding="utf-8")
    print("\n✓ registry.json  (%d 条)" % len(entries))
    print("✓ INDEX.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
