# MemForge claim / Evidence extraction 交接

2026-10-04。**当前方案没有通过验收，未提交、未部署、未重处理产品数据。**
用户要求：完成当前迭代后，如果仍失败，提供完整交接给另一位 Claude Code。
本文件交接当前真实状态，不是新的执行 backlog，也没有授权任何功能延期。

后续只读诊断补充：
[因果审计](2026-10-04-claim-evidence-causal-audit.md) 以历史源码和同一真实文档
复现 Confluence 可读性回退，定位到 2026-09-08 `a8302b5e`，早于 ReadingGroup；
并证明 v19 部分 Jira 信息在 adapter 阶段未进入 prompt，不能归因于模型漏读。
当前 design v7 仅明确输入完整性验收，未改变产品代码或选择新的提取架构。
下述 v19/v6 冻结试验和原交接 ZIP 保持原样；补充证据不代表验收通过。

后续 [delivery 验证](2026-10-04-claim-evidence-delivery-validation.md) 补上了实际本地
SQLite 写入、61 条 detail 和 64 个 ref 的 HTTP/resource/compact 检查；HANA 查询
使用 SQLite 桥接，不是物理 HANA。[Support 审计](2026-10-04-claim-evidence-support-audit.md)
确认同 pinned revision 的全部 61/64 项可无模型重绑，同时复现既有重复 selector
静默规范化、完整性错误归为 incomplete coverage 的契约差异。产品代码未改；
线上 Support/Change Impact 及完整验收仍未完成。原交接 ZIP 不包含这些后续文档。

## 交接结论

线上实际模型为 `sap/anthropic--claude-4.6-sonnet`，通过 CF 应用的 SAP AI Core
绑定、经过核对的 deployed factory/transport 调用。本地运行新的 canonical
extractor；这不是新代码已部署到 CF。Confluence/Jira 各一个完整已规划请求，
分别输出 56/5 条候选；零 transport retries，没有自审、引用修复、准入裁剪、
新 batching、输出 schema 拆分或提高 32,768 token 配额。

两位 source-first 独立 agent 在候选暴露前冻结知识清单，审阅全部 61 条候选、
61 个 Primary、3 个 Required。两人均判定两类来源不通过。

| 验收项 | 评审 A | 评审 B |
|---|---|---|
| Confluence 覆盖 | 48/53；有利解释争议项也仅 49/53 | 39/55；即使补计 12 个命名测试环境也仅 51/55 |
| Jira 覆盖 | 7/8 | 7/10 |
| Confluence Required | 1/1 | 1/1 |
| Jira Required | 1/2 | 1/2 |
| 重大 claim 错误 | 未确立；一项潜在重大模态错误未解决 | 一项 Confluence 模态错误 |
| 重大 Primary 错误 | 未确立 | 未确立 |

共同明确失败：`jira-0003` 的 labels Required 重复 Primary 已有的 WCAG 分类，
没有独立贡献。`confluence-0048` 将原文 `A task will be produced ... Fix by`
写成 `A task was produced ... fixed by`，旁边的 PASS
让完成状态看似合理，但不能直接证明指定 issue 已修复；严重性分歧必须保留。
覆盖率分母不同，不能只取较好的评审。测试环境/来源链接是否属于独立知识项，
以及某些条件是否仅在引用而未进入 claim，仍需一致的 materiality adjudication。
这不会改变双方确认的 Required 失败，也不能据此声称已达标。

确定性检查已通过：23 个受影响 OSS 测试文件 **781 passed**；对应/生命周期
联合检查 **104 passed**（两组重叠，不能相加）；Ruff 和 git diff --check 通过。
这些结果不证明提取语义、所有 source variants、HANA 当前发布或生产部署验收。

## 用户约束与完成合同

1. 保留 Primary/Required；catalog + 程序精确绑定必须实现可行。
2. Primary 支持中心实质断言；Required 尽可能覆盖相关独立支持，不要求 100% recall，
   不设最低引用数，不要重复/false positives。不得通过准入删除引用或淘汰本应保留
   的 memory 来改善结果，也不要偷偷加入自审/修复模型。
3. 通用 prompt/例子，不为 Confluence、某一页或某一用例 overfit。
4. 原生语法、字段含义、作者/时间 framing、source identity、coverage 均由各 adapter
   封装。共享代码仅消费声明，不散落 Confluence/Jira 特例。
5. `get_memory` 返回真实可读、固定 source revision 的引用；所有显示事实都有精确
   来源。展示文字不得用于确定性跨版本匹配。
