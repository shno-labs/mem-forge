# Claim / Evidence extraction：当前完整交接

2026-10-05。**本轮验证完成，方案仍未通过；整个优化目标未完成。**
未部署、未重处理产品数据，两个目标工作树仍有未提交修改。本交接替代旧交接对
“当前状态”的描述，但保留旧设计、输出和报告；它不是新的执行 backlog。

## 从哪里继续

先读 [联合验证报告](2026-10-05-model-comparison-progress.md)、
[冻结对照协议](2026-10-05-model-comparison-protocol.md)、
[原设计 v7](../design/claim-evidence-extraction-contract.md) 和
[摘要引用提案](../design/claim-evidence-summary-citations.md)。ADR0047 仍为 Proposed。
原设计是现有实现基线，摘要提案是独立实验，二者都没有达到发布验收。
不要把新实验的 snapshot 绑定直接接到产品的 quote/TextView 契约中。

用户最新允许探索：不让 LLM 输出精确 range；ref 可以考虑可读语义摘要；
跨 revision 的 ref-to-ref 映射是否必要，可以重新评估。**这些是探索授权，
不是已接受的新生产架构。** 保留 Primary/Required，Required recall 不求100%，
但已选内容应相关、不重复，claim 必须保留重要条件和模态。禁止用准入删掉
有用 Memory、事后引用剪枝或新增自审/语义修复层使指标看起来通过。
不为某一文档/来源写专用 prompt；来源语法和字段含义放在各自 adapter。

已确认验收：零重大 claim/Primary 错误；每类有用知识完整覆盖至少95%；
已选 Required 相关且非重复至少95%。支持摘要里的其他独立事实不自动算已
提取为 Memory；缺失的核心条件不能靠引用补足。原子粒度、历史事件是否耐用等
分歧必须公开保留，不能在看到输出后删除 gold 或选择更有利的评审。
升级重新 reprocess 可接受，不必强行兼容旧新 ref；将来的来源、版本、
可读呈现和真实 Support 必须可核查。图片在 OSS issue497，仍不纳入本版。

## 本轮实际做了什么

调用实际 CF 应用 SAP AI Core 绑定和核对的 deployed factory，在线模型 route
为 `sap/anthropic--claude-4.6-sonnet`。本地执行目标 OSS 工作树代码，**不是新
代码已经部署到 CF**。目标 EU12 dev，应用 `memforge-cloud-service`；当前
部署 OSS pin 仍为 `57f8b006962bf65a6430592b1a5002e15082c8c1`。
登录曾过期，用户登录后已恢复；本轮没有未解决的认证 blocker。

完整真实输入：Confluence storage HTML 70,981字符；Jira 完整 provider JSON
50,807字符；repo ADR0040 Markdown 18,445字符。原始字节和 prompt 均保存。
这些是真实单个快照，不是已经认证的一对连续 provider revisions。

第一组8个逻辑请求（10个 provider attempts）：

| 来源 | A：catalog | B：可读表示上的自由 quote | C：native quote＋可读解释 |
|---|---|---|---|
| Confluence | 56候选，Primary全绑定 | 53候选，12个Primary quote找不到 | 三次attempt后300秒deadline失败 |
| Jira | 5候选，Primary全绑定 | 5候选，1个Primary找不到；有方法缺陷 | 1候选，Primary找不到 |
| ADR | 29候选，Primary全绑定 | 21候选，10个Primary找不到 | 未规划 |

两位 source-first 盲评审完170候选/186 refs。162个located/bound引用的真实
carrier 坐标均验证成功，24个missing Primary保持失败。没有一类/一组满足
全部固定门槛。Jira B 的实验 harness 用普通文本读入移除了32个CR，而
25/95 structural ranges仍基于原表示；它是被方法污染的描述性结果，不能
单独用于归因。原冻结文件本身未变。原实验未完整保存 malformed provider
正文，缺失材料不能靠猜测补上。

第二组独立“whole-snapshot generated summary”实验：
不选quote/range，不做跨版本ref mapping；程序只绑定真实保留快照。
预推理审查关闭5个记录/预算缺口，source/prompt/schema字节未改变；275个
冻结文件执行前后校验通过。三个完整请求、四个provider attempts，全部返回。

