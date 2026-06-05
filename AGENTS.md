# AGENTS.md

本文件用于指导后续 Codex 在 `xunke` 小助手项目中进行代码阅读、功能开发、Bug 修复、SQL 修改、接口联调、部署脚本编写和代码审查。后续进入本项目时，应优先阅读本文件，再阅读相关代码。

## 1. 项目背景

`xunke` 是一个面向高校巡课、课堂数据查询、AI 问答、指标汇总、课堂预警、简报生成等场景的小助手项目。

当前代码主要围绕 AI 巡课助手展开，提供受控 SQL 查询、AI 小助手页面、课堂巡课/预警简报、语义规划、LLM 总结和调试 trace 等能力。

## 2. 当前项目主体

当前主要维护对象是 `query_service`。

注意事项：

- `offline_bundle/` 看起来是离线部署副本，是否继续同步维护：待确认。
- 根目录下较大的 SQL dump、zip、Docker 镜像 tar 文件默认不要修改。
- 除非用户明确要求，不要修改 `offline_bundle/`、大 SQL dump、zip、tar、离线镜像文件。
- 不要读取、打印或暴露 `.env` 中的敏感配置。

## 3. 项目目录结构

主要目录用途如下：

- `query_service/app/`：FastAPI 应用源码，包含路由、配置、数据库连接、模板查询、AI 小助手问答、巡课/预警业务逻辑、语义规划和 trace。
- `query_service/sql/`：控制表、模板种子、模板字段迁移等 SQL 文件。
- `query_service/resources/assistant_semantic/`：语义规划资源，包含意图、指标、模板映射、错误码等 JSON 配置。
- `query_service/scripts/`：辅助脚本，包括 ARM64 离线镜像构建和内置模板入库脚本。
- `query_service/assets/`：助手头像、用户头像、公司 logo 等静态资源。
- `rag/`：当前看到表/字段级检索资料 JSONL，是否已接入运行链路：待确认。
- `offline_bundle/`：离线部署副本或交付包副本，是否作为日常维护对象：待确认。

## 4. 技术栈

当前项目已确认使用：

- FastAPI：后端 Web 框架。
- Uvicorn：ASGI 运行服务。
- Pydantic / pydantic-settings：请求/响应结构与配置加载。
- PyMySQL：直连 MySQL。
- MySQL：业务库、控制库、课表库等数据源。
- OpenAI-compatible `/chat/completions`：大模型调用协议。
- Docker / ARM64 离线镜像构建脚本：用于离线部署交付。
- 原生 HTML/CSS/JS 页面：当前 assistant 页面主要内嵌在 `query_service/app/main.py`。

待确认：

- 是否有 Redis。
- 是否有 Elasticsearch。
- 是否有向量数据库。
- `rag/` 是否已接入运行链路。
- 是否存在外部鉴权、网关或统一权限系统。

## 5. 启动与运行命令

本地依赖安装：

```bash
cd query_service
pip install -r requirements.txt
```

本地启动：

```bash
cd query_service
uvicorn app.main:app --reload --port 8000
```

Dockerfile 中的启动方式：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

运行前通常需要配置环境变量或 `.env`，但 Codex 默认不得读取或输出 `.env` 敏感内容。

## 6. 测试与检查命令

- 自动化测试体系：待确认。
- 当前未发现明确的 `tests/`、`pytest.ini`、`pyproject.toml` 等测试配置。
- 后续修改后至少应提供最小手工验证命令。
- 如新增测试，应优先补充独立、小范围、可重复执行的测试脚本。
- 不要凭空编造不存在的测试命令。
- 涉及数据库或 LLM 的验证，应明确说明所需环境和可能的外部依赖。

## 7. API 路由结构

当前 API 路由主要集中在 `query_service/app/main.py`。

主要接口类型包括：

- 健康检查。
- SQL 模板查询。
- playground 问答。
- assistant 问答。
- assistant 流式问答。
- assistant plan。
- 巡课实时简报。
- 巡课今日简报。
- 预警实时查询。
- 预警今日查询。
- 预警推送预览。
- 视频点位。
- assistant 页面。
- debug trace 页面和接口。

约束：

- 当前未看到拆分的 `APIRouter`。
- 新增接口前必须先检查 `query_service/app/main.py` 的现有注册方式。
- 不要随意改变已有接口 URL、请求参数和响应结构。
- 流式问答接口当前使用 NDJSON 形式返回，应保持兼容。

## 8. 核心业务模块

