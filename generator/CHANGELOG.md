# 变更日志（Changelog）

本文件记录项目的所有显著变更。版本号与 `schema_version`、`app_version` 保持同步维护。
格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，遵循语义化版本。

## [Unreleased]

暂无未发布内容。

## [0.1.0] - 2026-10-06

首个发布版本。搭建设计器核心能力，确定 Schema 基线。

### 新增

- 新增三类节点：`XTR`（外部任务节点）、`LLM`（模型调用节点）、`ANALYSIS`（分析节点）。（影响 `schema_version`：是）
- 新增双文件导入导出能力：`project.json`（完整项目文件，含 `schema_version`、`app_version`、画布内容）与 `agent.json`（节点运行时编排文件）。（影响 `schema_version`：是）
- 新增 Schema 校验：导入时校验文件结构、必填字段与枚举取值，校验失败时给出明确错误提示。（影响 `schema_version`：否）
- 新增三档版本兼容策略：向上兼容（旧 `schema_version` 导入时自动升级）、同版本直读、向下拒绝（新 `schema_version` 拒绝导入并提示升级应用）。（影响 `schema_version`：是）
- 新增自动保存：定期将画布状态写入本地缓存，异常退出后可恢复。（影响 `schema_version`：否）
- 新增快捷键表：内置常用操作快捷键（新增节点、删除节点、复制、粘贴、保存、撤销、重做等），并提供可查阅的快捷键说明。（影响 `schema_version`：否）
- 新增帮助面板：提供使用说明、字段解释与版本兼容说明。（影响 `schema_version`：否）

### 预留

- 预留 `runtime.mode="config_only"` 配置项：当前版本固定为该值，未来扩展为可切换的运行模式。（影响 `schema_version`：是）
- 预留 `XTR.executor` 字段空实现：字段已在 Schema 中定义，但暂不承载任何执行逻辑。（影响 `schema_version`：是）
- 预留 `groups` 字段：用于节点分组的数据结构已写入 Schema，UI 暂不展示。（影响 `schema_version`：是）
- 预留 `notes` 字段：用于全局备注的顶层字段已写入 Schema，当前版本仅存储透传，不参与校验逻辑。（影响 `schema_version`：是）

### 已知限制

- 无真实模型调用：`LLM` 节点当前不发起任何实际请求，仅作设计态配置。（影响 `schema_version`：否）
- 无执行引擎：所有节点均为设计态定义，不具备运行时执行能力。（影响 `schema_version`：否）
- 无节点分组 UI：`groups` 字段虽有 Schema 定义，但画布上暂无分组展示与编辑入口。（影响 `schema_version`：否）
- 撤销栈不持久化：撤销/重做历史仅存在于当前会话，刷新或退出后清空，自动保存文件不包含撤销栈。（影响 `schema_version`：否）
