import json
from dataclasses import dataclass
from typing import Any

from app.db import get_connection


@dataclass
class QueryTemplate:
    template_id: str
    template_name: str
    template_sql: str
    param_schema: dict[str, Any]
    result_schema: dict[str, Any]


class TemplateRegistry:
    def get_template(self, template_id: str, tenant_id: str) -> QueryTemplate | None:
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
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (template_id, tenant_id, tenant_id))
                row = cursor.fetchone()

        if not row:
            return None

        return QueryTemplate(
            template_id=row["template_id"],
            template_name=row["template_name"],
            template_sql=row["template_sql"],
            param_schema=self._decode_json(row.get("param_schema")),
            result_schema=self._decode_json(row.get("result_schema")),
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