6. 将来未改变且唯一/有稳定原生身份的 ref 应准确对应；偏移变化、无关插入、声明的
   无害格式/重排不能误判。重复且无法区分的 occurrence 必须明确 ambiguous。
   一次升级 reprocess 可接受，但保留旧 Evidence/history，不能伪造原生来源。
7. 每次设计先明确假设和验收，再用完整真实文档、线上 Sonnet 和 source-first 盲评
   验证；失败修改 design，再改所属实现；不要继续逐样本 quickfix。
8. 验收：零重大 claim/Primary 错误；每类有用知识至少 95%，保留关键条件/分支；
   已选 Required 至少 95% 相关且非重复。图像引用暂不纳入，已记录 OSS issue497。
9. 未经确认不能为绕 provider limit 引入 batching、分 schema 或降低完整覆盖。
10. 最终完成还需所有 A1–A15 验收、两仓库 PR、checked CF deploy 与详细 smoke。
    当前没有满足完成条件；不要把“交接完成”写成“整个目标完成”。

权威文件（OSS 工作树）：

- `docs/design/claim-evidence-extraction-contract.md`：当前 design v7；完整 runtime flow、
  ownership、提取/准入/Support 分工、匹配算法、A1–A15、停止规则。
- `docs/adr/0047-define-claim-evidence-extraction-outcomes.md`：Proposed，尚未 Accepted；
  记录重要决策及 v19 假设失败。不要未验证就修改既有 accepted ADR。
- `docs/research/2026-10-04-claim-evidence-design-validation.md`：v18/v19 正负证据、
  评审分歧、确定性检查及未验收范围。
- `docs/research/2026-10-04-extraction-design-primary-sources.md`：官方 source/API 资料。

冻结试验使用 v5；v6 是试验后记录失败结论的设计更新，v7 是因果审计后的
输入完整性澄清，都不是另一份已通过方案。原交接 ZIP 保存的是 v6 时点工作文件。

## 精确工作树与 Git 状态

OSS：`/Users/i551096/.codex/worktrees/claim-evidence-contract/oss`
branch `codex/claim-evidence-contract`
base/HEAD `57f8b006962bf65a6430592b1a5002e15082c8c1`。

Cloud：`/Users/i551096/.codex/worktrees/claim-evidence-contract/memforge-cloud`
branch `codex/claim-evidence-contract-cloud`
base/HEAD `e1e8ec82f00ed327abb320ce1a4a88ac9084dee7`。

这两棵工作树从当时更新后的 main 创建；当前全部工作仍未提交。
`git diff` 不含未跟踪文件：必须同时检查 `git status --short` 和
`git ls-files --others --exclude-standard`。新 adapter、text_view、测试和设计文件
均包括未跟踪文件，不能只恢复一个 tracked diff。

不要 reset/stash 用户原工作目录 `/Users/i551096/Dev/memforge-cloud` 中无关的
uv.lock/research 改动。旧 OSS `/Users/i551096/Dev/mem-inception` 和旧 Cloud
`/Users/i551096/.codex/worktrees/claim-evidence-cloud/memforge-cloud` 不是本轮实现。

2026-10-04 核对仍开放的旧 draft PR（不是当前 fresh branches 的 PR）：

- OSS495 https://github.com/shno-labs/mem-forge/pull/495
- OSS498 https://github.com/shno-labs/mem-forge/pull/498
- Cloud545 https://github.com/dodoman-sun/memforge-cloud/pull/545

不要 merge 这些旧 draft 冒充当前验收。后续 merge 前按 AGENTS.md 检查全部
open PR 与 local/remote codex branches，报告 superseded/stale 项并明确处理意见。

## 实现地图与真正已闭合的职责

- `src/memforge/source_adapters/`：Confluence native storage、Jira 当前 rendered HTML
  与 literal old/new history、Teams framing、repo/pages/Markdown。contracts.py
  是 neutral declarations；dispatcher 主要派发。
- `source_representation.py`：注册当前/历史 profile。Jira current schema4；旧
  schema1/2/3 保留，不能拿旧转换后 Markdown 当原始 storage XML。
- `pipeline/evidence_fragments.py`：compiler8、原文范围/摘要、可读 view、声明的
  scalar comparison/presentation keys、field roles、wildcard sibling identity。
- `memory/text_view.py`：不可变 versioned descriptor，每个事实 origin 都有同
  Observation/revision 的精确范围和 SHA。展示与 canonical comparison 分开。
- `projection_context.py`、`revision_assessment.py`：共享 field/material 规则，
  工作授权和 whole-Support delta 不能按不同数组位置规则比较。
- `revision_reading.py`：governing anchors 与仅供阅读的 companions 分开；改变
  一条普通列表项不能授权整节；改变声明的表头/lead-in 可影响对应 unchanged core。
