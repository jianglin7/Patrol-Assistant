# Query Service

`query-service` 是AI巡课助手的轻量查询后端，负责 4 件事：

- 只允许执行白名单 SQL 模板
- 对查询参数做基础校验与标准化
- 强制注入 `tenant_id`
- 写入审计日志，方便排查和回放

## 目录结构

```text
query_service/
  app/
  sql/
  requirements.txt
  .env.example
```

## 快速启动

1. 初始化控制表与模板：

```bash
mysql -u root -p jy_application_digital_patrol < query_service/sql/ai_query_control_tables.sql
mysql -u root -p jy_application_digital_patrol < query_service/sql/seed_query_templates.sql
```

2. 安装依赖：

```bash
pip install -r query_service/requirements.txt
```

3. 配置环境变量：

```bash
cp query_service/.env.example query_service/.env
```

4. 启动服务：

```bash
cd query_service
uvicorn app.main:app --reload --port 8000
```

## 当前接口

- `GET /health`
- `POST /api/query/execute`
- `POST /api/playground/ask`（自然语言演示查询：异常课程/统计）
- `GET /assistant`（AI 小助手页面）
- `GET /embed` → 嵌入模式（仅对话区，重定向到 `/assistant?embed=1`）

接口细节见 [API接口规范.md](</Users/sz-seacraft/Documents/项目/小助手/xunke/query_service/API接口规范.md>).

## 演示 Demo（无需数据库）

如果你只想快速演示 AI 助手能力（异常课程查询 + 学情统计），可直接启动服务并打开：

```bash
cd query_service
uvicorn app.main:app --reload --port 8000
```

浏览器访问：`http://127.0.0.1:8000/assistant`

### 嵌入其它网站 / 小组件

- **推荐：iframe**（小助手与业务门户同域或内网可达即可，无需 CORS）  
  - 完整带大屏背景：`/assistant`  
  - **仅对话面板**（适合侧边栏、弹层、大屏角落）：`/embed`（等价于 `/assistant?embed=1`）；多租户可在地址加 `?tenant_id=你的租户`（`/embed?tenant_id=...` 会带到跳转链接）  
  - 示例：

```html
<iframe
  src="http://127.0.0.1:8001/embed"
  title="舟小智AI小助手"
  width="420"
  height="720"
  style="border:0;border-radius:12px;box-shadow:0 8px 24px rgba(15,23,42,0.12);"
  allow="clipboard-write"
></iframe>
```

- **父页面用 JavaScript 直接调 API**（不经过 iframe）：在 `.env` 配置 `CORS_ALLOW_ORIGINS` 为门户的 Origin（或开发环境 `*`，生产请白名单），对 `POST /api/assistant/ask`（或兼容路径 `POST /api/assistant/ask-stream`，均为一次 JSON）发 `fetch` 即可自行画 UI。

- **封装成「小组件」**：当前仓库提供的是 **单页 HTML + 接口**，没有单独 npm 包；常见做法是（1）iframe 嵌入，或（2）把 `fetch` + `response.json()` 抽成你们前端工程里的一个 Vue/React 组件，请求指向本服务部署地址。

可直接提问示例：

- `查询异常课程`
- `查询高三异常课程`
- `统计整体学情数据`
- `统计高二学情概览`
