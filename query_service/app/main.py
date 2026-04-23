import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any
from urllib.parse import urlencode

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, StreamingResponse
from starlette.middleware.cors import CORSMiddleware

from app.assistant_trace import assistant_trace_store, trace_emit
from app.config import settings
from app.demo import ask_demo_assistant
from app.patrol_api import (
    get_daily_patrol_brief,
    get_daily_warning_brief,
    get_push_strategy_preview,
    get_realtime_patrol_brief,
    get_realtime_warning_brief,
    route_assistant_query,
    get_video_points,
)
from app.schemas import ExecuteRequest, ExecuteResponse
from app.service import QueryService


app = FastAPI(title=settings.app_name)
service = QueryService()

STREAM_THINKING_DELAY_SEC = 0.45
STREAM_CHAR_DELAY_SEC = 0.02
STREAM_PRESET_THINKING_DELAY_SEC = 0.9
STREAM_PRESET_CHAR_DELAY_SEC = 0.05

_cors_origins = [o.strip() for o in settings.cors_allow_origins.split(",") if o.strip()]
if _cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins if _cors_origins != ["*"] else ["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
ASSISTANT_AVATAR_PATH = (
    "/Users/sz-seacraft/.cursor/projects/Users-sz-seacraft-Documents/assets/"
    "robot-fcc73b3d-ebb6-4426-a39d-40f7705e860b.png"
)
USER_AVATAR_PATH = (
    "/Users/sz-seacraft/.cursor/projects/Users-sz-seacraft-Documents/assets/"
    "image-10ac4d0d-8894-4d10-9b8e-4745a24ba08b.png"
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@app.post("/api/query/execute", response_model=ExecuteResponse)
def execute_query(request: ExecuteRequest) -> ExecuteResponse:
    return service.execute(request)


@app.post("/api/playground/ask")
def playground_ask(payload: dict[str, str]) -> dict[str, object]:
    question = payload.get("question", "")
    return ask_demo_assistant(question)


@app.get("/api/assistant/patrol/realtime-brief")
def patrol_realtime_brief(tenant_id: str | None = None) -> dict[str, object]:
    tid = tenant_id or settings.assistant_default_tenant_id
    return get_realtime_patrol_brief(tid)


@app.get("/api/assistant/patrol/daily-brief")
def patrol_daily_brief(tenant_id: str | None = None) -> dict[str, object]:
    tid = tenant_id or settings.assistant_default_tenant_id
    return get_daily_patrol_brief(tid)


@app.get("/api/assistant/warning/realtime")
def warning_realtime(tenant_id: str | None = None) -> dict[str, object]:
    tid = tenant_id or settings.assistant_default_tenant_id
    return get_realtime_warning_brief(tid)


@app.get("/api/assistant/warning/daily")
def warning_daily(tenant_id: str | None = None) -> dict[str, object]:
    tid = tenant_id or settings.assistant_default_tenant_id
    return get_daily_warning_brief(tid)


@app.post("/api/assistant/warning/push-preview")
def warning_push_preview(payload: dict[str, object]) -> dict[str, object]:
    tenant_id = str(payload.get("tenant_id") or settings.assistant_default_tenant_id)
    threshold_payload = payload.get("threshold")
    threshold = threshold_payload if isinstance(threshold_payload, dict) else None
    return get_push_strategy_preview(tenant_id, threshold)


@app.get("/api/assistant/video/points")
def video_points(tenant_id: str | None = None, date: str | None = None) -> dict[str, object]:
    tid = tenant_id or settings.assistant_default_tenant_id
    return get_video_points(tid, date)


@app.post("/api/playground/ask-stream")
async def playground_ask_stream(payload: dict[str, str]) -> StreamingResponse:
    """流式输出 demo 回答（meta -> delta* -> done）。"""
    question = payload.get("question", "")
    result = ask_demo_assistant(question)
    answer = str(result.get("answer", "")).strip()
    intent = str(result.get("intent", "查询结果"))

    async def event_stream() -> AsyncGenerator[str, None]:
        yield json.dumps({"type": "meta", "intent": intent}, ensure_ascii=False) + "\n"
        await asyncio.sleep(STREAM_THINKING_DELAY_SEC)
        if answer:
            for ch in answer:
                yield json.dumps({"type": "delta", "content": ch}, ensure_ascii=False) + "\n"
                await asyncio.sleep(STREAM_CHAR_DELAY_SEC)
        yield json.dumps({"type": "done"}, ensure_ascii=False) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


@app.post("/api/assistant/ask")
def assistant_ask(payload: dict[str, str]) -> dict[str, object]:
    question = payload.get("question", "")
    tenant_id = str(payload.get("tenant_id") or settings.assistant_default_tenant_id)
    trace_id: str | None = None
    if settings.assistant_trace_enabled:
        trace_id = assistant_trace_store.begin("/api/assistant/ask", question, tenant_id)
        trace_emit(trace_id, "handler_enter", question_len=len(question or ""))
    err: str | None = None
    try:
        return route_assistant_query(question, tenant_id, trace_id=trace_id)
    except Exception as ex:
        err = str(ex)
        trace_emit(trace_id, "handler_exception", error=repr(ex))
        raise
    finally:
        if trace_id:
            assistant_trace_store.finalize(trace_id, "error" if err else "ok", err)


@app.post("/api/assistant/ask-stream")
async def assistant_ask_stream(payload: dict[str, str]) -> StreamingResponse:
    """流式输出（meta -> delta* -> done）。既定问题与通用问题都按字吐出。"""
    question = payload.get("question", "")
    tenant_id = str(payload.get("tenant_id") or settings.assistant_default_tenant_id)
    trace_id: str | None = None
    if settings.assistant_trace_enabled:
        trace_id = assistant_trace_store.begin("/api/assistant/ask-stream", question, tenant_id)
        trace_emit(trace_id, "handler_enter", question_len=len(question or ""))

    async def event_stream() -> AsyncGenerator[str, None]:
        err: str | None = None
        try:
            yield json.dumps({"type": "meta"}, ensure_ascii=False) + "\n"
            trace_emit(trace_id, "ndjson_meta_sent")
            await asyncio.sleep(STREAM_THINKING_DELAY_SEC)

            result = await asyncio.to_thread(route_assistant_query, question, tenant_id, trace_id)
            answer = str(result.get("answer") or "").strip()
            intent = str(result.get("intent") or "")
            source = str(result.get("source") or "")
            trace_emit(trace_id, "stream_result_ready", intent=intent, answer_chars=len(answer))

            if answer:
                # 命中既定问题（库表简报）时，额外放慢思考与吐字节奏，营造更自然的输出过程
                char_delay = STREAM_CHAR_DELAY_SEC
                if source == "patrol_api":
                    await asyncio.sleep(STREAM_PRESET_THINKING_DELAY_SEC)
                    char_delay = STREAM_PRESET_CHAR_DELAY_SEC
                for ch in answer:
                    yield json.dumps({"type": "delta", "content": ch}, ensure_ascii=False) + "\n"
                    await asyncio.sleep(char_delay)
            else:
                yield json.dumps({"type": "delta", "content": "暂无可用结论。"}, ensure_ascii=False) + "\n"

            yield json.dumps({"type": "done"}, ensure_ascii=False) + "\n"
            trace_emit(trace_id, "ndjson_done_sent")
        except Exception as ex:
            err = str(ex)
            trace_emit(trace_id, "ndjson_generator_exception", error=repr(ex))
            yield json.dumps({"type": "delta", "content": "网络异常，回答中断。请重试。"}, ensure_ascii=False) + "\n"
            yield json.dumps({"type": "done"}, ensure_ascii=False) + "\n"
        finally:
            if trace_id:
                assistant_trace_store.finalize(trace_id, "error" if err else "ok", err)

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


_TRACE_DISABLED_DETAIL = (
    "助手轨迹未开启：在环境变量中设置 ASSISTANT_TRACE_ENABLED=true 后重启服务。"
)


@app.get("/api/debug/assistant-traces")
def debug_assistant_traces_list(limit: int = 50) -> dict[str, Any]:
    """列出近期助手提问追踪摘要（仅调试，不在小助手页面展示）。"""
    if not settings.assistant_trace_enabled:
        raise HTTPException(status_code=404, detail=_TRACE_DISABLED_DETAIL)
    return {"traces": assistant_trace_store.list_recent(limit)}


@app.get("/api/debug/assistant-traces/{trace_id}")
def debug_assistant_trace_detail(trace_id: str) -> dict[str, Any]:
    """单条提问的节点时间线（仅调试）。"""
    if not settings.assistant_trace_enabled:
        raise HTTPException(status_code=404, detail=_TRACE_DISABLED_DETAIL)
    rec = assistant_trace_store.get(trace_id)
    if not rec:
        raise HTTPException(status_code=404, detail="未找到该 trace_id")
    return rec.to_detail()


@app.get("/debug/assistant-traces", response_class=HTMLResponse)
def debug_assistant_traces_page() -> str:
    """简易 Web 页：查询助手追踪列表与单条时间线（需 ASSISTANT_TRACE_ENABLED=true）。"""
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>助手追踪查询</title>
  <style>
    :root { --bg: #0f1419; --card: #1a2332; --line: #2d3a4d; --text: #e6edf3; --muted: #8b9cb3; --accent: #58a6ff; --ok: #3fb950; --err: #f85149; }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: ui-sans-serif, "PingFang SC", "Microsoft YaHei", sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }
    header { padding: 16px 20px; border-bottom: 1px solid var(--line); display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
    h1 { font-size: 1.1rem; font-weight: 600; margin: 0; }
    .toolbar { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-left: auto; }
    label { color: var(--muted); font-size: 0.85rem; }
    input[type="number"] { width: 72px; padding: 6px 8px; border-radius: 6px; border: 1px solid var(--line); background: var(--card); color: var(--text); }
    button { padding: 6px 14px; border-radius: 6px; border: 1px solid var(--line); background: var(--card); color: var(--text); cursor: pointer; font-size: 0.9rem; }
    button:hover { border-color: var(--accent); color: var(--accent); }
    main { display: grid; grid-template-columns: 1fr 1fr; gap: 0; min-height: calc(100vh - 57px); }
    @media (max-width: 900px) { main { grid-template-columns: 1fr; } }
    .panel { border-right: 1px solid var(--line); padding: 16px; overflow: auto; max-height: calc(100vh - 57px); }
    .panel:last-child { border-right: none; }
    .banner { padding: 12px 14px; border-radius: 8px; margin-bottom: 14px; font-size: 0.9rem; }
    .banner.warn { background: rgba(248,81,73,0.12); border: 1px solid rgba(248,81,73,0.35); color: #ffb4af; }
    .banner.info { background: rgba(88,166,255,0.1); border: 1px solid rgba(88,166,255,0.25); color: #a6d5ff; }
    table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
    th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }
    th { color: var(--muted); font-weight: 500; }
    tr { cursor: pointer; }
    tr:hover td { background: rgba(88,166,255,0.06); }
    tr.active td { background: rgba(88,166,255,0.12); }
    .mono { font-family: ui-monospace, monospace; font-size: 0.78rem; word-break: break-all; }
    .status-ok { color: var(--ok); }
    .status-err { color: var(--err); }
    .detail-q { white-space: pre-wrap; font-size: 0.88rem; margin: 0 0 12px; padding: 12px; background: var(--card); border-radius: 8px; border: 1px solid var(--line); }
    .events { margin: 0; padding: 0; list-style: none; }
    .events li { padding: 8px 10px; border-bottom: 1px solid var(--line); display: grid; grid-template-columns: 72px 1fr; gap: 10px; font-size: 0.82rem; }
    .events .t { color: var(--muted); font-variant-numeric: tabular-nums; }
    .events .n { color: var(--accent); font-family: ui-monospace, monospace; font-size: 0.8rem; }
    .meta { color: var(--muted); font-size: 0.75rem; margin-top: 4px; word-break: break-all; }
    h2 { font-size: 0.95rem; margin: 0 0 12px; color: var(--muted); font-weight: 600; }
  </style>
</head>
<body>
  <header>
    <h1>助手追踪查询</h1>
    <div class="toolbar">
      <label>条数 <input type="number" id="limit" value="50" min="1" max="500" /></label>
      <button type="button" id="refresh">刷新列表</button>
    </div>
  </header>
  <main>
    <section class="panel" id="left">
      <div id="banner"></div>
      <div id="list-wrap"><p class="muted">加载中…</p></div>
    </section>
    <section class="panel" id="right">
      <h2>单条详情</h2>
      <p id="detail-empty" class="mono" style="color:var(--muted)">点击左侧一行查看节点时间线。</p>
      <div id="detail" style="display:none"></div>
    </section>
  </main>
  <script>
    const banner = document.getElementById("banner");
    const listWrap = document.getElementById("list-wrap");
    const detail = document.getElementById("detail");
    const detailEmpty = document.getElementById("detail-empty");
    let activeId = null;

    function showBanner(kind, text) {
      banner.className = "banner " + (kind === "warn" ? "warn" : "info");
      banner.textContent = text;
      banner.style.display = "block";
    }

    async function loadList() {
      const limit = Math.min(500, Math.max(1, parseInt(document.getElementById("limit").value, 10) || 50));
      listWrap.innerHTML = "<p style=color:var(--muted)>加载中…</p>";
      try {
        const r = await fetch("/api/debug/assistant-traces?limit=" + limit);
        if (r.status === 404) {
          const j = await r.json().catch(() => ({}));
          showBanner("warn", (j.detail || "追踪未开启") + " 请在 .env 设置 ASSISTANT_TRACE_ENABLED=true 并重启。");
          listWrap.innerHTML = "";
          return;
        }
        if (!r.ok) {
          showBanner("warn", "请求失败 HTTP " + r.status);
          listWrap.innerHTML = "";
          return;
        }
        banner.style.display = "none";
        const data = await r.json();
        const rows = data.traces || [];
        if (!rows.length) {
          listWrap.innerHTML = "<p style=color:var(--muted)>暂无记录。请先在小助手发几条问题再刷新。</p>";
          return;
        }
        let html = "<table><thead><tr><th>相对耗时</th><th>状态</th><th>接口</th><th>问题摘要</th></tr></thead><tbody>";
        for (const t of rows) {
          const st = t.status === "ok" ? "status-ok" : t.status === "error" ? "status-err" : "";
          html += "<tr data-id=\"" + escapeAttr(t.id) + "\" class=\"" + (t.id === activeId ? "active" : "") + "\">";
          html += "<td class=mono>" + (t.total_ms != null ? t.total_ms + " ms" : "—") + "</td>";
          html += "<td class=\"" + st + "\">" + escapeHtml(t.status) + "</td>";
          html += "<td class=mono>" + escapeHtml(t.endpoint || "") + "</td>";
          html += "<td>" + escapeHtml(t.question_preview || "") + "</td></tr>";
        }
        html += "</tbody></table>";
        listWrap.innerHTML = html;
        listWrap.querySelectorAll("tr[data-id]").forEach(function(tr) {
          tr.addEventListener("click", function() { loadDetail(tr.getAttribute("data-id")); });
        });
      } catch (e) {
        showBanner("warn", "网络错误: " + e);
        listWrap.innerHTML = "";
      }
    }

    function escapeHtml(s) {
      if (!s) return "";
      return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
    }
    function escapeAttr(s) {
      return escapeHtml(s).replace(/'/g, "&#39;");
    }

    async function loadDetail(id) {
      if (!id) return;
      activeId = id;
      listWrap.querySelectorAll("tr[data-id]").forEach(function(tr) {
        tr.classList.toggle("active", tr.getAttribute("data-id") === id);
      });
      detailEmpty.style.display = "none";
      detail.style.display = "block";
      detail.innerHTML = "<p style=color:var(--muted)>加载 " + escapeHtml(id) + " …</p>";
      try {
        const r = await fetch("/api/debug/assistant-traces/" + encodeURIComponent(id));
        if (!r.ok) {
          detail.innerHTML = "<p class=banner style=display:block>加载失败 HTTP " + r.status + "</p>";
          return;
        }
        const d = await r.json();
        let h = "<p class=mono style=color:var(--muted);margin:0 0 8px>id: " + escapeHtml(d.id) + "</p>";
        h += "<p class=mono style=color:var(--muted);margin:0 0 8px>tenant: " + escapeHtml(d.tenant_id || "") + "</p>";
        h += "<pre class=detail-q>" + escapeHtml(d.question || "") + "</pre>";
        h += "<p class=mono style=margin:0 0 8px>status: <span class=\"" + (d.status === "ok" ? "status-ok" : "status-err") + "\">" + escapeHtml(d.status) + "</span>";
        if (d.error) h += " — " + escapeHtml(d.error);
        h += "</p><ul class=events>";
        (d.events || []).forEach(function(ev) {
          h += "<li><span class=t>" + escapeHtml(String(ev.t_rel_ms)) + " ms</span><div>";
          h += "<div class=n>" + escapeHtml(ev.node) + "</div>";
          if (ev.meta && Object.keys(ev.meta).length) {
            h += "<div class=meta>" + escapeHtml(JSON.stringify(ev.meta)) + "</div>";
          }
          h += "</div></li>";
        });
        h += "</ul>";
        detail.innerHTML = h;
      } catch (e) {
        detail.innerHTML = "<p style=color:var(--err)>错误: " + escapeHtml(String(e)) + "</p>";
      }
    }

    document.getElementById("refresh").addEventListener("click", loadList);
    document.getElementById("limit").addEventListener("change", loadList);
    loadList();
  </script>
</body>
</html>"""


@app.get("/assistant/avatar")
def assistant_avatar() -> FileResponse:
    return FileResponse(ASSISTANT_AVATAR_PATH, media_type="image/png")


@app.get("/assistant/user-avatar")
def assistant_user_avatar() -> FileResponse:
    return FileResponse(USER_AVATAR_PATH, media_type="image/png")


@app.get("/embed")
def assistant_embed_entry(tenant_id: str | None = None) -> RedirectResponse:
    """嵌入专用入口：打开后进入无大屏背景的会话页，适合 iframe / WebView。"""
    q: dict[str, str] = {"embed": "1"}
    if tenant_id:
        q["tenant_id"] = tenant_id
    return RedirectResponse(
        url="/assistant?" + urlencode(q),
        status_code=307,
    )


@app.get("/assistant", response_class=HTMLResponse)
def assistant_page() -> str:
    return """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>AI小助手</title>
  <style>
    :root {
      --primary: #2d68ff;
      --primary-strong: #1e53cf;
      --text: #0f172a;
      --muted: #64748b;
      --line: #dbe4f4;
      --panel-bg: rgba(255, 255, 255, 0.93);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      background: radial-gradient(circle at 10% 10%, #f8fbff 0, #e9f1ff 38%, #dbe7ff 100%);
      color: var(--text);
      height: 100vh;
      overflow: hidden;
    }
    .background-board {
      position: fixed;
      inset: 0;
      padding: 34px 44px;
      display: grid;
      grid-template-rows: auto auto 1fr;
      gap: 18px;
      background:
        radial-gradient(900px 360px at 0% 0%, rgba(59,130,246,0.25), transparent 65%),
        radial-gradient(1000px 500px at 100% 20%, rgba(37,99,235,0.16), transparent 60%);
    }
    .board-title {
      color: #f8fbff;
      text-shadow: 0 6px 18px rgba(30, 64, 175, 0.45);
      font-size: 52px;
      font-weight: 700;
      letter-spacing: 0.04em;
      margin: 0;
    }
    .board-sub {
      color: rgba(255, 255, 255, 0.86);
      font-size: 20px;
      margin-top: 6px;
      font-weight: 500;
    }
    .board-cards {
      display: grid;
      grid-template-columns: repeat(4, minmax(160px, 1fr));
      gap: 14px;
    }
    .board-card {
      border: 1px solid rgba(255, 255, 255, 0.26);
      background: linear-gradient(180deg, rgba(255,255,255,0.22), rgba(255,255,255,0.08));
      border-radius: 14px;
      padding: 16px;
      color: #eff6ff;
      backdrop-filter: blur(5px);
    }
    .board-card .k {
      font-size: 13px;
      opacity: 0.9;
    }
    .board-card .v {
      margin-top: 8px;
      font-size: 28px;
      font-weight: 700;
    }
    .board-panel {
      border: 1px solid rgba(255, 255, 255, 0.2);
      border-radius: 16px;
      background: linear-gradient(180deg, rgba(255,255,255,0.16), rgba(255,255,255,0.07));
      backdrop-filter: blur(5px);
      min-height: 120px;
    }
    .assistant-panel {
      position: fixed;
      right: 34px;
      bottom: 104px;
      width: min(560px, calc(100vw - 28px));
      height: min(740px, calc(100vh - 170px));
      border-radius: 20px;
      border: 1px solid #dbe5f7;
      background: var(--panel-bg);
      backdrop-filter: blur(10px);
      box-shadow: 0 24px 46px rgba(30, 64, 175, 0.26);
      overflow: hidden;
      display: flex;
      flex-direction: column;
      transform-origin: right bottom;
      transform: translateY(24px) scale(0.96);
      opacity: 0;
      pointer-events: none;
      transition: transform 0.24s ease, opacity 0.24s ease;
    }
    .assistant-panel.open {
      transform: translateY(0) scale(1);
      opacity: 1;
      pointer-events: auto;
    }
    .header {
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
      background: linear-gradient(180deg, #ffffff 0%, #f1f7ff 100%);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
    }
    .header-main {
      display: flex;
      align-items: center;
      gap: 10px;
      min-width: 0;
    }
    .brand-logo {
      width: 34px;
      height: 34px;
      border-radius: 10px;
      overflow: hidden;
      background: #ecf4ff;
      border: 1px solid #cfe0ff;
      flex-shrink: 0;
    }
    .title {
      font-size: 18px;
      line-height: 1.1;
      font-weight: 700;
      margin: 0;
      color: #1e40af;
    }
    .subtitle {
      margin-top: 2px;
      color: var(--muted);
      font-size: 12px;
    }
    .meta {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }
    .meta-tag {
      border: 1px solid #cde0ff;
      background: linear-gradient(180deg, #f8fbff 0%, #edf4ff 100%);
      color: #1d4ed8;
      font-size: 11px;
      padding: 4px 8px;
      border-radius: 999px;
      white-space: nowrap;
      font-weight: 600;
    }
    .main {
      flex: 1;
      min-height: 0;
      display: grid;
      grid-template-rows: 1fr auto;
      background: linear-gradient(180deg, #ffffff 0%, #f5f9ff 100%);
    }
    .chat {
      min-height: 0;
      padding: 14px 14px 10px;
      overflow-y: auto;
      scrollbar-width: thin;
      scrollbar-color: #bcd0f7 transparent;
    }
    .chat::-webkit-scrollbar {
      width: 8px;
    }
    .chat::-webkit-scrollbar-track {
      background: transparent;
    }
    .chat::-webkit-scrollbar-thumb {
      background: linear-gradient(180deg, #c8d9fb 0%, #adc6f7 100%);
      border-radius: 999px;
      border: 2px solid transparent;
      background-clip: padding-box;
    }
    .chat::-webkit-scrollbar-thumb:hover {
      background: linear-gradient(180deg, #b8cef8 0%, #95b6f4 100%);
      background-clip: padding-box;
    }
    .chat-section-title {
      position: sticky;
      top: 0;
      z-index: 2;
      margin: -14px -14px 10px;
      padding: 8px 14px;
      background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(255,255,255,0.9));
      border-bottom: 1px solid #e7eefb;
      color: #60708a;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.08em;
      backdrop-filter: blur(6px);
    }
    .bubble {
      max-width: 86%;
      padding: 11px 13px;
      border-radius: 14px;
      margin-bottom: 10px;
      white-space: pre-wrap;
      line-height: 1.6;
      font-size: 14px;
    }
    .assistant {
      background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
      border: 1px solid #dce6f7;
      box-shadow: 0 8px 18px rgba(15, 23, 42, 0.04);
    }
    .user {
      margin-left: auto;
      background: linear-gradient(180deg, #ecf3ff 0%, #e4efff 100%);
      border: 1px solid #c6dafd;
      box-shadow: 0 8px 18px rgba(37, 99, 235, 0.12);
    }
    .suggestions {
      min-height: 96px;
      display: flex;
      flex-direction: column;
      padding: 8px 12px 10px;
      background: transparent;
      border-top: 1px solid rgba(226, 232, 240, 0.55);
      transition: min-height 0.24s ease, padding 0.24s ease, border-color 0.24s ease;
    }
    .suggestions.collapsed {
      min-height: 20px;
      padding: 5px 10px 6px;
      border-top-color: rgba(226, 232, 240, 0.35);
    }
    .suggestions-card {
      border-radius: 12px;
      padding: 8px 10px 9px;
      background: rgba(255, 255, 255, 0.42);
      border: 1px solid rgba(226, 232, 240, 0.65);
      box-shadow: none;
      backdrop-filter: blur(6px);
      transition: padding 0.24s ease, border-color 0.24s ease, background 0.24s ease;
    }
    .suggestions.collapsed .suggestions-card {
      padding: 6px 8px;
      border-color: rgba(226, 232, 240, 0.45);
      background: rgba(255, 255, 255, 0.28);
    }
    .suggestions .label {
      width: 100%;
      margin-bottom: 0;
      padding-bottom: 8px;
      margin-bottom: 8px;
      border-bottom: 1px solid rgba(241, 245, 249, 0.9);
      font-size: 11px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      flex-wrap: nowrap;
      transition: margin-bottom 0.22s ease, padding-bottom 0.22s ease, border-color 0.22s ease;
    }
    .suggestions.collapsed .label {
      padding-bottom: 0;
      margin-bottom: 0;
      border-bottom-color: transparent;
    }
    .label-main {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      min-width: 0;
    }
    .label-pill {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 2px 0;
      border-radius: 0;
      background: transparent;
      border: none;
      box-shadow: none;
    }
    .label-icon {
      font-size: 10px;
      color: #3b82f6;
      line-height: 1;
      opacity: 0.9;
    }
    .chips {
      display: flex;
      flex-direction: column;
      gap: 7px;
      overflow-y: auto;
      max-height: 168px;
      padding-right: 2px;
      scrollbar-width: thin;
      scrollbar-color: #cbd5e1 transparent;
      opacity: 1;
      transform: translateY(0);
      transition: max-height 0.24s ease, opacity 0.2s ease, transform 0.2s ease, margin 0.2s ease;
    }
    .chips.hidden {
      max-height: 0;
      opacity: 0;
      transform: translateY(-4px);
      overflow: hidden;
      pointer-events: none;
    }
    .chip {
      border: 1px solid rgba(226, 232, 240, 0.85);
      border-radius: 10px;
      background: rgba(255, 255, 255, 0.72);
      color: #475569;
      cursor: pointer;
      padding: 7px 10px 7px 8px;
      font-size: 12.5px;
      text-align: left;
      display: flex;
      align-items: center;
      gap: 9px;
      font-weight: 400;
      line-height: 1.45;
      letter-spacing: 0.01em;
      transition: border-color 0.18s ease, background 0.18s ease, box-shadow 0.18s ease, transform 0.12s ease;
      box-shadow: none;
    }
    .chip:hover {
      border-color: rgba(186, 199, 216, 0.95);
      background: rgba(255, 255, 255, 0.95);
      box-shadow: 0 1px 6px rgba(15, 23, 42, 0.05);
      transform: translateY(-0.5px);
    }
    .chip:active {
      transform: translateY(0);
    }
    .chip .chip-text {
      flex: 1;
      min-width: 0;
    }
    .composer {
      border-top: 1px solid var(--line);
      background: linear-gradient(180deg, #ffffff 0%, #f9fbff 100%);
      padding: 10px 10px 12px;
      display: flex;
      gap: 10px;
    }
    .composer input {
      flex: 1;
      height: 42px;
      border: 1px solid #d1d5db;
      border-radius: 10px;
      padding: 0 14px;
      font-size: 14px;
      outline: none;
      transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }
    .composer input:focus {
      border-color: #93c5fd;
      box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12);
    }
    .composer button {
      width: 80px;
      border: none;
      border-radius: 10px;
      background: linear-gradient(180deg, var(--primary) 0%, var(--primary-strong) 100%);
      color: #fff;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      transition: background-color 0.2s ease, transform 0.2s ease;
      box-shadow: 0 10px 18px rgba(37, 99, 235, 0.28);
    }
    .composer button:hover {
      background: linear-gradient(180deg, #377cff 0%, #225fdf 100%);
      transform: translateY(-1px);
    }
    .msg {
      display: flex;
      align-items: flex-start;
      gap: 10px;
      margin-bottom: 8px;
    }
    .msg.user-wrap {
      justify-content: flex-end;
    }
    .avatar {
      width: 32px;
      height: 32px;
      border-radius: 50%;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }
    .avatar.assistant-avatar {
      background: #fff;
      border: 1px solid #cfe0ff;
      overflow: hidden;
      padding: 0;
    }
    .avatar.user-avatar {
      background: #eef2ff;
      border: 1px solid #c7d2fe;
      order: 2;
      overflow: hidden;
      padding: 0;
    }
    .msg.user-wrap .bubble {
      order: 1;
    }
    .avatar-img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }
    .avatar-img.user-fill {
      transform: scale(1);
      transform-origin: center;
    }
    .ask-icon {
      width: 22px;
      height: 22px;
      border-radius: 7px;
      background: linear-gradient(145deg, rgba(219, 234, 254, 0.72) 0%, rgba(191, 219, 254, 0.62) 100%);
      border: 1px solid rgba(147, 197, 253, 0.55);
      box-shadow: none;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }
    .ask-icon svg {
      width: 11px;
      height: 11px;
      display: block;
    }
    .label-text {
      font-size: 11px;
      font-weight: 500;
      color: #64748b;
      letter-spacing: 0.04em;
    }
    .label-tools {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      flex-shrink: 0;
    }
    .suggestions.collapsed .label-tools {
      gap: 0;
    }
    .tool-btn {
      border: 1px solid transparent;
      background: rgba(248, 250, 252, 0.65);
      color: #64748b;
      border-radius: 8px;
      padding: 3px 9px;
      font-size: 11px;
      font-weight: 500;
      cursor: pointer;
      line-height: 1.35;
      transition: border-color 0.15s ease, color 0.15s ease, background 0.15s ease;
      box-shadow: none;
    }
    .tool-btn:hover {
      border-color: rgba(226, 232, 240, 0.95);
      color: #334155;
      background: rgba(255, 255, 255, 0.85);
    }
    .suggestions.collapsed #refreshSuggestBtn {
      display: none;
    }
    .suggestions.collapsed #toggleSuggestBtn {
      margin-left: auto;
      padding-left: 11px;
      padding-right: 11px;
    }
    .header-actions {
      display: inline-flex;
      gap: 8px;
      margin-left: auto;
    }
    .launcher {
      position: fixed;
      right: 34px;
      bottom: 28px;
      width: 72px;
      height: 72px;
      border: none;
      border-radius: 50%;
      background: linear-gradient(180deg, var(--primary) 0%, var(--primary-strong) 100%);
      color: #fff;
      cursor: pointer;
      box-shadow: 0 16px 32px rgba(37, 99, 235, 0.42);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 30px;
    }
    .online-dot {
      position: absolute;
      right: 6px;
      top: 8px;
      width: 14px;
      height: 14px;
      border-radius: 50%;
      background: #44d26f;
      border: 2px solid #d8eafe;
    }
    .close-btn {
      width: 28px;
      height: 28px;
      border: 1px solid #dbe7fb;
      border-radius: 8px;
      background: #fff;
      color: #5b6f89;
      cursor: pointer;
      line-height: 1;
      font-size: 16px;
    }
    .refresh-btn {
      border: 1px solid #dbe7fb;
      border-radius: 8px;
      background: #fff;
      color: #5b6f89;
      cursor: pointer;
      padding: 0 10px;
      height: 28px;
      font-size: 12px;
      white-space: nowrap;
    }
    .loading-wrap {
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }
    .loading-bars {
      display: inline-flex;
      align-items: flex-end;
      gap: 3px;
      height: 14px;
    }
    .loading-bars span {
      width: 3px;
      background: #4f7dff;
      border-radius: 3px;
      animation: pulse 1s ease-in-out infinite;
    }
    .loading-bars span:nth-child(1) { height: 6px; animation-delay: 0s; }
    .loading-bars span:nth-child(2) { height: 10px; animation-delay: 0.15s; }
    .loading-bars span:nth-child(3) { height: 7px; animation-delay: 0.3s; }
    .loading-bars span:nth-child(4) { height: 12px; animation-delay: 0.45s; }
    @keyframes pulse {
      0%, 100% { opacity: 0.35; transform: translateY(0); }
      50% { opacity: 1; transform: translateY(-1px); }
    }
    /* /assistant?embed=1：嵌入第三方站点 / iframe，仅保留对话区 */
    body.embed-mode {
      overflow: hidden;
      background: #f5f9ff;
    }
    body.embed-mode .background-board,
    body.embed-mode .launcher {
      display: none !important;
    }
    body.embed-mode .assistant-panel {
      position: fixed;
      inset: 0;
      right: 0;
      bottom: 0;
      width: 100%;
      height: 100%;
      max-height: none;
      transform: none;
      opacity: 1;
      pointer-events: auto;
      border-radius: 0;
      box-shadow: none;
      border: none;
    }
    body.embed-mode .assistant-panel.open {
      transform: none;
    }
    body.embed-mode .close-btn {
      display: none;
    }
    @media (max-width: 720px) {
      .background-board { padding: 20px 16px; }
      .board-title { font-size: 34px; }
      .board-sub { font-size: 15px; }
      .board-cards { grid-template-columns: repeat(2, minmax(120px, 1fr)); }
      .assistant-panel {
        right: 8px;
        bottom: 88px;
        width: calc(100vw - 16px);
        height: calc(100vh - 112px);
      }
      .launcher { right: 16px; bottom: 14px; }
      .bubble { max-width: 95%; }
      .meta { display: none; }
      .suggestions .label { flex-wrap: wrap; }
      .label-tools { width: 100%; justify-content: flex-end; margin-top: 4px; }
      .tool-btn { padding: 3px 8px; font-size: 11px; }
      .chips { max-height: 140px; }
    }
  </style>
</head>
<body>
  <div class="background-board">
    <div>
      <h1 class="board-title">高校智慧校园管理平台</h1>
      <div class="board-sub">当前节点：教务处数据看板（学情与课堂巡查）</div>
    </div>
    <div class="board-cards">
      <div class="board-card"><div class="k">今日巡查课堂</div><div class="v">196</div></div>
      <div class="board-card"><div class="k">实时预警课堂</div><div class="v">7</div></div>
      <div class="board-card"><div class="k">平均到课率</div><div class="v">93.2%</div></div>
      <div class="board-card"><div class="k">课堂活力高值</div><div class="v">32</div></div>
    </div>
    <div class="board-panel"></div>
  </div>

  <div id="assistantPanel" class="assistant-panel open">
    <div class="header">
      <div class="header-main">
        <div class="brand-logo">
          <img class="avatar-img" src="/assistant/avatar" alt="助手头像" />
        </div>
        <div>
          <h1 class="title">AI小助手</h1>
          <div class="subtitle">高校学情异常与教学评价智能分析助手</div>
        </div>
      </div>
      <div class="header-actions">
        <button id="refreshPageBtn" class="refresh-btn" title="刷新会话页面">刷新会话</button>
        <button id="closeBtn" class="close-btn" title="关闭">×</button>
      </div>
    </div>
    <div class="main">
      <div id="chatBox" class="chat">
        <div class="msg">
          <div class="avatar assistant-avatar"><img class="avatar-img" src="/assistant/avatar" alt="助手头像" /></div>
          <div class="bubble assistant">您好，我是课堂巡课与学情预警 AI 助教。您可以直接提问，我会尽量用清晰、简洁的中文为您解答。</div>
        </div>
      </div>
      <div class="suggestions">
        <div class="suggestions-card">
          <div class="label">
            <span class="label-main">
              <span class="label-pill">
                <span class="label-icon" aria-hidden="true">✦</span>
                <span class="label-text">您可能想问</span>
              </span>
            </span>
            <span class="label-tools">
              <button id="toggleSuggestBtn" class="tool-btn" type="button">收起 ▴</button>
              <button id="refreshSuggestBtn" class="tool-btn" type="button">换一批</button>
            </span>
          </div>
          <div class="chips" id="suggestionChips">
          </div>
        </div>
      </div>
    </div>
    <div class="composer">
      <input id="q" placeholder="请输入查询内容..." value="" />
      <button id="sendBtn" onclick="ask()">发送</button>
    </div>
  </div>
  <button id="launcher" class="launcher" title="打开AI小助手">💬<span class="online-dot"></span></button>
  <script>
    const urlParams = new URLSearchParams(window.location.search);
    const EMBED = urlParams.get("embed") === "1";
    const urlTenant = (urlParams.get("tenant_id") || "").trim();
    const TENANT_ID = urlTenant.length ? urlTenant : null;
    const assistantPanel = document.getElementById("assistantPanel");
    const launcher = document.getElementById("launcher");
    const closeBtn = document.getElementById("closeBtn");
    const refreshPageBtn = document.getElementById("refreshPageBtn");
    const toggleSuggestBtn = document.getElementById("toggleSuggestBtn");
    const refreshSuggestBtn = document.getElementById("refreshSuggestBtn");
    const suggestionsBox = document.querySelector(".suggestions");
    const chatBox = document.getElementById("chatBox");
    const sendBtn = document.getElementById("sendBtn");
    const suggestionChips = document.getElementById("suggestionChips");
    const suggestionPool = [
      "课表时间段实时巡课简报",
      "非课表时间段今日巡课汇总",
      "实时课堂AI预警简报（预警课堂占比、风险等级、预警类型）",
      "今日课堂AI预警汇总（已巡查课堂数、预警占比、风险等级）",
      "预警推送的阈值是多少（到课率、前排满座率、抬头率）",
      "当前正在上课课堂中需要重点关注的数量（实时巡课）"
    ];
    const bulbIcon = '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none"><path d="M12 3a7 7 0 0 0-4.95 11.95c.68.67 1.1 1.25 1.33 2.05h7.24c.23-.8.65-1.38 1.33-2.05A7 7 0 0 0 12 3Z" stroke="#3b82f6" stroke-width="1.65" stroke-linejoin="round"/><path d="M9.5 18h5M10 21h4" stroke="#3b82f6" stroke-width="1.65" stroke-linecap="round"/></svg>';

    function shuffle(array) {
      const copy = [...array];
      for (let i = copy.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [copy[i], copy[j]] = [copy[j], copy[i]];
      }
      return copy;
    }

    function refreshSuggestions() {
      suggestionChips.innerHTML = "";
      const selected = shuffle(suggestionPool).slice(0, 3);
      selected.forEach((text) => {
        const btn = document.createElement("button");
        btn.className = "chip";
        btn.innerHTML = '<span class="ask-icon">' + bulbIcon + '</span><span class="chip-text">' + text + '</span>';
        btn.addEventListener("click", () => askWithText(text));
        suggestionChips.appendChild(btn);
      });
    }

    function openAssistant() {
      assistantPanel.classList.add("open");
      launcher.style.display = "none";
      document.getElementById("q").focus();
    }

    function closeAssistant() {
      assistantPanel.classList.remove("open");
      launcher.style.display = "inline-flex";
    }
    function toggleSuggestions() {
      const isHidden = suggestionChips.classList.contains("hidden");
      suggestionChips.classList.toggle("hidden", !isHidden);
      suggestionsBox.classList.toggle("collapsed", !isHidden);
      toggleSuggestBtn.textContent = isHidden ? "收起 ▴" : "展开 ▾";
    }

    function appendBubble(role, text) {
      const wrap = document.createElement("div");
      wrap.className = role === "user" ? "msg user-wrap" : "msg";

      const avatar = document.createElement("div");
      avatar.className = "avatar " + (role === "user" ? "user-avatar" : "assistant-avatar");
      if (role === "user") {
        avatar.innerHTML = '<img class="avatar-img user-fill" src="/assistant/user-avatar" alt="用户头像" />';
      } else {
        avatar.innerHTML = '<img class="avatar-img" src="/assistant/avatar" alt="助手头像" />';
      }

      const div = document.createElement("div");
      div.className = "bubble " + role;
      div.textContent = text;

      wrap.appendChild(avatar);
      wrap.appendChild(div);
      chatBox.appendChild(wrap);
      chatBox.scrollTop = chatBox.scrollHeight;
      return div;
    }

    function renderAnswer(data) {
      if (!data || !data.success) {
        return "未获取到有效结果，请稍后重试。";
      }
      return data.answer || "暂无可用结论。";
    }

    function askWithText(text) {
      document.getElementById("q").value = text;
      ask();
    }

    async function ask() {
      const input = document.getElementById("q");
      const question = input.value.trim();
      if (!question) return;

      appendBubble("user", question);
      input.value = "";
      input.disabled = true;
      sendBtn.disabled = true;

      const assistantBubble = appendBubble("assistant", "正在分析问题...");
      try {
        const reqBody = { question };
        if (TENANT_ID) reqBody.tenant_id = TENANT_ID;
        const response = await fetch("/api/assistant/ask-stream", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(reqBody)
        });

        if (!response.ok) {
          assistantBubble.textContent = "服务请求失败，请检查接口状态。";
          return;
        }
        if (!response.body) {
          assistantBubble.textContent = "服务未返回流式内容，请稍后重试。";
          return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let buffer = "";
        let fullAnswer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split(String.fromCharCode(10));
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (!line.trim()) continue;
            let eventData;
            try {
              eventData = JSON.parse(line);
            } catch (e) {
              continue;
            }
            if (eventData.type === "meta") {
              assistantBubble.innerHTML = '<span class="loading-wrap">正在生成分析结论<div class="loading-bars"><span></span><span></span><span></span><span></span></div></span>';
            } else if (eventData.type === "delta") {
              fullAnswer += eventData.content || "";
              assistantBubble.textContent = fullAnswer;
              chatBox.scrollTop = chatBox.scrollHeight;
            } else if (eventData.type === "done" && !fullAnswer) {
              assistantBubble.textContent = "暂无可用结论。";
            }
          }
        }
      } catch (error) {
        assistantBubble.textContent = "网络异常，回答中断。请重试。";
      } finally {
        input.disabled = false;
        sendBtn.disabled = false;
        input.focus();
        refreshSuggestions();
      }
    }

    document.getElementById("q").addEventListener("keydown", function(event) {
      if (event.key === "Enter") {
        event.preventDefault();
        ask();
      }
    });
    launcher.addEventListener("click", openAssistant);
    closeBtn.addEventListener("click", closeAssistant);
    refreshPageBtn.addEventListener("click", () => window.location.reload());
    refreshSuggestBtn.addEventListener("click", refreshSuggestions);
    toggleSuggestBtn.addEventListener("click", toggleSuggestions);
    if (EMBED) {
      document.body.classList.add("embed-mode");
      document.title = "AI小助手";
    }
    refreshSuggestions();
    openAssistant();
  </script>
</body>
</html>
"""
