from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.builtin_templates import get_builtin_template_definition, list_builtin_template_ids  # noqa: E402
from app.db import get_control_connection  # noqa: E402


UPSERT_SQL = """
REPLACE INTO ai_query_template_registry (
  template_id,
  tenant_id,
  template_name,
  template_category,
  template_sql,
  param_schema,
  result_schema,
  enabled_flag
) VALUES (
  %(template_id)s,
  %(tenant_id)s,
  %(template_name)s,
  %(template_category)s,
  %(template_sql)s,
  %(param_schema)s,
  %(result_schema)s,
  1
)
"""


def _payload(item: dict[str, Any], tenant_id: str) -> dict[str, Any]:
    return {
        "template_id": item["template_id"],
        "tenant_id": tenant_id,
        "template_name": item["template_name"],
        "template_category": item.get("template_category"),
        "template_sql": item["template_sql"],
        "param_schema": json.dumps(item.get("param_schema") or {}, ensure_ascii=False),
        "result_schema": json.dumps(item.get("result_schema") or {}, ensure_ascii=False),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed built-in semantic query templates into control database.")
    parser.add_argument("--tenant-id", default="default", help="Template tenant id. Default: default")
    parser.add_argument("--dry-run", action="store_true", help="Print payload summary without writing database.")
    args = parser.parse_args()

    items = [get_builtin_template_definition(tid) for tid in list_builtin_template_ids()]
    payloads = [_payload(item, args.tenant_id) for item in items if item]

    if args.dry_run:
        for payload in payloads:
            print(f"{payload['template_id']}\t{payload['template_name']}\t{payload['template_category']}")
        print(f"total={len(payloads)}")
        return

    with get_control_connection() as conn:
        with conn.cursor() as cursor:
            cursor.executemany(UPSERT_SQL, payloads)
    print(f"seeded {len(payloads)} templates for tenant `{args.tenant_id}`")


if __name__ == "__main__":
    main()
