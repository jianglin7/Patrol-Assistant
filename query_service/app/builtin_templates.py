from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.config import settings


def _scope_is_live_sql() -> str:
    return "COALESCE(%(time_scope)s, 'finished') IN ('live', 'realtime', 'current', 'today_live')"


_COURSE_FILTER_SQL = """
  AND (%(org_keyword)s IS NULL OR COALESCE(c.tecl_org_name, '') LIKE CONCAT('%%', %(org_keyword)s, '%%'))
  AND (%(teacher_keyword)s IS NULL OR COALESCE(c.teacher_names, '') LIKE CONCAT('%%', %(teacher_keyword)s, '%%'))
  AND (
    %(course_keyword)s IS NULL
    OR COALESCE(c.subject_name, c.teaching_class_name, '') LIKE CONCAT('%%', %(course_keyword)s, '%%')
  )
  AND (%(classroom_keyword)s IS NULL OR COALESCE(c.classroom_name, '') LIKE CONCAT('%%', %(classroom_keyword)s, '%%'))
  AND (%(leti_min)s IS NULL OR COALESCE(c.leti_number, 0) >= %(leti_min)s)
  AND (%(leti_max)s IS NULL OR COALESCE(c.leti_number, 0) <= %(leti_max)s)
  AND (%(subject_source)s IS NULL OR COALESCE(c.subject_source, 0) = %(subject_source)s)
"""

_LIVE_COURSE_TIME_SQL = """
  AND c.course_start_time <= %(now_time)s
  AND c.course_end_time >= %(now_time)s
"""

_DAILY_FINISHED_COURSE_TIME_SQL = """
  AND DATE(c.course_start_time) = %(today)s
  AND c.course_end_time < %(now_time)s
"""

_FLEX_COURSE_TIME_SQL = f"""
  AND (
    ({_scope_is_live_sql()} AND c.course_start_time <= %(now_time)s AND c.course_end_time >= %(now_time)s)
    OR
    (
      COALESCE(%(time_scope)s, '') IN ('last_3d', 'last_7d', 'last_30d')
      AND c.course_start_time >= DATE_SUB(%(now_time)s, INTERVAL %(days)s DAY)
      AND c.course_start_time <= %(now_time)s
    )
    OR
    (
      NOT ({_scope_is_live_sql()})
      AND COALESCE(%(time_scope)s, '') NOT IN ('last_3d', 'last_7d', 'last_30d')
      AND DATE(c.course_start_time) = %(today)s
      AND c.course_end_time < %(now_time)s
    )
  )
"""

_FOCUS_CONDITION_SQL = """
COALESCE(c.tias_att_percent, 100) < %(focus_attendance_lt)s
AND COALESCE(c.tias_front_full_percent, 100) < %(focus_front_full_lt)s
AND COALESCE(c.tias_rise_percent, 100) < %(focus_rise_lt)s
"""

_VITALITY_CONDITION_SQL = """
COALESCE(c.tias_att_percent, 0) >= %(vitality_attendance_gte)s
AND COALESCE(c.tias_front_full_percent, 0) >= %(vitality_front_full_gte)s
AND COALESCE(c.tias_rise_percent, 0) >= %(vitality_rise_gte)s
"""


def _warning_time_sql(scope: str) -> str:
    if scope == "live":
        return "AND r.warning_time >= DATE_SUB(%(now_time)s, INTERVAL 2 HOUR)"
    if scope == "daily":
        return "AND DATE(r.warning_time) = %(today)s"
    return f"""
  AND (
    ({_scope_is_live_sql()} AND r.warning_time >= DATE_SUB(%(now_time)s, INTERVAL 2 HOUR))
    OR
    (
      COALESCE(%(time_scope)s, '') IN ('last_3d', 'last_7d', 'last_30d')
      AND r.warning_time >= DATE_SUB(%(now_time)s, INTERVAL %(days)s DAY)
      AND r.warning_time <= %(now_time)s
    )
    OR
    (
      NOT ({_scope_is_live_sql()})
      AND COALESCE(%(time_scope)s, '') NOT IN ('last_3d', 'last_7d', 'last_30d')
      AND DATE(r.warning_time) = %(today)s
    )
  )
"""


def _course_time_sql(scope: str) -> str:
    if scope == "live":
        return _LIVE_COURSE_TIME_SQL
    if scope == "daily":
        return _DAILY_FINISHED_COURSE_TIME_SQL
    return _FLEX_COURSE_TIME_SQL


