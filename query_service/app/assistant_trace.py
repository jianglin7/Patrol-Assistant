"""助手问答耗时与节点追踪（内存环形缓冲），仅供调试接口查询，不在助手页面展示。"""

from __future__ import annotations

import uuid
import hashlib
import re
from collections import deque
from dataclasses import dataclass, field
from threading import Lock
from time import monotonic
from typing import Any

from app.config import settings


_REDACTED = "[REDACTED]"
_QUESTION_REDACTED = "[QUESTION_REDACTED]"
_MAX_TRACE_TEXT_LEN = 240
_SENSITIVE_KEYWORDS = {
    "api_key",
    "apikey",
    "key",
    "token",
    "secret",
    "password",
    "passwd",
    "pwd",
    "authorization",
    "db_password",
    "mysql_password",
}
_KEY_VALUE_PATTERNS = (
    re.compile(
        r'(?i)("?(?:api[_-]?key|apikey|token|secret|password|passwd|pwd|authorization)"?\s*[:=]\s*")([^"\s,;&]+)("?)'
    ),
    re.compile(
        r"(?i)\b(api[_-]?key|apikey|token|secret|password|passwd|pwd|authorization)\b(\s*[:=]\s*)([^\s,;&]+)"
    ),
)
_BEARER_PATTERN = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
_DB_URI_PATTERN = re.compile(r"(?i)\b(?:jdbc:)?(?:mysql|postgresql|postgres|redis)://[^\s'\"<>]+")
_URL_CREDENTIAL_PATTERN = re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://)([^/\s:@]+):([^@\s/]+)@")
_ENV_PATTERN = re.compile(r"(?i)(?:^|[\s`'\"])(\.env)(?:$|[\s`'\"，。；;:：])")
_LONG_SQL_PATTERN = re.compile(
    r"(?is)\b(select|insert|update|delete|drop|truncate|alter|create)\b.{120,}"
)


def _short_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:16]


def _replace_quoted_secret(match: re.Match[str]) -> str:
    return f"{match.group(1)}{_REDACTED}{match.group(3)}"


def _replace_plain_secret(match: re.Match[str]) -> str:
    return f"{match.group(1)}{match.group(2)}{_REDACTED}"


def _is_sensitive_key(key: Any) -> bool:
    normalized = re.sub(r"[^a-z0-9_]+", "_", str(key or "").strip().lower()).strip("_")
    if normalized in _SENSITIVE_KEYWORDS:
        return True
    return any(token in normalized for token in ("password", "passwd", "token", "secret", "api_key", "apikey"))


def redact_sensitive_text(value: Any, *, max_len: int = _MAX_TRACE_TEXT_LEN) -> str:
    """Return a short, trace-safe string without obvious credentials or long SQL."""
    if value is None:
        return ""
    text = value if isinstance(value, str) else str(value)
    if not text:
        return ""

    redacted = _URL_CREDENTIAL_PATTERN.sub(r"\1[REDACTED]@", text)
    redacted = _DB_URI_PATTERN.sub("[DB_URI_REDACTED]", redacted)
    redacted = _BEARER_PATTERN.sub("Bearer [REDACTED]", redacted)
    redacted = _ENV_PATTERN.sub(" [ENV_REDACTED] ", redacted)
    redacted = _KEY_VALUE_PATTERNS[0].sub(_replace_quoted_secret, redacted)
    redacted = _KEY_VALUE_PATTERNS[1].sub(_replace_plain_secret, redacted)
    if len(redacted) > 160 and _LONG_SQL_PATTERN.search(redacted):
        redacted = _LONG_SQL_PATTERN.sub("[SQL_REDACTED]", redacted)
    if len(redacted) > max_len:
        redacted = redacted[:max_len] + "…"
    return redacted


def redact_trace_value(value: Any, *, max_len: int = _MAX_TRACE_TEXT_LEN, _depth: int = 0) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if _depth >= 3:
        return redact_sensitive_text(value, max_len=max_len)
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        for key, item in value.items():
            skey = str(key)
            clean[skey] = _REDACTED if _is_sensitive_key(skey) else redact_trace_value(item, max_len=max_len, _depth=_depth + 1)
        return clean
    if isinstance(value, (list, tuple, set)):
        return [redact_trace_value(item, max_len=max_len, _depth=_depth + 1) for item in list(value)[:20]]
    return redact_sensitive_text(value, max_len=max_len)