- `query_service/app/config.py`：应用配置、数据库配置、LLM 配置、助手开关、阈值和 trace 配置。配置通过 `pydantic-settings` 从环境变量和 `.env` 加载。
- `query_service/app/db.py`：数据库连接入口，包含业务库、控制库、课表库连接。当前使用 PyMySQL `DictCursor`。
- `query_service/app/service.py`：白名单 SQL 模板执行、参数默认值补齐、参数校验、租户注入、只读保护、审计日志。
- `query_service/app/registry.py`：从 `ai_query_template_registry` 读取模板，支持代码内置模板兜底。
- `query_service/app/patrol_api.py`：AI 巡课、小助手问答、课堂预警、简报、规则分桶、LLM 意图分类、澄清、业务查询、兜底逻辑等主逻辑。
- `query_service/app/semantic_planner.py`：加载 `resources/assistant_semantic/`，基于问题、指标和过滤条件生成 DSL / QueryPlan。
- `query_service/app/semantic_executor.py`：执行语义 QueryPlan，调用 QueryService 执行模板。
- `query_service/app/semantic_report.py`：将结构化取数结果交给 LLM 生成中文分析报告。
- `query_service/app/builtin_templates.py`：代码内置白名单 SQL 模板。
- `query_service/app/assistant_trace.py`：助手问答耗时与节点追踪的内存环形缓冲，供 debug trace 接口使用。

## 9. AI 小助手问答链路

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

约束：

- `route_assistant_query()` 是核心路由函数。
- 修改问答链路前必须先阅读 `query_service/app/patrol_api.py`。
- 不要直接绕过原有规则分桶、澄清、业务查询、语义规划逻辑。
- 对无法确认的链路细节应标记“待确认”。
- 对 AI 问答链路的修改必须保留原有兜底逻辑，尤其是 LLM 不可用时的降级返回。

## 10. 巡课指标与业务规则

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
- AI 巡查轮次优先从课表库计算，失败时可能回退 AI 巡课库，具体逻辑以 `patrol_api.py` 为准。
- 阈值可能由 `.env` 覆盖，不要读取或输出实际敏感配置。
- 修改业务口径前必须说明影响接口、影响指标和兼容风险。

## 11. 数据库 / SQL 开发规范

数据库与 SQL 修改必须格外谨慎：

1. 数据库访问集中在 `query_service/app/db.py`。
2. 当前使用 PyMySQL `DictCursor`。
3. 当前未看到 ORM 或连接池。
4. SQL 必须参数化，不要拼接用户输入。
5. 查询必须考虑租户隔离，特别是 `tenant_id`、`tenant_org_code` 等字段。
6. 查询业务数据时必须注意逻辑删除字段，例如 `delete_flag`、`recycle_sign` 等；具体字段以当前表结构和代码为准，无法确认时写“待确认”。
7. 不允许新增自由 SQL 执行接口。
8. 优先使用白名单模板或现有 QueryService 机制。
9. 修改 SQL 前必须说明涉及表、关联关系、过滤条件、租户隔离条件、逻辑删除条件和影响范围。
10. 不允许直接执行生产数据库写操作。
11. 生成 SQL 时必须检查 MySQL 语法、字段别名、缺失逗号、中文标点、WHERE 条件是否完整、是否可能跨租户查询。
12. 对无法确认的字段含义必须标记“待确认”。

SQL 模板来源包括：

- `query_service/sql/seed_query_templates.sql`
- `query_service/app/builtin_templates.py`
- `query_service/app/patrol_api.py`

## 12. 白名单模板与语义规划规范

白名单 SQL 模板相关代码位置：

- `query_service/app/service.py`
- `query_service/app/registry.py`
- `query_service/app/builtin_templates.py`
- `query_service/sql/seed_query_templates.sql`

语义规划相关代码位置：

- `query_service/app/semantic_planner.py`
- `query_service/app/semantic_executor.py`
- `query_service/app/semantic_report.py`
- `query_service/resources/assistant_semantic/`

修改语义模板时，需要同步考虑：

- JSON 语义资源。
- 内置 SQL 模板。
- 控制表种子脚本。
- 接口返回结构。
- LLM 总结逻辑。

不要只改一处导致模板 ID、指标名、参数名不一致。新增或调整模板时，应明确模板 ID、参数 schema、返回字段、语义映射和业务口径。

## 13. RAG / 知识库规范

当前看到 `rag/jy_application_digital_patrol_rag.jsonl`，内容像表/字段级检索资料。

但当前代码中未确认该 JSONL 已被加载使用。因此：

- 不要默认把 `rag/` 当作已接入生产链路。
- 不要私自把 `rag/` 目录接入生产链路。
- 如果后续要接入 RAG，需要先确认检索入口、索引构建方式、embedding 模型、向量库或 ES、召回数量、过滤条件、检索结果如何进入 LLM。
- 修改检索逻辑时，不要随意更改索引名、字段名、召回数量和过滤条件。

项目内还存在本地指标知识库和语义资源 JSON，它们与 RAG JSONL 的关系：待确认。

## 14. LLM 调用规范

当前 LLM 调用是 OpenAI-compatible `/chat/completions`。

配置项包括：

