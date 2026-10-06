# Primary / Required：使用与 revision 更新功能审查

2026-10-06。用户调整验收要求：主辅选择不理想，只要使用和更新 lifecycle
正确，可以暂时接受。本次审查通过真实 Confluence 的“引导句作 Primary、
实质列表作 Required”案例。角色质量不再作为这个案例的独立阻塞项。
这不是整个 extraction 优化已实现或已部署的声明。

## 实际使用流程

`get_memory` → HTTP Memory detail → 可见的 active Support Evidence Unit →
完整 Primary / Required items → MCP response compaction → 调用者读取。

真实线上 Sonnet 既有输出的 claim 陈述某次版本重构的五项需求。
Primary 只有“以下需求”的引导句；五项实质需求全部在 Required 中。
原始业务文档与逐条引用保存在本地私有验证记录；这里仅记录结构性结论。

两个 ref 属于同一个 Confluence Observation / revision / Evidence Unit。整组
支持该 claim；Primary 单独只是一句引导。真实 store 解码、API DTO 构造和
MCP 压缩均保留两部分、各自角色、正文、revision ID 与 pinned resource URL。
SQLite / HANA grouped read 校验完整 part set，而不是将 Primary 当作全部
Evidence。Memory detail 的来源可见性过滤仍在服务端执行。

源码入口：`tool_client.py:get_memory`、
`server/admin_api.py:_memory_evidence_details / _memory_evidence_unit_detail`、
`plugin_mcp_proxy.py:_compact_memory_response`、
SQLite / HANA `get_memory_evidence_units`。

历史 `extraction_context` 和 Unit 的辅助 excerpt 可只包含 Primary；它们
不是完整 Evidence 接口，MCP compaction 使用 grouped items，不以该字段
替代整组。调用者应结合全部返回证据理解 claim；返回完整证据不等于证明
每个下游模型都会正确推理。当前 `get_memory` 返回持久化 claim，并不重新
执行 claim 真伪判定，因此既有措辞过强的 claim 不能靠该接口自动修正。

## revision 更新流程

新 projection → 校验每一个旧 Primary / Required 的 pinned 来源和表示 →
逐 ref correspondence → 整组 Support route → impact 或完整 assessment →
既有 Lifecycle Plan / stale guards / atomic commit。

| 控制变更（基于真实 native body） | Primary / Required 结果 | 整组路由 |
| --- | --- | --- |
| 两部分和完整来源均未变 | Exact / Exact | Rebind Support，保留两部分，不调用模型 |
| 前面插入无关段落，原位置移动 | Exact / Exact，位置均变化 | Change Impact，输入包含两部分 |
| 修改列表中的 CNP 条件 | Exact / Modified | Support Assessment |
| 删除实质列表 | Exact / Modified | Support Assessment |
| 原列表新增重复副本 | Exact / Ambiguous | Support Assessment，不强选副本 |
| 本轮只提供 partial projection | Unknown / Unknown | 保留整组 unresolved，不据此退休 |

这说明 Primary 引导句未变不会遮蔽 Required 的变化。修改或删除触发的是
重新评估，并不预先指定必须退休：完整当前来源仍可能支持 claim。完整
支持判断、最后一个 active Support 的失效、独立其他 Support、stale/retry
与事务边界由既有 lifecycle 实现处理，相关回归检查通过。

`support_reading.py:correspond_evidence / _route` 对全部 parts 操作；
`revision_work.py:_rebound` 保留全部 parts；`_impact_work` 和 assessment
输入包含 Primary 与 Required。读新 revision 时保留完整读取和判否边界。
Primary 的 `primary_eligible` 授权检查仍有效，不能将仅授权为上下文的
内容提升成新 claim 的 Primary。

另一个角色职责是 relation 的 Evidence time：现有实现从 Primary 的
Observation revision 取得时间。该案例两部分同 Observation / revision，
所以角色位置不影响时间依据。不能据此声称不同 Observation、不同时间
或不同授权范围的任意主辅互换都没有影响。

## 验证证据与边界

私有证据目录：
`/Users/i551096/Downloads/MemForge-Evidence-Validation-2026-10-02/private/primary-required-functional-20261006`。

- `test_functional_roles.py` / `functional-results-final.log`：8 项通过。
  重放既有真实线上输出，使用实际 adapter、planner、executor、store
  decoder、API builder 和 MCP compactor。没有新的付费模型调用。
- OSS：`test_pinned_evidence_tools.py`、`test_support_reading.py`、
  `test_revision_work.py`、`test_projected_lifecycle_integration.py`、
  `test_lifecycle_guards.py`，222 项通过。日志 `oss-contract-results.log`。
- Cloud：`test_text_view_delivery_parity.py` 和 `test_hana_workspace_store.py`
  中 text-view / active-unit grouped Evidence / historical Required 相关检查，
  7 项通过、494 项未选。日志 `cloud-contract-results-final.log`。
- 旧 focused-display 的 294 个冻结文件复核零变动，记录于
  `prior-freeze-reverification.json`。两位盲评的原始意见和分歧保持原样。

定向修改是控制生成的 revision，非 provider 的真实连续更新。新案例的
SQLite / HANA read 使用 fetch seam 注入 fixture rows，验证真实查询条件与
解码/返回行为；不是物理 HANA roundtrip，也不是新 live HTTP smoke。
OSS suite 有实际 SQLite lifecycle 回归，但语义评估响应使用 fixture。
不将这些结果称为新线上 Sonnet 语义验证。

Cloud 首次 collection 错误来自 venv editable path 混用了 Dev HANA 与
目标 OSS。用目标 Cloud 的全部 package src paths 重新执行后通过。早期
测试 fixture 的 native kind / partial manifest 也已改正；保留旧失败日志，
没有因此更改产品代码。不是靠兼容分支消除产品问题。

## 验收结论与剩余发布范围

本例 joint Evidence delivery、Required change detection、整组 rebind 和
相关 lifecycle guards 审查通过，可以暂时接受主辅不理想，不新增角色
修复或 candidate 删除步骤。既有模型语义错误独立记录；静态程序不保证
claim 推理为真，也不证明 Sonnet 有不可突破的能力上限。

本次没有修改产品 Python。生成的 focused ref 正文仍是实验 sidecar，尚未
接入 persistence / API / UI。原发布合同中的集成、完整设计审计、真实连续
revision、物理 HANA、PR、checked CF deploy 和 smoke 尚未完成。后续
推进实现和发布，无需再以“主辅必须完全理想”重复实验。