def _warning_union_sql(scope: str) -> str:
    course_time = _course_time_sql(scope)
    warning_time = _warning_time_sql(scope)
    return f"""
(
  SELECT
    'study' AS warning_domain,
    r.course_id,
    r.tenant_id,
    r.course_name,
    r.clro_name,
    r.org_name,
    r.indicator_id,
    r.indicator_code,
    r.indicator_name,
    r.warning_level,
    r.warning_time,
    r.handle_status,
    COALESCE(c.subject_name, c.teaching_class_name, r.course_name, CONCAT('课程#', r.course_id)) AS course_display_name,
    COALESCE(c.teacher_names, '未知教师') AS teacher_names,
    COALESCE(c.classroom_name, r.clro_name, '未知教室') AS classroom_name,
    COALESCE(c.leti_name, CONCAT('第', COALESCE(c.leti_number, 0), '节')) AS leti_name,
    COALESCE(c.leti_number, 0) AS leti_number,
    COALESCE(c.tecl_org_name, r.org_name, '未知学院') AS course_org_name
  FROM t_warning_study_record r
  INNER JOIN t_tias_course c
    ON c.course_id = r.course_id
   AND c.tenant_id = r.tenant_id
   AND c.delete_flag = 0
  WHERE r.delete_flag = 0
    AND r.tenant_id = %(tenant_id)s
    {course_time}
    {warning_time}
    {_COURSE_FILTER_SQL}
  UNION ALL
  SELECT
    'teaching' AS warning_domain,
    r.course_id,
    r.tenant_id,
    r.course_name,
    r.clro_name,
    r.org_name,
    r.indicator_id,
    r.indicator_code,
    r.indicator_name,
    r.warning_level,
    r.warning_time,
    r.handle_status,
    COALESCE(c.subject_name, c.teaching_class_name, r.course_name, CONCAT('课程#', r.course_id)) AS course_display_name,
    COALESCE(c.teacher_names, '未知教师') AS teacher_names,
    COALESCE(c.classroom_name, r.clro_name, '未知教室') AS classroom_name,
    COALESCE(c.leti_name, CONCAT('第', COALESCE(c.leti_number, 0), '节')) AS leti_name,
    COALESCE(c.leti_number, 0) AS leti_number,
    COALESCE(c.tecl_org_name, r.org_name, '未知学院') AS course_org_name
  FROM t_warning_teaching_record r
  INNER JOIN t_tias_course c
    ON c.course_id = r.course_id
   AND c.tenant_id = r.tenant_id
   AND c.delete_flag = 0
  WHERE r.delete_flag = 0
    AND r.tenant_id = %(tenant_id)s
    {course_time}
    {warning_time}
    {_COURSE_FILTER_SQL}
) w
"""


def _base_schema() -> dict[str, Any]:
    return {
        "required": [],
        "properties": {
            "today": {"type": "date"},
            "now_time": {"type": "datetime"},
            "limit": {"type": "integer"},
        },
        "defaults": {
            "time_scope": "finished",
            "org_keyword": None,
            "teacher_keyword": None,
            "course_keyword": None,
            "classroom_keyword": None,
            "leti_min": None,
            "leti_max": None,
            "subject_source": None,
            "limit": settings.assistant_default_top_n,
            "focus_attendance_lt": settings.patrol_focus_attendance_lt,
            "focus_front_full_lt": settings.patrol_focus_front_full_lt,
            "focus_rise_lt": settings.patrol_focus_rise_lt,
            "vitality_attendance_gte": settings.patrol_vitality_attendance_gte,
            "vitality_front_full_gte": settings.patrol_vitality_front_full_gte,
            "vitality_rise_gte": settings.patrol_vitality_rise_gte,
            "days": 7,
        },
    }


def _template(
    template_id: str,
    template_name: str,
    category: str,
    sql: str,
    result_schema: dict[str, str] | None = None,
) -> dict[str, Any]:
    return {
        "template_id": template_id,
        "template_name": template_name,
        "template_category": category,
        "template_sql": sql.strip(),
        "param_schema": _base_schema(),
        "result_schema": result_schema or {},
    }


