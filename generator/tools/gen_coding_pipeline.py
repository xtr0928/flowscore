# -*- coding: utf-8 -*-
"""把 Multi-agent-programming-pipeline/coding_pipeline.py（协同编码管线·执行段）
映射为 pipeline-orchestrator 可导入的 pipeline.json + layout.json。

Masks secrets: no secrets involved（文件里只写环境变量名，不含任何密钥）。
"""
import json
from pathlib import Path

OUT_DIR = Path(r"D:\XTR-projects\pipeline-orchestrator\samples")
OUT_DIR.mkdir(parents=True, exist_ok=True)

PROVIDERS = {
    'deepseek': {"id": "deepseek", "label": "DeepSeek", "channel": "builtin",
                 "base_url": "https://api.deepseek.com/v1", "api_key_env": "DEEPSEEK_API_KEY"},
    'zhipu':    {"id": "zhipu", "label": "智谱 GLM", "channel": "builtin",
                 "base_url": "https://open.bigmodel.cn/api/paas/v4", "api_key_env": "ZHIPU_API_KEY"},
    'token8341':{"id": "token8341", "label": "token8341", "channel": "builtin",
                 "base_url": "https://admin.token8341.com/v1", "api_key_env": "TOKEN8341_API_KEY"},
}

def mc(label, provider, model, system, template, outfile, ports_in, out_label, fmt='md'):
    """构造一个 model_call 节点 config。ports_in: [(id,label), ...]"""
    return {
        "provider": dict(PROVIDERS[provider]),
        "model": model,
        "prompt": {"template": template, "variables": [], "system": system},
        "output": {"format": fmt, "filename_template": outfile,
                   "encoding": "utf-8", "overwrite": "overwrite"},
        "inputs": [{"id": pid, "type": "any", "label": plab} for pid, plab in ports_in],
        "outputs": [{"id": "out", "type": "text", "label": out_label}],
    }

