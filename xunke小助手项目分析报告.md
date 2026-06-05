# xunke 小助手项目分析报告

本文档基于当前 `xunke` 项目真实代码和已有 `AGENTS.md` 整理，用于项目交接、后续开发和代码审查。本文档不读取、不展示 `.env`、密钥、token、数据库密码、API Key 或完整数据库连接串。

## 1. 项目概览

`xunke` 当前主体是 `query_service`，一个面向 AI 巡课/课堂预警场景的轻量查询与问答后端。

核心职责包括：

- 白名单 SQL 模板查询。
- 租户隔离。
- 参数校验和默认值补齐。
- 查询审计日志。
- AI 小助手页面与问答接口。
- 巡课、预警、趋势、视频线索等业务简报。
- 语义规划与 LLM 总结。

## 2. 目录结构说明

主要目录如下：

- `query_service/`：当前主要维护对象。
- `query_service/app/`：FastAPI 应用源码，包含路由、配置、数据库访问、业务查询、问答链路、语义规划、trace。
- `query_service/sql/`：控制表、模板种子、模板 ID 迁移 SQL。
- `query_service/resources/assistant_semantic/`：语义规划配置，包括意图、指标、模板映射、错误码。
- `query_service/scripts/`：离线镜像构建、内置模板入库脚本。
- `query_service/assets/`：助手头像、用户头像、公司 logo。
- `rag/`：数据库结构/语义检索资料 JSONL。
- `offline_bundle/`：看起来是 `query_service` 的离线部署副本，是否继续维护待确认。
- 根目录：存在较大的 SQL dump、zip、Docker 镜像 tar 文件，默认不要修改。

## 3. 技术栈判断

已确认技术栈：

- 后端框架：FastAPI。
- 运行服务：Uvicorn。
- Python 依赖：`fastapi`、`uvicorn[standard]`、`pydantic`、`pydantic-settings`、`PyMySQL`。
- 数据库：MySQL，通过 PyMySQL 直连。
- 配置：`pydantic-settings` 从环境变量与 `.env` 加载。
- AI 调用：OpenAI-compatible `/chat/completions`，使用 Python 标准库 `urllib.request`。
- 前端页面：`main.py` 内嵌 HTML/CSS/原生 JS。
- 部署：Dockerfile + ARM64 离线镜像构建脚本。

待确认：

- 是否存在 Redis。
- 是否存在 Elasticsearch。
- 是否存在向量数据库。
- 是否存在外部鉴权或网关。
- 当前 RAG JSONL 是否已接入运行链路。

## 4. 启动入口与运行方式

本地安装依赖：

```bash
cd query_service
pip install -r requirements.txt
```

本地启动：

```bash
cd query_service
uvicorn app.main:app --reload --port 8000
```

Dockerfile 启动入口：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

FastAPI 应用对象位于：

- `query_service/app/main.py`

## 5. API 路由结构

主要路由集中在 `query_service/app/main.py`。

主要接口类型：

- `GET /health`：健康检查。
- `POST /api/query/execute`：SQL 模板查询。
- `POST /api/playground/ask`：playground 问答。
- `POST /api/playground/ask-stream`：playground 流式问答。
- `POST /api/assistant/ask`：assistant 普通问答。
- `POST /api/assistant/ask-stream`：assistant 流式问答。
- `POST /api/assistant/plan`：语义规划调试/执行。
- `GET /api/assistant/patrol/realtime-brief`：实时巡课简报。
- `GET /api/assistant/patrol/daily-brief`：今日巡课简报。
- `GET /api/assistant/warning/realtime`：实时预警。
- `GET /api/assistant/warning/daily`：今日预警。
- `POST /api/assistant/warning/push-preview`：预警推送预览。
- `GET /api/assistant/video/points`：视频点位。
- `GET /assistant`：AI 小助手页面。
- `GET /embed`：嵌入模式入口。
- `/api/debug/assistant-traces*`：debug trace 接口。
- `/debug/assistant-traces`：debug trace 页面。

当前未看到拆分的 `APIRouter`。新增接口前应先检查 `main.py` 的注册方式，不要随意改变已有 URL、请求参数和响应结构。

## 6. 核心业务模块