_PATROL_OVERVIEW_REALTIME_SQL = f"""
SELECT
  COALESCE(MIN(c.leti_name), '-') AS current_section,
  COUNT(*) AS course_section_count,
  COALESCE(ROUND(AVG(c.tias_att_percent), 2), 0) AS avg_attendance,
  COALESCE(ROUND(AVG(c.tias_front_full_percent), 2), 0) AS avg_front_full,
  COALESCE(ROUND(AVG(c.tias_rise_percent), 2), 0) AS avg_rise,
  COALESCE(SUM(CASE WHEN COALESCE(c.tias_att_percent, 100) < %(focus_attendance_lt)s THEN 1 ELSE 0 END), 0) AS low_attendance_count,
  COALESCE(SUM(CASE WHEN COALESCE(c.tias_front_full_percent, 100) < %(focus_front_full_lt)s THEN 1 ELSE 0 END), 0) AS low_front_full_count,
  COALESCE(SUM(CASE WHEN COALESCE(c.tias_rise_percent, 100) < %(focus_rise_lt)s THEN 1 ELSE 0 END), 0) AS low_rise_count,
  COALESCE(SUM(CASE WHEN COALESCE(c.tias_att_percent, 0) > 100 THEN 1 ELSE 0 END), 0) AS over_attendance_count,
  COALESCE(SUM(CASE WHEN {_FOCUS_CONDITION_SQL} THEN 1 ELSE 0 END), 0) AS focus_course_section_count,
  COALESCE(SUM(CASE WHEN {_VITALITY_CONDITION_SQL} THEN 1 ELSE 0 END), 0) AS high_vitality_course_section_count
FROM t_tias_course c
WHERE c.delete_flag = 0
  AND c.tenant_id = %(tenant_id)s
  {_LIVE_COURSE_TIME_SQL}
  {_COURSE_FILTER_SQL}
"""

_PATROL_OVERVIEW_DAILY_SQL = f"""
SELECT
  COUNT(*) AS patrolled_course_section_count,
  COUNT(DISTINCT c.leti_number) AS finished_section_count,
  COALESCE(ROUND(AVG(c.tias_att_percent), 2), 0) AS avg_attendance,
  COALESCE(ROUND(AVG(c.tias_front_full_percent), 2), 0) AS avg_front_full,
  COALESCE(ROUND(AVG(c.tias_rise_percent), 2), 0) AS avg_rise,
  COALESCE(SUM(CASE WHEN COALESCE(c.tias_att_percent, 100) < %(focus_attendance_lt)s THEN 1 ELSE 0 END), 0) AS low_attendance_count,
  COALESCE(SUM(CASE WHEN COALESCE(c.tias_front_full_percent, 100) < %(focus_front_full_lt)s THEN 1 ELSE 0 END), 0) AS low_front_full_count,
  COALESCE(SUM(CASE WHEN COALESCE(c.tias_rise_percent, 100) < %(focus_rise_lt)s THEN 1 ELSE 0 END), 0) AS low_rise_count,
  COALESCE(SUM(CASE WHEN COALESCE(c.tias_att_percent, 0) > 100 THEN 1 ELSE 0 END), 0) AS over_attendance_count,
  COALESCE(SUM(CASE WHEN {_FOCUS_CONDITION_SQL} THEN 1 ELSE 0 END), 0) AS focus_course_section_count,
  COALESCE(SUM(CASE WHEN {_VITALITY_CONDITION_SQL} THEN 1 ELSE 0 END), 0) AS high_vitality_course_section_count
FROM t_tias_course c
WHERE c.delete_flag = 0
  AND c.tenant_id = %(tenant_id)s
  {_DAILY_FINISHED_COURSE_TIME_SQL}
  {_COURSE_FILTER_SQL}
"""

_PATROL_SECTION_DISTRIBUTION_SQL = f"""
SELECT
  COALESCE(c.leti_number, 0) AS section_number,
  COALESCE(c.leti_name, CONCAT('第', COALESCE(c.leti_number, 0), '节')) AS section_name,
  COUNT(*) AS course_section_count,
  COALESCE(ROUND(AVG(c.tias_att_percent), 2), 0) AS avg_attendance,
  COALESCE(ROUND(AVG(c.tias_front_full_percent), 2), 0) AS avg_front_full,
  COALESCE(ROUND(AVG(c.tias_rise_percent), 2), 0) AS avg_rise,
  SUM(CASE WHEN {_FOCUS_CONDITION_SQL} THEN 1 ELSE 0 END) AS focus_course_section_count
FROM t_tias_course c
WHERE c.delete_flag = 0
  AND c.tenant_id = %(tenant_id)s
  {_DAILY_FINISHED_COURSE_TIME_SQL}
  {_COURSE_FILTER_SQL}
GROUP BY COALESCE(c.leti_number, 0), COALESCE(c.leti_name, CONCAT('第', COALESCE(c.leti_number, 0), '节'))
ORDER BY section_number
LIMIT %(limit)s
"""

