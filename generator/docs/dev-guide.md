# dev-guide.md — 开发者地图

> 本文档是代码协作的**地图与法律层**：谁在哪个分区干活、接口长什么样、想扩展时按什么步骤走、哪些红线绝对不能碰。
> 修改本文档视同修改协作契约，需团队评审通过后方可合入。
> 版本契约（`$version`、`SUPPORTED` 常量、四档兼容判定）以 [schema/SCHEMA_RULES.md](schema/SCHEMA_RULES.md) 为唯一依据，本文不重复其细节，只在涉及代码落点时引用。

---

## 目录

1. [代码分区地图（15 个分区）](#1-代码分区地图15-个分区)
2. [XTR 接口速查表](#2-xtr-接口速查表)
3. [扩展场景手册](#3-扩展场景手册)
4. [硬规则（红线）](#4-硬规则红线)
5. [分区行数上限与拆分登记](#5-分区行数上限与拆分登记)

---

## 1. 代码分区地图（15 个分区）

整个应用是一个单文件 `index.html`，通过注释横幅（`<!-- ═══ 分区 N：名称 ═══ -->`）切分为 15 个分区。
分区按依赖方向分四层，**依赖严格单向：① → ② → ③ → ④**。高层可以调用低层，**低层禁止反向调用高层**（禁止 require/引用、禁止事件上抛之外的任何形式耦合）。同层内分区之间允许互相调用，但仅限本表「协作」列声明的方向。

### 第①层：基础设施（分区 1–4）

| # | 分区名 | 职责 | 被谁依赖 |
|---|---|---|---|
| ①-1 | 常量与配置（Constants） | 内联的 `SUPPORTED` 版本常量、节点尺寸、颜色主题、快捷键表、错误文案。**本分区不得 import/引用任何其他分区**，是全图唯一的依赖叶子 | ②③④ 全部 |
| ①-2 | 工具函数（Utils） | 纯函数：版本号三段比较、深拷贝、ID 生成、节流防抖、DOM 查询糖。无状态、无副作用 | ②③④ 全部 |
| ①-3 | Schema 校验器（Validator） | 轻量 JSON Schema 校验器，仅支持 SCHEMA_RULES.md 第 4 节白名单关键字；`schema/*.json` 在构建期被内联为常量。负责按四档兼容表（legacy/older/ok/newer）判定数据版本 | ②-3、②-4、④-3 |
| ①-4 | 状态仓（Store） | 内存中的单一数据源：当前图文档（节点/边/文档级字段）、脏标记、undo 栈。只暴露 get/set/subscribe，不含业务逻辑 | ②③④ 全部 |

### 第②层：领域模型（分区 5–8）

| # | 分区名 | 职责 | 被谁依赖 |
|---|---|---|---|
| ②-1 | 节点类型注册表（NodeTypes） | `XTR.nodeTypes.register` 的实现；内置类型（意图/渠道/回复/条件…）在此注册；为 palette 与 inspector 提供元数据 | ③-1、③-2、③-3 |
| ②-2 | 渠道 Provider 注册表（Providers） | `XTR.providers.register` 的实现；渠道校验、消息模板渲染的抽象层；与 `samples/providers.builtin.json` 对齐 | ②-3、③-2 |
| ②-3 | 图模型 API（Graph） | `XTR.graph.*` 的实现：节点/边增删改查、批量操作、校验钩子。**所有写操作的唯一入口**（见第 4 节硬规则一） | ③ 全部、④-1 |
| ②-4 | 序列化与导入导出（IO） | 文档 ↔ JSON 双向转换、`$version` 写入、未知字段（`_unknown` / `node.ext`）的保留与回写、文件选择器交互 | ③-4、④-1、④-3 |

### 第③层：交互界面（分区 9–12）

| # | 分区名 | 职责 | 被谁依赖 |
|---|---|---|---|
| ③-1 | 调色板（Palette） | 左侧节点选择面板。**数据驱动**：遍历 `XTR.nodeTypes` 注册表自动渲染，新注册类型无需改本分区代码 | ④-2 |
| ③-2 | 属性检查器（Inspector） | 右侧属性编辑面板。**数据驱动**：按节点类型的字段 schema 自动生成表单；渠道字段按 provider 注册表联动 | ④-2 |
| ③-3 | 画布（Canvas） | 节点/边的渲染、拖拽、框选、缩放平移。渲染源是 ①-4 Store 的订阅，不直接改数据——**一切修改经 `XTR.graph`** | ④-2 |
| ③-4 | 命令与撤销（Commands） | 快捷键绑定、命令分发、undo/redo 的栈管理（栈本体在 ①-4） | ④-2 |

### 第④层：外壳与装配（分区 13–15）

| # | 分区名 | 职责 | 被谁依赖 |
|---|---|---|---|
| ④-1 | 工具栏与菜单（Toolbar） | 顶部按钮（新建/导入/导出/保存），全部是 `XTR.graph` / `XTR.io` 的 UI 入口 | 无（顶层） |
| ④-2 | 布局装配（Layout） | 三栏布局、面板开关、模态对话框容器 | 无（顶层） |
| ④-3 | 启动引导（Bootstrap） | 版本横幅（older 可关闭 / newer 常驻，见 SCHEMA_RULES.md 2.2）、`DOMContentLoaded` 初始化顺序、全局错误兜底 | 无（顶层） |

### 依赖方向示意

```
①-1 常量  ①-2 工具  ①-3 校验器  ①-4 状态仓
   └────────┬────────┴─────┬──────┘
            ▼              ▼
      ②-1 类型注册  ②-2 渠道注册  ②-3 图模型  ②-4 序列化
            └──────┬───────────┴──────┬──────┘
                   ▼                  ▼
        ③-1 调色板  ③-2 检查器  ③-3 画布  ③-4 命令
                   └──────┬──────────┘
                          ▼
              ④-1 工具栏  ④-2 布局  ④-3 引导
```

**判定依赖是否违规的快捷方法**：在待改分区里搜一下目标分区的函数名/全局对象名，若它属于更高层（编号更大或同层未声明协作），即为反向依赖，评审直接打回。

---

## 2. XTR 接口速查表

`XTR` 是挂在 `window` 上的唯一命名空间（分区 ②-3 中定义命名空间骨架，各分区挂载自己的子对象）。下表是全量公开接口，签名即契约，改动需走评审。

### 2.1 `XTR.graph` — 图模型（分区 ②-3）

| 方法 | 签名 | 说明 |
|---|---|---|
| `addNode` | `(type: string, pos: {x, y}, overrides?: object) => Node` | 新增节点，`type` 必须已注册 |
| `removeNode` | `(id: string) => void` | 删除节点及其关联边 |
| `updateNode` | `(id: string, patch: object) => void` | 浅合并更新节点字段，patch 先经类型 schema 校验 |
| `getNode` | `(id: string) => Node \| null` | 读取单节点 |
| `getNodes` | `(filter?: (n: Node) => boolean) => Node[]` | 读取节点集合 |
| `addEdge` | `(from: string, to: string, kind?: string) => Edge` | 新增连线，含成环/类型约束校验 |
| `removeEdge` | `(id: string) => void` | 删除连线 |
| `getEdges` | `() => Edge[]` | 读取全部连线 |
| `moveNodes` | `(ids: string[], dx: number, dy: number) => void` | 批量位移（拖拽用），单次入 undo 栈 |
| `beginBatch` / `endBatch` | `() => void` | 批量操作合并为一次 undo 记录 |
| `clear` | `() => void` | 清空当前文档（经确认） |
| `onChange` | `(cb: () => void) => unsubscribe` | 订阅文档变更，供画布/脏标记刷新 |

### 2.2 `XTR.nodeTypes` — 节点类型注册表（分区 ②-1）

| 方法/字段 | 签名 | 说明 |
|---|---|---|
| `register` | `(def: TypeDef) => void` | 注册类型。`TypeDef = { type, title, icon, category, fields: FieldDef[], defaults? }`，`type` 重复注册直接抛错 |
| `get` | `(type: string) => TypeDef \| null` | 查询单个定义 |
| `list` | `() => TypeDef[]` | 全量列表，palette/inspector 数据源 |
| `validateNode` | `(node: Node) => string[]` | 按字段 schema 校验节点，返回错误信息数组 |

`FieldDef = { key, label, widget: 'text'|'number'|'select'|'channel'|'textarea', options?, required?, default? }` —— inspector 依此自动生成表单。

### 2.3 `XTR.providers` — 渠道注册表（分区 ②-2）

| 方法 | 签名 | 说明 |
|---|---|---|
| `register` | `(def: ProviderDef) => void` | 注册渠道。`ProviderDef = { id, title, capabilities: string[], paramSchema?: FieldDef[] }` |
| `get` | `(id: string) => ProviderDef \| null` | 查询渠道定义 |
| `list` | `() => ProviderDef[]` | 全量列表，inspector 渠道下拉数据源 |
| `validateConfig` | `(id: string, config: object) => string[]` | 校验某渠道的节点配置 |

### 2.4 `XTR.io` — 导入导出（分区 ②-4）

| 方法 | 签名 | 说明 |
|---|---|---|
| `serialize` | `() => object` | 文档 → 可 JSON 化对象（含 `$version`，未知字段原样保留） |
| `deserialize` | `(data: object) => { status, version? }` | JSON → 文档。status ∈ `legacy/older/ok/newer`（判定表见 SCHEMA_RULES.md 2.2） |
| `exportFile` | `() => void` | 触发浏览器下载 |
| `importFile` | `() => Promise<void>` | 触发文件选择（`<input type="file">`，非 fetch） |

### 2.5 `XTR.version` — 版本能力（分区 ①-1 / ④-3）

| 字段/方法 | 签名 | 说明 |
|---|---|---|
| `SUPPORTED` | `{ current, min, max }` | 读取端能力声明，与 schema/SCHEMA_RULES.md 2.1 对账 |
| `compare` | `(a: string, b: string) => -1\|0\|1` | 三段数值比较，**禁止字符串直接比较** |

### 2.6 `XTR.history` — 撤销（分区 ③-4）

| 方法 | 签名 | 说明 |
|---|---|---|
| `undo` / `redo` | `() => void` | 撤销/重做 |
| `canUndo` / `canRedo` | `() => boolean` | 栈状态查询 |

---

## 3. 扩展场景手册

三个最常见的需求，照步骤做即可。**步骤中的「不可跳过」项跳过任何一步，评审直接打回。**

### 3.1 场景一：新增节点类型

例：新增「人工审核」节点。改动落点与顺序：

1. **【不可跳过】分区 ②-1**：调 `XTR.nodeTypes.register({ type: 'review', title: '人工审核', ... })`，完整声明 `fields` 与 `defaults`。
2. **（自动生效，勿改）** palette（③-1）与 inspector（③-2）是数据驱动的：注册完成后调色板自动出现新卡片、点击节点自动生成表单。**不要**为单个类型去硬编码 palette/inspector 的 DOM 或分支逻辑——出现 `if (type === 'review')` 这类代码即为实现错误。
3. **判断是否触碰导出结构**：
   - 若新类型会出现在序列化输出中（绝大多数会，`type` 枚举需追加 `'review'`），则按 SCHEMA_RULES.md 第 3 节三步流程走：先改两份 schema（节点 schema 与文档 schema 中 `type` 枚举同步追加，保持字段 optional），再改代码，最后升 **MINOR** 并同步更新代码与 `index.html` 两处 `SUPPORTED` 常量（对账见 SCHEMA_RULES.md 第 5 节）。
   - 若纯属前端展示类型、不落盘，则无需动版本号，但需在本文档第 1 节分区 ②-1 的描述中补一句说明。

### 3.2 场景二：新增渠道

例：新增「短信」渠道。

1. **【不可跳过】分区 ②-2**：调 `XTR.providers.register({ id: 'sms', title: '短信', capabilities: [...], paramSchema: [...] })`。
2. **【不可跳过】同步样例文件**：更新 `samples/providers.builtin.json`，追加同 id 的条目，保持与代码内注册表一致。此文件是「内置渠道的事实快照」，两边漂移会在评审对账时被检出。
3. （自动生效）inspector 的渠道下拉与参数表单由 `list()` / `paramSchema` 驱动，无需改 ③-2 代码。
4. 若渠道 id 会写入导出数据（会），同场景一第 3 步：两份 schema 的渠道枚举追加 + 升 MINOR + 同步 `SUPPORTED`。

### 3.3 场景三：新增导出字段

**先读 SCHEMA_RULES.md 第 3 节，本场景的版本号判定完全以它为准。** 这里只规定代码落点：

- **允许的「零版本号成本」落点只有两处**：
  1. `node.ext`（分区 ②-3 图模型预留的节点级扩展袋）——写任意键值，schema 已声明为开放对象；
  2. 文档根 `_unknown`（分区 ②-4 为 `newer` 档数据保留的未知字段袋）——仅在读取更高版本数据时原样回写。
  这两处之外**没有第三处**可以「悄悄」塞新字段。
- **除上述两处外，任何新增导出字段必须走版本号流程**：SCHEMA_RULES.md 三步顺序（改 schema → 改代码 → 升版本），且每步独立提交、独立验证。想跳过版本号流程又不想用 `ext`/`_unknown` 的，等价于制造一次未声明的 MAJOR 变更，按红线处理。
- 代码落点：字段读写逻辑放分区 ②-4（序列化）与 ②-3（图模型）中的对应节点/文档结构；UI 展示由 ③-2 inspector 的 `FieldDef` 声明驱动。

---

## 4. 硬规则（红线）

以下两条无例外，评审一票否决：

**红线一：所有写操作必须先有 `XTR.graph` API，再有 UI 入口。**

- 任何会改变文档数据的操作（新增/删除/修改节点或边、批量位移、清空），必须先在分区 ②-3 实现为 `XTR.graph.*` 方法，UI（③/④ 层）只做调用方。
- 禁止 UI 层直接改 Store（①-4）、直接改画布内部数据结构（③-3）、直接操作序列化对象（②-4）。
- 判定方法：grep UI 分区中的赋值语句（`node.xxx =`、`store.doc.nodes` 写访问），命中即为违规。
- 顺序同样不可颠倒：不允许「先在 UI 里写完能跑，回头补 graph API」——补不上的中间提交会产生绕过校验/undo 栈的数据通路。

**红线二：不得引入 ES Module、fetch 读本地文件、任何第三方库。**

- 项目是**单文件、零构建、零依赖**架构：`index.html` 直接双击可用。以下写法一律禁止：
  - `<script type="module">` / `import` / `export`（内联脚本保持普通 script，分区靠注释横幅切分，模块性靠本文档的分区纪律维持）；
  - `fetch('本地路径')` / `XHR` 读本地文件（本地 `file://` 协议下会被浏览器安全策略拦截，且违反零依赖原则）；文件读取只允许 `<input type="file">`（见 `XTR.io.importFile`）；
  - 任何 `<script src="外部库">`、CDN 引用、内联第三方库代码。
- schema 与样例 JSON 在构建期/维护期以常量形式内联进 ①-3 / ②-2，运行时不做任何网络与文件系统访问。

---

## 5. 分区行数上限与拆分登记

### 5.1 规则

- **单个分区（两个注释横幅之间）超过 600 行时，必须在本文档本节登记「待拆」，并在源码该分区横幅注释上加 `@pending-split` 标记。**
- 登记不等于立刻拆：先登记，拆分作为独立任务排期。但**未登记的超限分区不得合入新功能**——要么登记，要么本次顺手拆掉。
- 拆分方向必须遵守第 1 节依赖方向：新拆出的分区编号插入原层，不得借拆分之机引入反向依赖。

### 5.2 当前登记表

初始状态：15 个分区均未超限，登记表为空。

| 分区 | 当前行数（约） | 状态 | 登记日期 | 拆分计划 |
|---|---|---|---|---|
| — | — | 无待拆项 | — | — |

> 维护方式：每次合入涉及分区增删行数超过 ±100 的 PR，需顺手更新本表「当前行数」列；触发 600 上限时补全「状态/登记日期/拆分计划」三列。

---

*本文档与 `schema/SCHEMA_RULES.md` 共同构成协作契约：schema 相关疑问以 SCHEMA_RULES.md 为准，代码结构、接口与红线以本文为准。*