| 来源 | 候选 / refs | 耗时 | 完整覆盖 A | 完整覆盖 B |
|---|---|---|---|---|
| Confluence | 46 / 46 | 142.781秒 | 36/61（59.02%） | 37/62（59.68%） |
| Jira | 3 / 4 | 14.449秒 | 7/9（77.78%） | 6/10（60%） |
| ADR | 18 / 36 | 55.264秒 | 10/65（15.38%） | 9/55（16.36%） |

67候选、86 refs全部被两人逐条审阅，86/86 snapshot byte/hash绑定正确。
Required：Jira1/1；ADR两人都判16/18（88.89%）；Confluence未选，不因少选扣分。
三类都未通过验收。覆盖率不是“正确 claim 的比例”；不能误读成59%的claim正确。

共同实质错误：ADR claim/Primary将 Document 指针写在 Unit revision之前，
原文的序列是raw→revision→指针；一个 Required 错称只有确实commit新revision
才保存raw，原文允许后续sync已保存但尚未commit的input；Confluence Primary
擅加新correction的next-period归属。评审A还将若干省略paid/released/retro
条件和清理模糊chronology的情况判major；评审B的部分严重性较低。完整分歧保留。
不少ADR独立知识只出现在support notes，未进入Memory claim，这也是覆盖失败。

**有界因果结论：** quote精确定位确实带来额外失败点，但去掉quote与ref mapping
后仍有语义和覆盖错误。所以它们不是这些错误的必要原因，移除它们不足以使
当前方案通过。这不证明每个未来设计必须有精确quote，也不证明LLM或static
code在所有架构下都有不可逾越的上限。没有做单一变量、人口级准确率估计。

## 超时和 batch 的准确含义

现有实现并非没有batch：`plan_extraction_requests`按ReadingGroup打包，
incumbent Change Impact按Memory ID打包。目标快照的正常planner把Confluence
79个ReadingGroups和Jira95个ReadingGroups各打包为一个fit请求；它不是每个
group必然一个模型调用。输入fit不保证输出schema有效或在deadline内完成。
A走该生产planner/runner；B/C与摘要组是明确的完整文档机制实验，直接调用
structured client，**没有调用生产runner的分拆/业务恢复路径**。因此原C超时
不能用来声称生产batch无效，也不能把这几组称为已验证的生产全流程。

原C Confluence首轮 `memory_type` enum错误，第二轮JSON无效，第三轮用完
300秒；前两轮各14,630/14,301输出tokens，均stop，未达到32,768上限。
摘要组Confluence首轮JSON可解析，但31候选中13个类型是schema不接受的
`requirement`；JSON-text fallback随后返回46个schema-valid候选。原始两次
正文均保存，没有coerce类型。现有client的格式恢复/重试是transport行为，
不是新增模型自审；也不能宣称“零输出格式修复”。申请strict schema transport
不独立证明SAP链路实际执行了constrained decoding；实际违规已被本地校验发现。

未提高budget、截断文档、调小batch、分schema或裁剪候选。任何下一轮batch
重设计先按AGENTS.md解释schema/transport/ownership/execution-boundary的
替代方案与取舍，获得确认，不能仅为绕开失败路径而拆小。

## 版本与存储边界

`SourceUnitRevision`目前是append-only manifest，不含完整body。
`SourceUnitInput`目前只保留latest raw input，旧URI可能被覆盖。
历史Observation是不可变的，但不是每种adapter都有完整原始payload；历史
Confluence转换后的Markdown不能假装原生storage XML。给摘要贴旧revision ID
但读到最新版不构成可靠历史citation。任何snapshot方案必须复用确实完整的
既有表示，或明确保留准确的授权输入；不能每个ref复制整篇文档，也不能
扩大managed session原始对话收集的隐私范围。

来源真实性、展示摘要准确性、跨版本知识延续是三个不同任务。摘要字符串
无需成为跨版本identity；也不能用semantic similarity伪造provenance。
已有同pinned revision的61 Memory/64 parts重绑证明不是跨版本证明。
controlled insertion/move/paraphrase probe不是真实连续provider revision。
新revision上的完整incumbent固定claim Support评估、原子事务、authority、
unknown/absence/contradiction及destructive safety仍必须独立满足。

