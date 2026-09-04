# 大文档 Memory 关系判断与恢复：修复方案

状态：分阶段落实。增量 Primary authority 与 bounded Support revalidation
已经进入主线；多候选冲突 Review 仍是设计提案，不是已实现能力。日期：2026-09-05。

代码核对基线：OSS `d4004b44`；Cloud `d31dc5bd`。共享语义由 OSS 维护，Cloud 实现相同契约。
本文整理本次修复及独立设计评审结论。增量提取与重试基线属于已请求修复的范围；多候选 Review 是推荐的设计扩展，尚未批准为本次实现范围。既有 Accepted ADR 在修订获批前仍是当前契约。

## 1. 先说准备怎么修

推荐组合是：**减少不该生成的新候选，保留必须完成的关系判断；把已发现的语义冲突变成可审阅的业务结果，而不是整份文档重跑的异常。**

| 修复 | 具体改变 | 不会做什么 |
| --- | --- | --- |
| 让 v9 真正使用增量范围 | 根据固定的旧、新 revision，只从本次授权变化的完整结构片段生成新候选 | 不把旧全文都重新标为 Primary；不按数量截断候选 |
| 固定重试输入 | 使用不可变的 base/target revision 和已暂存的提取计划恢复 | 不再用已覆盖的下载缓存重算 diff |
| 正确处理候选冲突 | 推荐：冲突候选进入 Review，真正独立的结果随同一份完整 Unit Plan 提交 | 不随机选赢家、不把两条相反结论都发布、不因冲突重算数百次 |
| 区分重试职责 | 模型调用失败由模型层有限重试；已准备好的提交由 commit 层处理 | 不把模型、语义判断、数据库提交都变成整文档重试 |
| 显示实际工作 | 分别显示等待名额、提取、关系判断、提交、待 Review | 不把几小时的关系判断一直叫“正在创建 Memory：0/402” |

我不推荐先增加并发、增大 timeout，或者只取最相似的几条旧 Memory。这些不能解决本次错误的工作范围和语义重试问题。

## 2. 这次到底发生了什么

### 文档和候选不是同一个概念

这份文件是累计会议记录，约 28.5 万字符、29 个日期段，不是一份短 README。
本次主要增加约 9,206 字符，同时有 28 处旧 Markdown 分隔符变化。

第一轮已有 `diff_guided / small_diff` 上下文，但 v9 提取入口绕过了使用该上下文的旧规划路径，仍把整个变更 Observation 分成 11 批提取。随后一次重试又从已被新内容覆盖的 normalized artifact 读取“旧内容”，得到 `empty_diff`，进一步丢失了可靠的比较基线。

被分析的候选集为：113 条原始候选 → 112 条通过质量准入 → 110 条进入关系判断。
其中 107 条候选的 Primary 原文片段已经存在于旧 revision，只有 3 条来自新增日期段。

这证明大量历史内容被重新提取，**不证明那 107 条全是重复 Memory，也不能保证修复后恰好只提取 3 条**。完整结构扩展、旧段真实修改和质量判断都会影响结果；不得用这个数字作为删除规则。

`0/402` 的 402 是本轮处理的文件总数，不是 402 份都需要重新调用 LLM。第一份大文件未完成，使完成计数长期停在 0。后续已有未变化文件以零 LLM 调用完成的日志。

### 27,280 对是什么

```text
110 条本次提取的新候选
    ×
248 条同一个 Source Unit 已有的 active Memory
    = 27,280 对候选—旧 Memory 关系判断
```

这 248 条不是整个 workspace 的 Memory，也不是跨文档搜索结果。它们是本次同 Unit lifecycle 必须考虑的旧 Memory。
现有每个模型请求最多承载 64 对，单基础关系矩阵至少需要 427 次调用；Support 审计及其他证明另算。

