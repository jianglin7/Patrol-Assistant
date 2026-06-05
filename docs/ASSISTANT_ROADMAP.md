# xunke 小助手能力提升路线图

本文档基于当前项目代码、`AGENTS.md`、能力边界分析文档、任务拆解文档和项目分析文档整理，用于指导后续将 `xunke` 小助手从“能回答部分巡课问题”提升为“稳定、可控、可解释、可扩展的高校巡课数据助手”。

## 1. 总体目标

本阶段总体目标是让小助手具备以下四类能力：

- 稳定：高频巡课、预警、指标解释和简报问题能够稳定命中正确链路，LLM、数据库或模板失败时有清晰兜底。
- 可控：所有数据查询走白名单 SQL、业务函数或受控语义规划，不开放自由 SQL，不跨租户，不泄露敏感信息。
- 可解释：回答能说明时间范围、统计口径、关键指标和无数据原因，避免把 LLM 生成内容当成不可追溯结论。
- 可扩展：后续新增 SQL 模板、tool functions、语义资源、评测集、图表、RAG、推送等能力时，有清晰分层和验收标准。

## 2. 当前现状摘要

当前主体项目是 `query_service`，后端使用 FastAPI + Uvicorn，配置通过 `pydantic-settings` 从环境变量和 `.env` 加载，数据库访问通过 PyMySQL 直连 MySQL。小助手前端页面主要内嵌在 `query_service/app/main.py`，LLM 采用 OpenAI-compatible `/chat/completions` 调用方式。

当前已具备的能力包括：

- SQL 白名单模板查询：`/api/query/execute`，核心实现位于 `query_service/app/service.py`、`query_service/app/registry.py`、`query_service/app/builtin_templates.py` 和 `query_service/sql/seed_query_templates.sql`。
- 小助手问答：`/api/assistant/ask`、`/api/assistant/ask-stream`，核心链路位于 `query_service/app/main.py` 和 `query_service/app/patrol_api.py`。
- 语义规划：`/api/assistant/plan`，核心实现位于 `query_service/app/semantic_planner.py`、`query_service/app/semantic_executor.py`、`query_service/app/semantic_report.py` 和 `query_service/resources/assistant_semantic/`。
- 巡课简报：实时巡课、今日巡课、重点关注课堂、活力较高课堂等，主要位于 `query_service/app/patrol_api.py`。
- 预警查询：实时预警、今日预警、趋势、处置闭环、教师风险、预警视频线索等，主要位于 `query_service/app/patrol_api.py`。
- 本地规则回答和指标解释：`ASSISTANT_SUGGESTED_QUESTIONS`、`METRIC_KNOWLEDGE_BASE`、`_lookup_local_assistant_answer()`、`_lookup_metric_kb_answer()`。
- Trace 调试：`query_service/app/assistant_trace.py` 以及 `main.py` 中的 debug trace 接口。

当前主要限制包括：

- 未发现明确的自动化测试体系、`pytest.ini` 或 `pyproject.toml`，测试与回归方式待确认。
- `rag/jy_application_digital_patrol_rag.jsonl` 看起来是表/字段级检索资料，但代码中未确认已接入运行链路。
- `patrol_api.py` 承载大量业务、问答、LLM、SQL 和兜底逻辑，后续维护风险较高。
- 指标口径散落在本地知识库、SQL 模板、语义资源和 LLM prompt 中，存在口径分叉风险。
- 当前未看到统一 logging 配置；trace 和异常信息需要持续检查脱敏风险。
- 外部鉴权、网关、Redis、Elasticsearch、向量数据库是否存在：待确认。

## 3. 分阶段路线图

### Phase 0：基线整理与计划确认

- 阶段目标：把已有项目分析、能力边界、任务拆解和本路线图统一成后续开发基线。
- 主要任务：
  - 确认 `AGENTS.md`、能力边界文档、任务拆解文档、本路线图之间的规则一致。
  - 确认第一阶段只围绕稳定性、边界、追问、兜底和验证清单展开。
  - 整理高频问题样例，标注当前是否能稳定回答。
  - 标记所有“待确认”项，避免后续凭空假设。
- 涉及文件：
  - `AGENTS.md`
  - `小助手能力边界与提升方案分析报告.md`
  - `小助手能力提升任务拆解清单.md`
  - `xunke小助手项目分析报告.md`
  - `docs/ASSISTANT_ROADMAP.md`
