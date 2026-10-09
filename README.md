# 流谱 · FlowScore

**把 AI 工作流做成可读、可编排、可复用的东西。**

站点：**https://flowscore.zufe.com.cn** ｜ 旧站（GitHub 工作流精选导航）：https://pipeline.zufe.com.cn

---

## 这个仓库有什么

```
flowscore/
├── site/        站点源码（纯静态 HTML）
├── generator/   工作流生成器（可视化编排，自包含单文件）
├── library/     流谱管线库（schema + 校验工具 + 管线本体）
└── deploy/      部署脚本 + systemd 单元
```

### 1. `library/` —— 流谱管线库

管线的**权威存放地**。一个管线 = 一个目录：

```
library/pipelines/<id>/
├── meta.json           给程序：分类 / 标签 / 状态 / 排序
├── README.md           给人：这条管线解决什么问题（≥200 字）
├── pipeline.flow.json  给生成器：流谱格式的工作流本体
└── src/                管线本体的可运行实现（可选）
```

**流谱格式**（`format: "flowscore.pipeline"`）是**节点中心**的：每个节点自述完整契约，边信息内联在节点的端口里（`outputs[].to[]` / `inputs[].from[]`）。

| 概念 | 说明 |
|---|---|
| 节点类型 | `input` 入口 / `model_call` LLM 调用 / `output` 出口 / `task` 确定性步骤 / `note` 注释 |
| 端口 | `port` / `type` / `carries` / **`required`** 缺了能不能跑 / **`mode`** 多来源怎么合（all/any/first） |
| 注释节点 | 连到**输入端口** → 注入提示词（是代码）；连到**注释挂点** → 只挂靠展示；不连 → 纯漂浮 |
| 全局块 | `globals.settings` + `globals.prompts`（全局提示词，可 `apply_to` 指定范围） |
| **循环** | 边上的 `loop` 字段标记**回边**：`foreach` / `while` / `retry` |

**工具**：

```bash
python3 library/tools/validate.py                    # 校验全部管线（schema + 10 项图语义）
python3 library/tools/build_registry.py              # 生成 registry.json + INDEX.md
python3 library/tools/new_pipeline.py <id> --category 编程开发   # 新建管线骨架
```

校验器查两层：**schema 层**（JSON Schema）+ **图与目录层** 10 项（seq 连续 / 边双向一致 / 端口存在 / `mode` 用法 / 挂靠双向一致 / **环必须带 `loop` 标记** / 注释注入目标合法 / 目录规范）。

### 2. `generator/` —— 工作流生成器

自包含单文件（`index.html`，无依赖、离线可用）。功能：

- 可视化编排：拖拽节点、连端口、改参数
- **读流谱格式**：`?open=<url>` 直接打开站点上的管线
- **导出流谱格式**：无损往返（流谱独有字段走 `x` 扩展袋）
- 本地保存（localStorage）+ 导入/导出 JSON

打开方式：

```
https://flowscore.zufe.com.cn/orchestrator/
https://flowscore.zufe.com.cn/orchestrator/?open=/library/pipelines/<id>/pipeline.flow.json
```

### 3. `site/` —— 站点

纯静态：`index.html`（管线库）/ `pipeline.html`（详情页，含**只读 SVG 节点图**，循环画成橙色虚线大弧）/ `others.html`（旧站原首页）/ 简介 / 热度榜 / 社区 / agent。

---

## 部署

```bash
git clone git@github.com:xtr0928/flowscore.git
cd flowscore
./deploy/deploy.sh          # 摆好目录 + 软链 + 提示重启
systemctl --user restart flowscore-site
```

`deploy.sh` 会把 `site/` 复制到运行目录，并把 `generator/`、`library/` 软链成站点引用的 `orchestrator/`、`library/`。

Caddy 配置见 `site/Caddyfile`（默认端口 `61902`）；systemd 单元见 `deploy/flowscore-site.service`。

---

## 投稿「其他工作流」（GitHub 精选导航）

旧站的 GitHub 工作流精选导航仍在维护，投稿入口不变：

- ✍ **投稿**：点上方 **Issues → 新建 Issue → ✍ 投稿工作流**，填写仓库链接
- 🤖 数据接口：`https://pipeline.zufe.com.cn/api/workflows.json`
- 🔥 热度榜：https://pipeline.zufe.com.cn/hot.html

**收录标准**

1. **真·开箱即用**：有可运行的路径（脚本 / 应用 / Docker / 工作流文件），不是纯教程、论文或模型权重
2. **与 AI 工作流相关**：能替人自动完成一段实际工作
3. 开源且仓库可公开访问

**判定流程**

```
投稿 Issue → 服务器本地 Qwen3.8-27B 逐条读 README 判定
          → 通过 → 重新生成卡片站 → 收录上线
```

判定全程在本地完成，不依赖任何云端 API。

---

## 许可

MIT
