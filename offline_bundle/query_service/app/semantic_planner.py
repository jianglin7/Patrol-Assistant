from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import settings

_REALTIME_MARKERS = ("实时", "当前", "正在", "此刻", "进行中", "近2小时")
_LAST_3D_MARKERS = ("近3天", "最近3天", "过去3天", "三天内", "3天内")
_LAST_7D_MARKERS = ("近7天", "最近7天", "过去7天", "7天内", "一周内", "近一周", "最近一周", "过去一周", "本周", "周内")
_LAST_30D_MARKERS = ("近30天", "最近30天", "过去30天", "30天内", "一个月内", "近一个月", "最近一个月", "本月", "近一月")
_DAILY_MARKERS = ("今日", "当天", "汇总", "已结束", "今天")
_WARNING_HINTS = ("预警", "告警", "风险")
_PATROL_HINTS = ("巡课", "巡查", "到课率", "抬头率", "前排满座率", "课堂活动", "活力")


def _resource_base_dir() -> Path:
    base_dir = Path(__file__).resolve().parent.parent
    custom = (settings.assistant_auto_plan_resource_dir or "resources/assistant_semantic").strip()
    return (base_dir / custom).resolve()


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_semantic_resources() -> dict[str, Any]:
    base = _resource_base_dir()
    intents = _load_json(base / "intents.json")
    templates = _load_json(base / "templates.json")
    metrics = _load_json(base / "metrics.json")
    errors = _load_json(base / "error_codes.json")

    intent_items = intents.get("items") if isinstance(intents.get("items"), list) else []
    template_items = templates.get("items") if isinstance(templates.get("items"), list) else []
    metric_items = metrics.get("items") if isinstance(metrics.get("items"), list) else []
    error_items = errors.get("items") if isinstance(errors.get("items"), list) else []

    template_map = {
        str(item.get("intent") or "").strip(): item
        for item in template_items
        if str(item.get("intent") or "").strip()
    }
    intent_map = {
        str(item.get("intent") or "").strip(): item
        for item in intent_items
        if str(item.get("intent") or "").strip()
    }
    error_map = {
        str(item.get("code") or "").strip(): item
        for item in error_items
        if str(item.get("code") or "").strip()
    }

    return {
        "version": {
            "intents": intents.get("version"),
            "templates": templates.get("version"),
            "metrics": metrics.get("version"),
            "errors": errors.get("version"),
        },
        "intents": intent_items,
        "intent_map": intent_map,
        "templates": template_map,
        "metrics": metric_items,
        "error_map": error_map,
    }


def _text_has_any(text: str, keywords: list[str] | tuple[str, ...]) -> bool:
    return any(k and k in text for k in keywords)


def _extract_metric_hits(question: str, metric_items: list[dict[str, Any]]) -> tuple[list[str], dict[str, float]]:
    metric_ids: list[str] = []
    intent_scores: dict[str, float] = {}
    q = question.strip()
    for item in metric_items:
        metric_id = str(item.get("metric_id") or "").strip()
        if not metric_id:
            continue
        aliases = item.get("aliases") if isinstance(item.get("aliases"), list) else []
        if not aliases:
            continue
        if not _text_has_any(q, tuple(str(x) for x in aliases)):
            continue
        metric_ids.append(metric_id)
        weights = item.get("intent_weights") if isinstance(item.get("intent_weights"), dict) else {}
        for intent, weight in weights.items():
            try:
                w = float(weight)
            except (TypeError, ValueError):
                continue
            intent_scores[intent] = intent_scores.get(intent, 0.0) + w
    return metric_ids, intent_scores


def _intent_score_from_keywords(question: str, intent_item: dict[str, Any]) -> float:
    score = 0.0
    aliases = intent_item.get("aliases") if isinstance(intent_item.get("aliases"), list) else []
    keywords = intent_item.get("keywords") if isinstance(intent_item.get("keywords"), list) else []
    for alias in aliases:
        a = str(alias).strip()
        if a and a in question:
            score += 1.2
    for keyword in keywords:
        k = str(keyword).strip()
        if k and k in question:
            score += 0.9
    return score


def _derive_time_scope(question: str, default_scope: str) -> dict[str, str]:
    q = question.strip()
    if _text_has_any(q, _LAST_3D_MARKERS):
        return {"mode": "relative", "status": "last_3d", "label": "近3天"}
    if _text_has_any(q, _LAST_7D_MARKERS):
        return {"mode": "relative", "status": "last_7d", "label": "近7天"}
    if _text_has_any(q, _LAST_30D_MARKERS):
        return {"mode": "relative", "status": "last_30d", "label": "近30天"}
    if _text_has_any(q, _REALTIME_MARKERS):
        return {"mode": "realtime", "status": "live", "label": "当前在课"}
    if _text_has_any(q, _DAILY_MARKERS):
        return {"mode": "today", "status": "finished", "label": "今日已结束"}

    mapping = {
        "today_live": {"mode": "today", "status": "live", "label": "今日在课"},
        "today_finished": {"mode": "today", "status": "finished", "label": "今日已结束"},
        "today": {"mode": "today", "status": "all", "label": "今日"},
        "near_2h": {"mode": "relative", "status": "near_2h", "label": "近2小时"},
        "last_3d": {"mode": "relative", "status": "last_3d", "label": "近3天"},
        "last_7d": {"mode": "relative", "status": "last_7d", "label": "近7天"},
        "last_30d": {"mode": "relative", "status": "last_30d", "label": "近30天"},
        "latest": {"mode": "latest", "status": "latest", "label": "最近一条"},
        "none": {"mode": "none", "status": "none", "label": "无"},
    }
    return mapping.get(default_scope, {"mode": "today", "status": "finished", "label": "今日已结束"})