一轮在完成 453 次逻辑 LLM 调用后，因为多个候选被判断为同一旧 Memory 的相互矛盾的细化，整个文档尝试失败。外层把它当作可重试错误，再做了一轮昂贵语义工作。
后续既有自动重试终于提交，单次成功尝试仍用了约 124 分钟、537 次逻辑调用，并记录新增 31 条 Memory。

**后来一次提交成功，不代表前一次冲突判定被证明错误，更不代表设计缺陷已修复。** 目前日志没有给出前次确切冲突候选对，不能杜撰是哪两条业务结论矛盾。

## 3. “关系判断”实际有几种

| 判断 | 输入与问题 | 在本次方案中的处理 |
| --- | --- | --- |
| 候选与旧 Memory | 每个新候选与本 Unit 每条 mandatory incumbent：相同、细化、矛盾还是无关？ | 保留完整显式覆盖，不用 top-k 替代 |
| 旧 Memory 的 Support | 当前权威 Source revision 是否仍支持这条旧 claim？ | 独立审计，不能由“与新候选无关”推断旧 claim 已过时 |
| 候选之间的冲突 | 多个候选同时细化同一旧 Memory，它们能否同时成立？ | 在已有需要比较的集合内判断；检测到冲突后给出 Review 结果 |
| 后续 Evidence/修订证明 | 准备写入的完整 claim 是否有当前 Evidence，更新是否保持原有事实？ | 保留，不以关系标签或字符串相似替代证明 |
| 跨文档关系发现 | 新 Memory 与别的文档有什么关系？ | 保持现有提交后、有限候选、非破坏性的后台流程 |

LLM 负责判断关系，不直接决定 `update / supersede / retire`。动作仍由确定性 reducer、Source Authority 和 Lifecycle Plan 决定。
例如，“新候选与旧 claim 无关”并不意味着删除旧 claim；旧 Evidence 仍支持它时，正常结果是保留旧 claim，新增独立 claim。

## 4. 修复一：在乘法发生前，修正提取范围

### 新流程

```text
不可变 base revision + target revision
  → 确定本次变化范围
  → 扩展到可独立表达意义的完整结构片段
  → 这些片段作为 Primary candidates；必要旧文作为 Required-only / Context
  → v9 catalog 提取 + 现有 Candidate Ledger
  → 真实新候选 × 完整 mandatory incumbents
```

不按修改过的几个字符切 Evidence。修改表格行、列表项、段落或嵌入 HTML 时，由现有 representation compiler 保留足够的完整结构。
一个结构片段含有未修改文本是允许的；其整体被本次变化触及，不等于整份历史文档都重新获得提取权限。

实现职责：

- `SourceUnitDerivationService` 统一选择和持久化提取工作，fragment-catalog 路径不能绕过安全的增量计划。
- Primary 范围、必要上下文、计划策略及契约版本进入已有 derivation/batch identity。
- 使用 **最后成功提交的 Source Unit base** 和暂存 target，不把“已下载”当作“已完成 lifecycle”。不可恢复的 base 不伪造成空 diff，使用显式 full-document 策略或报告缺失。
- ADR 0030 的文本坐标是原始字符串中的 Unicode 字符半开区间，**不是 UTF-8 字节偏移**。Document 视图与 Observation 文本必须先验证映射；不能假设两个文本的偏移相同。
- 未变化旧段仍可提供必要背景，但不因 LLM 选择就升级为本次 Primary。
- 不硬编码忽略 `---` → `***`；没有可信的结构等价证明，就按实际变化处理。
- 删除-only 变化仍必须处理旧 Memory 的 Support；“没有新候选”不是“跳过 lifecycle”。

适用范围由 representation 决定，不为来源新增 if/else：

