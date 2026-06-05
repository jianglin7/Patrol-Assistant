from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from urllib import error, request

from app.assistant_trace import trace_emit, redact_sensitive_text, redact_trace_value
from app.config import merge_llm_chat_template_kwargs, settings


_FRIENDLY_FIELD_NAMES = {
    "current_section": "当前节次",
    "course_section_count": "课堂节次数",
    "patrolled_course_section_count": "已产生AI巡查数据的节次数",
    "finished_section_count": "已结束节次数",
    "avg_attendance": "平均到课率",
    "avg_front_full": "平均前排满座率",
    "avg_rise": "平均抬头率",
    "low_attendance_count": "到课率偏低节次数",
    "low_front_full_count": "前排满座率偏低节次数",
    "low_rise_count": "抬头率偏低节次数",
    "over_attendance_count": "到课率超过100%的节次数",
    "focus_course_section_count": "重点关注节次数",
    "high_vitality_course_section_count": "活力较高节次数",
    "section_number": "节次序号",
    "section_name": "节次",
    "org_name": "学院",
    "course_name": "课程",
    "teacher_names": "教师",
    "classroom_name": "教室",
    "leti_name": "节次",
    "leti_number": "节次序号",
    "att_percent": "到课率",
    "front_full_percent": "前排满座率",
    "rise_percent": "抬头率",
    "warning_record_count": "预警记录数",
    "warning_course_section_count": "预警节次数",
    "warning_ratio": "预警占比",
    "high_warning_count": "高等级预警数",
    "avg_warning_level": "平均预警等级",
    "overall_risk_level": "整体风险等级",
    "indicator_name": "预警类型",
    "warning_count": "预警数量",
    "worst_warning_level": "最严重等级",
    "latest_warning_time": "最近预警时间",
    "warning_level": "预警等级",
    "warning_level_name": "预警等级",
    "indicator_type_count": "涉及预警类型数",
    "pending_count": "待处理数",
    "hang_count": "挂起数",
    "closed_count": "已闭环数",
    "total_warning_count": "预警总数",
    "pending_ratio": "待处理占比",
    "closed_ratio": "闭环率",
    "day": "日期",
    "rule_name": "规则名称",
    "alarm_desc": "规则说明",
    "trigger_count_7d": "近7天触发次数",
    "course_display_name": "课程",
    "course_org_name": "学院",
    "teacher_count": "教师数",
    "classroom_status_count": "教室状态记录数",
    "active_classroom_count": "有人教室数",
    "avg_seat_percent": "平均就座率",
    "total_check_count": "巡检次数",
    "ok_count": "正常次数",
    "abnormal_count": "异常次数",
    "ok_ratio": "正常率",
    "sensitive_word_dict_count": "敏感词词库数量",
    "sensitive_warning_count_30d": "近30天敏感词相关预警数",
    "record_id": "录像记录",
    "vod_start_time": "录像开始时间",
    "vod_end_time": "录像结束时间",
    "file_url": "视频地址",
}

_FILTER_LABELS = {
    "org_name": "学院",
    "teacher_name": "教师",
    "course_name": "课程",
    "classroom_name": "教室",
    "leti_min": "起始节次",
    "leti_max": "结束节次",
    "subject_source": "课程类型",
}

_INTENT_LABELS = {
    "realtime_patrol": "实时AI巡课",
    "daily_patrol": "今日AI巡课",
    "realtime_warning": "实时课堂AI预警",
    "daily_warning": "今日课堂AI预警",
    "warning_handle": "预警处置闭环",
    "warning_trend": "预警趋势",
    "strategy_effect": "告警策略效果",
    "teacher_risk": "教师风险画像",
    "classroom_health": "教室健康度",
    "device_ops": "设备运维",
    "sensitive_word": "敏感词预警",
    "warning_video_trace": "预警视频回看",
}


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat(sep=" ") if isinstance(value, datetime) else value.isoformat()
    return str(value)


def _format_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        value = float(value)
    if isinstance(value, float):
        return round(value, 2)
    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="seconds")
    if isinstance(value, date):
        return value.isoformat()
    return value


