from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from urllib import error, request

from app.assistant_trace import trace_emit
from app.config import merge_llm_chat_template_kwargs, settings
from app.db import get_connection

# 知识库可查：巡查「轮次」与预警等级来源（对应 jy_application_digital_patrol 库表结构）
PATROL_ROUND_KNOWLEDGE_BASE = (
    "巡查轮次定义：以当日排课节次编号 leti_number/节次名称 leti_name 为一轮巡查对象；"
    "当日轮次总数取 tenant 下 t_tias_course 当日 DATE(course_start_time) 的 MAX(leti_number)（无节次号时退化为 COUNT(DISTINCT leti_number)）；"
    "当前轮次取进行中课堂 MIN(leti_number)。节次汇总亦可对照 t_course_date_slot_statistics、t_space_overview_detail。"
    "预警等级非独立字段：由 t_warning_study_record、t_warning_teaching_record 的 warning_level（1高2中3低4提示）"
    "与 t_patrol_warning_level 字典聚合后规则映射；实时口径为近2小时预警。"
)

ASSISTANT_LLM_FAILED_HINT = (
    "暂时无法从模型获取回答，请稍后重试。"
    "需要巡课/预警数据时可说：「实时巡课简报」「今日预警汇总」。"
)

ASSISTANT_STREAM_STATIC_GUIDE = (
    "你可以这样问（命中关键词会直接出简报，更快）：\n"
    "1 课表时段实时巡课：「当前节次实时巡课简报」「正在上课的课堂巡课」\n"
    "2 非课表/今日已上巡课：「今日巡课简报」「非课表时段巡课汇总」\n"
    "3 实时课堂预警：「实时预警简报」「当前课堂预警占比」\n"
    "4 今日课堂预警：「今日预警汇总」「今日预警类型」\n"
    "5 预警推送：「预警推送阈值」「企业微信通知老师」\n"
    "其它闲聊、常识等也会正常回答。若刚网络异常，请重试。"
)


def simple_assistant_bucket(question: str) -> str:
    """
    轻量关键词分桶（不做语义模型）：命中则走库表简报，否则 general 走大模型。
    返回值: push_preview | realtime_warning | daily_warning | realtime_patrol | daily_patrol | general
    """
    q = (question or "").strip()
    if not q:
        return "general"
    # 5 预警消息推送（含阈值、渠道）
    if any(
        k in q
        for k in (
            "推送",
            "阈值",
            "企业微信",
            "多渠道",
            "即时消息",
            "消息推送",
            "通知授课",
            "通知辅导",
            "校内消息",
            "预警推送",
        )
    ):
        return "push_preview"
    # 3 实时课堂预警
    if "预警" in q or "告警" in q:
        if any(
            k in q
            for k in (
                "实时",
                "正在",
                "当前",
                "此刻",
                "现在",
                "进行中课堂",
                "正在上课",
            )
        ):
            return "realtime_warning"
        # 4 今日课堂预警（无「实时/正在」等词时默认走今日汇总）
        if any(k in q for k in ("今日", "当天", "汇总", "已结束", "已巡查", "今日课堂")):
            return "daily_warning"
        return "daily_warning"
    # 1 / 2 智能巡课（不含预警）
    if any(k in q for k in ("巡课", "巡查", "智能巡课")):
        if any(
            k in q
            for k in (
                "实时",
                "正在",
                "当前节次",
                "课表",
                "进行中",
                "此刻",
                "现在",
                "正在上课",
            )
        ):
            return "realtime_patrol"
        if any(k in q for k in ("今日", "非课表", "已上", "当天", "汇总")):
            return "daily_patrol"
        return "realtime_patrol"
    return "general"


def _try_simple_bucket_answer(tenant_id: str, bucket: str) -> dict[str, Any] | None:
    """命中分桶时拉库生成简报（synthesize=False，不调二次 LLM）。"""
    if bucket == "general":
        return None
    try:
        if bucket == "realtime_patrol":
            data = get_realtime_patrol_brief(tenant_id, synthesize=False)
        elif bucket == "daily_patrol":
            data = get_daily_patrol_brief(tenant_id, synthesize=False)
        elif bucket == "realtime_warning":
            data = get_realtime_warning_brief(tenant_id, synthesize=False)
        elif bucket == "daily_warning":
            data = get_daily_warning_brief(tenant_id, synthesize=False)
        elif bucket == "push_preview":
            data = get_push_strategy_preview(tenant_id, None, synthesize=False)
        else:
            return None
    except Exception:
        return {
            "intent": bucket,
            "answer": "业务数据暂无法查询，请稍后重试或检查数据库连接。",
            "data": {},
            "source": "patrol_api_error",
        }
    brief = str(data.get("brief") or "").strip()
    if not brief:
        return None
    return {
        "intent": bucket,
        "answer": brief,
        "data": data,
        "source": "patrol_api",
    }