14个既有线上Jev分类probe的完整记录保留：native 6个问题精确三分类5/6，
4个人为改错claim均未被当supported，但cohort很小且有边界分歧。
这些不是真实67候选的完整classifier验收，不证明提取覆盖或safe retirement。
本次没有追加Jev兜底、重写坏claim或silent candidate rejection。

## 实现、检查与仍未验收的内容

之前实现地图见 [旧完整交接](2026-10-04-claim-evidence-handoff.md)，本轮没有
修改产品提取代码去追求新分数。最新已记录确定性检查：OSS868 passed；Cloud
seams524 passed（fixture/SQLite bridge，不是物理HANA）；详见
[Support修正](2026-10-04-claim-evidence-support-correction.md)。这些检查不证明
新方案语义通过。本轮新增的是隔离实验、预审、盲评、设计/ADR澄清和交接。

下一步应先确定来源到claim的任务边界和覆盖定义如何落到现有实现，再写新的
可证伪完整设计；不能把“换成摘要”或“再加一个review/repair模型”直接当解法。
现有adapter/ReadingGroup/citation机制和完全model-led机制的真实优缺点均有
对照证据。不要再在本轮冻结prompt或gold上逐样本优化，也不要替换failed结果。
如果采用新generation/schema/reading策略，另建实验身份，先冻结设计和完整
transport，再用真实文档与独立source-first盲评验证。

未完成的发布合同仍包括：全A1–A15审计、支持来源/variant输入完整性、真实
连续revision和线上完整incumbent Support/Impact、generic tool/UI行为、SQLite/
HANA parity和物理HANA验收、PR、checked CF deploy与详细smoke。本轮没有
accepted发布设计，也没有完成这些gate；不要部署这份失败实验。

## 精确文件、工作树与证据

OSS：`/Users/i551096/.codex/worktrees/claim-evidence-contract/oss`
`codex/claim-evidence-contract`，HEAD `57f8b006962bf65a6430592b1a5002e15082c8c1`。
Cloud：`/Users/i551096/.codex/worktrees/claim-evidence-contract/memforge-cloud`
`codex/claim-evidence-contract-cloud`，HEAD `e1e8ec82f00ed327abb320ce1a4a88ac9084dee7`。
两个工作树都未提交；本轮没有创建或合并PR。原工作目录的无关uv.lock/research
改动不能reset/stash。恢复修改必须同时包含tracked diff和untracked文件。
开始新goal/refactor及merge前按各repo AGENTS.md处理updated main/新分支和
stale PR；旧draft PR不是当前目标验收证据。

私有证据根：
`/Users/i551096/Downloads/MemForge-Evidence-Validation-2026-10-02/private/model-comparison-20261005`

- `freeze.json` / `execution-manifest.json`：原8请求、真实factory/budget/telemetry。
- `methodological-audit.json`：原试验的方法限制，包括Jira B换行/range drift。
- `blinded/` 与 `review-{a,b}/output-review/`：原全量匿名评审和carrier验证。
- `summary-citations/freeze.json`：后续3请求；aggregate
  `b658a2ef7f30dbd10f0b28e0258830c6756139a5be2e2663ff18dcc4b697c2a6`。
- `summary-citations/pre-inference-method-final-audit.json`：SHA
  `a52fa5b892ad7efbb9043b0c9b105c4f2071a5556e34c02016111e74a38a5c64`。
- `summary-citations/{confluence,jira,adr0040}/`：真实原文、prompt、provider正文、
  parsed response、全部candidates、status与telemetry，包括失败attempt。
- `review-{a,b}/output-review-summary/`：新全量逐candidate/ref/atom评审和hash。
- `current-handoff-manifest.json`：最新状态；旧auth failure保留为历史，不是当前blocker。

上述记录是在本机隔离验证目录，真实来源文本不复制到repo研究报告或GitHub。
交接包保留目标tracked diff、untracked文件、实验源/输出、评审与冻结依赖快照，
并带hash清单；没有CF binding/env credentials。原prompt/源码里的绝对路径
是执行证据。跨机器恢复不能静默改路径仍宣称相同freeze；本机交接可直接继续
在这些工作树检查。Claude CLI使用`claude`，不要假设`claude-code`或未核对的
`/opt/homebrew/bin/claude`存在。