def _warning_level_display(value: Any) -> Any:
    try:
        level = int(value)
    except (TypeError, ValueError):
        return value
    return {1: "高", 2: "中", 3: "低", 4: "提示"}.get(level, f"未知({level})")


def _friendly_key(key: str) -> str:
    return _FRIENDLY_FIELD_NAMES.get(key, key.replace("_", " "))


def _friendly_row(row: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in row.items():
        if value is None:
            continue
        if str(key) in {"warning_level", "worst_warning_level"}:
            value = _warning_level_display(value)
        result[_friendly_key(str(key))] = _format_value(value)
    return result


def _compact_filters(filters: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(filters, dict):
        return {}
    result: dict[str, Any] = {}
    for key, value in filters.items():
        if value in (None, ""):
            continue
        label = _FILTER_LABELS.get(str(key), str(key))
        if key == "subject_source":
            value = "本科生课程" if int(value) == 1 else "研究生课程" if int(value) == 2 else value
        result[label] = value
    return result


def _compact_execution(semantic_execution: dict[str, Any]) -> dict[str, Any]:
    max_steps = max(1, int(settings.assistant_semantic_report_max_steps or 6))
    max_rows = max(1, int(settings.assistant_semantic_report_max_rows_per_step or 5))
    steps: list[dict[str, Any]] = []
    for step in (semantic_execution.get("steps") or [])[:max_steps]:
        if not isinstance(step, dict):
            continue
        rows = step.get("data") if isinstance(step.get("data"), list) else []
        compact_rows = [_friendly_row(row) for row in rows[:max_rows] if isinstance(row, dict)]
        item: dict[str, Any] = {
            "查询主题": step.get("template_name") or step.get("template_id") or "未知主题",
            "是否成功": bool(step.get("success")),
            "返回行数": int(step.get("row_count") or 0),
            "样例数据": compact_rows,
        }
        if step.get("error"):
            item["异常说明"] = redact_trace_value(step.get("error"))
        steps.append(item)
    return {
        "执行概览": semantic_execution.get("summary") or {},
        "查询结果": steps,
    }


def _build_report_context(
    *,
    question: str,
    auto_plan: dict[str, Any],
    semantic_execution: dict[str, Any],
) -> dict[str, Any]:
    dsl = auto_plan.get("dsl") if isinstance(auto_plan.get("dsl"), dict) else {}
    time_scope = dsl.get("time_scope") if isinstance(dsl.get("time_scope"), dict) else {}
    return {
        "用户问题": question,
        "识别意图": _INTENT_LABELS.get(str(dsl.get("intent") or ""), str(dsl.get("intent") or "未知")),
        "统计范围": time_scope.get("label") or time_scope.get("status") or "默认范围",
        "筛选条件": _compact_filters(dsl.get("filters") if isinstance(dsl.get("filters"), dict) else {}),
        "Top数量": dsl.get("top_n"),
        "业务口径": {
            "预警等级": "1表示高风险、2表示中风险、3表示低风险、4表示提示；数字越小越严重。",
            "课堂节次": "同一课程在不同节次、教师或教室下按不同课堂节次展示。",
        },
        "取数结果": _compact_execution(semantic_execution),
    }


def _fallback_report(context: dict[str, Any], fallback_answer: str | None = None) -> str:
    summary = context.get("取数结果", {}).get("执行概览", {}) if isinstance(context.get("取数结果"), dict) else {}
    steps = context.get("取数结果", {}).get("查询结果", []) if isinstance(context.get("取数结果"), dict) else []
    success_count = int(summary.get("success_count") or 0)
    total_rows = int(summary.get("total_row_count") or 0)
    if success_count <= 0:
        return fallback_answer or (
            "【结论】当前未查询到可用业务数据，请稍后重试或调整时间范围、筛选条件。\n"
            "【建议】可换问“今日AI巡课汇总”“今日课堂AI预警汇总”或缩小到指定学院、节次。"
        )
    lines = [
        "【智能分析简报】",
        f"【结论】已按“{context.get('统计范围')}”完成{success_count}个维度查询，共返回{total_rows}行结果。",
    ]
    if context.get("筛选条件"):
        filters = "；".join(f"{k}={v}" for k, v in context["筛选条件"].items())
        lines.append(f"【筛选条件】{filters}")
    detail_lines: list[str] = []
    for idx, step in enumerate(steps[:4], start=1):
        rows = step.get("样例数据") if isinstance(step.get("样例数据"), list) else []
        if rows:
            first = "，".join(f"{k}{v}" for k, v in rows[0].items())
            detail_lines.append(f"{idx}. {step.get('查询主题')}：{first}")
        else:
            detail_lines.append(f"{idx}. {step.get('查询主题')}：暂无匹配记录")
    lines.append("【关键数据】\n" + "\n".join(detail_lines))
    lines.append("【建议】建议优先查看数量最高、风险最集中的学院/课堂，并结合节次、教师、教室进一步定位原因。")
    lines.append("【数据说明】本回答基于当前可查询到的AI巡课和课堂预警记录生成；无数据通常表示当前时间范围或筛选条件下暂无匹配记录。")
    return "\n".join(lines)


def compose_semantic_report(
    *,
    question: str,
    auto_plan: dict[str, Any],
    semantic_execution: dict[str, Any],
    fallback_answer: str | None = None,
    trace_id: str | None = None,
) -> str | None:
    if not settings.assistant_semantic_report_enabled:
        return None
    if not isinstance(semantic_execution, dict) or int(semantic_execution.get("summary", {}).get("success_count") or 0) <= 0:
        return None

    context = _build_report_context(
        question=question,
        auto_plan=auto_plan,
        semantic_execution=semantic_execution,
    )
    fallback = _fallback_report(context, fallback_answer=fallback_answer)
    prompt = (
        "请基于结构化取数结果，回答用户的课堂数据问题。\n"
        "要求：\n"
        "1. 先给结论，再给关键数据；根据问题选择展示预警类型、学院、课堂、节次、教师、教室等维度，不要套用完全固定的模板。\n"
        "2. 如果有Top榜，课程类条目要尽量体现课程、教师、节次、教室，避免看起来像重复课程。\n"
        "3. 如果某个维度无数据，要明确写“暂无匹配记录”，不要编造。\n"
        "4. 数据说明面向非技术人员，不要出现数据库字段名、SQL、模板ID、QueryPlan等技术词。\n"
        "5. 预警等级口径：1为高风险、2为中风险、3为低风险、4为提示，数字越小越严重；不要把提示级说成高风险。\n"
        "6. 建议动作要与风险等级匹配：如果主要是提示级，使用“持续观察、抽样复核、关注高频类型”，避免“严重、约谈、立即干预”等过重表述。\n"
        "7. 用中文，结构清晰，可使用【结论】【关键数据】【Top分析】【建议】【数据说明】等小标题。\n"
        f"结构化取数结果：{json.dumps(context, ensure_ascii=False, default=_json_default)}"
    )
    payload: dict[str, object] = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": "你是舟小智AI小助手，是高校课堂数据智能分析助手。你只基于给定数据回答，不编造。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.25,
        "max_tokens": int(settings.assistant_semantic_report_max_tokens or 900),
    }
    merge_llm_chat_template_kwargs(payload)
    req = request.Request(
        f"{settings.llm_base_url.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.llm_api_key}",
        },
        method="POST",
    )
    try:
        trace_emit(trace_id, "semantic_report_llm_begin", max_tokens=payload["max_tokens"])
        with request.urlopen(req, timeout=settings.llm_timeout_sec) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        content = str(body["choices"][0]["message"]["content"]).strip()
        trace_emit(trace_id, "semantic_report_llm_done", content_len=len(content))
        return content or fallback
    except (error.URLError, TimeoutError, KeyError, IndexError, ValueError) as exc:
        trace_emit(
            trace_id,
            "semantic_report_llm_failed",
            error_type=type(exc).__name__,
            error=redact_sensitive_text(exc, max_len=240),
        )
        return fallback