def _derive_dimensions(filters: dict[str, Any], metric_ids: list[str]) -> list[str]:
    dims: list[str] = []
    if filters.get("org_keyword"):
        dims.append("org")
    if filters.get("teacher_keyword"):
        dims.append("teacher")
    if filters.get("course_keyword"):
        dims.append("course")
    if filters.get("classroom_keyword"):
        dims.append("classroom")
    if filters.get("leti_min") is not None or filters.get("leti_max") is not None:
        dims.append("section")
    if filters.get("subject_source") is not None:
        dims.append("subject_source")

    if not dims:
        dims.extend(["org", "course", "section"])
    if metric_ids and "course" not in dims:
        dims.append("course")
    return dims


def _normalize_filters(query_options: dict[str, Any]) -> dict[str, Any]:
    return {
        "org_name": query_options.get("org_keyword"),
        "teacher_name": query_options.get("teacher_keyword"),
        "course_name": query_options.get("course_keyword"),
        "classroom_name": query_options.get("classroom_keyword"),
        "leti_min": query_options.get("leti_min"),
        "leti_max": query_options.get("leti_max"),
        "subject_source": query_options.get("subject_source"),
    }


def _fallback_intent(question: str) -> str:
    q = question.strip()
    if _text_has_any(q, _WARNING_HINTS):
        if _text_has_any(q, _REALTIME_MARKERS):
            return "realtime_warning"
        return "daily_warning"
    if _text_has_any(q, _PATROL_HINTS):
        if _text_has_any(q, _REALTIME_MARKERS):
            return "realtime_patrol"
        return "daily_patrol"
    return "general"


def plan_auto_query(
    question: str,
    tenant_id: str,
    query_options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resources = load_semantic_resources()
    q = (question or "").strip()
    options = query_options or {}

    metric_ids, metric_scores = _extract_metric_hits(q, resources["metrics"])
    scores: dict[str, float] = {}
    for item in resources["intents"]:
        intent = str(item.get("intent") or "").strip()
        if not intent or intent == "general":
            continue
        scores[intent] = _intent_score_from_keywords(q, item) + metric_scores.get(intent, 0.0)

    if _text_has_any(q, _WARNING_HINTS):
        scores["daily_warning"] = scores.get("daily_warning", 0.0) + 0.4
        scores["realtime_warning"] = scores.get("realtime_warning", 0.0) + (0.5 if _text_has_any(q, _REALTIME_MARKERS) else 0.2)
        if _text_has_any(q, _LAST_3D_MARKERS + _LAST_7D_MARKERS + _LAST_30D_MARKERS):
            scores["warning_trend"] = scores.get("warning_trend", 0.0) + 1.4
    if _text_has_any(q, _PATROL_HINTS):
        scores["daily_patrol"] = scores.get("daily_patrol", 0.0) + 0.4
        scores["realtime_patrol"] = scores.get("realtime_patrol", 0.0) + (0.5 if _text_has_any(q, _REALTIME_MARKERS) else 0.2)

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    best_intent = ranked[0][0] if ranked and ranked[0][1] > 0 else _fallback_intent(q)
    best_score = ranked[0][1] if ranked else 0.0
    second_score = ranked[1][1] if len(ranked) > 1 else 0.0

    if best_intent == "general":
        confidence = 0.2
    elif best_score <= 0:
        confidence = 0.35
    else:
        confidence = min(0.99, round(0.45 + (best_score - second_score) / max(1.0, best_score + second_score), 3))

    intent_meta = resources["intent_map"].get(best_intent) or resources["intent_map"].get("general", {})
    template_meta = resources["templates"].get(best_intent, {"template_ids": [], "execute_bucket": "general"})

    top_n = options.get("top_n")
    try:
        top_n_int = int(top_n)
    except (TypeError, ValueError):
        top_n_int = int(getattr(settings, "assistant_default_top_n", 5) or 5)
    top_n_int = max(1, min(int(getattr(settings, "assistant_max_top_n", 20) or 20), top_n_int))

    filters = _normalize_filters(options)
    dimensions = _derive_dimensions(filters, metric_ids)
    time_scope = _derive_time_scope(q, str(intent_meta.get("default_time_scope") or "today_finished"))

    dsl = {
        "tenant_id": tenant_id,
        "question": q,
        "intent": best_intent,
        "time_scope": time_scope,
        "metrics": metric_ids,
        "dimensions": dimensions,
        "filters": filters,
        "top_n": top_n_int,
        "output_blocks": ["summary", "core_metrics", "top_list", "advice", "notes"],
    }

    query_plan = {
        "intent": best_intent,
        "execute_bucket": str(template_meta.get("execute_bucket") or "general"),
        "template_ids": list(template_meta.get("template_ids") or []),
        "confidence": confidence,
        "steps": [
            {
                "step_type": "query",
                "template_id": tid,
                "params": {
                    "tenant_id": tenant_id,
                    "time_scope": time_scope.get("status"),
                    "filters": filters,
                    "top_n": top_n_int,
                },
            }
            for tid in list(template_meta.get("template_ids") or [])
        ],
    }

    if best_intent == "general":
        error = resources["error_map"].get("E_INTENT_UNSUPPORTED", {})
    else:
        error = resources["error_map"].get("OK", {})

    return {
        "dsl": dsl,
        "query_plan": query_plan,
        "error": {
            "code": str(error.get("code") or "OK"),
            "message": str(error.get("message") or "成功"),
            "retryable": bool(error.get("retryable", False)),
        },
        "resources_version": resources.get("version", {}),
    }