| 表示 | 处理原则 |
| --- | --- |
| Markdown / plain text，包括 Confluence、GitHub、本地文件 | 仅在当前权威文本可准确映射时使用结构化变化范围 |
| canonical record，包括采用该 profile 的 Jira、Teams、coding session 内容 | 保持完整 record 的解析权限，由 compiler 解码字段；不从 JSON 中间切半个对象 |
| 多 Observation 的会话或 issue | 继续依据新增/修改 Observation 和已有关系选择 Primary 与背景；不把整条线程重新提取 |
| 图片、PDF 等 Artifact | 保留现有 revision、eligibility 和资源预算契约；本次文本优化不改变其原子坐标权限 |

Source type 本身不能保证某个 profile；必须读取实际 revision 的 EvidenceRepresentationProfile。

### 能省多少

每去掉一条本来不该重新生成的候选，本例就减少 248 对判断。
若一个测试样例正确地产生 3 条候选，矩阵从 27,280 对降到 744 对；这是条件算例，不是本例的验收承诺。

真正首次导入或全文重写仍可能产生大量合理候选。这个修复不改变关系矩阵的 `候选数 × 旧 Memory 数` 复杂度。

## 5. 修复二：冲突不再触发整轮语义重跑

### 用一个例子说明推荐结果

以下是合成例子，不是声称已定位到线上那一对冲突：

- 旧 Memory M：“生产发布需要审批。”新 revision 仍有证据支持这一点。
- 新候选 A：“当前生产发布恰好需要 1 位审批人。”
- 新候选 B：“当前生产发布恰好需要 2 位审批人。”
- 新候选 C：“备份每天执行。”

A/B 指同一环境、时间和规则，不能同时成立；如果分别指测试/生产，或者旧制度/新制度，则不能仅因为数字不同就判矛盾。

```text
现在：完整关系判断 → A/B 冲突 → 异常 → 整份文档重跑

推荐：完整关系判断 → A/B 冲突 → 暂存 A/B 的 Review 提案
                                M 保留有依据的当前状态
                                C 正常新增
                              → 一份完整 Unit Plan 原子提交
```

“C 正常新增”不是按提取批次先写一部分。必须等完整候选/旧 Memory 覆盖和必要比较完成，证明 C 不依赖冲突部分，再在**同一个事务**中提交 C、Review、Projection、derivation applied 和 outbox。
如果判断本身未完成，则根本没有这份可提交的完整 Plan。

### 推荐的最小职责划分

1. **Reconciler** 返回完整普通结果和确切冲突参与者；`failure` 只表达没有获得可安全使用的完整结果。不能把不完整 ledger 包装成 Review 成功。
2. **Engine / Lifecycle Planner** 将冲突转换为 Review 提案，并确保每条 mandatory incumbent 恰好有一个明确处置。A/B 此时不是可检索的 active Memory。
3. **Datastore** 原子写入完整 Plan；每条 Memory、Support、Source revision 和权限照常检查。
4. **Sync caller** 不理解 A/B 关系图；收到已应用结果及 pending Review 数即可。下一轮相同输入识别已 applied，不再重算。

### 不能漏掉共享候选

假设 A 除了关联 M，还准备更新旧 Memory N。不能把 M 送去 Review，却经由 N 把 A 发布出去。
冲突隔离必须覆盖已有关系 ledger 中共享候选的受影响操作，直到剩下的操作真正独立。
这一计算仅使用已经得到的关系，不额外新增全局 `N × N` LLM 调用，也不建立跨 Source 等待队列。

如果共享候选涉及多条旧 Memory，解决提案必须覆盖整组受影响写入并原子审批；不能让多个独立 Review 各自先发布其中一部分。**这是 Review interface 需要明确支持的内容，不是当前单 incumbent Review 已有的能力。**

### 为什么现有 Review 不能直接套用

当前 `LifecycleReview` 主要携带一条旧 Memory 的一份 proposed mutations。UI 的动作是接受这份提案或保留当前状态；approval 会应用整份提案，不是从多个候选中选一个。

因此本方案需要明确扩展：

