# 流谱管线库 · FlowScore Registry

> 存放**流谱格式**（`flowscore.pipeline`）管线的地方。一个管线 = 一个目录，目录里三件套 + 本体。
> 站点首页的数据源是根目录的 `registry.json`（**自动生成，勿手改**）。

---

## 一条管线长什么样

```
pipelines/<id>/
├── meta.json            ① 目录元数据 —— 只放【站点概念】：分类 / 标签 / 状态
├── README.md            ② 管线介绍 —— 给人读：解决什么、怎么跑、注意什么
├── pipeline.flow.json   ③ 流谱格式 —— 给生成器/AI 读：节点图
└── src/                 ④ 管线本体 —— 原始实现（代码 / 配置 / 提示词模板），可选
```

**为什么要分三份，而不是合并成一个文件**

| 文件 | 给谁看 | 内容 |
|---|---|---|
| `meta.json` | 站点 / 程序 | 分类、标签、状态、排序 |
| `README.md` | **人** | 场景、用法、坑 |
| `pipeline.flow.json` | **生成器 / AI** | 节点图：编号、输入来源、输出去向、传递方式、节点职责 |
| `src/` | **执行者** | 真实实现 |

**关键：管线的「名字」和「一句话自述」只写在 `pipeline.flow.json` 里**（`identity.name` / `about.summary`）。
`meta.json` **不重复**它们 —— 双写必然漂移。`registry.json` 生成时才把两边合并。

---

## 常用命令

```bash
# 新建一条管线（生成可过校验的最小骨架）
python3 tools/new_pipeline.py <id> --category 编程开发 --name "显示名"

# 校验（schema + 10 项图语义检查）
python3 tools/validate.py                    # 全部
python3 tools/validate.py pipelines/<id>     # 单条

# 生成站点索引（先校验，不过的不收录并在 skipped[] 里给原因）
python3 tools/build_registry.py
```

**工作流**：`new_pipeline.py` → 写正文 → `validate.py` → `meta.json` 里 `status` 改 `published` → `build_registry.py`

---

## 收录规则（不过就不收录）

```
① 三件套齐全：meta.json / README.md / pipeline.flow.json
② meta.id == 目录名 == flow.identity.id        # 三者必须一致
③ flow 过 schema（schema/pipeline.flow.schema.json）
④ 10 项图检查全过（见下）
⑤ README ≥ 200 字，且不含脚手架占位文字
⑥ meta.status == "published"    # draft / archived 不进 registry
```

### 10 项图语义检查

| # | 检查 | 级别 |
|---|---|---|
| 01 | `seq` 1..N 连续无缺口 | ERROR |
| 02 | 引用的节点与端口都存在 | ERROR |
| 03 | **双向一致** —— A 说输出给 B ⇔ B 说输入来自 A | ERROR |
| 04 | **`mode` 只在多来源时写**（多来源未写=错；单来源写了=也错） | ERROR |
| 05 | 无孤立节点（input/output/note 除外） | WARN |
| 06 | DAG 无环 | ERROR |
| 07 | **挂靠双向一致** —— note.`attached_to` ⇔ 目标 `annotations` | ERROR |
| 08 | 注释只能注入 `model_call` 节点 | ERROR |
| 09 | `inject` 两端一致 | ERROR |
| 10 | `globals.prompts[].id` 唯一；`exclude` 引用存在 | ERROR |

**为什么校验器是必需品**：流谱格式是「节点中心」—— 一条连线**两端各写一次**。
双写换来了「读一个节点 = 拿到它的完整契约」，代价就是**必须用机器把一致性关进笼子**。

---

## 管线的三种注释（`type: "note"`）

**行为由「连到哪个连接点」决定**，不需要额外声明：

```
      ┌──── 注释挂点 ────┐     ← 注释连这里 = 不注入（纯挂靠展示）
      │                  │
      │      节点         │
      │                  │
      └──── 输入端口 ────┘     ← 注释连这里 = 注入提示词
```

| 形态 | 格式表现 | 是否影响执行 |
|---|---|---|
| **注入** | `outputs[]` 指向真实输入端口 + `inject: system/user_prefix/user_suffix` | **是** —— 改文本 = 改行为 |
| **挂靠** | `attached_to: [{ node }]`（只写 node，无 port） | 否 |
| 纯漂浮 | `outputs: []` + `attached_to: []` | 否 |

⚠️ **注入了提示词的注释是代码，不是注释** —— 改它要按 PATCH 版本号走。

---

## 目录里还有什么

```
schema/    三个 JSON Schema（pipeline.flow / meta / registry）
tools/     validate.py · build_registry.py · new_pipeline.py
pipelines/ 每条管线一个子目录
registry.json  站点数据源（生成）
INDEX.md       人看的总目录（生成）
```

## 当前收录

见 [INDEX.md](INDEX.md)。

---

## 安全

`.gitignore` 已挡住 `.env` / `*.key` / `*token*` / `*凭据*` / `*密码*`。
**管线本体里不要放密钥** —— 用环境变量，README 里写变量名（脱敏成 `***`）。