_PATROL_ORG_RISK_SQL = f"""
SELECT
  COALESCE(c.tecl_org_name, '未知学院') AS org_name,
  COUNT(*) AS course_section_count,
  SUM(CASE WHEN {_FOCUS_CONDITION_SQL} THEN 1 ELSE 0 END) AS focus_course_section_count,
  COALESCE(ROUND(AVG(c.tias_att_percent), 2), 0) AS avg_attendance,
  COALESCE(ROUND(AVG(c.tias_front_full_percent), 2), 0) AS avg_front_full,
  COALESCE(ROUND(AVG(c.tias_rise_percent), 2), 0) AS avg_rise
FROM t_tias_course c
WHERE c.delete_flag = 0
  AND c.tenant_id = %(tenant_id)s
  {_FLEX_COURSE_TIME_SQL}
  {_COURSE_FILTER_SQL}
GROUP BY COALESCE(c.tecl_org_name, '未知学院')
ORDER BY focus_course_section_count DESC, course_section_count DESC, avg_attendance ASC
LIMIT %(limit)s
"""

_PATROL_FOCUS_TOP_SQL = f"""
SELECT
  COALESCE(c.subject_name, c.teaching_class_name, CONCAT('课程#', c.course_id)) AS course_name,
  COALESCE(c.teacher_names, '未知教师') AS teacher_names,
  COALESCE(c.classroom_name, '未知教室') AS classroom_name,
  COALESCE(c.leti_name, CONCAT('第', COALESCE(c.leti_number, 0), '节')) AS leti_name,
  COALESCE(c.leti_number, 0) AS leti_number,
  COALESCE(c.tecl_org_name, '未知学院') AS org_name,
  COALESCE(c.tias_att_percent, 0) AS att_percent,
  COALESCE(c.tias_front_full_percent, 0) AS front_full_percent,
  COALESCE(c.tias_rise_percent, 0) AS rise_percent
FROM t_tias_course c
WHERE c.delete_flag = 0
  AND c.tenant_id = %(tenant_id)s
  {_FLEX_COURSE_TIME_SQL}
  {_COURSE_FILTER_SQL}
  AND {_FOCUS_CONDITION_SQL}
ORDER BY att_percent ASC, rise_percent ASC, front_full_percent ASC
LIMIT %(limit)s
"""

_PATROL_VITALITY_TOP_SQL = f"""
SELECT
  COALESCE(c.subject_name, c.teaching_class_name, CONCAT('课程#', c.course_id)) AS course_name,
  COALESCE(c.teacher_names, '未知教师') AS teacher_names,
  COALESCE(c.classroom_name, '未知教室') AS classroom_name,
  COALESCE(c.leti_name, CONCAT('第', COALESCE(c.leti_number, 0), '节')) AS leti_name,
  COALESCE(c.leti_number, 0) AS leti_number,
  COALESCE(c.tecl_org_name, '未知学院') AS org_name,
  COALESCE(c.tias_att_percent, 0) AS att_percent,
  COALESCE(c.tias_front_full_percent, 0) AS front_full_percent,
  COALESCE(c.tias_rise_percent, 0) AS rise_percent
FROM t_tias_course c
WHERE c.delete_flag = 0
  AND c.tenant_id = %(tenant_id)s
  {_FLEX_COURSE_TIME_SQL}
  {_COURSE_FILTER_SQL}
  AND {_VITALITY_CONDITION_SQL}
ORDER BY att_percent DESC, front_full_percent DESC, rise_percent DESC
LIMIT %(limit)s
"""


def _warning_overview_sql(scope: str) -> str:
    course_time = _course_time_sql(scope)
    union_sql = _warning_union_sql(scope)
    return f"""
SELECT
  base.course_section_count,
  COUNT(w.course_id) AS warning_record_count,
  COUNT(DISTINCT w.course_id) AS warning_course_section_count,
  ROUND(IFNULL(COUNT(DISTINCT w.course_id) / NULLIF(base.course_section_count, 0), 0) * 100, 2) AS warning_ratio,
  COALESCE(SUM(CASE WHEN w.warning_level = 1 THEN 1 ELSE 0 END), 0) AS high_warning_count,
  COALESCE(ROUND(AVG(w.warning_level), 2), 0) AS avg_warning_level,
  CASE
    WHEN COALESCE(SUM(CASE WHEN w.warning_level = 1 THEN 1 ELSE 0 END), 0) > 0
      OR ROUND(IFNULL(COUNT(DISTINCT w.course_id) / NULLIF(base.course_section_count, 0), 0) * 100, 2) >= 50 THEN '高'
    WHEN COALESCE(SUM(CASE WHEN w.warning_level = 2 THEN 1 ELSE 0 END), 0) > 0
      OR ROUND(IFNULL(COUNT(DISTINCT w.course_id) / NULLIF(base.course_section_count, 0), 0) * 100, 2) >= 20 THEN '中'
    WHEN COUNT(w.course_id) > 0 THEN '低'
    ELSE '无'
  END AS overall_risk_level
FROM (
  SELECT COUNT(*) AS course_section_count
  FROM t_tias_course c
  WHERE c.delete_flag = 0
    AND c.tenant_id = %(tenant_id)s
    {course_time}
    {_COURSE_FILTER_SQL}
) base
LEFT JOIN {union_sql} ON 1 = 1
GROUP BY base.course_section_count
"""