- 展示旧 claim、冲突候选及各自 revision-pinned Evidence；显式表达可选的完整提案，而不是把 A/B 混入同一份待批准 mutations。
- 决策携带所选 proposal identity 和 Decision Fingerprint；审批结果唯一、幂等，不能同时激活互斥候选。
- 共享候选的多 incumbent 影响整体校验，保留原子性；普通单提案仍是简单情况。
- Source revision、任一受影响 Memory 或 Support 变化后，旧提案不能覆盖新状态；进入既有 stale/refresh 流程。
- “保留旧 Memory”也要有合法 postcondition。若当前 Evidence 已无法证明旧 claim，不能只把 Review 改成 rejected，就留下一条失去保护的 stale Support。
- 对确实需要暂存的旧 Support，只允许现有精确 contested-Support Review 规则；Review 不等于为旧 claim 生成了一份新的 current v2 Support。

仅加 `flag_for_review=True` 不够：当前 ADD 路径仍可能直接创建 active Memory，NOOP 也不会自动产生 Review。

**范围边界：**本方案首先处理本次已存在的“同一 incumbent 的不相容 refiners”检查。当前实现并不检查所有新候选的全部两两冲突，首次导入且没有旧 Memory 时尤其如此；不能声称本次扩展会证明整个知识库无矛盾。

## 6. 重试规则：重试失败的步骤，不重试事实冲突

| 情况 | 推荐处理 |
| --- | --- |
| 单次模型调用的暂时性错误或可恢复 schema 错误 | 现有 structured-LLM 层在同一逻辑预算内有限重试 |
| Support revalidation 返回 schema 合法但不属于当前 workset 的 ref | 使用同一不可变小 workset 和 allowed-ref manifest 最多纠正一次；仍失败则终止该 Unit，不重跑 extraction/relation |
| 逻辑调用预算耗尽、关系 ledger 不完整 | 不提交 Unit Plan；保留精确失败和已有提取结果；本轮不再透明重放整个关系矩阵 |
| 完整判断发现 A/B 不相容 | 按第 5 节形成 Review 业务结果，不靠再次采样期待矛盾消失 |
| 已准备好 Plan，只是可修复的提交依赖未就绪 | 保留既有 Deferred / commit-only retry，不重跑 LLM |
| 真正新 revision、相关 Memory/Support 或语义契约变化 | 按新输入重新判断；不得复用失效旧结果 |
| 运维需要重新评估同一失败输入 | 显式、可审计的有界恢复，不由每次 schedule 隐式重复 |

`retryable=False` 只能停止当前调用栈；现有 scheduled recovery 还会找到 completed-but-not-applied derivation。
所以**不能单独把这一行当作完整修复**。冲突 Review 的原子提交会关闭该 derivation；未完成的执行失败则必须使用已有执行/失败记录约束自动恢复预算，让恢复入口遵守同一个失败分类。
不新增一张通用 replay/cache ledger，也不把失败 derivation 伪标为 applied。执行失败恢复的持久判定仍需在实现前完成契约测试。

这与通用 retry 原则一致：暂时故障才适合自动重试，嵌套重试会放大延迟；幂等不等于重新推理没有成本。[Microsoft Retry pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/retry)

## 7. 真正很大的关系矩阵怎么办

本次不减少 mandatory incumbents、不新增分批业务状态，也不把所有关系塞进一个巨型 prompt。沿用现有计算批次和共享并发预算。

可以作为单独测量后再选择的优化：让每一对关系输出更紧凑的显式标签，保留 pair identity、refinement 方向及必要的矛盾证明。
例如无关关系不重复输出一大段解释，但每对仍必须有明确结果。