- 预期收益：统一团队对能力边界、开发顺序和安全限制的理解。
- 风险点：文档和代码不同步；业务口径未确认导致后续返工。
- 验收标准：
  - 路线图评审通过。
  - 第一阶段任务范围明确，不包含大重构、生产部署、数据库写操作。
  - 所有待确认项有明确责任方或后续确认方式。
- 是否需要业务确认：需要。

### Phase 1：稳定性与边界优化

- 阶段目标：解决“问不准、答不稳、边界不清、兜底不足”的问题。
- 主要任务：
  - 检查 trace、异常、LLM 失败、数据库失败时的敏感信息输出风险。
  - 建立 SQL 租户隔离与逻辑删除检查清单，重点关注 `tenant_id`、`tenant_org_code`、`delete_flag`、`recycle_sign` 等条件。
  - 梳理高频模糊问法，补充追问规则和推荐追问话术。
  - 统一无数据、暂不支持、LLM 失败、模板缺失、数据库异常的用户侧兜底文案。
  - 建立最小手工验证清单，覆盖 assistant 问答、流式问答、语义规划、模板查询、巡课简报和预警查询。
- 涉及文件：
  - `query_service/app/main.py`
  - `query_service/app/patrol_api.py`
  - `query_service/app/service.py`
  - `query_service/app/assistant_trace.py`
  - `query_service/app/semantic_executor.py`
  - `query_service/app/semantic_report.py`
  - `query_service/app/builtin_templates.py`
  - `query_service/sql/seed_query_templates.sql`
- 预期收益：减少误答、漏答、敏感信息泄露、跨租户查询和不可解释失败。
- 风险点：追问规则过严会降低回答效率；错误兜底过泛会降低排障价值。
- 验收标准：
  - 高频模糊问题能触发追问或明确边界提示。
  - 业务查询失败时不暴露堆栈、密钥、token、数据库密码或完整连接串。
  - 新增或修改 SQL 前能说明涉及表、关联关系、租户条件、逻辑删除条件和影响范围。
  - 最小验证清单可重复执行，且不包含数据库写操作。
- 是否需要业务确认：部分需要，特别是追问话术、指标口径和错误文案。

#### Phase 1 当前进展更新

已完成能力：

- 已完成“小助手问题边界识别与模糊问题追问兜底”。
- 已增加安全边界规则：拒绝读取 `.env`、密钥、token、数据库密码、API Key、完整数据库连接串；拒绝删除、修改、清库；拒绝跨租户、绕过权限；真实推送类问题提示先做预览或权限确认。
- 已完成真正流式输出初步接入：固定话术支持通过 NDJSON `delta` 输出；LLM 总结尝试使用 OpenAI-compatible `/chat/completions stream=true`；前端收到 `delta` 后立即 append。
- 已修正真实推送安全边界误判，避免“帮我真实推送预警”进入模糊追问。
- 已生成最小评测问题集文档：`docs/ASSISTANT_EVAL_CASES.md`，包含 64 条回归问题。

遗留问题：

- 64 条评测问题尚未实际执行，仍需记录每条问题的命中分支、追问/拒答、数据查询、流式输出和通过情况。
- P0 安全专项 review 尚未完成，trace/debug/异常响应仍需专项检查。
- SQL 租户隔离与逻辑删除全量审计尚未完成，核心 SQL 中 `tenant_id`、`tenant_org_code`、`recycle_sign` 等过滤要求需逐项确认。
- LLM 失败降级场景尚未真实回归，包括超时、空响应、格式异常和 streaming 失败等场景。
- 流式输出体验不稳定，部分回答仍可能大段输出。
- 固定话术虽然走 `delta`，但因为没有节流，可能被快速塞入队列并一次性输出。
- 上游 LLM 即使 `stream=true`，也可能返回较大的 delta。
- 后端目前没有对 delta 统一做二次切分和节流。
- 部分业务分支仍是内部完整生成后，再由外层输出。
- 前端不是主要问题，主要问题在后端 delta 产生节奏、queue drain 逻辑或上游代理缓冲。

当前处理结论：

- 风险等级：中。
- 影响范围：用户体验。
- 是否影响主流程正确性：暂未发现。
- 是否阻塞下一阶段：不阻塞。
- 是否立即修复：否，进入待办问题池。
- 暂不继续扩大流式改造范围。
- 下一步建议进入“P0 回归执行与结果记录”，优先实际执行 `docs/ASSISTANT_EVAL_CASES.md` 中 64 条问题并形成失败项清单。

