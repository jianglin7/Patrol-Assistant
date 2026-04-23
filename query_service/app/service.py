import json
from datetime import date, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from app.db import get_connection
from app.registry import QueryTemplate, TemplateRegistry
from app.schemas import ExecuteRequest, ExecuteResponse, ExecuteMeta


class QueryService:
    def __init__(self, registry: TemplateRegistry | None = None):
        self.registry = registry or TemplateRegistry()

    def execute(self, request: ExecuteRequest) -> ExecuteResponse:
        request_id = request.request_id or uuid4().hex
        started_at = datetime.now()

        template = self.registry.get_template(request.template_id, request.tenant_id)
        if not template:
            self._safe_write_audit_log(
                request_id=request_id,
                request=request,
                normalized_params={"tenant_id": request.tenant_id},
                success=False,
                result_count=0,
                started_at=started_at,
                error_code="TEMPLATE_NOT_FOUND",
                error_msg=f"template `{request.template_id}` is not enabled for tenant `{request.tenant_id}`",
            )
            raise HTTPException(
                status_code=404,
                detail={
                    "request_id": request_id,
                    "success": False,
                    "error_code": "TEMPLATE_NOT_FOUND",
                    "error_msg": f"template `{request.template_id}` is not enabled for tenant `{request.tenant_id}`",
                },
            )

        try:
            normalized_params = self._normalize_and_validate_params(
                template=template,
                tenant_id=request.tenant_id,
                params=request.params,
            )
            rows = self._run_query(template.template_sql, normalized_params)
        except HTTPException as exc:
            self._safe_write_audit_log(
                request_id=request_id,
                request=request,
                normalized_params={"tenant_id": request.tenant_id, **request.params},
                success=False,
                result_count=0,
                started_at=started_at,
                error_code=exc.detail["error_code"],
                error_msg=exc.detail["error_msg"],
            )
            raise
        except Exception as exc:  # pragma: no cover - runtime guard
            self._safe_write_audit_log(
                request_id=request_id,
                request=request,
                normalized_params={"tenant_id": request.tenant_id, **request.params},
                success=False,
                result_count=0,
                started_at=started_at,
                error_code="QUERY_EXECUTION_FAILED",
                error_msg=str(exc),
            )
            raise HTTPException(
                status_code=500,
                detail={
                    "request_id": request_id,
                    "success": False,
                    "error_code": "QUERY_EXECUTION_FAILED",
                    "error_msg": str(exc),
                },
            ) from exc

        self._safe_write_audit_log(
            request_id=request_id,
            request=request,
            normalized_params=normalized_params,
            success=True,
            result_count=len(rows),
            started_at=started_at,
            error_code=None,
            error_msg=None,
        )

        return ExecuteResponse(
            request_id=request_id,
            success=True,
            template_id=template.template_id,
            template_name=template.template_name,
            data=rows,
            meta=ExecuteMeta(
                row_count=len(rows),
                executed_at=datetime.now().isoformat(timespec="seconds"),
                normalized_params=normalized_params,
                result_schema=template.result_schema or None,
            ),
        )

    def _safe_write_audit_log(self, **kwargs: Any) -> None:
        try:
            self._write_audit_log(**kwargs)
        except Exception:
            # 审计失败不应影响主查询链路。
            return

    def _normalize_and_validate_params(
        self,
        template: QueryTemplate,
        tenant_id: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        schema = template.param_schema or {}
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        defaults = schema.get("defaults", {})

        normalized: dict[str, Any] = {"tenant_id": tenant_id}
        merged_params = {**defaults, **params}

        if "now_time" not in merged_params:
            merged_params["now_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if "today" not in merged_params:
            merged_params["today"] = self._as_datetime(merged_params["now_time"]).date().isoformat()

        if "window_minutes" in merged_params and "window_start" not in merged_params:
            now_dt = self._as_datetime(merged_params["now_time"])
            merged_params["window_start"] = (
                now_dt - timedelta(minutes=int(merged_params["window_minutes"]))
            ).strftime("%Y-%m-%d %H:%M:%S")

        for key, value in merged_params.items():
            expected = properties.get(key, {}).get("type")
            normalized[key] = self._coerce_value(key, value, expected)

        missing = [field for field in required if field not in normalized or normalized[field] in (None, "")]
        if missing:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error_code": "MISSING_REQUIRED_PARAM",
                    "error_msg": f"missing required params: {', '.join(missing)}",
                },
            )

        return normalized

    def _coerce_value(self, name: str, value: Any, expected_type: str | None) -> Any:
        if expected_type is None or expected_type == "string":
            return value
        if expected_type == "integer":
            try:
                return int(value)
            except (TypeError, ValueError) as exc:
                raise self._invalid_param(name, "must be integer") from exc
        if expected_type == "number":
            try:
                return float(value)
            except (TypeError, ValueError) as exc:
                raise self._invalid_param(name, "must be number") from exc
        if expected_type == "date":
            try:
                return self._as_date(value).isoformat()
            except ValueError as exc:
                raise self._invalid_param(name, "must be in YYYY-MM-DD format") from exc
        if expected_type == "datetime":
            try:
                return self._as_datetime(value).strftime("%Y-%m-%d %H:%M:%S")
            except ValueError as exc:
                raise self._invalid_param(name, "must be in YYYY-MM-DD HH:MM:SS format") from exc
        return value

    @staticmethod
    def _run_query(template_sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(template_sql, params)
                rows = cursor.fetchall()
        return rows or []

    def _write_audit_log(
        self,
        request_id: str,
        request: ExecuteRequest,
        normalized_params: dict[str, Any],
        success: bool,
        result_count: int,
        started_at: datetime,
        error_code: str | None,
        error_msg: str | None,
    ) -> None:
        duration_ms = int((datetime.now() - started_at).total_seconds() * 1000)
        audit_sql = """
        INSERT INTO ai_query_audit_log (
          request_id,
          user_id,
          tenant_id,
          template_id,
          request_params,
          normalized_params,
          result_count,
          success_flag,
          error_code,
          error_msg,
          duration_ms,
          created_time
        ) VALUES (
          %(request_id)s,
          %(user_id)s,
          %(tenant_id)s,
          %(template_id)s,
          %(request_params)s,
          %(normalized_params)s,
          %(result_count)s,
          %(success_flag)s,
          %(error_code)s,
          %(error_msg)s,
          %(duration_ms)s,
          %(created_time)s
        )
        """

        payload = {
            "request_id": request_id,
            "user_id": request.user_id,
            "tenant_id": request.tenant_id,
            "template_id": request.template_id,
            "request_params": json.dumps(request.params, ensure_ascii=False),
            "normalized_params": json.dumps(normalized_params, ensure_ascii=False),
            "result_count": result_count,
            "success_flag": 1 if success else 0,
            "error_code": error_code,
            "error_msg": error_msg,
            "duration_ms": duration_ms,
            "created_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(audit_sql, payload)

    @staticmethod
    def _as_datetime(value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        raise ValueError("invalid datetime")

    @staticmethod
    def _as_date(value: Any) -> date:
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.strptime(value, "%Y-%m-%d").date()
        raise ValueError("invalid date")

    @staticmethod
    def _invalid_param(name: str, msg: str) -> HTTPException:
        return HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error_code": "INVALID_PARAM",
                "error_msg": f"param `{name}` {msg}",
            },
        )