不能让 LLM “只返回有关系的”，再把漏项默认成 UNRELATED。遗漏和真的无关必须可区分；数量相同也不能代替 ID 集合正确、无重复、无越界的校验。[JSON Schema array validation](https://json-schema.org/understanding-json-schema/reference/array)

这只能减少 token 和单次请求耗时，**不能降低关系矩阵的渐近复杂度**。它不是本次已批准的必做变更，也不是解决语义冲突的方法。
若正确增量之后，真实合理候选仍产生不可接受的矩阵，必须再评估关系覆盖契约，而不是偷偷用相似度裁掉旧 Memory。

## 8. 大文档还有一个必须关闭的安全风险

当前 incumbent Support audit 只传 `updated_document[:100000]`、`changed_hunks[:40000]`。对 28.5 万字符的文档，“返回了 248 个判断”不等于“看到了足以判断这 248 条 claim 的 Evidence”。

修复必须将审计输入与实际 Support 及 Revision Delta 对齐，使用现有 compiler 提供必要的完整当前片段和变更上下文；不能用固定文档前缀充当完整权威视图。
未覆盖到的文本不证明 claim 已失去支持。无法取得足够 Evidence 时，只能保留准确的未决处置、进入已有 Review/失败路径，不能自动 REMOVE，也不能虚构 KEEP 的 current Support。

这是已确认的静态输入截断风险，**尚无证据证明本次因此错误删除了 Memory**。具体输入封装和超预算处置须通过长文档尾部 Evidence 测试后，才能把本方案标为 implementation-ready；不以再增加全局审计轮次来掩盖它。

## 9. 进度、资源和其他 Source

- 一个文件的进度除“完成文件数”外，显示当前阶段。关系判断可显示已完成 pair / 本次完整 pair 总数；模型返回前不能假装整批已经完成。
- 等待 lifecycle 名额明确显示等待，不描述成正在提取。Review 待处理与 Source Sync 执行失败分开显示。
- 先修正多余工作和无效重试，再评估现有 admission 位置与最坏工作集；不凭一次低 RSS 就上调全局并发。
- 本次 Confluence 等待 cookbook 名额是已观测的 head-of-line blocking。释放异常尝试的名额是基本要求，但巨大、合法且成功的矩阵仍可能占用很久，不能声称 conflict fix 单独解决公平性。
- 后台跨文档关系发现沿用现有 outbox/worker。Source Sync 成功和后台工作全部完成是两项状态，不互相冒充。[AWS transactional outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)

## 10. 实施顺序与验收

这是一份修复契约，不是另建的执行 backlog。执行状态仍以 GitHub issue/PR 为准。

1. **先做确定性红测：**固定 base/target、真实 v9 derive 入口、完整关系结果和冲突响应，不依赖 live LLM 的随机性来复现。
2. **修正增量与恢复基线：**同一 target 在失败、重试、进程重启后使用一致的权威输入；中文、emoji、表格/列表、嵌入 HTML、canonical record、Artifact 和删除-only 均覆盖。
3. **敲定 Review 扩展后实现冲突结果：**测 A/B 冲突+C 独立、A 同时影响 M/N、缺失关系结果、Source 已更新、权限变化，以及保留旧状态时的 Support 合法性。
4. **一起验证错误分类与恢复入口：**普通 sync 和 scheduled recovery 都不得无限重放同一 semantic failure；真实未完成调用与 commit-only retry 不混淆。
5. **关闭输入覆盖与性能风险：**尾部 Evidence 不能被前缀截断误判；记录候选、incumbent、pair、各阶段调用数、重试原因、时间和峰值 RSS。承认真实矩阵仍需完整判断。
6. **SQLite/HANA 同一组事务契约测试：**Review、独立写入、Projection、derivation 状态与 outbox 要么全提交，要么全回滚；重复调用幂等，陈旧请求拒绝。
7. **更新 canonical ADR，PR、部署后有界验证：**从明确水位开始，只验证真正需要处理的新 revision 或显式批准的恢复 cohort。不因旧失败历史还存在就 force 重跑整个 Source。

最低通过条件：

- 小修改不会再自动重新提取整个历史文档；不存在“重试把自己的新内容当旧基线”。
- 每条 mandatory incumbent 仍有明确、完整处置；任意缺失、重复、越界关系结果不能进入正常提交。
- 已发现的冲突候选不会成为 active Memory，也不会经由别的 incumbent 泄漏；独立内容可以在完整 Unit Plan 中提交。
- 相同已处置输入的下一轮 sync 不会再次跑数百次关系调用；Review 选择只能应用相应完整提案。
- 原子性、权限、stale guards、Support 真实性在 OSS 与 Cloud 一致。
- 性能指标说明“省掉了哪些工作”；没有新证据前不承诺固定倍数提速或所有大文档都变成几次调用。

## 11. 代码落点、ADR 与问题跟踪

| 落点 | 本次责任 |
| --- | --- |
| `source_derivation.py`、`pipeline/projection_context.py` | 统一 revision-pinned 工作规划，修正 fragment 路径绕过增量范围 |
| `pipeline/sync.py` 与 Document artifact interface / Cloud adapter | 不从可变缓存获取 authoritative retry base；区分模型、语义与提交恢复 |
| `pipeline/reconciler.py` | 完整关系/Support 判断；返回可审阅冲突与准确诊断，而非全局语义重跑异常 |
| `memory/engine.py`、`memory/lifecycle_planner.py` | 冲突隔离、完整覆盖、一次 Unit Plan；不让 sync 理解关系图 |
| `memory/lifecycle_review.py`、Review interface/UI、SQLite/HANA | 仅在扩展获批后支持明确提案选择、共享候选影响及完整 stale/authority 校验 |
| Source activity interface/UI | 展示等待、提取、关系判断、提交与 Review，不制造虚假进度 |

相关 Accepted ADR：

- [0017：可恢复 derivation 与完整 reconciliation](../adr/0017-stage-recoverable-source-unit-derivation-before-lifecycle-commit.md)：目前 incompatible refiners 仍 fail-closed；需要显式修订为“完整冲突结果可由 Review 处置”，不能悄悄改变。
- [0030：revision-pinned Evidence Fragment](../adr/0030-compile-revision-pinned-evidence-fragments.md)：继续保持 representation、结构完整性、角色与精确坐标契约。
- [0008：仅排除已证明不受影响的 incumbent](../adr/0008-prune-only-proven-disjoint-incumbents.md)：有新候选时，不因旧 Evidence 位置未变就跳过关系判断。
- [0009：跨文档关系发现](../adr/0009-bound-cross-document-relation-discovery.md)：非破坏性、后台、有限候选，不是同 Unit 破坏性 lifecycle 的替代品。

已核对的 issue：

- [Cloud #196](https://github.com/dodoman-sun/memforge-cloud/issues/196)：增量范围与受控 Anchors，OPEN。
- [Cloud #220](https://github.com/dodoman-sun/memforge-cloud/issues/220)：document lifecycle admission 优化，OPEN。
- [OSS #268](https://github.com/shno-labs/mem-forge/issues/268)：已关闭的一候选/多 incumbent 修复，不是本次多候选互斥问题已被解决的证明。

Review 扩展若确认进入实现，应先建立一条协调 issue，列明 OSS、Cloud、UI、事务与验收范围；不要拆成重复的跨仓库 backlog。本文没有创建 issue、修改产品代码或执行生产写入。

### 自检结论

核心方向清晰且必要：修正提取工作范围、稳定输入、分离语义结果与执行重试。
多候选 Review 不是一行补丁，其复杂度来自真实的共享候选和 Evidence 生命周期约束；我推荐这个方向，但不会声称当前已能直接复用 Review 完成。
尚需敲定的实现细节是多 incumbent 提案的原子选择、未完成执行的持久恢复预算，以及长文档 Support 输入完整性。它们是 implementation-ready 的门槛，不应被“先加个 flag”略过。
