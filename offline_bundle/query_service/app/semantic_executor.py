from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from app.schemas import ExecuteRequest
from app.semantic_planner import load_semantic_resources
from app.service import QueryService


_ERROR_CODE_MAP = {
    "TEMPLATE_NOT_FOUND": "E_TEMPLATE_NOT_FOUND",
    "MISSING_REQUIRED_PARAM": "E_TEMPLATE_PARAM_MISSING",
    "INVALID_PARAM": "E_FILTER_CONFLICT",
    "READONLY_SQL_BLOCKED": "E_SQL_READONLY_BLOCKED",
    "QUERY_EXECUTION_FAILED": "E_DB_QUERY_FAILED",
}


def _error_meta(code: str, message: str | None = None) -> dict[str, Any]:
    errors = load_semantic_resources().get("error_map", {})
    meta = errors.get(code, {}) if isinstance(errors, dict) else {}
    return {
        "code": code,
        "message": message or str(meta.get("message") or code),
        "retryable": bool(meta.get("retryable", False)),
    }


def _flatten_step_params(step: dict[str, Any]) -> dict[str, Any]:
    raw_params = step.get("params") if isinstance(step.get("params"), dict) else {}
    filters = raw_params.get("filters") if isinstance(raw_params.get("filters"), dict) else {}

    params: dict[str, Any] = {}
    for key, value in raw_params.items():
        if key in {"tenant_id", "filters"}:
            continue
        params[key] = value

    for key, value in filters.items():
        params[key] = value

    # Give SQL templates both business-facing names and existing helper-style aliases.
    alias_pairs = {
        "org_name": "org_keyword",
        "teacher_name": "teacher_keyword",
        "course_name": "course_keyword",
        "classroom_name": "classroom_keyword",
    }
    for src, dst in alias_pairs.items():
        if src in params and dst not in params:
            params[dst] = params[src]

    top_n = params.get("top_n")
    if top_n is not None and "limit" not in params:
        params["limit"] = top_n

    time_scope = str(params.get("time_scope") or "")
    if time_scope == "near_2h" and "window_minutes" not in params:
        params["window_minutes"] = 120
    elif time_scope == "last_3d" and "days" not in params:
        params["days"] = 3
    elif time_scope == "last_7d" and "days" not in params:
        params["days"] = 7
    elif time_scope == "last_30d" and "days" not in params:
        params["days"] = 30

    return {k: v for k, v in params.items() if v is not None}


def _map_exception(exc: Exception) -> dict[str, Any]:
    if isinstance(exc, HTTPException) and isinstance(exc.detail, dict):
        raw_code = str(exc.detail.get("error_code") or "E_INTERNAL")
        code = _ERROR_CODE_MAP.get(raw_code, raw_code if raw_code.startswith("E_") else "E_INTERNAL")
        return _error_meta(code, str(exc.detail.get("error_msg") or exc.detail.get("message") or code))

    text = str(exc)
    lowered = text.lower()
    if "connect" in lowered or "connection" in lowered:
        return _error_meta("E_DB_CONNECT_FAIL_BUSINESS", text)
    if "timeout" in lowered:
        return _error_meta("E_DB_QUERY_TIMEOUT", text)
    return _error_meta("E_DB_QUERY_FAILED", text)


def execute_semantic_plan(
    auto_plan: dict[str, Any],
    *,
    tenant_id: str | None = None,
    user_id: str | None = None,
    service: QueryService | None = None,
    continue_on_error: bool = True,
) -> dict[str, Any]:
    query_plan = auto_plan.get("query_plan") if isinstance(auto_plan.get("query_plan"), dict) else {}
    dsl = auto_plan.get("dsl") if isinstance(auto_plan.get("dsl"), dict) else {}
    tid = tenant_id or str(dsl.get("tenant_id") or "")
    svc = service or QueryService()

    steps = query_plan.get("steps") if isinstance(query_plan.get("steps"), list) else []
    step_results: list[dict[str, Any]] = []
    success_count = 0
    total_rows = 0
    first_error: dict[str, Any] | None = None

    if not steps:
        intent = str(query_plan.get("intent") or dsl.get("intent") or "")
        code = "E_INTENT_UNSUPPORTED" if intent in {"", "general"} else "E_TEMPLATE_NOT_FOUND"
        error = _error_meta(code)
        return {
            "success": False,
            "error_code": error["code"],
            "error_message": error["message"],
            "retryable": bool(error.get("retryable")),
            "summary": {
                "step_count": 0,
                "success_count": 0,
                "failed_count": 0,
                "total_row_count": 0,
            },
            "steps": [],
        }

    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            continue
        template_id = str(step.get("template_id") or "").strip()
        if not template_id:
            err = _error_meta("E_TEMPLATE_NOT_FOUND", "template_id is empty")
            first_error = first_error or err
            step_results.append({"index": index, "success": False, "template_id": "", "error": err})
            if not continue_on_error:
                break
            continue

        try:
            response = svc.execute(
                ExecuteRequest(
                    tenant_id=tid,
                    user_id=user_id,
                    template_id=template_id,
                    params=_flatten_step_params(step),
                )
            )
            payload = response.model_dump()
            row_count = int(payload.get("meta", {}).get("row_count") or 0)
            total_rows += row_count
            success_count += 1
            step_results.append(
                {
                    "index": index,
                    "success": True,
                    "template_id": template_id,
                    "template_name": payload.get("template_name"),
                    "row_count": row_count,
                    "data": payload.get("data") or [],
                    "meta": payload.get("meta") or {},
                }
            )
        except Exception as exc:  # pragma: no cover - runtime integration guard
            err = _map_exception(exc)
            first_error = first_error or err
            step_results.append(
                {
                    "index": index,
                    "success": False,
                    "template_id": template_id,
                    "row_count": 0,
                    "error": err,
                }
            )
            if not continue_on_error:
                break

    failed_count = len(step_results) - success_count
    if step_results and success_count == 0:
        error = first_error or _error_meta("E_TEMPLATE_NOT_FOUND")
        success = False
    else:
        error = _error_meta("OK")
        success = True

    return {
        "success": success,
        "error_code": error["code"],
        "error_message": error["message"],
        "retryable": bool(error.get("retryable")),
        "summary": {
            "step_count": len(step_results),
            "success_count": success_count,
            "failed_count": failed_count,
            "total_row_count": total_rows,
        },
        "steps": step_results,
    }