def _fetch_patrol_round_metrics(tenant_id: str, now: datetime) -> dict[str, Any]:
    """当日轮次总数与当前节次轮次：来自 t_tias_course.leti_number（见 round_definition_kb）。"""
    row = _fetch_one(
        """
        SELECT
          COALESCE(daily.max_leti, 0) AS max_leti,
          COALESCE(daily.distinct_leti, 0) AS distinct_leti,
          COALESCE(live.min_live_leti, 0) AS current_live_leti
        FROM (
          SELECT
            MAX(leti_number) AS max_leti,
            COUNT(DISTINCT leti_number) AS distinct_leti
          FROM t_tias_course
          WHERE delete_flag = 0
            AND tenant_id = %(tenant_id)s
            AND DATE(course_start_time) = DATE(%(now)s)
            AND leti_number IS NOT NULL
        ) daily
        CROSS JOIN (
          SELECT MIN(leti_number) AS min_live_leti
          FROM t_tias_course
          WHERE delete_flag = 0
            AND tenant_id = %(tenant_id)s
            AND leti_number IS NOT NULL
            AND course_start_time <= %(now)s
            AND course_end_time >= %(now)s
        ) live
        """,
        {"tenant_id": tenant_id, "now": now},
    )
    mx = _to_int(row.get("max_leti"))
    dc = _to_int(row.get("distinct_leti"))
    cur = _to_int(row.get("current_live_leti"))
    daily_total = max(mx, dc)
    denom = daily_total if daily_total > 0 else 1
    progress_pct = min(100, int(round(cur / denom * 100))) if cur else 0
    if daily_total == 0:
        progress_pct = 0
    return {
        "daily_round_total": daily_total,
        "current_round_number": cur,
        "patrol_round_progress": f"{progress_pct}%",
    }


def _risk_from_warning_level_stats(
    worst_level: int | None,
    avg_warning_level: float | None,
    warning_ratio: float,
) -> str:
    """库无 overall_risk 字段：用 warning_level（1高2中3低4提示）MIN/AVG 与预警课堂占比做规则映射。"""
    if worst_level is None and (avg_warning_level is None or avg_warning_level == 0.0) and warning_ratio == 0.0:
        return "低"
    w = worst_level
    avg = float(avg_warning_level or 0.0)
    r = float(warning_ratio or 0.0)
    if w == 1 or avg <= 1.7 or r >= 35.0:
        return "高"
    if w == 2 or avg <= 2.5 or r >= 15.0:
        return "中"
    if w == 3 or avg <= 3.4 or r > 0.0:
        return "低"
    return "低"