- `query_service/app/config.py`：配置项，包含应用、数据库、LLM、助手开关、阈值、trace 配置。
- `query_service/app/db.py`：业务库、控制库、课表库连接。
- `query_service/app/service.py`：模板查询执行、参数标准化、只读保护、审计日志。
- `query_service/app/registry.py`：查询模板注册表读取，支持内置模板兜底。
- `query_service/app/patrol_api.py`：AI 巡课、预警、专项分析、问答路由、规则分桶、LLM 调用主逻辑。
- `query_service/app/semantic_planner.py`：语义资源加载与 QueryPlan 生成。
- `query_service/app/semantic_executor.py`：按 QueryPlan 执行模板查询。
- `query_service/app/semantic_report.py`：结构化结果交给 LLM 生成分析报告。
- `query_service/app/builtin_templates.py`：代码内置白名单 SQL 模板。
- `query_service/app/assistant_trace.py`：助手问答耗时和节点追踪。
- `query_service/app/demo.py`：playground demo 模拟问答。
- `query_service/app/schemas.py`：Pydantic 请求/响应模型。

## 7. AI 小助手问答链路

当前链路大致是：

```text
前端 /assistant 页面
→ POST /api/assistant/ask-stream
→ assistant_ask_stream()
→ route_assistant_query()
→ 本地问答 / 指标释义
→ 抽取查询条件与会话上下文
→ 规则分桶
→ 可选 LLM 澄清
→ 业务查询 / 语义规划 / 模板执行
→ LLM 总结
→ NDJSON 流式返回
```

关键函数：

- `assistant_ask_stream()`：流式接口入口。
- `assistant_ask()`：普通问答接口入口。
- `route_assistant_query()`：核心问答路由函数。
- `simple_assistant_bucket()`：关键词规则分桶。
- `_extract_query_options()`：抽取 TopN、学院、教师、课程、教室、节次、本科/研究生等条件。
- `_build_llm_clarification_response()`：LLM 澄清判断。
- `_build_clarification_response()`：规则澄清。
- `_try_simple_bucket_answer()`：按 bucket 调业务函数。
- `_summarize()`：调用 LLM 生成简报。
- `_general_llm_answer()`：通用问答兜底。

## 8. 巡课指标与业务规则

当前已识别的指标包括：

- 到课率。
- 前排满座率。
- 抬头率。
- 课堂活动指数。
- AI 巡查覆盖率。
- 预警课堂占比。
- 风险等级 / 预警等级。
- 预警类型。
- AI 巡查轮次。
- 重点关注课堂。
- 活力较高课堂。
- 今日节次进度。

业务口径：

- 实时巡课主要围绕当前正在上课课堂。
- 今日巡课主要围绕今日已结束课程。
- 预警数据聚合自学情/教情等预警记录。
- AI 巡查轮次优先从课表库计算，失败时可能回退 AI 巡课库。
- 阈值可能由 `.env` 覆盖，本文档不读取或展示实际敏感配置。

## 9. 数据库 / SQL 访问方式

数据库访问集中在 `query_service/app/db.py`：

- `get_business_connection()`：业务库。
- `get_control_connection()`：控制库。
- `get_schedule_connection()`：课表库。
- `get_connection()`：兼容旧调用，默认业务库。

查询方式：

- 使用 PyMySQL `DictCursor`。
- 使用参数化 SQL。
- 当前未看到 ORM 或连接池。
- `QueryService` 会强制注入 `tenant_id`。
- 控制表包括 `ai_query_template_registry`、`ai_query_audit_log`、`ai_metric_definition`。
- `DB_READONLY` 开启后，仅允许只读 SQL，并跳过审计写入。

SQL 主要来源：

- `query_service/sql/seed_query_templates.sql`
- `query_service/app/builtin_templates.py`
- `query_service/app/patrol_api.py`

SQL 开发必须注意：

- 租户隔离：`tenant_id` / `tenant_org_code`。
- 逻辑删除：例如 `delete_flag`、`recycle_sign`，具体字段以表结构为准。
- 参数化查询。
- 不新增自由 SQL 执行接口。
- 不执行生产数据库写操作。

## 10. RAG / 知识库 / 大模型调用方式

当前看到三类“知识/语义”来源：

