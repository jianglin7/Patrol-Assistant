import json
from dataclasses import dataclass
from typing import Any

from app.builtin_templates import get_builtin_template_definition
from app.config import settings
from app.db import get_control_connection


@dataclass
class QueryTemplate:
    template_id: str
    template_name: str
    template_sql: str
    param_schema: dict[str, Any]
    result_schema: dict[str, Any]


class TemplateRegistry:
    def get_template(self, template_id: str, tenant_id: str) -> QueryTemplate | None:
        row = None
        sql = """
        SELECT
          template_id,
          template_name,
          template_sql,
          param_schema,
          result_schema
        FROM ai_query_template_registry
        WHERE template_id = %s
          AND enabled_flag = 1
          AND (tenant_id = %s OR tenant_id = 'default')
        ORDER BY CASE WHEN tenant_id = %s THEN 0 ELSE 1 END
        LIMIT 1
        """
        try:
            with get_control_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (template_id, tenant_id, tenant_id))
                    row = cursor.fetchone()
        except Exception:
            if not settings.assistant_builtin_template_fallback_enabled:
                raise

        if not row:
            return self._get_builtin_template(template_id)

        return QueryTemplate(
            template_id=row["template_id"],
            template_name=row["template_name"],
            template_sql=row["template_sql"],
            param_schema=self._decode_json(row.get("param_schema")),
            result_schema=self._decode_json(row.get("result_schema")),
        )

    @staticmethod
    def _get_builtin_template(template_id: str) -> QueryTemplate | None:
        if not settings.assistant_builtin_template_fallback_enabled:
            return None
        item = get_builtin_template_definition(template_id)
        if not item:
            return None
        return QueryTemplate(
            template_id=item["template_id"],
            template_name=item["template_name"],
            template_sql=item["template_sql"],
            param_schema=item.get("param_schema") or {},
            result_schema=item.get("result_schema") or {},
        )

    @staticmethod
    def _decode_json(value: Any) -> dict[str, Any]:
        if not value:
            return {}
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            return json.loads(value)
        return {}