### Phase 2：常用能力补齐

- 阶段目标：补齐领导、督导、教学管理人员高频使用场景，提高命中率和回答完整度。
- 主要任务：
  - 补充常见指标解释和指标别名。
  - 补充高频 SQL 白名单模板，如学院巡课排名、低到课率课堂 Top、课程/教师/教室维度对比、近 7 天预警趋势。
  - 完善 `resources/assistant_semantic/` 中的意图、指标、模板映射和错误码。
  - 优化推荐问题，确保推荐问题尽量命中当前稳定链路。
  - 梳理并统一回答结构：结论、关键数据、建议、统计口径、无数据说明。
- 涉及文件：
  - `query_service/app/patrol_api.py`
  - `query_service/app/builtin_templates.py`
  - `query_service/app/service.py`
  - `query_service/app/registry.py`
  - `query_service/sql/seed_query_templates.sql`
  - `query_service/resources/assistant_semantic/intents.json`
  - `query_service/resources/assistant_semantic/metrics.json`
  - `query_service/resources/assistant_semantic/templates.json`
  - `query_service/resources/assistant_semantic/error_codes.json`
- 预期收益：用户能用自然语言稳定查询更多巡课和预警问题。
- 风险点：模板 ID、参数名、指标名、接口返回结构不一致；新增 SQL 可能遗漏租户隔离或逻辑删除条件。
- 验收标准：
  - 每个新增能力都有用户问法、模板或业务函数、验证方式。
  - 新增 SQL 只读、参数化，并通过租户隔离与逻辑删除检查。
  - 高频推荐问题能够命中规则分桶、业务函数或语义规划链路。
- 是否需要业务确认：需要，尤其是指标口径、排行维度和默认时间范围。

### Phase 3：评测与可观测性

- 阶段目标：建立问题集、验收标准、trace 日志和回归检查，让后续迭代有可重复验证基础。
- 主要任务：
  - 建立问答评测集，覆盖巡课、预警、趋势、Top、指标解释、追问、无数据和失败兜底。
  - 建立 SQL 模板检查清单或脚本，检查只读、参数、租户隔离、逻辑删除、字段别名和 MySQL 语法。
  - 规范 trace 字段，记录节点耗时、分桶结果、澄清结果、模板命中、LLM 调用结果，同时避免敏感信息。
  - 为核心接口补充最小自动化或半自动化验证方式。
  - 定义回归通过标准，减少靠人工感觉判断回答质量。
- 涉及文件：
  - `query_service/app/assistant_trace.py`
  - `query_service/app/main.py`
  - `query_service/app/patrol_api.py`
  - `query_service/app/service.py`
  - `query_service/app/semantic_executor.py`
  - `query_service/app/semantic_report.py`
  - 后续测试目录或验证文档：待确认。
- 预期收益：降低回归风险，提高问题定位效率。
- 风险点：缺少稳定测试数据；真实数据库和 LLM 环境依赖导致评测不可复现。
- 验收标准：
  - 至少形成一套 50 条左右的高频问题评测集。
  - 每条评测问题标注期望链路、期望能力、是否依赖数据库/LLM。
  - trace 输出不含敏感信息，且能定位主要耗时和失败节点。
- 是否需要业务确认：需要，评测问题和期望回答需要业务共同确认。

### Phase 4：结构优化

- 阶段目标：逐步拆分大文件，抽象 service、tool function 和语义规划层，降低维护成本。
- 主要任务：
  - 将 `patrol_api.py` 中的巡课、预警、视频/设备、LLM、上下文、澄清、路由分桶逻辑逐步拆分。
  - 抽象稳定的 tool functions 层，统一工具输入、输出、错误分类和 trace。
  - 将指标字典、指标别名、指标口径从代码散点逐步收敛到统一资源。
  - 保持现有 API URL、请求参数和响应结构兼容。
  - 在重构前后使用评测集和最小验证清单做回归。
- 涉及文件：
  - `query_service/app/patrol_api.py`
  - `query_service/app/main.py`
  - `query_service/app/service.py`
  - `query_service/app/semantic_planner.py`
  - `query_service/app/semantic_executor.py`
  - `query_service/app/semantic_report.py`
  - 后续新增 service/tool 模块：待确认。
