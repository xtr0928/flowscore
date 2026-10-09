#!/usr/bin/env python3
"""流谱管线校验器。

用法：
    python3 tools/validate.py                    # 校验 pipelines/ 下全部管线
    python3 tools/validate.py pipelines/<id>     # 只校验一条

检查两层：
  A. schema 层 —— meta.json / pipeline.flow.json 是否符合 schema/
  B. 图与目录层 —— 10 项语义检查（双向一致、mode 用法、挂靠一致、DAG…）

退出码：0 = 全过；1 = 有错误。
"""
import argparse
import collections
import json
import sys
from pathlib import Path

try:
    import jsonschema
except ImportError:
    jsonschema = None

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = ROOT / "schema"
PIPELINES_DIR = ROOT / "pipelines"

README_MIN = 200          # README 最少字数（防占位符上线）
PLACEHOLDER_MARKERS = ("（写清楚", "（一句话说清", "（端点、依赖", "（模型的坑", "（写一句人话", "（写设计意图", "TODO:", "待补充", "待填写")
NODE_TYPES_REQUIRE_WIRING = ("model_call",)   # 必须同时有进有出的类型


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def schema_errors(doc, name):
    """返回 (errors, warnings)。jsonschema 缺失时给出警告并跳过。"""
    if jsonschema is None:
        return [], ["未安装 jsonschema，跳过 schema 校验（pip install jsonschema）"]
    sp = SCHEMA_DIR / name
    if not sp.exists():
        return [], ["找不到 schema/%s，跳过" % name]
    sch = load_json(sp)
    v = jsonschema.Draft202012Validator(sch)
    es = []
    for e in sorted(v.iter_errors(doc), key=lambda x: list(x.path)):
        loc = "/".join(str(x) for x in e.path) or "(根)"
        es.append("%s: %s" % (loc, e.message))
    return es, []


