# Claim / Evidence extraction：最新交接

后续实现更新：[focused-display 集成报告](2026-10-06-focused-display-integration.md)。
正文已接入存储、API/MCP 与两套 UI；生产路径线上 Sonnet 新一轮生成86条
claim、93段引用正文，独立审查未发现重大事实或正文忠实度错误。1,024项
OSS、524项Cloud adapter回归通过。存在知识遗漏，尚未证明95%覆盖率；
物理HANA、部署和live smoke仍未验收。以下旧实验记录与ZIP保持原样。

后续验收澄清：用户允许主辅选择不理想的情况，在 `get_memory` 使用和
revision lifecycle 正确性审查通过后暂时接受。
[定向功能审查](2026-10-06-primary-required-functional-review.md) 已通过该
Confluence 引导句 / 实质列表案例（8 项定向、222 项 OSS、7 项 Cloud）。
这取代把该案例的 Primary 角色质量单独作为阻塞项的要求；下文保留原始
严格盲评结果。整个集成和发布仍未完成，原 ZIP 未改。

2026-10-06。本轮线上 Sonnet 验证及两位独立盲评已完成，**完整 extraction
方案仍未通过**。按用户之前的要求，停止本轮迭代，交接到下一位协作者。
未部署、未 reprocess 产品数据；整个优化目标未完成。本文是当前结果交接，
不是新的执行 backlog，也不替代 GitHub issue/PR 生命周期。

## 从这里开始

先读 [本轮完整报告](2026-10-06-focused-evidence-display-validation.md) 和
[focused display 提案](../design/claim-evidence-focused-display.md)，再读
[上一轮交接](2026-10-05-claim-evidence-current-handoff.md)。前者是最新实验；
后者保留原 v7 实现合同、历次失败实验和完整发布范围。ADR0047 和提案仍为
Proposed；不要把单次正确 binding、可读正文或成功调用当作发布批准。

用户当前方向：保留 Primary / Required 和现有 source block 粒度，包括
整条表格行。LLM 在选择 ref ID 的同一响应里生成尽量复述原文的精简正文；
不再要求其输出自由 quote 或精确 range。完整原文块、anchor、hash 和
adapter-rendered excerpt 继续作为来源和跨 revision 对应依据。生成正文
不参与匹配，不替代 Support Assessment 的证据。UI / `get_memory` 不强制
显示“LLM 整理”标签，但不得将其声明为逐字引用，仍需对应版本原文入口。

来源语法、富文本/宏/字段含义归对应 adapter；通用 prompt 不对某种文档
overfit。Required recall 尽力覆盖，不要求100%，已选项应准确、相关、非重复。
用户允许偶发生成正文错误，但未批准数值容错门槛；该指标独立于 claim / ref
语义门槛。禁止新增自审/语义兜底、剪枝坏候选、删 gold、缩小 batch 来追分。
升级重新 reprocess 可接受，不需强行兼容旧新 ref。图片另见 OSS issue497。

## 本轮如何验证

CF 已重新登录，当前无认证 blocker。线上实际 route 是
`sap/anthropic--claude-4.6-sonnet`，使用核对后的 deployed factory 和真实
SAP AI Core binding；凭据仅在进程内。执行代码来自目标工作树，**没有部署**。
EU12 dev / `memforge-cloud-service`，部署 OSS pin 仍是
`57f8b006962bf65a6430592b1a5002e15082c8c1`。

完整真实快照：Confluence native storage 70,981字符、Jira provider JSON
50,807字符、ADR0040 Markdown 18,445字符。与旧 source-first inventories
字节相同。生产 adapters → planner → `LlmBatchRunner` → structured client
→ selector resolution → 完整 assembly，只有 process-local prompt / schema
加入 display；不改产品 persistence、API 或 UI。

每种来源由现有 planner 规划为一个请求，不缩小 batch / budget / 输入。
共3逻辑调用、4个记录的 LiteLLM dispatch；Confluence 第一次连接断开，由
既有重试完成。没有新增自审、语义修复或候选剪枝。完整保留每次实际
messages / SAP placeholder / schema、raw returned body、失败类型、parsed
outputs、真实 source parts 和 telemetry。记录不独立证明 SDK 内部 HTTP
attempts 或服务端 constrained decoding。

本地10项机制检查通过：display/ref 结构、SAP 安全记录、实际 pipeline
原文与 display 分离，以及完整 native Confluence 上未变/移动/重复/修改/
外围条件改变的控制变体。这些不是一对真实连续 provider revisions。
294个文件和外部 runtime identity 在执行前后冻结验证通过；aggregate SHA:
`9960162d0001c86f375a89020a03836fda3448b4f9656f76433c3f818da69672`。

reviewer 准备阶段与最后推理前 protocol 有525字节差异，只增加实验观察
超时和 recorder attestation 范围；确切删除这两段可还原原 hash。语义门槛、
sources、inventories、rubrics 均未变，两个版本及独立检查保存。不是推理后
改验收标准。详见 `protocol-change-note.json`。