- 本地指标知识库：`patrol_api.py` 中的 `METRIC_KNOWLEDGE_BASE`。
- 语义资源 JSON：`resources/assistant_semantic/intents.json`、`templates.json`、`metrics.json`、`error_codes.json`。
- RAG JSONL：`rag/jy_application_digital_patrol_rag.jsonl`，内容是表/字段级检索文本。

待确认：

- 当前代码中未确认 `rag/*.jsonl` 已被加载使用。
- 未确认是否存在 embedding、向量库、ES 或其他检索链路。
- 不要默认把 `rag/` 当成已接入生产链路。

大模型调用方式：

- 使用 OpenAI-compatible `/chat/completions`。
- 用于意图分类、澄清判断、业务简报总结、语义报告生成、通用回答。
- 使用 `llm_base_url`、`llm_model`、`llm_api_key` 等配置。
- 支持通过 `chat_template_kwargs.enable_thinking` 控制 Qwen/vLLM 类模型思考行为。
- 不要在代码、日志或接口响应中输出 API Key。

## 11. 日志、异常处理与测试情况

日志/追踪：

- 当前未发现统一 logging 配置，待确认。
- 有内存 trace：`query_service/app/assistant_trace.py`。
- trace 通过 `ASSISTANT_TRACE_ENABLED` 控制，默认应关闭。
- 提供 debug API 和 debug HTML 页面查看近期问答节点耗时。

异常处理：

- `QueryService` 对模板不存在、参数错误、查询失败会转为 HTTPException。
- 审计日志写入失败不会影响主查询链路。
- 业务简报查询异常会返回“业务数据暂无法查询”一类兜底。
- LLM 调用失败会返回 fallback 文案或通用失败提示。

测试：

- 当前未发现 `tests/`、`pytest.ini`、`pyproject.toml` 等测试配置。
- 是否有外部测试脚本或手工验证流程：待确认。

## 12. 后续生成或维护 AGENTS.md 时应写入的规则

`AGENTS.md` 已生成，后续应持续维护以下规则：

- 不读取、不输出 `.env`、密钥、数据库密码、token、完整连接串。
- 默认不要修改大 SQL dump、tar、zip、`offline_bundle/`，除非用户明确要求。
- API 路由当前集中在 `app/main.py`，新增接口前先检查现有路由风格。
- 查询必须走白名单模板或明确只读 SQL，不新增自由 SQL 执行接口。
- SQL 必须参数化，必须保留 `tenant_id` 隔离。
- 修改问答链路前先看 `patrol_api.py`、`semantic_planner.py`、`semantic_executor.py`、`semantic_report.py`。
- 修改模板时同步考虑：内置模板、控制表种子、语义 `templates.json` 映射。
- LLM 调用保持 OpenAI-compatible `/chat/completions` 协议，不在日志/响应中泄露 API key。
- debug trace 默认应受配置控制，生产默认关闭。
- 重要变更需要最小验证方案。

## 13. 待确认问题

- `offline_bundle/` 是否仍需要同步维护，还是只作为离线交付快照。
- `rag/jy_application_digital_patrol_rag.jsonl` 是否计划接入实际 RAG 检索链路。
- 生产环境真实 `.env` 配置、数据库库名、租户映射、LLM 地址等，本文档未读取，均待确认。
- 是否需要补充测试框架和最小接口测试。
- 是否需要把内嵌 HTML 页面拆出独立前端文件，当前代码未体现该规划。
- 是否存在外部网关、鉴权、租户注入机制，当前项目代码中未看到明确鉴权层。
- `DB_READONLY` 在生产是否开启，待确认。
- `assistant_auto_plan_template_execute_enabled` 实际部署是否开启，待确认。

## 14. 主要阅读过的目录和文件

- `AGENTS.md`
- `query_service/app/`
- `query_service/sql/`
- `query_service/resources/assistant_semantic/`
- `query_service/scripts/`
- `rag/`
- `query_service/README.md`
- `query_service/API接口规范.md`
- `query_service/assistant_qa_sequence.md`
- `query_service/requirements.txt`
- `query_service/Dockerfile`
- `query_service/.env`：仅确认项目中存在过相关配置机制，本文档不读取或展示内容。