def get_realtime_patrol_brief(tenant_id: str, *, synthesize: bool = True) -> dict[str, Any]:
    now = datetime.now()
    rounds = _fetch_patrol_round_metrics(tenant_id, now)
    row = _fetch_one(
        """
        SELECT
          COALESCE(MIN(leti_name), '-') AS current_section,
          COUNT(*) AS classroom_count,
          COALESCE(ROUND(AVG(tias_att_percent), 2), 0) AS avg_attendance,
          COALESCE(ROUND(AVG(tias_front_full_percent), 2), 0) AS avg_front_full,
          COALESCE(ROUND(AVG(tias_rise_percent), 2), 0) AS avg_rise,
          SUM(CASE WHEN COALESCE(tias_att_percent, 100) < 90
                        OR COALESCE(tias_front_full_percent, 100) < 65
                        OR COALESCE(tias_rise_percent, 100) < 65
                   THEN 1 ELSE 0 END) AS focus_classroom_count,
          SUM(CASE WHEN COALESCE(tias_att_percent, 0) >= 95
                        AND COALESCE(tias_front_full_percent, 0) >= 80
                        AND COALESCE(tias_rise_percent, 0) >= 75
                   THEN 1 ELSE 0 END) AS high_vitality_count
        FROM t_tias_course
        WHERE delete_flag = 0
          AND tenant_id = %(tenant_id)s
          AND course_start_time <= %(now)s
          AND course_end_time >= %(now)s
        """,
        {"tenant_id": tenant_id, "now": now},
    )
    payload = {
        "current_section": row["current_section"],
        "classroom_count": _to_int(row["classroom_count"]),
        "patrol_round": rounds["current_round_number"],
        "daily_round_total": rounds["daily_round_total"],
        "patrol_round_progress": rounds["patrol_round_progress"],
        "round_definition_kb": PATROL_ROUND_KNOWLEDGE_BASE,
        "avg_attendance": _to_float(row["avg_attendance"]),
        "avg_front_full": _to_float(row["avg_front_full"]),
        "avg_rise": _to_float(row["avg_rise"]),
        "focus_classroom_count": _to_int(row["focus_classroom_count"]),
        "high_vitality_count": _to_int(row["high_vitality_count"]),
        "generated_at": now.isoformat(timespec="seconds"),
    }
    round_txt = (
        f"第{payload['patrol_round']}/{payload['daily_round_total']}轮"
        if payload["daily_round_total"]
        else f"第{payload['patrol_round']}轮（当日课程无 leti_number 节次编号）"
    )
    fallback = (
        f"实时巡查{round_txt}（进度{payload['patrol_round_progress']}）："
        f"当前{payload['current_section']}共{payload['classroom_count']}个课堂，"
        f"平均到课率{payload['avg_attendance']}%，前排满座率{payload['avg_front_full']}%，抬头率{payload['avg_rise']}%。"
        f"重点关注{payload['focus_classroom_count']}个课堂，活力较高{payload['high_vitality_count']}个课堂。"
    )
    if synthesize:
        payload["brief"] = _summarize("请基于课堂实时巡课指标输出100字以内简报。", payload, fallback)
    else:
        payload["brief"] = fallback
    return payload