- 预期收益：降低单文件复杂度，让新增能力更容易复用和测试。
- 风险点：大文件拆分容易引入行为变化；导入关系和兜底逻辑可能被破坏。
- 验收标准：
  - 拆分前后核心接口行为保持兼容。
  - 高频评测集通过。
  - 每次拆分范围小、可回滚，并说明影响接口和验证方式。
- 是否需要业务确认：通常不需要；涉及口径变化时需要。

### Phase 5：产品能力增强

- 阶段目标：在稳定基线之上增强简报、图表、预警推送、多轮分析、RAG 等产品能力。
- 主要任务：
  - 支持结构化简报和图表数据返回。
  - 支持每日/每周教学运行报告。
  - 支持更完整的多轮分析，如先总览、再下钻学院/课程/教师。
  - 设计 RAG 接入方案，确认检索入口、索引构建、embedding 模型、向量库或 ES、召回数量、过滤条件和结果入 prompt 方式。
  - 从预警推送预览逐步扩展到真实推送，但必须补齐权限、审计、回滚和灰度机制。
  - 探索可配置 Agent 编排，但必须继续保留白名单查询、安全边界和兜底逻辑。
- 涉及文件：
  - `query_service/app/main.py`
  - `query_service/app/patrol_api.py`
  - `query_service/app/semantic_planner.py`
  - `query_service/app/semantic_executor.py`
  - `query_service/app/semantic_report.py`
  - `query_service/resources/assistant_semantic/`
  - `rag/jy_application_digital_patrol_rag.jsonl`
  - 未来前端、消息平台、检索服务模块：待确认。
- 预期收益：从查询助手升级为可交互、可分析、可运营的巡课数据助手。
- 风险点：RAG、推送、多 Agent、图表结构化返回都可能扩大架构和安全面；不适合在基线未稳时直接推进。
- 验收标准：
  - 每个增强能力都有灰度范围、权限边界、验收问题集和回滚方案。
  - RAG 接入前先完成设计评审，不默认把 `rag/` 视为生产链路。
  - 推送能力必须先支持预览、确认和审计。
- 是否需要业务确认：需要。

## 4. P0 / P1 / P2 / P3 任务池