- 增加无稳定身份的重复 occurrence，提取授权不能选“第二份”；Support reading
  则读所有数量变化的当前副本，尚有副本存活时不能指定某份旧副本已删除。
  原生/嵌套/Markdown/plain-text 和 parent wildcard fields 共用这一原则。
- `memory_extractor.py`：通用 claim/Primary/Required 紧凑 schema；批次中任一
  unresolved/malformed selector 则整个 derivation 失败，不发布成功子集。
- `candidate_admission.py`：value + 同轮 dedupe，覆盖所有 candidates；无法评判
  则 atomic failure。没有引用剪枝、角色提升或 `evidence_incomplete` 补救。
- `support_reading.py`/`revision_work.py`/`coordinator_review.py`：旧固定 claim 的
  whole-source 评估是独立职责；ref match 不能证明 claim 仍正确。
- descriptor 经过 derivation、Lifecycle Plan、Evidence identity、SQLite/HANA、
  Support 与 get_memory/resource/proxy/UI/plugin clients。新增 nullable JSON
  字段；旧 NULL identity 保留，不增加新的 domain graph 或 lifecycle state。
- 不支持的历史 view contract 保留原 excerpt/identity 并显示 interpretation
  unavailable；已知 typed 来源损坏仍报错，不能改用最新 renderer 蒙混。

仍有未使用的旧 `fragment_selector_correction.py` helper 与 standalone tests；
实际 extractor call path 不再调用它。不要因为看到 helper 就恢复后处理流程。

## 尚未实现/验收的关键范围

- **Managed concept adapter 缺失**：agent_session dispatcher 仍 inline，
  session_summary/agent_concept 声明普通 Markdown；generated frontmatter、title、
  mf:claim、Citations 还没有完全由 owned format 区分。需 actual writer→adapter→
  compiler→store→get_memory/resource 验证，不能词语/正则猜测删除作者 JSON/code。
- Managed upload 当前仅 `retention=none`：原始对话是 transient authorization，
  durable source 是 concept 文档；event ID/hash 不能恢复原话。用户问“啥意思”
  不是同意修改保存策略或延期该功能。此轮不改变 transcript retention，也不能
  用 concept-source 验收冒充原始对话引用验收。它不阻碍实现 owned concept format。
- 真实 Jira cohort 没有 comments；collector fixture 不等于 real-comment 验收。
- 真实 Teams、held-out Markdown/HTML、authentic consecutive 大文档 revisions
  尚未完成本轮线上/盲评。已调 Confluence 不能当 held-out 泛化证明。
- 有实际大 Confluence 文档的 controlled 插入对应检查：73 unique exact，
  六个重复 ambiguous。它不是实际 provider 的连续版本，也不是重复文本无条件保证。
- 当前 whole-source lifecycle/get_memory/resource/group/private/access/stale/idempotent
  的最终 SQLite/HANA 用户入口一致性审计未完成。历史 HANA520 pass 不能替代本次
  compiler8/source4 完整 acceptance。
- fresh main/proposal 线上比较、A14 bounded upgrade/dry-run/apply、A15 CF deploy/smoke
  未完成；旧文档变不可读的首次历史 commit/是否由 ReadingGroup 引入也尚未在本轮
  重新证明，不能把猜测写为已经确立的回归起点。
- 图片延期：仅 OSS issue497 https://github.com/shno-labs/mem-forge/issues/497。
  不要将其它未闭合验收项标为用户已批准 deferred feature。

## 线上与盲评证据位置

private 根目录：
`/Users/i551096/Downloads/MemForge-Evidence-Validation-2026-10-02/private/canonical-native-20261003`

保留 `contract-v18-20261004` 和 `contract-v19-20261004`，不要覆盖负面记录。
V19：

- native 原文：`confluence/confluence-native-original.html`（71,051 bytes，SHA
  `38eda4ad6e0563c6a759881d1f35817d2ab3a4112a22363600d270d5a2a0789b`）；
  `jira/jira-native-original.json`（50,807 bytes，SHA
  `828b504feef809f8d9d9c19e551b70989fdb6f751fe7efe7a0f9c433db52dae3`）。
- source tree freeze（OSS+Cloud+executed helper/factory）：
  `934ec430f2c0faf60d4ee1babefa7c340481f535dee087fb6df00fb3ebcaeded`。
- 全候选盲评包：`blind-candidates.json`，SHA
  `416632a6a19667b9f03ec6bfada7cdad519c87133c7c8594087a7071ca253ae4`。
- `independent-reviews/` 包含两份 frozen inventory、全部最终候选审计和 static review。
- 每个 source 子目录有 native fragments、coverage、prompt、untouched response、
  call/telemetry、bound candidates、manifest；root 有 execution logs 与 freeze runner。