def get_daily_patrol_brief(tenant_id: str, *, synthesize: bool = True) -> dict[str, Any]:
    today = datetime.now().date()
    row = _fetch_one(
        """
        SELECT
          COUNT(*) AS classroom_count,
          COALESCE(ROUND(AVG(tias_att_percent), 2), 0) AS avg_attendance,
          COALESCE(ROUND(AVG(tias_front_full_percent), 2), 0) AS avg_front_full,
          COALESCE(ROUND(AVG(tias_rise_percent), 2), 0) AS avg_rise,
          COALESCE(ROUND(SUM(COALESCE(tias_avg_concentration, 0)), 2), 0) AS activity_data,
          SUM(CASE WHEN COALESCE(tias_att_percent, 100) < 90
                        OR COALESCE(tias_front_full_percent, 100) < 65
                        OR COALESCE(tias_rise_percent, 100) < 65
                   THEN 1 ELSE 0 END) AS focus_classroom_count,
          SUM(CASE WHEN COALESCE(tias_att_percent, 0) >= 95
                        AND COALESCE(tias_front_full_percent, 0) >= 80
                        AND COALESCE(tias_rise_percent, 0) >= 75
                   THEN 1 ELSE 0 END) AS high_vitality_count
        FROM t_tias_course
        WHERE delete_flag = 0
          AND tenant_id = %(tenant_id)s
          AND DATE(course_start_time) = %(today)s
        """,
        {"tenant_id": tenant_id, "today": today},
    )
    payload = {
        "classroom_count": _to_int(row["classroom_count"]),
        "avg_attendance": _to_float(row["avg_attendance"]),
        "avg_front_full": _to_float(row["avg_front_full"]),
        "avg_rise": _to_float(row["avg_rise"]),
        "activity_data": _to_float(row["activity_data"]),
        "focus_classroom_count": _to_int(row["focus_classroom_count"]),
        "high_vitality_count": _to_int(row["high_vitality_count"]),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    fallback = (
        f"今日已巡查{payload['classroom_count']}个课堂，平均到课率{payload['avg_attendance']}%，"
        f"前排满座率{payload['avg_front_full']}%，抬头率{payload['avg_rise']}%。"
        f"课堂活动数据{payload['activity_data']}，重点关注{payload['focus_classroom_count']}个，"
        f"活力较高{payload['high_vitality_count']}个。"
    )
    if synthesize:
        payload["brief"] = _summarize("请基于今日非课表巡课指标输出100字以内简报。", payload, fallback)
    else:
        payload["brief"] = fallback
    return payload


def get_realtime_warning_brief(tenant_id: str, *, synthesize: bool = True) -> dict[str, Any]:
    now = datetime.now()
    rounds = _fetch_patrol_round_metrics(tenant_id, now)
    row = _fetch_one(
        """
        SELECT
          sec.current_section,
          sec.class_count,
          COALESCE(warn.warning_classroom_count, 0) AS warning_classroom_count,
          warn.warning_types,
          warn.worst_warning_level,
          warn.avg_warning_level
        FROM (
          SELECT
            COALESCE(MIN(leti_name), '-') AS current_section,
            COUNT(*) AS class_count
          FROM t_tias_course
          WHERE delete_flag = 0
            AND tenant_id = %(tenant_id)s
            AND course_start_time <= %(now)s
            AND course_end_time >= %(now)s
        ) sec
        LEFT JOIN (
          SELECT
            COUNT(DISTINCT w.course_id) AS warning_classroom_count,
            GROUP_CONCAT(DISTINCT w.indicator_name ORDER BY w.indicator_name SEPARATOR '、') AS warning_types,
            MIN(w.warning_level) AS worst_warning_level,
            AVG(w.warning_level) AS avg_warning_level
          FROM (
            SELECT r.course_id, r.indicator_name, r.warning_level
            FROM t_warning_study_record r
            INNER JOIN t_tias_course c
              ON c.course_id = r.course_id
             AND c.tenant_id = r.tenant_id
            WHERE r.delete_flag = 0
              AND r.tenant_id = %(tenant_id)s
              AND c.delete_flag = 0
              AND c.course_start_time <= %(now)s
              AND c.course_end_time >= %(now)s
              AND r.warning_time >= DATE_SUB(%(now)s, INTERVAL 2 HOUR)
            UNION ALL
            SELECT r.course_id, r.indicator_name, r.warning_level
            FROM t_warning_teaching_record r
            INNER JOIN t_tias_course c
              ON c.course_id = r.course_id
             AND c.tenant_id = r.tenant_id
            WHERE r.delete_flag = 0
              AND r.tenant_id = %(tenant_id)s
              AND c.delete_flag = 0
              AND c.course_start_time <= %(now)s
              AND c.course_end_time >= %(now)s
              AND r.warning_time >= DATE_SUB(%(now)s, INTERVAL 2 HOUR)
          ) w
        ) warn ON 1 = 1
        """,
        {"tenant_id": tenant_id, "now": now},
    )
    class_count = _to_int(row["class_count"])
    warning_count = _to_int(row["warning_classroom_count"])
    ratio = round((warning_count / class_count * 100), 2) if class_count else 0.0
    worst = row.get("worst_warning_level")
    avg_lvl = row.get("avg_warning_level")
    risk = _risk_from_warning_level_stats(
        _to_int(worst) if worst is not None else None,
        _to_float(avg_lvl) if avg_lvl is not None else None,
        ratio,
    )
    payload = {
        "patrol_round": rounds["current_round_number"],
        "daily_round_total": rounds["daily_round_total"],
        "patrol_round_progress": rounds["patrol_round_progress"],
        "round_definition_kb": PATROL_ROUND_KNOWLEDGE_BASE,
        "current_section": row["current_section"],
        "class_count": class_count,
        "warning_classroom_count": warning_count,
        "warning_ratio": ratio,
        "worst_warning_level": _to_int(worst) if worst is not None else None,
        "avg_warning_level": round(_to_float(avg_lvl), 3) if avg_lvl is not None else None,
        "overall_warning_risk": risk,
        "warning_types": row["warning_types"] or "暂无",
        "risk_level_rule": (
            "overall_warning_risk 由库表 warning_level（学情 t_warning_study_record + 教情 t_warning_teaching_record）"
            "的 MIN/AVG 与预警课堂占比共同规则映射，非库内现成字段；等级含义见 t_patrol_warning_level。"
        ),
        "generated_at": now.isoformat(timespec="seconds"),
    }
    fallback = (
        f"实时巡查进度{payload['patrol_round_progress']}，{payload['current_section']}共{payload['class_count']}个课堂，"
        f"预警课堂{payload['warning_classroom_count']}个，占比{payload['warning_ratio']}%，整体风险{payload['overall_warning_risk']}。"
        f"预警类型：{payload['warning_types']}。"
    )
    if synthesize:
        payload["brief"] = _summarize("请基于实时课堂预警指标输出100字以内简报。", payload, fallback)
    else:
        payload["brief"] = fallback
    return payload


def get_daily_warning_brief(tenant_id: str, *, synthesize: bool = True) -> dict[str, Any]:
    today = datetime.now().date()
    row = _fetch_one(
        """
        SELECT
          base.inspected_classroom_count,
          COALESCE(warn.warning_classroom_count, 0) AS warning_classroom_count,
          warn.warning_types,
          warn.worst_warning_level,
          warn.avg_warning_level
        FROM (
          SELECT COUNT(DISTINCT course_id) AS inspected_classroom_count
          FROM t_tias_course
          WHERE delete_flag = 0
            AND tenant_id = %(tenant_id)s
            AND DATE(course_start_time) = %(today)s
        ) base
        LEFT JOIN (
          SELECT
            COUNT(DISTINCT w.course_id) AS warning_classroom_count,
            GROUP_CONCAT(DISTINCT w.indicator_name ORDER BY w.indicator_name SEPARATOR '、') AS warning_types,
            MIN(w.warning_level) AS worst_warning_level,
            AVG(w.warning_level) AS avg_warning_level
          FROM (
            SELECT r.course_id, r.indicator_name, r.warning_level
            FROM t_warning_study_record r
            INNER JOIN t_tias_course c
              ON c.course_id = r.course_id
             AND c.tenant_id = r.tenant_id
            WHERE r.delete_flag = 0
              AND r.tenant_id = %(tenant_id)s
              AND c.delete_flag = 0
              AND DATE(c.course_start_time) = %(today)s
              AND DATE(r.warning_time) = %(today)s
            UNION ALL
            SELECT r.course_id, r.indicator_name, r.warning_level
            FROM t_warning_teaching_record r
            INNER JOIN t_tias_course c
              ON c.course_id = r.course_id
             AND c.tenant_id = r.tenant_id
            WHERE r.delete_flag = 0
              AND r.tenant_id = %(tenant_id)s
              AND c.delete_flag = 0
              AND DATE(c.course_start_time) = %(today)s
              AND DATE(r.warning_time) = %(today)s
          ) w
        ) warn ON 1 = 1
        """,
        {"tenant_id": tenant_id, "today": today},
    )
    inspected = _to_int(row["inspected_classroom_count"])
    warning = _to_int(row["warning_classroom_count"])
    ratio = round((warning / inspected * 100), 2) if inspected else 0.0
    worst = row.get("worst_warning_level")
    avg_lvl = row.get("avg_warning_level")
    risk = _risk_from_warning_level_stats(
        _to_int(worst) if worst is not None else None,
        _to_float(avg_lvl) if avg_lvl is not None else None,
        ratio,
    )
    payload = {
        "inspected_classroom_count": inspected,
        "warning_classroom_count": warning,
        "warning_ratio": ratio,
        "worst_warning_level": _to_int(worst) if worst is not None else None,
        "avg_warning_level": round(_to_float(avg_lvl), 3) if avg_lvl is not None else None,
        "overall_warning_risk": risk,
        "warning_types": row["warning_types"] or "暂无",
        "risk_level_rule": (
            "overall_warning_risk 由当日学情+教情预警 warning_level 的 MIN/AVG 与预警课堂占比规则映射。"
        ),
        "round_definition_kb": PATROL_ROUND_KNOWLEDGE_BASE,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    fallback = (
        f"今日已巡查课堂{inspected}个，预警课堂{warning}个，占比{ratio}%，整体风险{risk}。"
        f"预警类型：{payload['warning_types']}。"
    )
    if synthesize:
        payload["brief"] = _summarize("请基于今日课堂预警汇总输出100字以内简报。", payload, fallback)
    else:
        payload["brief"] = fallback
    return payload


def get_push_strategy_preview(
    tenant_id: str,
    threshold: dict[str, float] | None = None,
    *,
    synthesize: bool = True,
) -> dict[str, Any]:
    threshold = threshold or {"attendance": 88, "front_full": 65, "rise": 65}
    now = datetime.now()
    row = _fetch_one(
        """
        SELECT COUNT(*) AS trigger_count
        FROM t_tias_course
        WHERE delete_flag = 0
          AND tenant_id = %(tenant_id)s
          AND course_start_time <= %(now)s
          AND course_end_time >= %(now)s
          AND (
            COALESCE(tias_att_percent, 100) < %(attendance)s OR
            COALESCE(tias_front_full_percent, 100) < %(front_full)s OR
            COALESCE(tias_rise_percent, 100) < %(rise)s
          )
        """,
        {
            "tenant_id": tenant_id,
            "now": now,
            "attendance": threshold["attendance"],
            "front_full": threshold["front_full"],
            "rise": threshold["rise"],
        },
    )
    trigger = _to_int(row["trigger_count"])
    payload = {
        "trigger_count": trigger,
        "threshold": threshold,
        "channels": ["企业微信", "微信", "校内消息平台"],
        "notify_roles": ["授课教师", "辅导员"],
        "generated_at": now.isoformat(timespec="seconds"),
    }
    fallback = (
        f"当前阈值为到课率<{threshold['attendance']}%、前排满座率<{threshold['front_full']}%、抬头率<{threshold['rise']}%，"
        f"预计触发{trigger}条预警消息，将通过企业微信、微信和校内平台同步发送给授课教师及辅导员。"
    )
    if synthesize:
        payload["brief"] = _summarize("请基于预警推送配置输出80字以内说明。", payload, fallback)
    else:
        payload["brief"] = fallback
    return payload


def get_video_points(tenant_id: str, date_str: str | None = None) -> dict[str, Any]:
    if date_str:
        target_day = datetime.strptime(date_str, "%Y-%m-%d").date()
    else:
        target_day = datetime.now().date()
    rows = _fetch_all(
        """
        SELECT
          mr.clro_name,
          pt.plan_start_time,
          pt.plan_end_time,
          TIMESTAMPDIFF(SECOND, pt.plan_start_time, pt.plan_end_time) AS duration_sec
        FROM t_ops_video_history_monitor_record mr
        JOIN t_ops_video_history_plan_time pt ON pt.monitor_record_id = mr.id
        WHERE mr.delete_flag = 0
          AND pt.delete_flag = 0
          AND mr.tenant_id = %(tenant_id)s
          AND mr.video_date = %(video_date)s
        ORDER BY pt.plan_start_time
        LIMIT 12
        """,
        {"tenant_id": tenant_id, "video_date": target_day},
    )
    points = []
    for idx, row in enumerate(rows, 1):
        start_time = row["plan_start_time"].strftime("%H:%M:%S") if row["plan_start_time"] else "-"
        end_time = row["plan_end_time"].strftime("%H:%M:%S") if row["plan_end_time"] else "-"
        points.append(
            {
                "index": idx,
                "classroom": row["clro_name"] or "未知教室",
                "start_time": start_time,
                "end_time": end_time,
                "duration_sec": _to_int(row["duration_sec"]),
                "ppt_thumbnail": f"/static/ppt/slide_{idx}.png",
                "core_point": f"第{idx}段关键讲解内容（自动提炼）",
            }
        )
    payload = {
        "point_count": len(points),
        "timeline": points,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    payload["brief"] = _summarize(
        "请基于视频打点结果输出80字以内说明。",
        {"point_count": len(points), "date": str(target_day)},
        f"{target_day}已完成{len(points)}个视频打点节点生成，并支持PPT缩略图时间轴联动跳转。",
    )
    return payload


def get_study_stats_brief(tenant_id: str) -> dict[str, Any]:
    row = _fetch_one(
        """
        SELECT
          COALESCE(ROUND(AVG(CASE WHEN subject_source = 1 THEN tias_att_percent END), 2), 0) AS undergrad_att,
          COALESCE(ROUND(AVG(CASE WHEN subject_source = 2 THEN tias_att_percent END), 2), 0) AS graduate_att,
          COALESCE(ROUND(AVG(CASE WHEN subject_source = 1 THEN tias_rise_percent END), 2), 0) AS undergrad_rise,
          COALESCE(ROUND(AVG(CASE WHEN subject_source = 2 THEN tias_rise_percent END), 2), 0) AS graduate_rise,
          SUM(CASE WHEN subject_source = 1 THEN 1 ELSE 0 END) AS undergrad_course_count,
          SUM(CASE WHEN subject_source = 2 THEN 1 ELSE 0 END) AS graduate_course_count
        FROM t_tias_course
        WHERE delete_flag = 0 AND tenant_id = %(tenant_id)s
        """,
        {"tenant_id": tenant_id},
    )
    payload = {
        "undergrad_att": _to_float(row["undergrad_att"]),
        "graduate_att": _to_float(row["graduate_att"]),
        "undergrad_rise": _to_float(row["undergrad_rise"]),
        "graduate_rise": _to_float(row["graduate_rise"]),
        "undergrad_course_count": _to_int(row["undergrad_course_count"]),
        "graduate_course_count": _to_int(row["graduate_course_count"]),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    payload["brief"] = _summarize(
        "请基于本研课程学情统计输出100字以内简报。",
        payload,
        (
            f"本科课程{payload['undergrad_course_count']}门，平均到课率{payload['undergrad_att']}%，抬头率{payload['undergrad_rise']}%；"
            f"研究生课程{payload['graduate_course_count']}门，平均到课率{payload['graduate_att']}%，抬头率{payload['graduate_rise']}%。"
        ),
    )
    return payload


def get_study_anomaly_brief(tenant_id: str) -> dict[str, Any]:
    rows = _fetch_all(
        """
        SELECT
          course_name,
          teacher_names,
          tecl_org_name,
          COALESCE(tias_att_percent, 0) AS att_percent,
          COALESCE(tias_front_full_percent, 0) AS front_full_percent,
          COALESCE(tias_rise_percent, 0) AS rise_percent
        FROM t_tias_course
        WHERE delete_flag = 0
          AND tenant_id = %(tenant_id)s
          AND (
            COALESCE(tias_att_percent, 100) < 90 OR
            COALESCE(tias_front_full_percent, 100) < 65 OR
            COALESCE(tias_rise_percent, 100) < 65
          )
        ORDER BY (COALESCE(tias_att_percent, 0) + COALESCE(tias_front_full_percent, 0) + COALESCE(tias_rise_percent, 0)) ASC
        LIMIT 5
        """,
        {"tenant_id": tenant_id},
    )
    top = rows[0] if rows else None
    payload = {
        "anomaly_count": len(rows),
        "top_anomaly": top or {},
        "list": rows,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    if top:
        fallback = (
            f"当前识别到{len(rows)}门需重点关注课程，风险最高为{top['tecl_org_name']}《{top['course_name']}》"
            f"（到课率{top['att_percent']}%，前排满座率{top['front_full_percent']}%，抬头率{top['rise_percent']}%）。"
        )
    else:
        fallback = "当前未识别到明显异常课程，整体课堂状态稳定。"
    payload["brief"] = _summarize("请输出学情异常课程简报。", payload, fallback)
    return payload


def get_teacher_eval_brief(tenant_id: str, question: str) -> dict[str, Any]:
    teacher_name = _extract_teacher_name(question)
    like_pattern = f"%{teacher_name}%" if teacher_name else "%"
    row = _fetch_one(
        """
        SELECT
          COALESCE(MAX(teacher_names), '-') AS teacher_name,
          COUNT(*) AS course_count,
          COALESCE(ROUND(AVG(tias_att_percent), 2), 0) AS avg_attendance,
          COALESCE(ROUND(AVG(tias_rise_percent), 2), 0) AS avg_rise,
          COALESCE(ROUND(AVG(tias_front_full_percent), 2), 0) AS avg_front_full
        FROM t_tias_course
        WHERE delete_flag = 0
          AND tenant_id = %(tenant_id)s
          AND teacher_names LIKE %(teacher)s
        """,
        {"tenant_id": tenant_id, "teacher": like_pattern},
    )
    payload = {
        "teacher_name": row["teacher_name"] if row.get("teacher_name") else teacher_name or "未知教师",
        "course_count": _to_int(row["course_count"]),
        "avg_attendance": _to_float(row["avg_attendance"]),
        "avg_rise": _to_float(row["avg_rise"]),
        "avg_front_full": _to_float(row["avg_front_full"]),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    payload["brief"] = _summarize(
        "请输出教师课堂评价风格的简报。",
        payload,
        (
            f"{payload['teacher_name']}相关课堂共{payload['course_count']}门，平均到课率{payload['avg_attendance']}%，"
            f"抬头率{payload['avg_rise']}%，前排满座率{payload['avg_front_full']}%。"
        ),
    )
    return payload


def route_assistant_query(
    question: str,
    tenant_id: str,
    trace_id: str | None = None,
) -> dict[str, Any]:
    """轻量关键词分桶：五类巡课/预警/推送走库表简报；其余走大模型通用回答。"""
    text = (question or "").strip()
    if not text:
        trace_emit(trace_id, "branch_empty_question")
        return {
            "intent": "",
            "answer": (
                "请输入问题。示例：「当前节次实时巡课简报」「今日巡课汇总」「实时预警简报」"
                "「今日预警汇总」「预警推送阈值」；其它问题也会尽量简短回答。"
            ),
            "data": {},
            "source": "none",
        }
    bucket = simple_assistant_bucket(text)
    trace_emit(trace_id, "simple_bucket", bucket=bucket)
    hit = _try_simple_bucket_answer(tenant_id, bucket)
    if hit is not None:
        trace_emit(trace_id, "patrol_api_hit", source=hit.get("source"))
        return hit
    trace_emit(trace_id, "llm_general_path")
    trace_emit(trace_id, "llm_blocking_before_urlopen", max_tokens=220)
    general_answer = _general_llm_answer(text, trace_id=trace_id)
    trace_emit(
        trace_id,
        "llm_blocking_after_urlopen",
        has_answer=bool(general_answer),
        answer_chars=len(general_answer or ""),
    )
    if general_answer:
        return {"intent": "general", "answer": general_answer, "data": {}, "source": "llm"}
    return {
        "intent": "general",
        "answer": ASSISTANT_LLM_FAILED_HINT,
        "data": {},
        "source": "llm",
    }


def _general_llm_messages(question: str) -> list[dict[str, str]]:
    system = (
        "你是高校巡课与学情预警场景的 AI 助教。回答务必简短（尽量 120 字内）。"
        "打招呼、常识、与业务无关的问题用通用能力直接答，不编造数据库指标。"
        "若用户要实时到课率、预警占比等具体数，请提示可说「实时巡课简报」「今日预警汇总」等以便系统拉数。"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": question},
    ]


def _to_int(value: Any) -> int:
    if value is None:
        return 0
    return int(value)


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    return float(value)


def _extract_teacher_name(question: str) -> str:
    if "老师" not in question:
        return ""
    prefix = question.split("老师")[0]
    return prefix[-3:].strip("，。；： ")


def _fetch_one(sql: str, params: dict[str, Any]) -> dict[str, Any]:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            result = cursor.fetchone() or {}
    return result


def _fetch_all(sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall() or []
    return rows


def _summarize(task: str, data: dict[str, Any], fallback: str) -> str:
    prompt = (
        "你是高校AI助教巡课助手，请基于给定结构化数据生成简洁专业的中文简报，不要编造不存在的数据。\n"
        f"任务: {task}\n"
        f"数据: {json.dumps(data, ensure_ascii=False)}\n"
        "输出要求：1-3句话。"
    )
    llm_url = f"{settings.llm_base_url.rstrip('/')}/chat/completions"
    payload: dict[str, object] = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": "你是高校巡课数据分析助手。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 220,
    }
    merge_llm_chat_template_kwargs(payload)
    req = request.Request(
        llm_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.llm_api_key}",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=settings.llm_timeout_sec) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"].strip()
        return content or fallback
    except (error.URLError, TimeoutError, KeyError, IndexError, ValueError):
        return fallback


def _general_llm_answer(question: str, trace_id: str | None = None) -> str | None:
    llm_url = f"{settings.llm_base_url.rstrip('/')}/chat/completions"
    payload: dict[str, object] = {
        "model": settings.llm_model,
        "messages": _general_llm_messages(question),
        "temperature": 0.35,
        "max_tokens": 220,
    }
    merge_llm_chat_template_kwargs(payload)
    req = request.Request(
        llm_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.llm_api_key}",
        },
        method="POST",
    )
    try:
        trace_emit(
            trace_id,
            "llm_urlopen_begin",
            stream=False,
            timeout_sec=settings.llm_timeout_sec,
            enable_thinking=settings.llm_enable_thinking,
        )
        with request.urlopen(req, timeout=settings.llm_timeout_sec) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"].strip()
        trace_emit(trace_id, "llm_urlopen_done", http_status=getattr(resp, "status", None))
        return content or None
    except (error.URLError, TimeoutError, KeyError, IndexError, ValueError) as ex:
        trace_emit(
            trace_id,
            "llm_urlopen_failed",
            error_type=type(ex).__name__,
            error=str(ex)[:400],
        )
        return None