- `llm_base_url`
- `llm_model`
- `llm_api_key`
- `llm_timeout_sec`
- `llm_enable_thinking`

规范：

- 不要在代码、日志、接口响应中输出 API Key。
- 不要硬编码模型地址、模型名、API Key。
- 对 Qwen/vLLM 类模型的 `enable_thinking` 配置要谨慎处理。
- LLM 失败时必须有兜底文案或降级逻辑。
- 外部 LLM 调用失败不能导致普通业务查询完全不可用，除非业务本身必须依赖 LLM。
- 不要把 prompt、trace 或异常信息写成会泄露敏感配置的内容。

## 15. 日志、Trace 与异常处理规范

- 当前未发现统一 logging 配置：待确认。
- 存在 `query_service/app/assistant_trace.py` 和 debug trace 接口。
- trace 默认应由配置开关控制，生产环境不应默认开启。
- 不要用大量 `print` 替代日志。
- 异常日志不要输出密钥、token、数据库密码、完整连接串。
- 用户侧错误信息要友好，不直接暴露内部堆栈。
- 外部接口、LLM、数据库调用失败时应保留明确错误分类和兜底返回。
- 审计日志失败不应影响主查询链路，这一点应与现有 `QueryService` 行为保持一致。

## 16. API 开发规范

1. 保持现有接口 URL、请求参数和响应结构兼容。
2. 新增接口前先检查 `query_service/app/main.py` 和 `query_service/app/patrol_api.py` 的现有风格。
3. 业务逻辑不要继续无限堆积到路由层，能抽 service 时优先抽 service。
4. 请求参数和响应结构应遵循项目现有 Pydantic / dict 返回风格。
5. 流式接口要保持 NDJSON 返回约定。
6. 异常处理要与现有接口风格保持一致。
7. 新增接口必须提供最小验证方式。
8. 不要随意改变 assistant 页面现有调用路径。
9. 涉及跨域时先检查 `cors_allow_origins` 配置，不要硬编码生产域名。

## 17. 代码修改原则

1. 默认不要大范围重构。
2. 修改前先阅读相关模块。
3. 优先保持现有接口兼容。
4. 新功能优先遵循现有目录分层。
5. 不要随意引入新依赖。
6. 不要修改生产配置。
7. 不要修改大 SQL dump、tar、zip、离线包，除非用户明确要求。
8. 修改后必须说明改了哪些文件、为什么这样改、影响哪些接口或功能、如何验证、是否存在待确认风险。
9. 对 `query_service/app/patrol_api.py` 这类大文件修改要格外谨慎，优先局部改动。
10. 遇到无法确认的信息，写“待确认”，不要凭空编造。

## 18. 安全限制

1. 不要读取或输出 `.env` 敏感内容。
2. 不要提交密钥、token、数据库密码、API Key。
3. 不要执行 `rm -rf`、`drop table`、`truncate`、`delete from`、`update`、`insert` 等危险操作。
4. 不要直接修改生产数据库。
5. 不要绕过鉴权、租户隔离或权限校验。
6. 不要在日志和接口响应中暴露敏感数据。
7. 不要输出完整数据库连接串。
8. 不要私自重启服务、部署服务或修改生产环境。
9. 不要为了验证而执行数据库写操作。
10. 不要把用户输入直接拼入 SQL、日志或 prompt 中造成注入风险。

## 19. Codex 推荐工作方式

后续在本项目中使用 Codex 时，应遵循：

1. 先读代码，再给方案。
2. 先小范围修改，再扩大范围。
3. 修改前说明计划。
4. 修改后说明变更文件。
5. 提供测试或手工验证命令。
6. 对风险点和待确认点明确标注。
7. 优先使用只读命令理解项目。
8. 涉及数据库、部署、重启、删除文件时必须先征求确认。
9. 对 `patrol_api.py` 这类大文件修改要格外谨慎，优先局部改动。
10. 对 AI 问答链路修改要保留原有兜底逻辑。
11. 涉及 SQL 口径调整时，先说明口径变化，再改代码或模板。
12. 涉及 UI 页面时，先确认当前页面仍主要内嵌在 `main.py`。

## 20. 禁止操作清单

Codex 在本项目中默认禁止：

1. 删除文件或目录。
2. 清空数据库。
3. 修改生产配置。
4. 输出敏感信息。
5. 私自重构核心问答链路。
6. 私自更改接口协议。
7. 私自新增大型依赖。
8. 私自执行部署或重启服务。
9. 私自修改数据库结构。
10. 私自改变租户隔离逻辑。
11. 私自修改大 SQL dump、zip、tar、离线镜像文件。
12. 私自把 `rag/` 目录接入生产链路。
13. 私自修改 `offline_bundle/`。
14. 私自执行数据库写操作。
15. 私自读取或展示 `.env`、密钥、token、数据库密码、API Key、完整数据库连接串。