def _warning_type_sql() -> str:
    union_sql = _warning_union_sql("flex")
    return f"""
SELECT
  COALESCE(w.indicator_name, '未知类型') AS indicator_name,
  COUNT(*) AS warning_count,
  COUNT(DISTINCT w.course_id) AS course_section_count,
  MIN(w.warning_level) AS worst_warning_level,
  MAX(w.warning_time) AS latest_warning_time
FROM {union_sql}
GROUP BY COALESCE(w.indicator_name, '未知类型')
ORDER BY warning_count DESC, latest_warning_time DESC
LIMIT %(limit)s
"""


def _warning_level_sql() -> str:
    union_sql = _warning_union_sql("flex")
    return f"""
SELECT
  w.warning_level,
  CASE w.warning_level
    WHEN 1 THEN '高'
    WHEN 2 THEN '中'
    WHEN 3 THEN '低'
    WHEN 4 THEN '提示'
    ELSE '未知'
  END AS warning_level_name,
  COUNT(*) AS warning_count,
  COUNT(DISTINCT w.course_id) AS course_section_count
FROM {union_sql}
GROUP BY w.warning_level
ORDER BY w.warning_level
"""


def _warning_course_top_sql() -> str:
    union_sql = _warning_union_sql("flex")
    return f"""
SELECT
  w.course_display_name AS course_name,
  w.teacher_names,
  w.classroom_name,
  w.leti_name,
  w.leti_number,
  w.course_org_name AS org_name,
  COUNT(*) AS warning_count,
  COUNT(DISTINCT w.indicator_name) AS indicator_type_count,
  MIN(w.warning_level) AS worst_warning_level,
  MAX(w.warning_time) AS latest_warning_time
FROM {union_sql}
GROUP BY
  w.course_id,
  w.course_display_name,
  w.teacher_names,
  w.classroom_name,
  w.leti_name,
  w.leti_number,
  w.course_org_name
ORDER BY warning_count DESC, worst_warning_level ASC, latest_warning_time DESC
LIMIT %(limit)s
"""


def _warning_org_top_sql() -> str:
    union_sql = _warning_union_sql("flex")
    return f"""
SELECT
  w.course_org_name AS org_name,
  COUNT(*) AS warning_count,
  COUNT(DISTINCT w.course_id) AS course_section_count,
  COUNT(DISTINCT w.indicator_name) AS indicator_type_count,
  MIN(w.warning_level) AS worst_warning_level
FROM {union_sql}
GROUP BY w.course_org_name
ORDER BY warning_count DESC, course_section_count DESC
LIMIT %(limit)s
"""


_WARNING_HANDLE_STATUS_SQL = """
SELECT
  COUNT(*) AS total_warning_count,
  COALESCE(SUM(CASE WHEN w.handle_status = 1 THEN 1 ELSE 0 END), 0) AS pending_count,
  COALESCE(SUM(CASE WHEN w.handle_status = 2 THEN 1 ELSE 0 END), 0) AS hang_count,
  COALESCE(SUM(CASE WHEN w.handle_status IN (3, 4) THEN 1 ELSE 0 END), 0) AS closed_count,
  ROUND(IFNULL(COALESCE(SUM(CASE WHEN w.handle_status = 1 THEN 1 ELSE 0 END), 0) / NULLIF(COUNT(*), 0), 0) * 100, 2) AS pending_ratio,
  ROUND(IFNULL(COALESCE(SUM(CASE WHEN w.handle_status IN (3, 4) THEN 1 ELSE 0 END), 0) / NULLIF(COUNT(*), 0), 0) * 100, 2) AS closed_ratio
FROM (
  SELECT handle_status
  FROM t_warning_study_record
  WHERE delete_flag = 0
    AND tenant_id = %(tenant_id)s
    AND DATE(warning_time) = %(today)s
  UNION ALL
  SELECT handle_status
  FROM t_warning_teaching_record
  WHERE delete_flag = 0
    AND tenant_id = %(tenant_id)s
    AND DATE(warning_time) = %(today)s
) w
"""

