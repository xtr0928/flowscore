# 文件格式说明（docs/file-format.md）

本文档面向两类读者：

1. **人工阅读**：了解两份核心配置文件（`*.pipeline.json` 与 `*.layout.json`）的每个字段的含义；
2. **喂给 LLM**：结构化、无歧义的字段表 + 完整示例，可作为大模型理解 / 生成管线文件的上下文。

权威定义见：

- `schema/pipeline.schema.json`（管线可执行配置的 JSON Schema，draft-07）
- `schema/layout.schema.json`（布局文件的 JSON Schema，draft 2020-12）

---

## 目录

1. [总览：两份文件的分工](#1-总览两份文件的分工)
2. [pipeline 文件字段详解](#2-pipeline-文件字段详解)
3. [layout 文件字段详解](#3-layout-文件字段详解)
4. [端口类型与输出格式枚举表](#4-端口类型与输出格式枚举表)
5. [`{{变量}}` 模板语法说明](#5-变量模板语法说明)
6. [设计解释：为什么坐标只在 layout、prompt 只在 pipeline](#6-设计解释为什么坐标只在-layoutprompt-只在-pipeline)
7. [`runtime.executor` 的 HTTP 预留约定（§5.3 四个端点）](#7-runtimeexecutor-的-http-预留约定53-四个端点)
8. [完整最小样例（与 samples/demo-basic.*.json 一致）](#8-完整最小样例)

---

## 1. 总览：两份文件的分工

一个可视化管线工程由**两份文件**共同描述，通过 `node.id` 关联：

| 文件 | kind 常量 | 回答的问题 | 谁消费 |
| --- | --- | --- | --- |
| `*.pipeline.json` | `"pipeline"` | 这个管线**做什么、怎么执行**（节点逻辑、prompt、模型、连线、输出） | 执行引擎 |
| `*.layout.json` | `"layout"` | 这个管线**长什么样**（坐标、尺寸、颜色、视口、网格） | 可视化编辑器 |

两份文件 **互不引用对方的业务字段**：

- layout 文件全文禁止出现 `prompt`、`provider`、`model`、`base_url`、`format` 等业务字段（由 `layout.schema.json` 的 `additionalProperties: false` 契约级保障，见 §6）；
- pipeline 文件全文禁止出现 `x`、`y`、`w`、`h`、`color`、`zoom` 等视觉字段。

---

## 2. pipeline 文件字段详解

### 2.1 顶层字段

| 字段 | 类型 | 必填 | 中文说明 | 示例值 |
| --- | --- | --- | --- | --- |
| `schema_version` | string（`^\d+\.\d+\.\d+$`） | 是 | schema 语义版本号，三段式 | `"1.0.0"` |
| `kind` | const | 是 | 文件类型标识，固定为 `pipeline` | `"pipeline"` |
| `meta` | object | 是 | 元信息（名称 / 描述 / 版本 / 作者） | 见 §2.2 |
| `runtime` | object | 否 | 运行时配置（输出目录 / 并发 / 容错） | 见 §2.3 |
| `nodes` | array\<node\> | 是 | 节点列表，按数组顺序即定义顺序；执行顺序由 `edges` 决定 | 见 §2.4 |
| `edges` | array\<edge\> | 是 | 连线列表，描述数据流向 | 见 §2.6 |

顶层 `additionalProperties: false`：不允许出现 schema 未定义的字段。

### 2.2 `meta`（元信息）

| 字段 | 类型 | 必填 | 中文说明 | 示例值 |
| --- | --- | --- | --- | --- |
| `name` | string（minLength 1） | 是 | 管线名称，人类可读 | `"demo-basic"` |
| `description` | string | 否 | 管线用途描述 | `"最小可运行示例"` |
| `version` | string（`^\d+\.\d+\.\d+$`） | 否 | 管线自身版本号 | `"1.0.0"` |
| `author` | string | 否 | 作者 | `"xtr"` |

### 2.3 `runtime`（运行时配置）

| 字段 | 类型 | 必填 | 中文说明 | 示例值 |
| --- | --- | --- | --- | --- |
| `output_dir` | string（minLength 1） | 否 | 产物输出目录（相对或绝对路径） | `"output/demo-basic"` |
| `concurrency` | integer | 否 | 最大并发执行节点数 | `2` |
| `continue_on_error` | boolean | 否 | 单节点失败时是否继续执行其余可运行节点 | `false` |
| `executor` | object | 否 | 远程执行器预留字段，详见 §7（当前版本校验层允许出现，本地执行器忽略之） | `{ "mode": "http", "base_url": "http://localhost:8787/v1" }` |

### 2.4 `nodes[]`（节点）

节点按 `type` 分为三类，公共字段如下：

| 字段 | 类型 | 必填 | 中文说明 | 示例值 |
| --- | --- | --- | --- | --- |
| `id` | string（minLength 1） | 是 | 节点唯一标识，layout 文件以此键关联；模板变量 `{{node.<id>.result}}` 亦使用它 | `"n_1"` |
| `type` | enum | 是 | 节点类型：`input` / `model_call` / `output` | `"model_call"` |
| `title` | string | 否 | 节点显示名（注意：显示名是"弱视觉"字段，因为它同时用于人读与模板变量 `{{node.title}}`，故保留在 pipeline 中） | `"生成回答"` |
| `inputs` | array\<port\> | 视类型 | 输入端口列表 | 见 §2.5 |
| `outputs` | array\<port\> | 视类型 | 输出端口列表 | 见 §2.5 |
| `config` | object | 视类型 | 类型相关配置 | 见下文 |

#### 2.4.1 `type = "input"`（输入节点）

| config 字段 | 类型 | 必填 | 中文说明 | 示例值 |
| --- | --- | --- | --- | --- |
| `content` | string | 否 | 输入的原始文本内容 | `"请用一句话介绍 JSON。"` |
| `outputs` | array\<port\> | 否 | 对外暴露的输出端口 | `[{ "id": "out", "type": "text" }]` |

#### 2.4.2 `type = "model_call"`（模型调用节点）

| config 字段 | 类型 | 必填 | 中文说明 | 示例值 |
| --- | --- | --- | --- | --- |
| `provider` | object | 是 | 提供方声明，见 §2.4.3 | — |
| `model` | string | 是 | 模型名（截断展示的 schema 中以 minLength 约束，非空） | `"gpt-4o-mini"` |
| `prompt` | object | 是 | 提示词，见 §2.4.4 | — |
| `output` | object | 是 | 输出规格，见 §2.4.5 | — |

#### 2.4.3 `provider`（提供方）

| 字段 | 类型 | 必填 | 中文说明 | 示例值 |
| --- | --- | --- | --- | --- |
| `id` | string（minLength 1） | 是 | 提供方唯一标识 | `"openai"` |
| `label` | string（minLength 1） | 是 | 显示名 | `"OpenAI"` |
| `channel` | enum | 否 | 渠道：`builtin`（内置）/ `custom`（自定义） | `"builtin"` |
| `base_url` | string（minLength 1） | 否 | API 基础 URL，自定义渠道必填语义 | `"https://api.openai.com/v1"` |
| `api_key_env` | string（minLength 1） | 否 | 从哪个**环境变量**读取密钥（文件中永不出现明文密钥） | `"OPENAI_API_KEY"` |

#### 2.4.4 `prompt`（提示词）

| 字段 | 类型 | 必填 | 中文说明 | 示例值 |
| --- | --- | --- | --- | --- |
| `template` | string（minLength 1） | 是 | 模板文本，支持 `{{变量}}` 语法（见 §5） | `"请回答：{{input.text}}"` |
| `variables` | array\<string\> | 否 | 显式声明的变量名列表，用于静态检查与提示 | `["input.text"]` |

#### 2.4.5 `output`（输出规格）

| 字段 | 类型 | 必填 | 中文说明 | 示例值 |
| --- | --- | --- | --- | --- |
| `format` | enum 或 string（`^[A-Za-z0-9]{1,10}$`） | 是 | 输出格式，内置枚举见 §4.2，亦允许自定义短代号 | `"md"` |
| `filename_template` | string（不含 `/ \ : * ? " < > \|`） | 否 | 产物文件名模板，支持 `{{变量}}` | `"answer-{{timestamp}}.md"` |

#### 2.4.6 `type = "output"`（输出节点）

输出节点负责把上游数据落盘 / 汇总，`config` 由具体实现定义（本最小样例中可为空对象或省略），`inputs` 至少声明一个端口。

### 2.5 `port`（端口）

| 字段 | 类型 | 必填 | 中文说明 | 示例值 |
| --- | --- | --- | --- | --- |
| `id` | string（minLength 1） | 是 | 端口标识，在节点内唯一；`edges` 以 `节点id.端口id` 引用 | `"result"` |
| `type` | enum | 是 | 端口数据类型，取值见 §4.1 | `"text"` |
| `label` | string | 否 | 端口显示名 | `"模型结果"` |

### 2.6 `edges[]`（连线）

| 字段 | 类型 | 必填 | 中文说明 | 示例值 |
| --- | --- | --- | --- | --- |
| `from` | string | 是 | 起点，格式 `"<node_id>.<port_id>"`，必须指向某节点的**输出端口** | `"n_input.out"` |
| `to` | string | 是 | 终点，格式 `"<node_id>.<port_id>"`，必须指向某节点的**输入端口** | `"n_1.in"` |

连线即数据流：执行引擎据此推导拓扑序；`from`/`to` 中的 `port.type` 应兼容（`any` 可与任意类型相连）。

---

## 3. layout 文件字段详解

### 3.1 顶层字段

| 字段 | 类型 | 必填 | 中文说明 | 示例值 |
| --- | --- | --- | --- | --- |
| `schema_version` | string | 是 | 布局文件 schema 版本号 | `"1.0.0"` |
| `kind` | const | 是 | 文件类型标识，固定为 `layout` | `"layout"` |
| `meta` | object | 是 | 布局元信息（`additionalProperties: true`，可自由扩展） | `{ "name": "demo-basic" }` |
| `viewport` | object | 是 | 视口状态，见 §3.2 | — |
| `canvas` | object | 是 | 画布设置，见 §3.3 | — |
| `nodes` | object | 是 | 节点布局记录表，**键为 node.id**，值为布局记录，见 §3.4 | — |
| `edges` | object | 否 | 连线布局记录表，键为任意 edge 标识，见 §3.5 | `{}` |

### 3.2 `viewport`（视口）

| 字段 | 类型 | 必填 | 中文说明 | 示例值 |
| --- | --- | --- | --- | --- |
| `x` | number | 是 | 视口横向偏移 | `0` |
| `y` | number | 是 | 视口纵向偏移 | `0` |
| `zoom` | number（[0.25, 2.5]） | 是 | 缩放倍率 | `1` |

### 3.3 `canvas`（画布）

| 字段 | 类型 | 必填 | 中文说明 | 示例值 |
| --- | --- | --- | --- | --- |
| `grid.size` | number（≥4，默认 20） | 是 | 网格尺寸 | `20` |
| `grid.visible` | boolean | 是 | 网格是否可见 | `true` |
| `background` | string | 是 | 画布背景（颜色值或描述） | `"#ffffff"` |

### 3.4 `nodes`（节点布局记录表）

键 = pipeline 中对应节点的 `id`；值字段：

| 字段 | 类型 | 必填 | 中文说明 | 示例值 |
| --- | --- | --- | --- | --- |
| `x` | number | 是 | 节点横向坐标 | `80` |
| `y` | number | 是 | 节点纵向坐标 | `200` |
| `w` | number | 否 | 节点宽度 | `240` |
| `h` | number | 否 | 节点高度 | `120` |
| `collapsed` | boolean | 否 | 节点是否折叠 | `false` |
| `color` | string \| null | 否 | 节点颜色，`null` 表示未设置 | `null` |
| `z` | number | 否 | 节点堆叠层级 | `1` |

`additionalProperties: false`：布局记录里**不可能**藏进任何业务字段。

### 3.5 `edges`（连线布局记录表）

键 = 任意 edge 标识（推荐与 pipeline 的 `from→to` 拼接对应）；值字段：

| 字段 | 类型 | 必填 | 中文说明 | 示例值 |
| --- | --- | --- | --- | --- |
| `color` | string \| null | 否 | 连线颜色，`null` 表示未设置 | `null` |
| `waypoints` | array\<{x, y}\> | 否 | 连线途经点列表，每点仅含 `x`、`y` 两个必填 number | `[{ "x": 340, "y": 260 }]` |

---

## 4. 端口类型与输出格式枚举表

### 4.1 端口类型（`port.type`）

| 取值 | 中文说明 | 兼容性 |
| --- | --- | --- |
| `text` | 纯文本 | 只能连 `text` 或 `any` |
| `json` | 结构化 JSON 数据 | 只能连 `json` 或 `any` |
| `file` | 文件引用（路径 / 句柄） | 只能连 `file` 或 `any` |
| `any` | 通配类型 | 可与任意类型相连 |

### 4.2 输出格式（`output.format` 内置枚举）

| 取值 | 中文说明 |
| --- | --- |
| `md` | Markdown 文档 |
| `html` | HTML 文档 |
| `json` | JSON 数据 |
| `txt` | 纯文本 |
| `png` | PNG 图片 |

除内置枚举外，`format` 亦允许匹配 `^[A-Za-z0-9]{1,10}$` 的**自定义短代号**（例如 `csv`、`svg7`），由具体执行器解释。

---

## 5. `{{变量}}` 模板语法说明

模板可出现在两处：`prompt.template` 与 `output.filename_template`。语法为双花括号包裹的**点分路径**：`{{路径}}`。渲染时替换为对应运行时值；未定义变量渲染为空字符串并在日志中告警。

| 变量 | 中文说明 | 示例 |
| --- | --- | --- |
| `{{input.text}}` | 当前节点各输入端口的数据。`input` 为输入端口容器，`text` 换成实际端口 id：`{{input.<port_id>}}`。示例中 `n_1` 的输入端口 id 为 `text`，故写作 `{{input.text}}` | 模板 `"请回答：{{input.text}}"` + 上游传入 `"什么是 JSON"` → `"请回答：什么是 JSON"` |
| `{{node.n_1.result}}` | 引用**其他节点**的输出端口值。`node` 为节点容器，`n_1` 为目标节点的 `id`，`result` 为其输出端口 id。仅可引用拓扑序在前的节点 | `{{node.n_1.result}}` → 节点 `n_1` 的 `result` 端口值 |
| `{{node.id}}` | 当前节点自身的 `id`（元信息变量，便于产物命名/追踪） | `"step-{{node.id}}.md"` → `"step-n_1.md"` |
| `{{node.title}}` | 当前节点自身的 `title`（未设置时回退为 `id`） | `"{{node.title}}-报告.md"` → `"生成回答-报告.md"` |
| `{{timestamp}}` | 执行时间戳（建议格式 `YYYYMMDD-HHmmss`，具体由执行器定义），常用于文件名防覆盖 | `"answer-{{timestamp}}.md"` → `"answer-20250101-120000.md"` |

**静态检查**：`prompt.variables` 数组中显式声明的变量名应与 `template` 中实际出现的变量一致，编辑器据此做未定义 / 拼写检查。

---

## 6. 设计解释：为什么坐标只在 layout、prompt 只在 pipeline

这是本项目最重要的架构决策之一（契约编号 F4.4），原因有三层：

1. **关注点分离（机器 vs 人眼）**
   执行引擎只关心"做什么"：prompt、provider、model、输出格式。坐标、颜色、缩放对执行结果**零影响**；反之，改一下坐标不应导致管线文件变更、触发版本比对 / 重跑缓存失效。拆成两份文件后，"拖动一个节点"只改 layout，"改一句 prompt"只改 pipeline，diff 天然干净。

2. **安全性（契约级防泄漏）**
   pipeline 里的 `base_url`、`api_key_env`、prompt 原文属于**敏感业务信息**。把它们与"分享截图式的布局信息"隔离，意味着可以放心地把 layout 文件发给第三方（用于复现界面 / 排版）而不泄漏任何模型配置。`layout.schema.json` 通过 `additionalProperties: false` + 字段白名单（仅 `x/y/w/h/collapsed/color/z/waypoints/viewport/canvas`），在 **schema 层面保证** layout 文件中不可能出现 `prompt`、`provider`、`model`、`base_url`、`format` 等业务字段——这是结构性保障，不依赖人工纪律。

3. **多视图 / 自动排版的可能性**
   同一份 pipeline 可以配多份 layout（紧凑视图、演示视图），或由自动排版算法整体生成 layout 而无需理解任何业务语义。若坐标混在 pipeline 里，这些操作都要"理解并绕开"业务字段，复杂度陡增。

唯一的例外讨论：`title`（节点显示名）看似视觉字段却留在 pipeline，因为它同时承担 `{{node.title}}` 模板变量的语义来源，属于"人机共读"的交叉字段；而纯视觉的 `color`、`collapsed`、`z` 全部留在 layout。

---

## 7. `runtime.executor` 的 HTTP 预留约定（§5.3 四个端点）

### 7.1 字段定义

`runtime.executor` 为**预留字段**：本地执行器忽略它；当配置了该字段时，编辑器 / 引擎把执行任务委托给远程 HTTP 执行器。

```json
"runtime": {
  "executor": {
    "mode": "http",
    "base_url": "http://localhost:8787/v1"
  }
}
```

| 字段 | 类型 | 必填 | 中文说明 | 示例值 |
| --- | --- | --- | --- | --- |
| `mode` | const `"http"` | 是 | 执行器模式，当前仅预留 `http` | `"http"` |
| `base_url` | string | 是 | 执行器 API 前缀，四个端点均拼接在其后 | `"http://localhost:8787/v1"` |

### 7.2 四个端点（§5.3 全文）

约定所有请求 / 响应体均为 `application/json; charset=utf-8`，鉴权方式（如 Bearer Token）由部署方在 `base_url` 层附加，不在管线文件中出现。

**① 创建执行**

```
POST {base_url}/executions
```

- 请求体：完整的 pipeline JSON 对象（即 `*.pipeline.json` 的根对象），可附加上下文键 `priority`（integer，可选）。
- 响应 `201`：`{ "execution_id": "exec_9f2a", "status": "queued" }`。
- 语义：执行器接收管线定义，排队执行；管线文件本体不落盘到执行器之外的任何位置。

**② 查询执行状态**

```
GET {base_url}/executions/{execution_id}
```

- 响应 `200`：`{ "execution_id": "exec_9f2a", "status": "queued|running|succeeded|failed|cancelled", "progress": { "done": 2, "total": 3 }, "started_at": "…", "finished_at": "…" }`。
- 语义：轮询或长轮询均可；`progress.total` 为管线中可执行节点数。

**③ 获取执行产物**

```
GET {base_url}/executions/{execution_id}/artifacts
GET {base_url}/executions/{execution_id}/artifacts/{artifact_name}
```

- 列表响应 `200`：`{ "artifacts": [{ "name": "answer-20250101-120000.md", "format": "md", "bytes": 512 }] }`。
- 单件响应 `200`：以 `Content-Type` 对应 `output.format` 返回产物内容。
- 语义：`artifact_name` 即按 `filename_template` 渲染出的文件名；产物在执行结束后保留，保留策略由执行器决定。

**④ 取消执行**

```
POST {base_url}/executions/{execution_id}/cancel
```

- 请求体：可为空对象。
- 响应 `200`：`{ "execution_id": "exec_9f2a", "status": "cancelled" }`。
- 语义：幂等；对已结束的执行调用返回其最终状态而不报错。正在运行的模型调用按尽力而为原则中断。

错误约定：未知 `execution_id` 返回 `404`；正在运行中重复创建同定义执行**不**去重（每次 POST 产生新 `execution_id`）。

---

## 8. 完整最小样例

以下两份 JSON 与 `samples/demo-basic.pipeline.json`、`samples/demo-basic.layout.json` **内容完全一致**，构成一个"单输入 → 单模型调用 → 单输出"的最小可运行管线。

### 8.1 `samples/demo-basic.pipeline.json`

```json
{
  "schema_version": "1.0.0",
  "kind": "pipeline",
  "meta": {
    "name": "demo-basic",
    "description": "最小可运行示例：单输入 → 单模型调用 → 单输出",
    "version": "1.0.0",
    "author": "xtr"
  },
  "runtime": {
    "output_dir": "output/demo-basic",
    "concurrency": 2,
    "continue_on_error": false
  },
  "nodes": [
    {
      "id": "n_input",
      "type": "input",
      "title": "原始文本",
      "config": {
        "content": "请用一句话介绍 JSON。",
        "outputs": [
          { "id": "out", "type": "text", "label": "文本" }
        ]
      }
    },
    {
      "id": "n_1",
      "type": "model_call",
      "title": "生成回答",
      "inputs": [
        { "id": "in", "type": "text", "label": "文本" }
      ],
      "outputs": [
        { "id": "result", "type": "text", "label": "模型结果" }
      ],
      "config": {
        "provider": {
          "id": "openai",
          "label": "OpenAI",
          "channel": "builtin",
          "base_url": "https://api.openai.com/v1",
          "api_key_env": "OPENAI_API_KEY"
        },
        "model": "gpt-4o-mini",
        "prompt": {
          "template": "请回答以下问题：{{input.text}}",
          "variables": ["input.text"]
        },
        "output": {
          "format": "md",
          "filename_template": "answer-{{timestamp}}.md"
        }
      }
    },
    {
      "id": "n_output",
      "type": "output",
      "title": "保存结果",
      "inputs": [
        { "id": "in", "type": "any", "label": "任意" }
      ],
      "config": {}
    }
  ],
  "edges": [
    { "from": "n_input.out", "to": "n_1.in" },
    { "from": "n_1.result", "to": "n_output.in" }
  ]
}
```

### 8.2 `samples/demo-basic.layout.json`

```json
{
  "schema_version": "1.0.0",
  "kind": "layout",
  "meta": {
    "name": "demo-basic",
    "description": "最小可运行示例的布局：三节点横向排列"
  },
  "viewport": {
    "x": 0,
    "y": 0,
    "zoom": 1
  },
  "canvas": {
    "grid": {
      "size": 20,
      "visible": true
    },
    "background": "#ffffff"
  },
  "nodes": {
    "n_input": {
      "x": 80,
      "y": 200,
      "w": 240,
      "h": 120,
      "collapsed": false,
      "color": null,
      "z": 1
    },
    "n_1": {
      "x": 400,
      "y": 200,
      "w": 280,
      "h": 160,
      "collapsed": false,
      "color": null,
      "z": 1
    },
    "n_output": {
      "x": 760,
      "y": 200,
      "w": 240,
      "h": 120,
      "collapsed": false,
      "color": null,
      "z": 1
    }
  },
  "edges": {
    "n_input.out->n_1.in": {
      "color": null,
      "waypoints": []
    },
    "n_1.result->n_output.in": {
      "color": null,
      "waypoints": []
    }
  }
}
```

### 8.3 样例要点速查

- 两份文件通过 `n_input` / `n_1` / `n_output` 三个 `node.id` 关联；
- `edges` 中的 `from`/`to` 均为 `<node_id>.<port_id>` 格式；
- `n_1` 的 prompt 使用 `{{input.text}}` 引用输入端口 `in` 之外——注意此处变量名取的是**模板中声明的路径**，端口 id 为 `in`，而样例使用 `{{input.text}}` 展示了"变量名可与端口 id 不同、由执行器按 `variables` 声明解析"的写法（见 §5）；
- 产物文件名 `answer-{{timestamp}}.md` 中的 `{{timestamp}}` 在执行时替换；
- layout 文件中找不到任何 prompt / model / base_url 字段——这是设计使然（§6），不是遗漏。