- root `evidence-manifest.json` 给所有 private artifact 摘要；
  `working-state-at-handoff.json` 记录文件/branch/HEAD/hash，不是可恢复 commit。
  `goal-working-files.zip` 包含两仓库 changed files、untracked files 和 tracked
  binary patches，便于保留未提交工作；不要覆盖有其它改动的 checkout。
  设计 v5 副本保存在 `design-snapshot/`；这是 inference
  后取得的副本，mtime 早于 run，不能宣称其 hash 在 run 开始前已经记录。

盲评 SHA：A inventory `516a49cad53c4599723cf688b34634e5950fa4bf330042884d3e157a71303bf8`；
B inventory `0a69f53ef3b6c56d9fd07468dd4d041c28675ebd864aff2ef750e0ef4c45177a`；
A candidate audit `55ae5ea572dee077483b1aea774b5d2e16902491a06dfa61bb2ce9b3ce3c1eca`；
B candidate audit `4f9c42ab47f5881162e84425a7dcb416cc7aa14cecfed006be4aaf7f5448f9f7`。
这些 denominator 是 fresh independent inventories，不能直接拿来与 v18 分数作
同分母提升比较。原始 Observation-range integrity 由 compiler 前置校验，不是
盲评根据 displayed excerpt/hash 推断出的正确性。

CF target：`https://api.cf.eu12.hana.ondemand.com`；
org `GSHCM_AI_Innovation_hcmgcn-wo4dz1tb`；space `dev`；app `memforge-cloud-service`；
app GUID `1c0e93ef-98a6-4a48-ab8a-c5cb3a671529`；binding `memforge-aicore`。
Deployed OSS pin 仍为 `57f8b006`。token/service bindings 仅留在运行进程内，
不要打印或保存 `cf env`、VCAP_SERVICES、OAuth payload。

## 下一位 Claude Code 的第一步

先读完整 design/ADR/报告，再核对当前 Git 与 private manifest。对 v19 的
Required 重复、模态与遗漏做一致的源文本 adjudication，确认哪些是 source
表示问题、catalog selection granularity 问题、或生成模型行为。现有通用
framing+single-pass 方案没有达到质量标准，不能直接做下一次措辞微调然后重跑。

下一份方案要先写可实现的最小 extraction 契约与完整验证计划，再由用户讨论
新的架构取舍；保留已经证明的 exact binding/correspondence，禁止输出后裁剪，
不要未经允许加入 reviewer/repair model 或 provider-limit batching。所有 source
专属逻辑继续留在 adapter。当前没有选定/授权替代架构。

验证命令（fresh OSS 目录，必须显式 PYTHONPATH，防止 import 旧 editable repo）：

```sh
PYTHONPATH=src /Users/i551096/Dev/memforge-cloud/.venv/bin/python -m pytest -q tests/test_jira_native_evidence.py tests/test_text_view_contract.py tests/test_support_relation_coordination.py tests/test_revision_assessment.py tests/test_projection_context.py
```

完整 changed-file 23-file suite 的清单 `changed-test-files.json`、执行脚本
`run_changed_suite.py` 和日志保留在本轮 private root。线上 runner 还使用
`/Users/i551096/Downloads/MemForge-Evidence-Validation-2026-10-02/private/full_runtime_replay.py`；
该外部 helper 的 hash 已进入 executable freeze，不要不核对就替换它。
781 passes 是相关 seam evidence，不是全 repo 测试或验收。Cloud 测试需要 fresh
OSS/src 加 fresh Cloud 的 packages/*/src；当前未重新跑所有 Cloud gates。

不要重新执行已经完成的 `freeze_and_run.py`：它使用 exclusive files 防止覆盖。
新试验必须另建目录、冻结 design/code/source/inventories、记录假设，不能因为
读取超时就重启 paid call。先检查真实 process/session/manifest 是否仍运行。

Claude CLI 命令为 `claude`，全路径 `/Users/i551096/.local/bin/claude`。此前账户
hold 与 CF Sonnet 是两条路径；本轮 CF Sonnet 已成功，不能把 Claude CLI 问题
写成当前模型验证的 blocker。

如果未来质量及全合同都通过，再提交两仓库并开 PR、处理 superseded drafts、
checked CF deploy 与 bounded smoke。Cloud 部署必须用
`deploy/cloud-foundry/scripts/prepare-deploy.sh --push` 或 `--push-rendered`，
不能裸 `cf push`。2GB quota 情况按对应 skill；共享协议先改 OSS，再保持 HANA
一致。部署前不能宣称该完整目标已实现。