| 优先级 | 任务名称 | 目标 | 涉及文件/模块 | 实现难度 | 风险 | 验收方式 |
| --- | ---- | -- | ------- | ---- | -- | ---- |
| P0 | 敏感信息与 trace 脱敏检查 | 避免 `.env`、API Key、数据库密码、完整连接串进入日志、trace 或响应 | `assistant_trace.py`、`main.py`、`patrol_api.py`、`semantic_report.py` | 低 | 过度脱敏影响排障 | 构造 LLM/DB/模板失败场景，确认用户响应和 trace 不含敏感信息 |
| P0 | SQL 租户隔离与逻辑删除检查清单 | 降低跨租户、脏数据和口径错误风险 | `service.py`、`builtin_templates.py`、`patrol_api.py`、`seed_query_templates.sql` | 中 | 不同表字段含义需确认 | 每条新增/修改 SQL 说明表、JOIN、过滤、租户、逻辑删除、影响范围 |
| P0 | LLM 失败降级兜底统一 | LLM 不可用时业务查询仍能给出可理解结果 | `patrol_api.py`、`semantic_report.py`、`config.py` | 低到中 | 兜底文案过泛 | 模拟 LLM 超时/空响应/JSON 失败，接口不崩溃且有友好提示 |
| P0 | 最小接口验证清单 | 给后续改动提供基础回归依据 | `main.py`、`patrol_api.py`、`service.py`、`semantic_*` | 低 | 依赖现场 DB/LLM | 验证清单覆盖健康检查、问答、流式、plan、query、巡课、预警 |
| P0 | P0 回归执行与结果记录 | 把 64 条评测问题从文档清单变成实际回归结果 | `docs/ASSISTANT_EVAL_CASES.md`、assistant 接口、trace/debug 页面 | 低到中 | 依赖现场 DB/LLM，失败项需分类判断 | 每条问题记录命中分支、追问/拒答、是否查询数据、是否流式、是否通过，并产出失败项清单 |
| P0 | 问答能力边界提示 | 对暂不支持、问题模糊、敏感请求给出明确边界 | `patrol_api.py`、assistant 页面文案待确认 | 低 | 文案过硬影响体验 | 模糊问题、越权问题、写操作问题均不会直接误答 |
| P1 | 流式输出体验优化，方案待定 | 改善用户侧“大段一下子返回”的体验 | `main.py`、`patrol_api.py`、上游 LLM/代理配置待确认 | 中 | 容易扩大流式改造范围和回归面 | 先建立 streaming smoke 测试，再决定是否统一切分、节流和加 no-buffering headers |
| P1 | 追问逻辑优化 | 缺时间、对象、业务域、指标时先追问 | `patrol_api.py` | 中 | 追问过多 | 高频模糊问题能触发明确追问 |
| P1 | 指标解释与指标别名补齐 | 提高指标问答稳定性和口径一致性 | `patrol_api.py`、`metrics.json` | 中 | 业务口径不一致 | 到课率、抬头率、前排满座率、活动指数、巡查覆盖率、预警占比可稳定解释 |
| P1 | 回答结构统一 | 让业务回答包含结论、关键数据、建议和口径 | `patrol_api.py`、`semantic_report.py` | 中 | 过度模板化 | 高频问题回答结构稳定，无数据提示清晰 |
| P1 | 推荐问题优化 | 引导用户点击稳定支持的问题 | `main.py`、`patrol_api.py` | 低 | 推荐问题超出能力边界 | 推荐问题均能命中规则、模板或语义规划 |
| P1 | 多轮上下文边界增强 | 简单追问可继承条件，跨域追问不误继承 | `patrol_api.py` | 中 | 多实例内存上下文不共享 | “改成 Top3”“只看某学院”“取消筛选”能稳定处理 |
| P2 | 高频 SQL 模板补齐 | 扩展学院、课程、教师、教室、趋势、排行查询 | `builtin_templates.py`、`seed_query_templates.sql`、`templates.json` | 中 | SQL 口径和租户隔离风险 | 新模板只读、参数化、可执行，并有样例问法 |
| P2 | tool functions 分层 | 把查询工具从路由/问答逻辑中抽出来 | `patrol_api.py`、未来 service/tool 模块 | 中高 | 拆分引入行为变化 | 核心接口回归通过，调用链更清晰 |
| P2 | 语义规划资源完善 | 提高自然语言到模板的命中率 | `semantic_planner.py`、`resources/assistant_semantic/` | 中 | 模板 ID/参数不一致 | plan 输出能稳定映射到已有模板 |
| P2 | RAG 接入方案设计 | 明确 `rag/` 是否、如何进入生产链路 | `rag/`、未来检索模块、LLM prompt | 高 | 检索污染、权限和性能风险 | 先完成设计评审，不直接接入生产 |
| P2 | 图表与结构化报表 | 支持趋势、排行、分布的可视化表达 | `main.py`、`patrol_api.py`、前端模块待确认 | 中高 | 接口结构变化 | 新增结构化字段保持兼容，前端可渲染 |
| P3 | 拆分 `patrol_api.py` | 降低维护复杂度 | `patrol_api.py`、新增模块待确认 | 高 | 破坏现有兜底链路 | 分批拆分，每批有回归和回滚说明 |
| P3 | 统一指标字典 | 统一代码、模板、语义资源、文档口径 | `metrics.json`、`patrol_api.py`、SQL 模板、文档 | 中高 | 口径需业务确认 | 指标名、别名、公式、来源表、默认时间范围可追溯 |
| P3 | 自动化测试与问答评测 | 支撑长期迭代 | tests 目录待确认、验证脚本待确认 | 中 | 缺测试数据 | 评测集可重复执行并输出通过/失败 |
| P3 | 可观测性平台接入 | 追踪 LLM、DB、SQL、意图、耗时和失败 | `assistant_trace.py`、日志模块待确认 | 高 | 日志敏感信息风险 | 指标和日志脱敏，能定位失败节点 |
| P3 | 可配置 Agent 编排 | 支持复杂多轮任务和工具组合 | 未来 agent 模块、semantic/tool 层 | 高 | 安全边界扩大 | 仍保持白名单工具和权限边界 |

## 5. 第一阶段建议只做什么

第一个 1 到 2 周建议只落地以下 7 个任务，避免过早大改架构：