@dataclass
class TraceEvent:
    node: str
    t_rel_ms: float
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class AssistantTraceRecord:
    id: str
    endpoint: str
    question: str
    question_len: int
    question_hash: str
    tenant_id: str
    start_mono: float
    events: list[TraceEvent] = field(default_factory=list)
    status: str = "running"  # running | ok | error
    error: str | None = None

    def to_summary(self) -> dict[str, Any]:
        last = self.events[-1] if self.events else None
        total_ms = last.t_rel_ms if last else 0.0
        return {
            "id": self.id,
            "endpoint": self.endpoint,
            "question_preview": self.question[:120] + ("…" if len(self.question) > 120 else ""),
            "question_len": self.question_len,
            "question_hash": self.question_hash,
            "tenant_id": self.tenant_id,
            "status": self.status,
            "total_ms": round(total_ms, 2),
            "event_count": len(self.events),
        }

    def to_detail(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "endpoint": self.endpoint,
            "question": self.question,
            "question_len": self.question_len,
            "question_hash": self.question_hash,
            "tenant_id": self.tenant_id,
            "status": self.status,
            "error": self.error,
            "events": [
                {"node": e.node, "t_rel_ms": round(e.t_rel_ms, 2), "meta": e.meta}
                for e in self.events
            ],
        }


class AssistantTraceStore:
    """线程安全；条目数有上限，超出则丢弃最旧记录。"""

    def __init__(self, max_entries: int) -> None:
        self._max = max(10, max_entries)
        self._lock = Lock()
        self._order: deque[str] = deque()
        self._by_id: dict[str, AssistantTraceRecord] = {}

    def begin(self, endpoint: str, question: str, tenant_id: str) -> str:
        tid = str(uuid.uuid4())
        raw_question = question or ""
        rec = AssistantTraceRecord(
            id=tid,
            endpoint=endpoint,
            question=_QUESTION_REDACTED,
            question_len=len(raw_question),
            question_hash=_short_hash(raw_question) if raw_question else "",
            tenant_id=redact_sensitive_text(tenant_id or "", max_len=80),
            start_mono=monotonic(),
        )
        with self._lock:
            self._by_id[tid] = rec
            self._order.append(tid)
            while len(self._order) > self._max:
                old = self._order.popleft()
                self._by_id.pop(old, None)
        return tid

    def event(self, trace_id: str | None, node: str, **meta: Any) -> None:
        if not trace_id or not settings.assistant_trace_enabled:
            return
        t_rel_ms = 0.0
        with self._lock:
            rec = self._by_id.get(trace_id)
            if not rec:
                return
            t_rel_ms = (monotonic() - rec.start_mono) * 1000.0
            clean_meta = {
                str(k): redact_trace_value(v)
                for k, v in meta.items()
                if v is not None and not _is_sensitive_key(k)
            }
            rec.events.append(TraceEvent(node=node, t_rel_ms=t_rel_ms, meta=clean_meta))

    def finalize(self, trace_id: str | None, status: str, error: str | None = None) -> None:
        if not trace_id or not settings.assistant_trace_enabled:
            return
        with self._lock:
            rec = self._by_id.get(trace_id)
            if not rec or rec.status != "running":
                return
            rec.status = status
            rec.error = redact_sensitive_text(error, max_len=200) if error else None

    def list_recent(self, limit: int) -> list[dict[str, Any]]:
        if not settings.assistant_trace_enabled:
            return []
        lim = max(1, min(500, limit))
        with self._lock:
            ids = list(self._order)
        ids.reverse()
        out: list[dict[str, Any]] = []
        for tid in ids[:lim]:
            with self._lock:
                rec = self._by_id.get(tid)
            if rec:
                out.append(rec.to_summary())
        return out

    def get(self, trace_id: str) -> AssistantTraceRecord | None:
        with self._lock:
            return self._by_id.get(trace_id)


assistant_trace_store = AssistantTraceStore(settings.assistant_trace_max_entries)


def trace_emit(trace_id: str | None, node: str, **meta: Any) -> None:
    assistant_trace_store.event(trace_id, node, **meta)