_WARNING_HANDLE_SLA_SQL = """
SELECT
  COALESCE(w.indicator_name, '未知类型') AS indicator_name,
  COUNT(*) AS warning_count,
  SUM(CASE WHEN w.handle_status = 1 THEN 1 ELSE 0 END) AS pending_count,
  SUM(CASE WHEN w.handle_status = 2 THEN 1 ELSE 0 END) AS hang_count,
  SUM(CASE WHEN w.handle_status IN (3, 4) THEN 1 ELSE 0 END) AS closed_count,
  ROUND(IFNULL(SUM(CASE WHEN w.handle_status IN (3, 4) THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 0) * 100, 2) AS closed_ratio
FROM (
  SELECT indicator_name, handle_status
  FROM t_warning_study_record
  WHERE delete_flag = 0
    AND tenant_id = %(tenant_id)s
    AND DATE(warning_time) = %(today)s
  UNION ALL
  SELECT indicator_name, handle_status
  FROM t_warning_teaching_record
  WHERE delete_flag = 0
    AND tenant_id = %(tenant_id)s
    AND DATE(warning_time) = %(today)s
) w
GROUP BY COALESCE(w.indicator_name, '未知类型')
ORDER BY pending_count DESC, warning_count DESC
LIMIT %(limit)s
"""

_WARNING_TREND_7D_SQL = f"""
SELECT
  DATE(x.warning_time) AS day,
  COUNT(*) AS warning_count,
  COUNT(DISTINCT x.course_id) AS course_section_count
FROM (
  SELECT r.course_id, r.warning_time
  FROM t_warning_study_record r
  INNER JOIN t_tias_course c
    ON c.course_id = r.course_id
   AND c.tenant_id = r.tenant_id
   AND c.delete_flag = 0
  WHERE r.delete_flag = 0
    AND r.tenant_id = %(tenant_id)s
    AND r.warning_time >= DATE_SUB(%(now_time)s, INTERVAL 7 DAY)
    AND r.warning_time <= %(now_time)s
    {_COURSE_FILTER_SQL}
  UNION ALL
  SELECT r.course_id, r.warning_time
  FROM t_warning_teaching_record r
  INNER JOIN t_tias_course c
    ON c.course_id = r.course_id
   AND c.tenant_id = r.tenant_id
   AND c.delete_flag = 0
  WHERE r.delete_flag = 0
    AND r.tenant_id = %(tenant_id)s
    AND r.warning_time >= DATE_SUB(%(now_time)s, INTERVAL 7 DAY)
    AND r.warning_time <= %(now_time)s
    {_COURSE_FILTER_SQL}
) x
GROUP BY DATE(x.warning_time)
ORDER BY day
"""

_STRATEGY_RULE_TRIGGER_SQL = """
SELECT
  COALESCE(i.indicator_name, e.alarm_desc, '未知规则') AS rule_name,
  e.alarm_desc,
  (
    SELECT COUNT(*)
    FROM (
      SELECT indicator_id, warning_time
      FROM t_warning_study_record
      WHERE delete_flag = 0
        AND tenant_id = %(tenant_id)s
        AND warning_time >= DATE_SUB(%(now_time)s, INTERVAL 7 DAY)
      UNION ALL
      SELECT indicator_id, warning_time
      FROM t_warning_teaching_record
      WHERE delete_flag = 0
        AND tenant_id = %(tenant_id)s
        AND warning_time >= DATE_SUB(%(now_time)s, INTERVAL 7 DAY)
    ) w
    WHERE w.indicator_id = e.indicator_id
  ) AS trigger_count_7d
FROM t_patrol_alarm_event e
LEFT JOIN t_patrol_indicator_type i
  ON i.id = e.indicator_id
 AND i.tenant_id = e.tenant_id
 AND i.delete_flag = 0
WHERE e.delete_flag = 0
  AND e.tenant_id = %(tenant_id)s
ORDER BY trigger_count_7d DESC, e.id
LIMIT %(limit)s
"""

