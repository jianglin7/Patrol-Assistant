"""助手问答耗时与节点追踪（内存环形缓冲），仅供调试接口查询，不在助手页面展示。"""

from __future__ import annotations

import uuid
from collections import deque
from dataclasses import dataclass, field
from threading import Lock
from time import monotonic
from typing import Any

from app.config import settings


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
        rec = AssistantTraceRecord(
            id=tid,
            endpoint=endpoint,
            question=question or "",
            tenant_id=tenant_id or "",
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
            clean_meta = {k: v for k, v in meta.items() if v is not None}
            rec.events.append(TraceEvent(node=node, t_rel_ms=t_rel_ms, meta=clean_meta))

    def finalize(self, trace_id: str | None, status: str, error: str | None = None) -> None:
        if not trace_id or not settings.assistant_trace_enabled:
            return
        with self._lock:
            rec = self._by_id.get(trace_id)
            if not rec or rec.status != "running":
                return
            rec.status = status
            rec.error = error

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