1. 整理最小问答验收集  
   覆盖巡课汇总、实时巡课、今日巡课、预警汇总、趋势、Top、指标解释、模糊追问、越权拒绝、失败兜底。验收方式是每条问题标明期望链路、期望结果类型和依赖条件。

2. 整理 SQL 安全检查清单  
   明确新增或修改 SQL 必查：MySQL 语法、参数化、字段别名、租户条件、逻辑删除条件、WHERE 完整性、跨租户风险、影响接口。验收方式是对现有高频模板抽样走清单。

3. 检查 trace 和异常脱敏边界  
   只检查和小范围修正 trace/异常输出，不改变业务逻辑。验收方式是确认 debug trace 和用户侧错误不展示密钥、token、数据库密码、API Key 或完整连接串。

4. 优化模糊问题追问规则  
   优先处理“情况怎么样”“哪个最多”“某老师/某课程风险”“今天怎么样”等高频模糊问法。验收方式是评测集中模糊问题不再直接误答。

5. 统一失败和无数据兜底文案  
   区分无数据、暂不支持、问题不清楚、LLM 失败、数据库失败、模板缺失。验收方式是模拟或构造典型场景，确认提示可理解且不泄露内部细节。

6. 补齐核心指标解释和别名  
   先覆盖到课率、抬头率、前排满座率、课堂活动指数、AI 巡查覆盖率、预警课堂占比、风险等级。验收方式是用户问法含别名时也能命中指标解释。

7. 优化推荐问题为“稳定可答”集合  
   删除或调整当前不能稳定回答的问题，优先推荐能命中规则分桶、白名单模板或明确业务函数的问题。验收方式是推荐问题逐条可验证。

这些任务都应保持小范围改动，优先复用 `patrol_api.py`、`service.py`、`semantic_*` 和现有 JSON 语义资源，不新增大型依赖，不改变现有接口协议。

## 6. 暂不建议做的事情

- 暂不建议大范围重构 `patrol_api.py`：当前问答链路、业务查询和兜底逻辑耦合较深，应先建立评测集和验证清单。
- 暂不建议继续扩大流式改造范围：当前流式问题主要影响用户体验，暂未发现影响主流程正确性；应先建立 streaming smoke 测试和回归清单，再决定是否改 `main.py` 输出包装层、no-buffering headers 或更多业务分支。
- 暂不建议直接接入复杂 RAG：当前只看到 `rag/jy_application_digital_patrol_rag.jsonl`，未确认生产链路，接入前需要设计检索入口、索引、embedding、权限和过滤规则。
- 暂不建议直接改数据库结构：当前任务重点是查询助手稳定性，结构变更需要 DBA、业务和回滚方案。
- 暂不建议直接做自动推送到生产环境：推送涉及权限、审计、误发、撤回和灰度，当前更适合先完善推送预览。
- 暂不建议开放自由 SQL 或自由 Text2SQL：会绕过白名单、租户隔离和只读保护，安全风险高。
- 暂不建议直接上多 Agent 编排：当前基础能力、评测和工具边界尚未完全稳定，过早引入会扩大不可控面。
- 暂不建议新增大型依赖或基础设施：Redis、ES、向量库、观测平台等需要先确认部署环境和运维责任。
- 暂不建议改变现有接口 URL、请求参数和响应结构：当前页面和外部集成可能依赖现有协议。

## 7. 下一步建议

最推荐的下一步任务是：P0 回归执行与结果记录。

建议下一轮 Codex 任务可以直接写成：

```text
请基于 docs/ASSISTANT_EVAL_CASES.md 执行 64 条小助手回归问题，并新增或更新一份回归结果记录文档。
每条问题记录：用户问法、实际命中分支、是否追问、是否拒答、是否查询数据、是否流式输出、是否通过、失败原因和建议修复方向。
执行过程中不要修改业务代码，不执行数据库写操作，不读取或输出 .env、密钥、token、数据库密码、API Key 或完整连接串。
完成后形成失败项清单，再根据失败项决定下一轮修复任务。
```

这个任务应优先做的原因：

- 评测集文档已经存在，下一步应确认真实执行结果，而不是继续补文档。
- 它能尽快暴露当前 P0 改动是否破坏主链路、安全边界、追问逻辑或流式兼容。
- 它不需要改业务代码，风险低，但能为后续修复提供清晰失败项。
- 它能帮助业务人员、后端开发、DBA 和产品一起确认哪些问题当前已经稳定，哪些问题应进入下一轮修复。