_TEACHER_RISK_TOP_7D_SQL = """
SELECT
  COALESCE(c.teacher_names, '未知教师') AS teacher_names,
  COUNT(*) AS warning_count,
  COUNT(DISTINCT w.course_id) AS course_section_count,
  COUNT(DISTINCT w.indicator_name) AS indicator_type_count,
  MIN(w.warning_level) AS worst_warning_level,
  MAX(w.warning_time) AS latest_warning_time
FROM (
  SELECT course_id, tenant_id, indicator_name, warning_level, warning_time
  FROM t_warning_study_record
  WHERE delete_flag = 0
    AND tenant_id = %(tenant_id)s
    AND warning_time >= DATE_SUB(%(now_time)s, INTERVAL 7 DAY)
  UNION ALL
  SELECT course_id, tenant_id, indicator_name, warning_level, warning_time
  FROM t_warning_teaching_record
  WHERE delete_flag = 0
    AND tenant_id = %(tenant_id)s
    AND warning_time >= DATE_SUB(%(now_time)s, INTERVAL 7 DAY)
) w
LEFT JOIN t_tias_course c
  ON c.course_id = w.course_id
 AND c.tenant_id = w.tenant_id
 AND c.delete_flag = 0
GROUP BY COALESCE(c.teacher_names, '未知教师')
ORDER BY warning_count DESC, latest_warning_time DESC
LIMIT %(limit)s
"""

_CLASSROOM_HEALTH_OVERVIEW_SQL = """
SELECT
  COUNT(*) AS classroom_status_count,
  COALESCE(SUM(CASE WHEN has_people = 1 THEN 1 ELSE 0 END), 0) AS active_classroom_count,
  COALESCE(ROUND(AVG(COALESCE(tias_seat_percent, 0)), 2), 0) AS avg_seat_percent
FROM t_patrol_classroom_status
WHERE delete_flag = 0
  AND tenant_id = %(tenant_id)s
  AND tias_event_time >= DATE_SUB(%(now_time)s, INTERVAL 2 HOUR)
"""

_DEVICE_OPS_OVERVIEW_SQL = """
SELECT
  COUNT(*) AS total_check_count,
  COALESCE(SUM(CASE WHEN result_status = 1 THEN 1 ELSE 0 END), 0) AS ok_count,
  COALESCE(SUM(CASE WHEN result_status = 2 THEN 1 ELSE 0 END), 0) AS abnormal_count,
  ROUND(IFNULL(COALESCE(SUM(CASE WHEN result_status = 1 THEN 1 ELSE 0 END), 0) / NULLIF(COUNT(*), 0), 0) * 100, 2) AS ok_ratio
FROM t_ops_check_device_result
WHERE delete_flag = 0
  AND tenant_id = %(tenant_id)s
  AND execute_start_time >= DATE_SUB(%(now_time)s, INTERVAL 3 DAY)
"""

_SENSITIVE_WORD_30D_SQL = """
SELECT
  (
    SELECT COUNT(*)
    FROM t_patrol_sensitive_words
    WHERE delete_flag = 0
      AND tenant_id = %(tenant_id)s
  ) AS sensitive_word_dict_count,
  COUNT(*) AS sensitive_warning_count_30d,
  COUNT(DISTINCT course_id) AS course_section_count,
  MAX(warning_time) AS latest_warning_time
FROM t_warning_teaching_record
WHERE delete_flag = 0
  AND tenant_id = %(tenant_id)s
  AND warning_time >= DATE_SUB(%(now_time)s, INTERVAL 30 DAY)
  AND (
    indicator_name LIKE '%%敏感词%%'
    OR indicator_code LIKE '%%sensitive%%'
  )
"""