nodes = [
    {"id": "n_req", "type": "input", "label": "需求文本", "config": {
        "content": "（把项目需求粘贴到这里。例：做一个单文件 HTML 的番茄钟应用，支持任务列表与统计图）",
        "outputs": [{"id": "text", "type": "text", "label": "文本"}]}},

    {"id": "n_p0", "type": "model_call", "label": "① 需求理解", "config": mc(
        "① 需求理解", 'deepseek', 'deepseek-v4-pro',
        "你是协同编码管线的编排者 DeepSeek。输入用户需求，输出结构化需求文档（中文）。必须包含以下小节：\n"
        "# 需求文档\n## 目标（一段话）\n## 功能清单（- 条目）\n## 边界（做什么/不做什么）\n"
        "## 技术约束（语言/框架/环境）\n## 交付物清单（预期产出哪些文件，逐条）\n## 视觉判定\n"
        "VISUAL: yes|no ← 仅一行。若交付物含 HTML/CSS/SVG/图表生成代码/图片，填 yes，否则 no",
        "用户需求：\n{{ input.text }}", "requirements.md",
        [("in", "需求")], "需求文档")},

    {"id": "n_p1", "type": "model_call", "label": "② 整体设计", "config": mc(
        "② 整体设计", 'deepseek', 'deepseek-flash',
        "你是协同编码管线的架构设计者 DeepSeek-Flash。基于需求文档，设计整体情况（不写代码）。输出必须严格按以下格式（中文）：\n"
        "# 设计文档\n## 项目结构（树状）\n## 数据模型/接口（如有）\n## 文件清单\n"
        "对每个文件输出一节：\n### FILE: <相对路径>\n职责：一句话\n依赖: <逗号分隔；无依赖则写 无>\n规格：<完整规格>\n"
        "文件按实施顺序排列；相互独立的文件前可用 ## GROUP 标记（可并行编写）。",
        "需求文档：\n{{ node.n_p0.out }}", "design.md",
        [("req", "需求文档")], "设计文档")},

    {"id": "n_p1b", "type": "model_call", "label": "③ 视觉规格", "config": mc(
        "③ 视觉规格", 'token8341', 'qwen3.8-max',
        "你是协同编码管线的视觉与 UI 设计者 Qwen。基于需求与设计文档，输出视觉规格（中文），包含：\n"
        "# 视觉规格\n## 页面清单（- 页面路径 + 用途）\n## 每个页面的视觉规格（布局结构、配色方案、字号层级、组件样式、响应式要求）\n"
        "## 图表/图片清单（类型、数据标注要求）\n## 视觉检查清单（可逐项核对的检查项）",
        "需求文档：\n{{ node.n_p0.out }}\n\n设计文档（节选文件清单）：\n{{ node.n_p1.out }}", "visual_spec.md",
        [("req", "需求"), ("design", "设计")], "视觉规格")},

    {"id": "n_p2", "type": "model_call", "label": "④ 逐文件编码", "config": mc(
        "④ 逐文件编码", 'zhipu', 'glm-5.3',
        "你是协同编码管线的代码编写者 GLM-5.3。按规格编写该文件的完整代码。规则：只输出完整代码，不要任何解释、不要 markdown 代码块围栏。\n"
        "若文件较大：必须完整输出全文，禁止省略、禁止以注释代替内容、禁止改写与任务无关的部分。\n"
        "真实管线中此环节逐文件调用、每次只带该文件规格与声明的依赖文件（独立上下文）。",
        "设计文档（含文件清单与逐文件规格）：\n{{ node.n_p1.out }}\n\n按清单中每个文件的规格逐一输出完整代码：",
        "code-output.txt", [("design", "设计文档")], "代码文件", fmt='txt')},

    {"id": "n_p3a", "type": "model_call", "label": "⑤ 代码审查", "config": mc(
        "⑤ 代码审查", 'deepseek', 'deepseek-flash',
        "你是本管线新开启的独立审查实例，与设计者、编码者互不相识，不承袭任何先前结论。以需求原文为最高基准、规格文档为对照，独立审查代码（逻辑/安全/风格/遗漏/规格偏差）。\n"
        "输出第一行：✅ 通过 或 ⚠️ 需修改；若需修改，随后逐条列出「问题位置 + 问题说明 + 修改建议」。",
        "需求文档：\n{{ node.n_p0.out }}\n\n设计规格：\n{{ node.n_p1.out }}\n\n代码（逐文件审查）：\n{{ node.n_p2.out }}",
        "review_code.md", [("req", "需求"), ("spec", "规格"), ("code", "代码")], "代码审查报告")},

    {"id": "n_p3b", "type": "model_call", "label": "⑥ 视觉审查", "config": mc(
        "⑥ 视觉审查", 'token8341', 'qwen3.8-max',
        "你是协同编码管线的视觉审查者 Qwen。对照视觉规格检查页面/图片的实际渲染效果。\n"
        "检查：布局与规格一致性 / 配色 / 文字可读性与截断 / 元素可见性 / 图表标注。\n"
        "输出：✅ 通过 或 ⚠️ 需修改（逐条列出问题位置+建议）。真实管线中此环节对页面截图做视觉审查。",
        "视觉规格：\n{{ node.n_p1b.out }}\n\n页面与代码：\n{{ node.n_p2.out }}",
        "review_visual.md", [("spec", "视觉规格"), ("code", "代码")], "视觉审查报告")},

    {"id": "n_p4", "type": "model_call", "label": "⑦ 汇总修复", "config": mc(
        "⑦ 汇总修复", 'deepseek', 'deepseek-v4-pro',
        "你是协同编码管线的编排者 DeepSeek，负责应用审查修复并生成最终交付报告。\n"
        "修复时输出修复后的完整文件内容，不要解释、不要 markdown 围栏。\n"
        "报告包含：# 交付报告\n## 交付物（文件清单与用途）\n## 审查与修复摘要\n## 验证状态\n## 残留风险与使用说明",
        "代码审查报告：\n{{ node.n_p3a.out }}\n\n视觉审查报告：\n{{ node.n_p3b.out }}",
        "final_report.md", [("review_code", "代码审查"), ("review_visual", "视觉审查")], "最终报告")},

    {"id": "n_end", "type": "output", "label": "交付报告", "config": {
        "format": "md", "filename_template": "final_report.md",
        "encoding": "utf-8", "overwrite": "overwrite",
        "inputs": [{"id": "in", "type": "any", "label": "内容"}]}},
]

