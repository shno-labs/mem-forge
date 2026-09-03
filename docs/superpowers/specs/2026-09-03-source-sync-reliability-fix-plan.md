# Source Sync 三项修复计划

日期：2026-09-03。执行由 [Issue #385](https://github.com/shno-labs/mem-forge/issues/385) 跟踪；本文件为实施及验收契约，不代替测试、部署或线上同步证据。

独立审查后已补充诊断结果判定、OSS retry parity、精确重试目标与 handoff 刷新要求。B 的文本资源预算仍是实施前必须关闭的设计选择，见 4.1；本文件不是全部实施前置已经通过的声明。

依据：[只读调查与本地复现](../../research/2026-09-03-source-sync-reliability-investigation.md)。调查基线为 OSS `5aba41a8ef37a87a3abd1a887d5e71d97018b380`、Cloud `776937cd685e9c58dab8a680a61d384c3a95e448`；执行前必须与最新 main 校准。

本文件定义实施范围与验收契约，不替代 GitHub Issue/PR 执行状态。涉及仓库：`shno-labs/mem-forge`（本地 OSS checkout）和 `dodoman-sun/memforge-cloud`。实施基线更新为 OSS `25b87235`、Cloud `e979037`。本计划不授权重跑 ingestion、修改线上 Memory、重写 lifecycle history 或修改上游 GitHub 文件。

## 1. 完成目标与边界

| 修复线 | 应交付的结果 | 不作出的承诺 |
| --- | --- | --- |
| A. relation 失败诊断 | 普通执行和 recovery 均保留失败步骤、安全错误类别及真实调用统计；失败仍不提交不完整 Plan | 不声称已查明历史事件的原始异常，不保证外部模型永不失败 |
| B. GitHub 读取一致性 | 扫描与读取使用同一不可变版本，按原始字节校验；Cloud/daemon 文本行为一致 | 不猜测混合编码文件的原意，不忽略错误字节 |
| C. 等待重试与手动 Sync | 等待不是 Syncing；显示下次重试；用户可提前同一待执行任务；浏览器不伪造 job 失败 | 不重置重试预算、不抢占正在执行的任务、不取消权限和 lifecycle gate |

保留现有 Source Unit、Evidence、Support、Lifecycle Plan 和任务身份。无需新的数据库任务状态、诊断台账、字符集检测框架、VPN 检测守护程序或额外 retry 层。

## 2. 实施准备

1. 开始代码工作前检查两个仓库的未提交修改、open PR 和相关分支；保留用户已有工作。更新 main，从最新 main 创建新的 `codex/` 分支或隔离 worktree，不能继续使用调查时的旧分支作为实现基线。
2. 在协调仓库关联对应 Issue；没有现有 Issue 时，在实施阶段建立一个覆盖两个仓库的协调 Issue，列明 type/area、优先级、触发条件、验收和非目标，不创建重复跨仓库 backlog。实际进度只记录在 Issue/PR。
3. 将调查中的临时 red-capable harness 转为仓库内回归测试，不能把 `/tmp` 文件当作永久测试依赖。测试使用假 provider 和隔离 SQLite，不访问线上 Source。
4. A 先补齐诊断；B、C 保持独立提交，便于审查和定位回归。B 的资源门槛未关闭时可以先完成 C，但不得把 A/C 的通过视为 B 或整体发布已验收。不是三个相互依赖的新运行时系统。

## 3. A：relation 失败诊断与 recovery 一致性

### 3.1 改动

相关 OSS 文件：

- `src/memforge/pipeline/reconciler.py`
- `src/memforge/memory/relation_classifier.py`
- `src/memforge/memory/engine.py`
- `src/memforge/pipeline/sync.py`
- `src/memforge/llm/structured.py`
- `src/memforge/evals/agent_evaluation.py`

步骤：

1. 将普通 `_process_item` 和 `_resume_source_derivations` 的现有诊断作用域统一封装。复用 `StructuredLlmMetricsCollector` 和 `source_unit_llm_summary`，不新增 tracing 存储。普通执行在 projection 后绑定真实 Unit；recovery 使用已有 attempt 中的 Unit 身份。
2. 对已绑定 Unit 且正常返回或抛出受控异常的执行，在 finally 中完成一次 summary；隔离并发 Unit 的 context，避免嵌套 scope 重复统计。强制进程退出不能依赖 finally，也不补造缺失历史。
3. 将一个小的安全失败描述传过 classifier → reconciler → MemoryEngine → runtime event：使用现有 operation 名称、`terminal_category`、`error_code`。扩展现有 binder 的可选参数，复用已有字段；未知错误保持 unknown，不猜成 timeout。禁止保存原始 provider 请求/响应、凭证或 traceback。
4. 用 structured client 已发出的实际 telemetry 统计 logical calls 和 provider attempts，包括失败调用。不得使用计划 batch 数、全部 planned pairs，或仅成功返回阶段的计数代替实际调用；不得重复累计 candidate ledger 与同一 collector 的调用。
5. 保持原有 outcome、reason code、完整 mandatory coverage、原子提交及 fail-closed。不因诊断变化把旧 failed event 改成 pass；已有空诊断字段可读，不批量回填历史。诊断写入失败不能掩盖原始业务异常或触发已提交 Plan 的重放。

诊断实现约束：

- summary outcome 依据真实结果，不以“函数正常返回”代替成功。recovery 的 extraction error 返回和 stale/already-applied skip 都可能是 `None`，必须区分失败、跳过与真正完成；沿用已有结果/原因语义，不新增业务状态。
- 一个 Unit 执行复用同一个 collector；stage 统计采用该 collector 的区间/差量或等价机制。现有 `metrics_scope` 会替换 ContextVar，不能嵌套另一个 collector 后假定外层自动收到相同调用。
- 新诊断参数缺省时保持既有 event payload/hash 形状；新执行有诊断时按既有 immutable 规则记录，不改变已有 event 的身份或覆盖内容。

### 3.2 测试与验收

主要测试落点：`tests/test_relation_first_reconciliation.py`、`tests/test_projected_lifecycle_integration.py`、`tests/test_sync_bookkeeping.py`，以及现有 structured-LLM/evaluation 测试。

- 分类第二次调用失败、Support audit 第二次调用失败：实际两次调用不能报零；保留明确失败操作和安全类别/code。
- 同一种 timeout、schema failure、logical deadline 分别经过普通和 recovery 路径：已绑定 Unit 时各记录一次正确 summary；正常成功、零 LLM 调用和并发执行也覆盖。
- 在真实 MemoryEngine 接口注入 mandatory 判断失败：Plan 数量仍为零，旧 revision、旧 Support 不变，不生成错误的 retire/update。
- 可选 revision-composition proof 的既有保守行为保持不变；不能为了诊断统一而扩大 fatal failure 范围。
- 现有 provider retry、schema fallback/repair 和 logical deadline 测试保持通过；不增加新的 retry 预算。
- SQLite 与 Cloud 对安全诊断字段、summary 的保存和读取一致；旧 event 的解析及 immutable/idempotency 契约不变。
- recovery extraction error 的正常返回不记为 committed；stale/already-applied skip 不被误记为新成功提交。同一执行中的 Unit 总数、reconciliation 区间及 candidate ledger 计数不重不漏。

完成口径：修好“失败却无法定位”的已复现缺陷。历史 `relation_first_failed` 的原始触发原因仍标为未知，不以模拟 timeout 的成功测试代替历史 RCA。

## 4. B：GitHub 固定版本、原始字节读取

### 4.1 改动

相关 OSS 文件：`src/memforge/genes/github_repo_gene.py`、`src/memforge/github_repo_utils.py`、`src/memforge/main.py` 中 daemon GitHub snapshot/blob 路径；必要时同步 local package admission 的验证。

步骤：

1. Cloud 和 daemon 均在 collection 开始时解析配置 ref 到一个不可变 commit/root tree，记录该次扫描的文件路径、blob SHA 和可用大小。后续正文读取不再重新解析 `main`。
2. Cloud/daemon 文本使用 `git/blobs/{sha}` 的 raw media type 做有界流式读取，不整份缓冲 Blob JSON/Base64。共享身份/大小/hash 验证和文本解码逻辑；HTTP 与 `gh` 继续留在各自既有 Adapter 中，不建立新的 transport 类层级。daemon 的 raw stdout 必须边读边受限，不能沿用 `capture_output=True` 后再判大小。
3. 校验 raw 响应完整性、声明长度、inventory 大小（有值时）和按实际字节重算的 Git blob SHA，之后严格解码。此文本路径不再需要 Base64 解码；既有 binary/metadata helper 不作无关修改。不能使用 `Contents?ref=<commit>` 或 Contents→Blob fallback 作为最终方案：前者不能解决已复现的转码，后者保留两套字节契约。
4. 稳定 Document/Source Unit 身份继续基于配置的仓库/ref/path；commit SHA 只锁定本次内容版本，不能导致每次 commit 创建新 Document 身份。
5. 文本采用一致的严格 UTF-8 解码，去掉 Cloud 的静默 `errors="replace"`。编码错误以可操作的失败显示，不当作空文件，不进入 Memory 提取。保留正常空文件的 authoritative-empty 语义。
6. 不改变 binary Artifact 的 streaming、资源限制和 lineage。选中的非普通文件模式（如 symlink）不能被悄悄当成包含 link target 的文档；本次不扩展 symlink 解析能力，使用明确的 unsupported/partial 处置，不能静默跳过并声称完整覆盖。

**文本资源预算细化：** 见[读取、正文生命周期与验收提案](../../research/2026-09-03-github-text-resource-budget.md)。推荐 raw stream + 实际字节上限 + 现有 256 KiB 读取块；daemon 沿已有逐文件上传接口读/校验/上传后释放正文，不把整批正文积存在 `prepared`。完整 manifest 与最终处理 gate 不变，不引入 batching。Cloud 复用现有完整 Document admission。

4 MiB/文件是待验证的初始预算提案，不是已证明安全或已获准缩小的产品范围。本地实测显示密集结构可能比更大的普通文本耗费更多解析内存，因此字节上限不能替代真实 pipeline 的资源验收。采用前必须核对既有大文件兼容性、daemon/receiver 同策略、实际部署配额下的解析与上传峰值；不通过这些门槛就不能宣称 B production-ready。超限明确失败、保留旧 Support，不截断正文、不伪装删除、不自动转成其他编码。

### 4.2 混合编码文件的独立处置

`data_masking_orchestration_Service/example/agent_pii_masking/README.md` 的原始 blob 不是合法 UTF-8。Blob 读取修复只能保证拿到正确的 4,992 字节，不能证明哪些字符是作者原意。

- 保持明确失败，不自动将整份文件按 CP1252 解码，不用替换字符修补。
- 由源内容负责人确认文本，正常提交 UTF-8 新 revision；如需我们修改上游仓库，需要另外明确授权。
- 可先交付代码修复，但在此文件完成权威内容处置并通过后续验证前，报告必须写明“产品读取契约已修复，该文件仍受编码问题阻塞”，不能宣布 Source 全部恢复。

### 4.3 测试与验收

主要测试落点：`tests/test_github_repo_gene.py`、现有 daemon GitHub collection/local package 测试及共享 helper 测试。

- 扫描后 `main` 移动：仍读取扫描时的 blob，不请求 mutable Contents，不发生身份漂移。
- 固定对象的 Contents 转码 fixture：raw Blob 原始字节通过正确校验；错误 SHA、大小、截断响应和意外返回的 JSON 均不被当作文本接纳。
- 使用真实计算出的 Git object hash，不能依靠任意 `readme-sha` 占位测试。
- 合法 UTF-8、空文件在 Cloud/daemon 一致；混合/非法 UTF-8 一致拒绝，正常修正后的新 UTF-8 revision 可解析。
- truncated inventory、权限失败和不存在对象不能变成成功空快照或授权删除。
- 现有二进制流式处理、文件大小限制、选中 scope 和 provider-mode 规则无回归。
- 文本预算临界值与超限、inventory size 缺失/虚报、响应长度缺失/虚报均有测试，证明完整缓冲前受限；不能靠解析后的长度检查声称内存已受保护。
- daemon 多文件正文不会全部驻留；完整 manifest/finalize、失败不授权删除和 lease fencing 不变。实际 normalization/planner/compiler 与 local upload/replay 分别覆盖普通文本、结构密集文本和 Unicode 的资源峰值。

协议依据：[GitHub Blob API](https://docs.github.com/en/rest/git/blobs) 支持按文件 SHA 获取 base64 或原始字节；[Python codecs](https://docs.python.org/3/library/codecs.html) 的 strict 解码在非法编码时抛错。这里选择严格解码是 MemForge 的可信文本契约，不是声称 API 能判断作者原意。

## 5. C：等待重试状态与手动立即重试

### 5.1 展示契约

复用 `queued/pending`、`leased/running`、terminal 状态及 `next_attempt_at`；等待仅是派生展示，不新增数据库状态。

这里的“复用”不意味着所有 Adapter 已具备字段：Cloud local job 已有 `next_attempt_at`，调查基线的 OSS local job 缺少该列、失败延期及领取时间条件。C 包含补齐这一共享契约，不能只改 UI。

| 当前情况 | 显示 | 操作 |
| --- | --- | --- |
| 存在未来重试时间 | `Waiting to retry · Next retry 12:02`，安全的上次失败说明，静态时钟 | `Retry now` 可用；没有旋转图标或进度条 |
| 已可领取但未执行 | 本地 `Waiting for device`，服务端普通 queued 提示 | 合并到已有任务，不显示 `Syncing now` |
| 已领取/正在运行 | 真实处理阶段与进度 | 不重复启动，不抢占当前 lease |
| 最终失败 | `Action needed` 及失败详情 | 既有授权 retry 流程 |

`Next retry` 与常规 `Auto sync` 的下一次计划时间分别标注；成功同步时间只由真实成功推进。使用现有可访问性 status 提示，避免每秒播报倒计时，参见 [W3C Status Messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html)。

### 5.2 后端：一个明确的手动请求语义

相关 OSS：`server/admin_api.py`、`server/source_admin_service.py`、`storage/database.py`、现有 local-agent/store protocols。相关 Cloud：`routes/local_agent_jobs.py`、`routes/workspace_proxy_router.py`、`worker.py`、control-plane SQLite/HANA store；server-run enqueue 的对应 OSS/HANA 实现。

1. 在既有 enqueue Interface 中显式区分 manual 与 scheduled intent，沿用现有 trigger 概念；由受授权的入口提供，不根据 payload 文本或来源 URL 猜测。
2. 手动请求若命中同一可重试 queued/pending 任务，在其现有事务内条件更新可执行时间为 now/立即可领取，返回同一个 job/run ID。定时扫描只 coalesce，保留原 backoff。
3. 不提前或抢占正在 leased/running 的当前 attempt，不修改它的 lease/预算。保留已有新 snapshot、force 请求及 handoff 对后续 rerun 的合法登记；不是禁止所有 running 记录的后续工作元数据更新。条件更新竞争失败后按现有状态读取/coalesce，不创建并发副本。重复点击不会重置 attempt budget 或产生两个执行者。
4. 保持 Source 权限、执行 owner、暂停/删除、maintenance、config revision 和 activity epoch 检查。失效的旧任务不能因为 manual intent 复活；遵循既有失效/重新 admission 路径。
5. 尝试次数、历史失败和正常调度策略保持；耗尽的 terminal job 沿用已有“新手动请求”规则。只提前 MemForge 的自动等待，不绕过 provider 的限流或当前执行的 deadline。
6. LocalAgentJob 与 SourceSyncRun 各自实现相同的用户语义，不合并两种状态机或事务。测试所有实际使用的手动入口，不能只修一个未被 UI 调用的路由。
7. OSS local job 采用最小 additive migration 增加 nullable `next_attempt_at`；沿用现有共享 retry delay/attempt policy，补齐失败完成、领取候选及条件更新、terminal 清除和状态序列化。旧行保留 NULL，不猜测历史失败应有的重试时间，不修改 Memory/history。Cloud 复用已有字段。
8. `Retry now` 指向当前展示的执行记录种类及 ID，不只按 Source type 分流。本地采集已交给 Cloud、当前等待的是 server run 时，沿既有受授权 Source sync 入口处理明确的 run retry target，并校验 workspace/source/当前任务与权限，直接提前该 run；不能创建另一个采集 job 或重新上传。目标已变为 running/terminal 或已被替代时，返回当前权威状态，不把旧点击转成全新 ingestion。普通新 Sync 和既有 terminal retry 语义不变。
9. `source_admin_service` 不再把有 `next_attempt_at` 的 pending run 一律序列化成 recovering。未来等待与到期 queued 保持 pending，由 presenter 派生；只有真正过期的 running lease 等既有恢复场景继续显示 recovering。

### 5.3 前端：请求接受与后台完成解耦

相关文件：`admin-ui/src/api/types.ts`、`views/sources/sourceSyncActivity.ts`、`SourcesPage.tsx`、`SourceRow.tsx`、`components/admin/SourceSyncStatusCard.tsx`。

1. 接入已有 `next_attempt_at`，在统一 activity projection/presenter 派生等待标签、图标和 retry 能力。不要在多个 Source type 分支重复判断。
2. Sync/Retry 请求被接受并获得 job/run ID 后，立即解除请求本身的 pending；复用现有 current-job/source 查询持续更新状态。
3. 从同步请求路径移除等待整个 job 的一小时 polling promise 及它生成的 synthetic failed job。保留仍需要短时返回结果的 setup/auth 流程，不误删其 polling。
4. 状态查询失败显示“暂时无法刷新状态”，不得伪造 durable job failed。刷新页面、切换 workspace 后仍以对应 workspace 的后台记录为准，旧 optimistic 状态不能长期遮盖新结果。
5. 等待期间只开放所需的 `Retry now`；不为了按钮可用而整体解除 configure/delete 等操作保护。
6. 接受请求后的刷新由 query 生命周期接管：job terminal/handoff receipt 到达时刷新 Sources/stats；receipt 指向的 run 尚未出现在 Sources 时，继续通过现有 query 等待该 run，直到匹配其当前状态。不能在 local job succeeded 后同时停止两个 query，使页面永久停在 `waiting_for_cloud`。使用 workspace-scoped query/状态，不新增轮询协调器或 synthetic job。

### 5.4 测试与验收

- Clock-controlled UI 测试覆盖未来等待、到期但未领取、真正执行、最终结果；等待不显示 busy spinner/进度条。
- 手动请求结束不依赖后台任务完成；模拟一小时后仍 queued，不出现浏览器伪造的失败。刷新查询的网络异常也不改变任务结果。
- 通过真实路由验证：manual 可提前、scheduled 不可提前；重复请求、lease 竞争、错误 owner/workspace、维护中、暂停和旧 config/epoch 都保持正确。
- OSS SQLite、Cloud control-plane SQLite/HANA 及 server-run Adapter 的条件更新、绑定参数、返回 ID/状态保持一致。
- 设置向导、登录、daemon 心跳、SourceSyncRun handoff receipt 和既有 terminal retry 无回归。
- OSS 旧 schema 升级后旧行/ID/attempt 不变；新失败产生延期、延期前不能领取、manual 可提前、耗尽/terminal 清除，与 Cloud 契约一致。
- 本地采集已成功且 server run 正在 backoff：点击重试返回同一 run，不新建 local job、不重新采集；目标与 lease 竞争或已 terminal 时不复活旧任务。
- 本地任务由 queued → succeeded(handoff) → server pending/running → terminal，Sources 初始只有旧 terminal 记录：无需刷新页面就收敛到真实结果。覆盖服务端 pending 的未来/已到期时间、过期 running lease，以及原有新 snapshot 后续 rerun。

## 6. 文档、PR 与发布顺序

1. 共享语义以 OSS ADR 为准：A/B 首先落实已有 [ADR 0012](../../adr/0012-deepen-the-extraction-lifecycle-hot-path.md) 和 [ADR 0011](../../adr/0011-separate-collection-evidence-from-body-materialization.md)，只在确需澄清持久决策时修改，不记录调试流水账。
2. C 在 [ADR 0001](../../adr/0001-project-source-sync-activity-from-existing-execution-records.md) 同 PR 记录手动提前重试、等待展示、请求/执行解耦；不创建重复 Cloud lifecycle ADR。没有新的领域实体，不改 glossary 凑文档。
3. 全部改动走 review 和相关仓库 PR；合并前检查尚未处理的 PR/分支，验证 OSS/Cloud Adapter parity。Cloud 更新 pinned OSS 依赖和 composed UI，不能只部署后台或只更新本地包。
4. CF 发布使用受控 `prepare-deploy.sh --push` 或 `--push-rendered` 路径并遵守 2 GB 配额流程，不使用裸 `cf push`。记录真实 commit、部署版本和 web/worker 健康。
5. 无 Memory/Evidence/lifecycle 数据迁移或历史回填；仅 C 的 OSS local-job nullable 列做 additive schema migration，不删除列来回滚。回滚旧 OSS broker 会失去该版本新增的延期领取保护，部署/回滚说明必须明确这一限制；必要时停止受影响执行器而非宣称旧版仍保持相同 retry 契约。应用回滚保留诊断历史，不删除 failed events 或改成功状态。

## 7. 有界线上验收与完成口径

部署不是自动同步授权。执行前记录 workspace/source、具体 run/job ID、Unit revision 及时间水位；线上会产生 Source/Memory 变化的动作，需要届时确认准确目标，不把当前老 job ID 或等待时间当作仍然有效。

| 验收项 | 最小验证 | 通过标准 |
| --- | --- | --- |
| A | 先用隔离模型验证普通/recovery 完整调用路径；部署后读取新 cohort 的 event/summary | 失败有安全原因和实际计数，summary 不重不漏，mandatory 失败不写 Plan |
| B | 从部署环境 GET-only 验证主 README 和固定问题 blob；分别校验字节与文本阶段 | pinned 字节正确；混合编码明确失败而非乱码入库；源修正后再验证新 revision |
| C | 一个届时确认仍在 backoff 的 job 做授权手动提前；用隔离测试覆盖并发/错误权限，不在生产制造 VPN 故障 | 同一 job 提前且仅一个执行者；等待 UI 正确；真实执行后才显示 Syncing |
| 综合 | 必要时仅对确认目标做一次普通增量 sync，并读取该 run 的增量日志/结果 | 不全 workspace 重放，不用历史 failed 总数判断新版本失败 |

最终报告必须分别列出：代码/测试、PR/merge、实际部署、在线验证，以及混合编码文件是否仍被阻塞。历史 relation 原始异常未知和旧失败历史保留不妨碍诊断修复验收，但绝不能被改写为“旧故障已根治”。若新增错误分类明确，再单独决定针对性的修复；不在本计划中预先扩展为性能重构。