_WARNING_VIDEO_LATEST_MATCH_SQL = """
SELECT
  w.course_id,
  w.course_name,
  w.teacher_names,
  w.classroom_name,
  w.leti_name,
  w.leti_number,
  w.org_name,
  w.indicator_name,
  w.warning_level,
  w.warning_time,
  v.record_id,
  v.vod_start_time,
  v.vod_end_time,
  v.file_url
FROM (
  SELECT
    x.course_id,
    COALESCE(c.subject_name, c.teaching_class_name, x.course_name, CONCAT('课程#', x.course_id)) AS course_name,
    COALESCE(c.teacher_names, '未知教师') AS teacher_names,
    COALESCE(c.classroom_name, x.clro_name, '未知教室') AS classroom_name,
    COALESCE(c.leti_name, CONCAT('第', COALESCE(c.leti_number, 0), '节')) AS leti_name,
    COALESCE(c.leti_number, 0) AS leti_number,
    COALESCE(c.tecl_org_name, x.org_name, '未知学院') AS org_name,
    COALESCE(x.indicator_name, '未知预警') AS indicator_name,
    x.warning_level,
    x.warning_time
  FROM (
    SELECT course_id, tenant_id, course_name, clro_name, org_name, indicator_name, warning_level, warning_time
    FROM t_warning_study_record
    WHERE delete_flag = 0
      AND tenant_id = %(tenant_id)s
    UNION ALL
    SELECT course_id, tenant_id, course_name, clro_name, org_name, indicator_name, warning_level, warning_time
    FROM t_warning_teaching_record
    WHERE delete_flag = 0
      AND tenant_id = %(tenant_id)s
  ) x
  LEFT JOIN t_tias_course c
    ON c.course_id = x.course_id
   AND c.tenant_id = x.tenant_id
   AND c.delete_flag = 0
  ORDER BY x.warning_time DESC
  LIMIT 1
) w
LEFT JOIN t_media_video_record v
  ON v.delete_flag = 0
 AND v.tenant_id = %(tenant_id)s
 AND v.vod_start_time <= w.warning_time
 AND v.vod_end_time >= w.warning_time
ORDER BY v.vod_start_time DESC
LIMIT 1
"""


def _build_templates() -> dict[str, dict[str, Any]]:
    templates = [
        _template("tpl_patrol_overview_realtime", "实时AI巡课核心指标", "patrol", _PATROL_OVERVIEW_REALTIME_SQL),
        _template("tpl_patrol_org_risk_rank", "AI巡课学院重点关注排行", "patrol", _PATROL_ORG_RISK_SQL),
        _template("tpl_patrol_focus_top", "重点关注课堂Top", "patrol", _PATROL_FOCUS_TOP_SQL),
        _template("tpl_patrol_vitality_top", "活力较高课堂Top", "patrol", _PATROL_VITALITY_TOP_SQL),
        _template("tpl_patrol_overview_daily_finished", "今日已结束AI巡课核心指标", "patrol", _PATROL_OVERVIEW_DAILY_SQL),
        _template("tpl_patrol_section_distribution", "今日AI巡课节次分布", "patrol", _PATROL_SECTION_DISTRIBUTION_SQL),
        _template("tpl_warning_overview_realtime", "实时AI预警核心指标", "warning", _warning_overview_sql("live")),
        _template("tpl_warning_type_distribution", "AI预警类型分布", "warning", _warning_type_sql()),
        _template("tpl_warning_level_distribution", "AI预警等级分布", "warning", _warning_level_sql()),
        _template("tpl_warning_course_top", "高风险课堂Top", "warning", _warning_course_top_sql()),
        _template("tpl_warning_org_top", "学院预警排行", "warning", _warning_org_top_sql()),
        _template("tpl_warning_overview_daily_finished", "今日已结束AI预警核心指标", "warning", _warning_overview_sql("daily")),
        _template("tpl_warning_handle_status", "今日预警处置状态", "warning_handle", _WARNING_HANDLE_STATUS_SQL),
        _template("tpl_warning_handle_sla", "今日预警处置类型排行", "warning_handle", _WARNING_HANDLE_SLA_SQL),
        _template("tpl_warning_trend_7d", "近7天预警趋势", "warning_trend", _WARNING_TREND_7D_SQL),
        _template("tpl_strategy_rule_trigger", "近7天策略规则触发效果", "strategy", _STRATEGY_RULE_TRIGGER_SQL),
        _template("tpl_teacher_risk_top_7d", "近7天教师风险排行", "teacher", _TEACHER_RISK_TOP_7D_SQL),
        _template("tpl_classroom_health_overview", "近2小时教室健康度", "classroom", _CLASSROOM_HEALTH_OVERVIEW_SQL),
        _template("tpl_device_ops_overview", "近3天设备运维概览", "device", _DEVICE_OPS_OVERVIEW_SQL),
        _template("tpl_sensitive_word_30d", "近30天敏感词预警概览", "sensitive_word", _SENSITIVE_WORD_30D_SQL),
        _template("tpl_warning_video_latest_match", "最近预警视频回看匹配", "warning_video", _WARNING_VIDEO_LATEST_MATCH_SQL),
    ]
    return {item["template_id"]: item for item in templates}


_BUILTIN_TEMPLATES = _build_templates()


def get_builtin_template_definition(template_id: str) -> dict[str, Any] | None:
    item = _BUILTIN_TEMPLATES.get(template_id)
    return deepcopy(item) if item else None


def list_builtin_template_ids() -> list[str]:
    return sorted(_BUILTIN_TEMPLATES)