edges = [
    {"from": "n_req", "from_port": "text", "to": "n_p0", "to_port": "in"},
    {"from": "n_p0", "from_port": "out", "to": "n_p1", "to_port": "req"},
    {"from": "n_p0", "from_port": "out", "to": "n_p1b", "to_port": "req"},
    {"from": "n_p0", "from_port": "out", "to": "n_p3a", "to_port": "req"},
    {"from": "n_p1", "from_port": "out", "to": "n_p1b", "to_port": "design"},
    {"from": "n_p1", "from_port": "out", "to": "n_p2", "to_port": "design"},
    {"from": "n_p1", "from_port": "out", "to": "n_p3a", "to_port": "spec"},
    {"from": "n_p2", "from_port": "out", "to": "n_p3a", "to_port": "code"},
    {"from": "n_p1b", "from_port": "out", "to": "n_p3b", "to_port": "spec"},
    {"from": "n_p2", "from_port": "out", "to": "n_p3b", "to_port": "code"},
    {"from": "n_p3a", "from_port": "out", "to": "n_p4", "to_port": "review_code"},
    {"from": "n_p3b", "from_port": "out", "to": "n_p4", "to_port": "review_visual"},
    {"from": "n_p4", "from_port": "out", "to": "n_end", "to_port": "in"},
]

POS = {
    "n_req": (60, 400), "n_p0": (340, 400),
    "n_p1": (620, 300), "n_p1b": (620, 560),
    "n_p2": (900, 320),
    "n_p3a": (1180, 240), "n_p3b": (1180, 560),
    "n_p4": (1460, 400), "n_end": (1740, 400),
}

pipeline = {
    "schema_version": "1.0.0",
    "kind": "pipeline",
    "meta": {
        "name": "协同编码管线（执行段）",
        "description": "四模型分工协同编码管线：DeepSeek-V4-Pro 需求理解/汇总修复 · DeepSeek-Flash 整体设计/代码审查 · GLM-5.3 逐文件编码 · Qwen3.8-Max 视觉规格/视觉审查。对应 Multi-agent-programming-pipeline/pipeline/coding_pipeline.py 的 Phase 0-4，用于在本编排器中可视化与再编排。",
        "version": "1.0.0",
        "author": "xtr0928",
        "pipeline_id": "coding-pipeline",
    },
    "runtime": {"output_dir": "pipeline-output", "concurrency": 3, "continue_on_error": True},
    "nodes": nodes,
    "edges": edges,
}

layout = {
    "schema_version": "1.0.0",
    "kind": "layout",
    "meta": {"pipeline_id": "coding-pipeline", "name": "协同编码管线（执行段）"},
    "viewport": {"x": 0, "y": 196, "zoom": 0.53},
    "canvas": {"grid": {"size": 20, "visible": True}, "background": "#0f1115"},
    "nodes": {nid: {"x": x, "y": y} for nid, (x, y) in POS.items()},
}

# ---- 自检：id 唯一 / 边端点与端口存在 / 端口标签 ----
ids = [n["id"] for n in nodes]
assert len(ids) == len(set(ids)), "node id 重复"
byname = {n["id"]: n for n in nodes}
for e in edges:
    a, b = byname[e["from"]], byname[e["to"]]
    outs = [p["id"] for p in a["config"].get("outputs", [])]
    ins = [p["id"] for p in b["config"].get("inputs", [])]
    assert e["from_port"] in outs, f"{e} 的输出端口不存在"
    assert e["to_port"] in ins, f"{e} 的输入端口不存在"
assert set(POS) == set(ids), "layout 与 pipeline 节点不一致"
assert len(edges) == 13

p_file = OUT_DIR / "coding-pipeline.pipeline.json"
l_file = OUT_DIR / "coding-pipeline.layout.json"
p_file.write_text(json.dumps(pipeline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
l_file.write_text(json.dumps(layout, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("WROTE:", p_file, f"({p_file.stat().st_size} bytes)")
print("WROTE:", l_file, f"({l_file.stat().st_size} bytes)")
print("nodes:", len(nodes), "edges:", len(edges))