## 结果与剩余问题

82候选 / 90 refs 全部来源绑定检查成功。两位 agent 分别读完所有候选、ref、
display 和各自所有冻结 atoms（A135，B132含5 supplementary）。它们均失败。

| 来源 | Full core A | Full core B | Required relevant/distinct，两人相同 |
|---|---:|---:|---:|
| Confluence | 11/61（18.03%） | 59/62（95.16%） | 1/1 |
| Jira | 7/9（77.78%） | 7/10（70%） | 1/2 |
| ADR0040 | 44/65（67.69%） | 39/55（70.91%） | 2/5 |

Confluence 巨大的 recall 分歧来自原冻结 rubric 的独立可用含义：A要求每条
scenario Memory 带 page-wide early-stage 限定，45条因此只算 partial；B按
局部 scenario 条件/状态给分，另检查全局限定。不能误读为18%的 Memory 正确。
不要平均分、选择有利 lane 或在看到输出后删除限定。分歧不影响失败结论。

两人共同确认3条 Confluence claim 将 “We verify that” 写成
“verification confirms”，把目标强化为已确认结果：`Birch-confluence-0006`、
`-0014`、`-0040`。display 与原文保持目标语气，错误在 claim。A判正确 governing
Primary 但支持不完整；B也判这3个 Primary 无法直接支持更强 claim，并额外指出
`-0000` 的 Primary 仅引出列表、实际要求全在 Required（A0 / B4 major Primary）。

Jira遗漏 Open 等独立事实；一条 Required 重复 WCAG Primary。ADR一些 metadata /
Artifact / request成本 / non-goals 等只在 display 或原文中，没有进入 Memory。
其中3个 Required 是其他独立事实，与 migration102 claim 的支持无关。
用户的 Required best effort 容忍遗漏，不是容忍多余 false-positive 选项。

两人均未发现90段生成正文的实质忠实度错误；A列5处阅读摩擦，B列4处。
Confluence Primary 的完整 adapter view 中位664.5 / 最长1263字符，生成
display 中位305.5 / 最长898。ADR仍有1592字符正文；无固定字数 cap，未靠
硬截断省略重要条件。这是有限样本的方向证据，不是100%生成准确性证明。

本轮证明：**可读 display 与静态原文匹配可以分离**。当前失败项不是 ref
坐标绑定失败，而是 claim 模态、独立知识覆盖与 ref-role selection。
它不隔离 prompt / schema / 任务边界和模型推理各自的因果贡献，不证明
Sonnet 存在无法越过的能力上限，也不证明完整方案不存在。

## 交接后的边界

本轮不再改 prompt 逐样本重跑。下一位应先明确通用 extraction 任务/覆盖/
上下文合同如何落到实际 ReadingGroup/runner，再提出有可证伪假设的冻结
完整设计。保留失败结果、两位独立评分和分歧，不用 citation-only 内容冒充
Memory coverage；不要准入删掉应提取知识或新增模型兜底修补失败。

原文匹配唯一且未变时不会因生成 display 改写而改变结果；重复原文仍歧义，
整行内任何保留内容改变仍可标 Modified，外围条件改变仍需 Change Impact /
完整 incumbent Support。没有“所有未来大文档未变部分100%自动匹配”的证明。

发布合同尚未完成：全 A1–A15 审计、支持 source/variant 完整性、真实连续
revision、完整 incumbent Support/Impact 与 destructive safety、display
storage/API/UI 集成、SQLite/HANA parity 和物理 HANA 验收、PR、checked CF
deploy 与详细 smoke。不得部署当前失败实验。后续部署仍需使用批准的
`prepare-deploy.sh --push` 或 `--push-rendered` 流程。

## 文件与重放

私有证据根：
`/Users/i551096/Downloads/MemForge-Evidence-Validation-2026-10-02/private/focused-display-20261006`。
从 `protocol.md`、`freeze.json`、`execution-measurements.json`、`blinded/manifest.json`、
两条 lane 的 report / metrics / 全量 candidate/ref judgments / atom mappings 开始。
`pilot.py`、`test_pilot.py` 和冻结 prompt/schema 保留；不要覆盖已有 paid case。
credentials 未打包，CF可能再次过期。Claude CLI 使用 `claude`，不是
`claude-code`；本轮两位是 Codex agent，不是 Claude CLI 或在线 Sonnet judge。

目标 OSS：`/Users/i551096/.codex/worktrees/claim-evidence-contract/oss`；目标 Cloud：
`/Users/i551096/.codex/worktrees/claim-evidence-contract/memforge-cloud`。
两个目标工作树仍有原目标未提交修改；本轮没有新产品 Python 变更。
旧 ZIP `MemForge-Claim-Evidence-Handoff-20261005-213319.zip` 保留原样，新 ZIP
包含旧 ZIP、完整本轮证据、冻结 runtime 路径映射、最新文档和 tracked diff。
详见新 ZIP 的 README / MANIFEST；不要将打包成功视为完成实现或发布。