def check_graph(doc):
    """10 项图语义检查。返回 (errors, warnings, info)。"""
    errs, warns, info = [], [], []
    nodes = {n["id"]: n for n in doc["nodes"]}
    notes = [n for n in doc["nodes"] if n["type"] == "note"]

    # 01 seq 连续
    seqs = sorted(n["seq"] for n in doc["nodes"])
    if seqs != list(range(1, len(seqs) + 1)):
        errs.append("01 seq 不连续：%s（应为 1..%d）" % (seqs, len(seqs)))
    else:
        info.append("seq 1..%d 连续" % len(seqs))

    # 02/03 引用存在 + 双向一致
    outs, ins = collections.Counter(), collections.Counter()
    for n in doc["nodes"]:
        for o in n.get("outputs", []):
            for t in o["to"]:
                tn = nodes.get(t["node"])
                if tn is None:
                    errs.append("02 引用不存在的节点：%s -> %s" % (n["id"], t["node"]))
                    continue
                if t["port"] not in {i["port"] for i in tn.get("inputs", [])}:
                    errs.append("02 目标端口不存在：%s.%s -> %s.%s"
                                % (n["id"], o["port"], t["node"], t["port"]))
                if n["type"] == "note" and tn["type"] != "model_call":
                    errs.append("08 注释 %s 注入到 %s（type=%s）—— 只能注入 model_call"
                                % (n["id"], t["node"], tn["type"]))
                outs[(n["id"], o["port"], t["node"], t["port"])] += 1
        for i in n.get("inputs", []):
            for f in i["from"]:
                fn = nodes.get(f["node"])
                if fn is None:
                    errs.append("02 引用不存在的节点：%s <- %s" % (n["id"], f["node"]))
                    continue
                if f["port"] not in {o["port"] for o in fn.get("outputs", [])}:
                    errs.append("02 源端口不存在：%s.%s <- %s.%s"
                                % (f["node"], f["port"], n["id"], i["port"]))
                ins[(f["node"], f["port"], n["id"], i["port"])] += 1

    for e in sorted(set(outs) - set(ins)):
        errs.append("03 单向声明（只有输出侧）：%s.%s -> %s.%s" % e)
    for e in sorted(set(ins) - set(outs)):
        errs.append("03 单向声明（只有输入侧）：%s.%s -> %s.%s" % e)
    info.append("数据边 %d 条，双向一致" % len(outs))

    # 04 mode 只在多来源时写
    for n in doc["nodes"]:
        for i in n.get("inputs", []):
            k, has = len(i["from"]), "mode" in i
            if k >= 2 and not has:
                errs.append("04 %s.%s 有 %d 个来源但没写 mode（all/any/first）" % (n["id"], i["port"], k))
            if k == 1 and has:
                errs.append("04 %s.%s 单来源却写了 mode（噪音，删掉）" % (n["id"], i["port"]))

    # 05 孤立节点
    for n in doc["nodes"]:
        if n["type"] in ("input", "output", "note"):
            continue
        if not n.get("inputs") or not n.get("outputs"):
            warns.append("05 疑似孤立节点：%s（type=%s）" % (n["id"], n["type"]))

    # 06 无环（loop 感知）：纯环 = 错；含 loop 边标记的环 = 合法
    def _kahn(skip_loop):
        indeg = {x: 0 for x in nodes}
        adj = collections.defaultdict(list)
        for n in doc["nodes"]:
            for o in n.get("outputs", []):
                for t in o["to"]:
                    if t["node"] not in nodes:
                        continue
                    if skip_loop and t.get("loop"):
                        continue
                    adj[n["id"]].append(t["node"])
                    indeg[t["node"]] += 1
        q = [x for x, v in indeg.items() if v == 0]
        seen = 0
        while q:
            x = q.pop()
            seen += 1
            for y in adj[x]:
                indeg[y] -= 1
                if indeg[y] == 0:
                    q.append(y)
        return seen

    seen_all = _kahn(skip_loop=False)
    n_total = len(nodes)
    if seen_all == n_total:
        info.append("DAG 无环")
    else:
        seen_simple = _kahn(skip_loop=True)
        if seen_simple == n_total:
            loop_edges = sum(1 for n in doc["nodes"] for o in n.get("outputs", [])
                             for t in o["to"] if t.get("loop"))
            info.append("含环 %d 个节点，已全部由 %d 条 loop 回边标注（合法）"
                        % (n_total - seen_all, loop_edges))
        else:
            errs.append("06 存在未标注的环：拓扑排序只覆盖 %d/%d 个节点 "
                        "（环必须至少有一条边带 loop 标记）" % (seen_simple, n_total))

    # 07 挂靠双向一致
    att_map = {}
    for n in notes:
        if not n.get("text"):
            errs.append("07 注释 %s 没有 text" % n["id"])
        att = n.get("attached_to", [])
        att_map[n["id"]] = {a["node"] for a in att}
        for a in att:
            tn = nodes.get(a["node"])
            if tn is None:
                errs.append("07 注释 %s 挂靠到不存在的节点 %s" % (n["id"], a["node"]))
                continue
            if tn["type"] in ("input", "output"):
                errs.append("07 注释 %s 挂靠到 %s 节点（无意义，挂靠应指向 model_call）"
                            % (n["id"], tn["type"]))
            if n["id"] not in tn.get("annotations", []):
                errs.append("07 挂靠单向：注释 %s 挂在 %s 上，但 %s 没在 annotations 里声明"
                            % (n["id"], a["node"], a["node"]))
    for n in doc["nodes"]:
        for aid in n.get("annotations", []):
            if aid not in nodes:
                errs.append("07 %s 的 annotations 引用了不存在的 %s" % (n["id"], aid))
            elif n["id"] not in att_map.get(aid, set()):
                errs.append("07 挂靠单向：%s 声明了注释 %s，但 %s 没挂过来" % (n["id"], aid, aid))
    if notes:
        n_inj = sum(1 for x in notes if x.get("outputs"))
        n_att = sum(1 for x in notes if x.get("attached_to"))
        n_free = sum(1 for x in notes if not x.get("outputs") and not x.get("attached_to"))
        info.append("注释 %d 个 → 注入 %d / 挂靠 %d / 纯漂浮 %d" % (len(notes), n_inj, n_att, n_free))

    # 09 inject 两端一致
    inj = 0
    for n in doc["nodes"]:
        for o in n.get("outputs", []):
            if "inject" not in o:
                continue
            inj += 1
            for t in o["to"]:
                tn = nodes.get(t["node"])
                if tn is None:
                    continue
                for ti in tn.get("inputs", []):
                    if ti["port"] == t["port"] and ti.get("inject") != o["inject"]:
                        errs.append("09 inject 不一致：%s.%s=%r vs %s.%s=%r"
                                    % (n["id"], o["port"], o["inject"],
                                       t["node"], t["port"], ti.get("inject")))
    if inj:
        info.append("注入型端口 %d 个" % inj)

    # 10 globals 引用合法
    g = doc.get("globals", {})
    ids = [p.get("id") for p in g.get("prompts", [])]
    if len(ids) != len(set(ids)):
        errs.append("10 globals.prompts 的 id 有重复：%s" % ids)
    for n in doc["nodes"]:
        for ex in n.get("config", {}).get("globals", {}).get("exclude", []):
            if ex not in ids:
                errs.append("10 %s 排除的全局提示词 %s 不存在" % (n["id"], ex))
    if ids or g.get("settings"):
        info.append("全局提示词 %d 条 / 全局设置 %d 项" % (len(ids), len(g.get("settings", {}))))

    return errs, warns, info


