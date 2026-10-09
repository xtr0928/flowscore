#!/usr/bin/env python3
"""新建一条管线骨架。

用法：
    python3 tools/new_pipeline.py <id> --category 编程开发 [--name "显示名"] [--force]

生成 pipelines/<id>/ 三件套（可直接过校验的最小可运行骨架）：
    meta.json           status=draft（改 published 才会进 registry）
    README.md           含占位提示，需自己写够 200 字
    pipeline.flow.json  3 节点最小图：input → model_call → output
"""
import argparse
import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate import PIPELINES_DIR, README_MIN  # noqa: E402

README_TPL = """# {name}

> {summary}

## 这份管线解决什么

（写清楚：什么场景、什么输入、什么产出。至少 {minlen} 字才过校验。）

## 怎么跑

```bash
# 用流谱生成器打开
#   首页 → 这条管线 → 「用生成器打开」
# 或直接拖入 pipeline.flow.json
```

## 前置条件

{requires}

## 注意事项

（模型的坑、耗时、配额、已知限制。）
"""


def flow_skeleton(pid, name, summary):
    return {
        "format": "flowscore.pipeline",
        "format_version": "2.1.0",
        "identity": {
            "id": pid,
            "name": name,
            "version": "0.1.0",
            "author": "xtr0928",
            "license": "MIT",
            "created": datetime.date.today().isoformat(),
            "based_on": None,
        },
        "about": {"summary": summary, "requires": [], "produces": []},
        "globals": {"settings": {}, "prompts": [], "apply_to": "all"},
        "runtime": {"concurrency": 1, "continue_on_error": False, "timeout_sec": 600},
        "nodes": [
            {
                "seq": 1, "id": "n_in", "type": "input", "label": "输入",
                "does": "管线起点：接收用户输入",
                "inputs": [],
                "outputs": [{
                    "port": "text", "type": "text", "carries": "用户输入",
                    "to": [{"node": "n_main", "port": "text"}],
                }],
            },
            {
                "seq": 2, "id": "n_main", "type": "model_call", "label": "主处理",
                "does": "（写一句人话：这个节点干什么）",
                "note": "（写设计意图：为什么这么连）",
                "inputs": [{
                    "port": "text", "type": "text", "carries": "用户输入",
                    "required": True,
                    "from": [{"node": "n_in", "port": "text"}],
                }],
                "outputs": [{
                    "port": "result", "type": "text", "carries": "处理结果",
                    "to": [{"node": "n_out", "port": "content"}],
                }],
                "config": {
                    "provider": {"id": "deepseek", "model": "deepseek-v4-flash"},
                    "prompt": {"template": "……", "variables": ["input.text"]},
                    "params": {"temperature": 0.2, "max_tokens": 4000},
                },
            },
            {
                "seq": 3, "id": "n_out", "type": "output", "label": "落盘",
                "does": "把结果写成文件",
                "inputs": [{
                    "port": "content", "type": "text", "carries": "处理结果",
                    "required": True,
                    "from": [{"node": "n_main", "port": "result"}],
                }],
                "outputs": [],
                "config": {"write_to": "deliverables/out.md", "format": "md"},
            },
        ],
    }


def main():
    ap = argparse.ArgumentParser(description="新建流谱管线骨架")
    ap.add_argument("pid")
    ap.add_argument("--category", required=True)
    ap.add_argument("--name")
    ap.add_argument("--summary")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    d = PIPELINES_DIR / a.pid
    if d.exists() and not a.force:
        print("已存在：%s（要覆盖加 --force）" % d)
        return 1
    d.mkdir(parents=True, exist_ok=True)

    name = a.name or a.pid
    summary = a.summary or "（一句话说清这份管线干什么，站点卡片会显示）"

    (d / "meta.json").write_text(json.dumps({
        "id": a.pid, "category": a.category, "tags": [],
        "status": "draft", "featured": False, "order": 100,
        "cover": None,
        "notes": "脚手架生成，写完内容后把 status 改成 published",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    (d / "pipeline.flow.json").write_text(
        json.dumps(flow_skeleton(a.pid, name, summary), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")

    (d / "README.md").write_text(
        README_TPL.format(name=name, summary=summary, minlen=README_MIN,
                          requires="（端点、依赖、目录权限…）"),
        encoding="utf-8")

    print("✓ 建好 %s" % d)
    for f in ("meta.json", "pipeline.flow.json", "README.md"):
        print("    %s" % f)
    print("\n下一步：")
    print("  1) 写正文（README ≥ %d 字、flow 的 does/note 写清楚）" % README_MIN)
    print("  2) python3 tools/validate.py pipelines/%s" % a.pid)
    print("  3) meta.json 里 status 改 published")
    print("  4) python3 tools/build_registry.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