def check_dir(d):
    """校验一个管线目录。返回 (errors, warnings, info)。"""
    errs, warns, info = [], [], []
    d = Path(d)

    for f in ("meta.json", "pipeline.flow.json", "README.md"):
        if not (d / f).exists():
            errs.append("三件套缺失：%s" % f)
    if errs:
        return errs, warns, info

    try:
        meta = load_json(d / "meta.json")
    except json.JSONDecodeError as e:
        return ["meta.json 不是合法 JSON：%s" % e], warns, info
    try:
        flow = load_json(d / "pipeline.flow.json")
    except json.JSONDecodeError as e:
        return ["pipeline.flow.json 不是合法 JSON：%s" % e], warns, info

    e, w = schema_errors(meta, "meta.schema.json")
    errs += ["meta.json 不符合 schema —— " + x for x in e]
    warns += w
    e, w = schema_errors(flow, "pipeline.flow.schema.json")
    errs += ["pipeline.flow.json 不符合 schema —— " + x for x in e]
    warns += w

    # 目录级一致性
    fid = flow.get("identity", {}).get("id")
    if meta.get("id") != d.name:
        errs.append("meta.id=%r 与目录名 %r 不一致" % (meta.get("id"), d.name))
    if fid != d.name:
        errs.append("flow.identity.id=%r 与目录名 %r 不一致" % (fid, d.name))
    if meta.get("id") and fid and meta["id"] != fid:
        errs.append("meta.id=%r 与 flow.identity.id=%r 不一致（两份文件各说各话）"
                    % (meta["id"], fid))

    readme = (d / "README.md").read_text(encoding="utf-8").strip()
    n = len(readme)
    hits = [m for m in PLACEHOLDER_MARKERS if m in readme]
    if hits:
        errs.append("README.md 仍含占位符文字：%s —— 请写真实内容" % "、".join(hits))
    if n < README_MIN:
        errs.append("README.md 只有 %d 字（要求 ≥ %d）—— 防占位符上线" % (n, README_MIN))
    else:
        info.append("README %d 字" % n)

    try:
        ge, gw, gi = check_graph(flow)
        errs += ge
        warns += gw
        info += gi
    except (KeyError, TypeError) as e:
        errs.append("图结构异常，无法继续检查：%r" % e)

    return errs, warns, info


def main():
    ap = argparse.ArgumentParser(description="流谱管线校验器")
    ap.add_argument("paths", nargs="*", help="管线目录（默认 pipelines/ 下全部）")
    ap.add_argument("-q", "--quiet", action="store_true", help="只打印失败的")
    args = ap.parse_args()

    targets = [Path(p) for p in args.paths]
    if not targets:
        if not PIPELINES_DIR.exists():
            print("找不到 %s" % PIPELINES_DIR)
            return 1
        targets = sorted([p for p in PIPELINES_DIR.iterdir() if p.is_dir()])

    if not targets:
        print("pipelines/ 下还没有任何管线")
        return 0

    total_err = 0
    for d in targets:
        errs, warns, info = check_dir(d)
        ok = not errs
        total_err += len(errs)
        if ok and args.quiet:
            continue
        head = "✓" if ok else "✗"
        print("%s %s" % (head, d.name))
        for i in info:
            if not args.quiet:
                print("    · %s" % i)
        for w in warns:
            print("    ! %s" % w)
        for e in errs:
            print("    X %s" % e)
        print()

    print("=" * 46)
    print("检查 %d 条管线，%s" % (len(targets),
                                "全部通过" if total_err == 0 else "%d 处错误" % total_err))
    return 0 if total_err == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
