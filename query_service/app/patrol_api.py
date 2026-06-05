from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from urllib import error, request

from app.assistant_trace import trace_emit
from app.config import merge_llm_chat_template_kwargs, settings
from app.db import get_connection, get_schedule_connection

# 知识库可查：AI巡查「轮次」与预警等级来源
PATROL_ROUND_KNOWLEDGE_BASE = (
    "AI巡查轮次定义：以当日排课中的节次为一轮AI巡查对象；"
    "当日轮次总数优先根据课表中的今日节次计算；"
    "若课表暂不可用，则回退到已同步的AI巡课课程记录。"
    "当前轮次取当前正在上课课堂所在的最早节次。"
    "预警等级根据学情、教情预警记录中的等级信息聚合后映射；实时口径为近2小时预警。"
)

ASSISTANT_LLM_FAILED_HINT = (
    "我现在暂时无法连接通用问答服务，但仍可以查询AI巡课和课堂预警数据。"
    "你可以试试问：「今日AI巡课汇总」「实时课堂AI预警简报」「近7天预警趋势」。"
)

ASSISTANT_SUGGESTED_QUESTIONS = (
    "课表时间段实时AI巡课简报",
    "非课表时间段今日AI巡课汇总",
    "实时课堂AI预警简报",
    "今日课堂AI预警汇总",
    "今日预警处置闭环",
    "近7天预警趋势和Top风险类型",
    "当前告警策略阈值效果",
    "近7天教师风险画像",
    "近30天敏感词相关预警统计",
    "最近一条预警对应的视频回看区间",
)

ASSISTANT_STREAM_STATIC_GUIDE = (
    "你可以这样问（命中关键词会直接出简报，更快）：\n"
    "1 课表时段实时AI巡课：「当前节次实时AI巡课简报」「正在上课的课堂AI巡课」\n"
    "2 非课表/今日已上AI巡课：「今日AI巡课简报」「非课表时段AI巡课汇总」\n"
    "3 课堂AI预警：「实时课堂AI预警简报」「今日课堂AI预警汇总」\n"
    "4 专项分析：「近7天预警趋势」「近7天教师风险画像」「敏感词预警统计」\n"
    "5 使用帮助：「你能做什么」「支持哪些问题」「到课率是什么意思」\n"
    "其它开放问题也会尽量回答；若通用问答服务暂不可用，业务简报仍可继续查询。"
)

REALTIME_PATROL_DEFINITION_TAIL = (
    "口径说明：AI巡查轮次表示“当前上到第几节/今天共几节”；"
    "重点关注课堂指到课、前排就座和专注度三项指标同时低于阈值的课堂；"
    "活力较高课堂指到课、前排就座和专注度整体表现都较好的课堂。"
)

DAILY_PATROL_DEFINITION_TAIL = (
    "口径说明：今日已上课节数表示今天已经完成授课的节次数；"
    "课堂活动数据用于反映课堂整体活跃情况；"
    "重点关注课堂指到课、前排就座和专注度三项指标同时低于阈值的课堂；"
    "活力较高课堂指到课、前排就座和专注度整体表现都较好的课堂。"
)

METRIC_KNOWLEDGE_BASE: list[tuple[tuple[str, ...], str, str]] = [
    (
        ("到课率", "出勤率"),
        "到课率",
        "到课率=实到人数/应到人数×100%，用于反映课堂出勤水平。",
    ),
    (
        ("前排满座率", "前排就坐率"),
        "前排满座率",
        "前排满座率=前排实到人数/前排座位数×100%，用于观察课堂前排就坐活跃度。",
    ),
    (
        ("抬头率", "抬头"),
        "抬头率",
        "抬头率用于衡量课堂专注度，值越高通常代表学生参与和注意力越好。",
    ),
    (
        ("课堂活动数据", "活动数据", "活跃度"),
        "课堂活动指数",
        "课堂活动指数用于反映课堂互动、专注和活跃情况，数值越高通常表示课堂越活跃；若为0，可能是暂无有效记录或该指标尚未完整接入。",
    ),
    (
        ("AI巡查覆盖率", "巡查覆盖率", "AI巡课覆盖率", "覆盖率"),
        "AI巡查覆盖率",
        "AI巡查覆盖率=已完成AI巡查课程节次/今日排课课程节次×100%，用于观察今日排课中已有AI巡查结果的比例。",
    ),
    (
        ("预警课堂占比", "预警占比"),
        "预警课堂占比",
        "预警课堂占比=预警课堂数/AI巡查课堂数×100%，用于观察风险覆盖范围。",
    ),
    (
        ("风险等级", "预警风险等级", "整体风险"),
        "风险等级",
        "整体预警风险等级由最严重预警等级、平均预警等级与预警课堂占比综合判断，分为高、中、低等层级。",
    ),
    (
        ("预警类型", "预警课堂类型"),
        "预警类型",
        "预警类型来自学情/教情预警指标名称聚合（如纪律、互动、专注等）。",
    ),
    (
        ("AI巡查轮次", "巡查轮次", "轮次", "AI巡课轮次", "巡课轮次"),
        "AI巡查轮次",
        "AI巡查轮次优先按节次编号计算；当日总轮次取当日最大或去重节次号，当前轮次取进行中课堂对应节次。",
    ),
    (
        ("重点关注课堂", "重点关注", "关注课堂"),
        "重点关注课堂",
        "重点关注课堂指到课率、前排满座率、抬头率三项指标同时低于当前阈值的课堂，适合优先核查和回访。",
    ),
    (
        ("活力较高课堂", "活力高课堂", "活力课堂"),
        "活力较高课堂",
        "活力较高课堂指到课率、前排满座率、抬头率同时达到较高标准的课堂，可作为课堂表现较好的参考样本。",
    ),
    (
        ("今日节次进度", "节次进度", "已上课节数"),
        "今日节次进度",
        "今日节次进度表示“已完成授课节次/今日排课总节次”，用于快速判断当天课程推进到什么阶段。",
    ),
    (
        ("预警阈值", "推送阈值", "阈值"),
        "预警推送阈值",
        "默认阈值为到课率<88%、前排满座率<65%、抬头率<65%，可按场景调整。",
    ),
]

LLM_FIELD_LABELS: dict[str, str] = {
    "generated_at": "生成时间",
    "current_section": "当前节次",
    "classroom_count": "课堂数（非教室间数）",
    "class_count": "课堂数（非教室间数）",
    "course_count": "课程节次数",
    "inspected_course_count": "已完成AI巡查课程节次数",
    "today_scheduled_course_count": "今日排课课程节次数",
    "today_completed_course_count": "今日已结束课程节次数",
    "today_live_course_count": "当前在上课程节次数",
    "today_scheduled_classroom_count": "今日排课课程节次数（兼容字段，非教室间数）",
    "today_completed_classroom_count": "今日已结束课程节次数（兼容字段，非教室间数）",
    "today_live_classroom_count": "当前在上课程节次数（兼容字段，非教室间数）",
    "inspected_classroom_count": "已完成AI巡查课堂数（非教室间数）",
    "warning_classroom_count": "预警课堂数（非教室间数）",
    "active_classroom_count": "有人教室数（间）",
    "completed_classroom_count": "已完成课堂数（非教室间数）",
    "daily_classroom_total": "今日课堂总数（非教室间数）",
    "focus_classroom_count": "重点关注课堂数",
    "focus_course_count": "重点关注课程节次数",
    "high_vitality_count": "活力较高课堂数",
    "high_vitality_course_count": "活力较高课程节次数",
    "low_attendance_count": "到课率偏低课堂数",
    "low_attendance_course_count": "到课率偏低课程节次数",
    "low_front_full_count": "前排满座率偏低课堂数",
    "low_rise_count": "抬头率偏低课堂数",
    "low_rise_course_count": "抬头率偏低课程节次数",
    "over_attendance_count": "到课率超过100%的课堂数",
    "today_scheduled_section_count": "今日排课节次数",
    "today_scheduled_section_max": "今日最大节次序号",
    "today_scheduled_section_distinct": "今日排课去重节次数",
    "finished_section_count": "今日已完成授课节次数",
    "finished_section_source": "已完成节次数据来源",
    "today_schedule_source": "今日课表数据来源",
    "inspection_coverage_ratio": "AI巡查覆盖率（%）",
    "patrol_round": "AI巡查当前轮次",
    "daily_round_total": "AI巡查今日总轮次",
    "patrol_round_progress": "AI巡查进度",
    "round_data_source": "巡查轮次数据来源",
    "round_definition_kb": "AI巡查轮次口径说明",
    "avg_attendance": "平均到课率（%）",
    "avg_front_full": "平均前排满座率（%）",
    "avg_rise": "平均抬头率（%）",
    "avg_seat_percent": "平均就座率（%）",
    "att_percent": "到课率（%）",
    "front_full_percent": "前排满座率（%）",
    "rise_percent": "抬头率（%）",
    "activity_data": "课堂活动指数",
    "focus_ratio": "重点关注占比（%）",
    "high_vitality_ratio": "活力较高占比（%）",
    "warning_ratio": "预警课堂占比（%）",
    "warning_record_count": "预警记录数（条）",
    "total_warning_count": "预警总数（条）",
    "total_warning_count_7d": "近7天预警总数（条）",
    "avg_daily_warning_count_7d": "近7天日均预警数（条）",
    "warning_count": "预警数（条）",
    "high_level_count": "高等级预警数（条）",
    "high_level_ratio": "高等级预警占比（%）",
    "pending_count": "待处理预警数（条）",
    "hang_count": "挂起预警数（条）",
    "closed_count": "已闭环预警数（条）",
    "pending_ratio": "待处理占比（%）",
    "closed_ratio": "闭环率（%）",
    "warning_level": "预警等级",
    "warning_level_name": "预警等级名称",
    "worst_warning_level": "最严重预警等级",
    "worst_warning_level_name": "最严重预警等级名称",
    "avg_warning_level": "平均预警等级",
    "warning_types": "预警类型",
    "indicator_name": "指标名称",
    "indicator_type_count": "指标类型数",
    "teacher_name": "教师姓名",
    "teacher_names": "教师姓名",
    "teacher_count": "教师数",
    "course_name": "课程名称",
    "classroom_name": "教室名称",
    "leti_name": "节次名称",
    "leti_number": "节次序号",
    "org_name": "学院名称",
    "tecl_org_name": "开课学院名称",
    "trigger_count": "预计触发数（条）",
    "trigger_count_7d": "近7天触发数（次）",
    "triggered_rule_count_7d": "近7天有触发记录的规则数",
    "zero_trigger_rule_count": "暂无触发的规则数",
    "rule_count": "告警规则总数",
    "sampled_rule_count": "抽样规则数",
    "total_check_3d": "近3天设备巡检总数",
    "ok_count_3d": "近3天设备正常数",
    "abnormal_count_3d": "近3天设备异常数",
    "ok_ratio_3d": "近3天设备正常率（%）",
    "point_count": "视频打点节点数",
    "duration_sec": "时长（秒）",
    "date": "日期",
    "day": "日期",
    "latest_day": "最近日期",
    "peak_day": "峰值日期",
    "threshold": "阈值配置",
    "channels": "推送渠道",
    "notify_roles": "通知角色",
    "trend_7d": "近7天趋势",
    "top3_indicators": "指标Top3",
    "org_top5": "学院Top5",
    "org_focus_top10": "学院重点关注Top10",
    "section_distribution": "节次分布",
    "focus_course_top10": "重点关注课程Top10",
    "high_vitality_course_top10": "活力较高课程Top10",
    "warning_level_distribution": "预警等级分布",
    "status_distribution": "处置状态分布",
    "type_handle_top5": "待处理类型Top5",
    "org_pending_top5": "学院待处理Top5",
    "top_trigger_type_7d": "近7天触发类型Top5",
    "top_strategy_effect": "告警策略触发Top5",
    "teacher_risk_top5": "教师风险Top5",
    "teacher_warning_type_top5": "教师预警类型Top5",
    "list": "明细列表",
    "top_anomaly": "最高风险课程",
    "anomaly_count": "异常课程数",
    "timeline": "视频时间轴",
}


def _lookup_metric_kb_answer(question: str) -> str | None:
    q = (question or "").strip()
    if not q:
        return None
    need_explain = any(k in q for k in ("什么是", "是什么意思", "含义", "解释", "啥意思", "怎么算", "定义"))
    matched: list[tuple[str, str]] = []
    for aliases, name, desc in METRIC_KNOWLEDGE_BASE:
        if any(alias in q for alias in aliases):
            matched.append((name, desc))
    if not matched:
        return None
    # 对指标关键词本身也直接解释；若用户是普通业务问句，则按既定分桶优先
    if not need_explain and not any(k in q for k in ("指标", "口径", "释义", "定义")):
        return None
    lines = [f"{name}：{desc}" for name, desc in matched[:4]]
    return "\n".join(lines)


def _format_supported_questions() -> str:
    return "\n".join(f"{idx}. {text}" for idx, text in enumerate(ASSISTANT_SUGGESTED_QUESTIONS, start=1))


def _lookup_local_assistant_answer(question: str) -> str | None:
    """不依赖大模型的基础问答，让寒暄、帮助和能力介绍稳定可用。"""
    q = (question or "").strip()
    if not q:
        return None
    compact = "".join(q.lower().split()).strip("。！？?!.，,；;：:")
    if not compact:
        return None

    greeting_words = (
        "你好",
        "您好",
        "hello",
        "hi",
        "嗨",
        "哈喽",
        "在吗",
        "在不在",
        "早上好",
        "下午好",
        "晚上好",
    )
    if compact in greeting_words:
        return (
            "你好，我是课堂AI巡课小助手。你可以问我实时AI巡课、今日AI巡课汇总、"
            "课堂AI预警、预警趋势、教师风险画像等问题。"
        )

    thanks_words = ("谢谢", "感谢", "多谢", "辛苦了", "好的", "好", "明白", "收到")
    if compact in thanks_words:
        return "不客气，我会继续帮你盯住AI巡课和课堂预警数据。需要时可以直接问“今日AI巡课汇总”。"

    goodbye_words = ("再见", "拜拜", "回头见", "下次见")
    if compact in goodbye_words:
        return "再见，有需要时随时回来问我课堂AI巡课和预警情况。"

    identity_keywords = ("你是谁", "你叫什么", "你是干什么", "介绍一下你", "小助手介绍")
    if any(k in compact for k in identity_keywords):
        return (
            "我是课堂AI巡课小助手，主要帮助教务、督导和学院管理人员查看AI巡课简报、"
            "课堂AI预警、趋势分析、教师风险画像和视频回看线索。"
        )

    help_keywords = (
        "你能做什么",
        "能做什么",
        "能回答什么",
        "支持哪些问题",
        "支持什么问题",
        "目前支持的问题",
        "怎么用",
        "如何使用",
        "使用说明",
        "帮助",
        "菜单",
        "问题清单",
        "问什么",
    )
    if any(k in compact for k in help_keywords):
        return (
            "我目前主要支持这些问题：\n"
            f"{_format_supported_questions()}\n"
            "也可以问指标含义，例如“到课率是什么意思”“AI巡查覆盖率怎么算”。"
        )

    return None


def simple_assistant_bucket(question: str) -> str:
    """
    轻量关键词分桶（不做语义模型）：命中则走库表简报，否则 general 走大模型。
    返回值: push_preview | realtime_warning | daily_warning | realtime_patrol | daily_patrol
      | warning_handle | warning_trend | strategy_effect | teacher_risk | classroom_health
      | device_ops | sensitive_word | warning_video_trace | general
    """
    q = (question or "").strip()
    if not q:
        return "general"

    def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
        return any(k in text for k in keywords)

    # 为避免既定问题相互干扰，先命中最“专有”的场景词，再命中泛化词。
    push_keywords = (
        "预警推送",
        "消息推送",
        "即时消息",
        "企业微信",
        "微信通知",
        "校内消息",
        "多渠道",
        "通知授课",
        "通知辅导",
        "推送提醒",
    )
    push_threshold_keywords = (
        "推送阈值",
        "预警阈值",
        "推送策略阈值",
    )
    strategy_effect_keywords = ("阈值效果", "策略效果", "触发频次", "规则触发", "告警策略")
    warning_handle_keywords = ("处置闭环", "处理闭环", "处理效率", "待处理预警", "预警处理")
    warning_trend_keywords = ("风险趋势", "预警趋势", "top风险", "高风险最多", "近7天预警")
    teacher_risk_keywords = ("教师风险画像", "教师风险", "教师预警画像", "教师异常排行")
    classroom_health_keywords = ("教室健康度", "空闲异常", "无课教室", "教室状态异常")
    device_ops_keywords = ("设备运维", "设备巡检", "设备异常", "运维简报")
    sensitive_word_keywords = ("敏感词", "涉敏", "敏感词预警")
    warning_video_keywords = ("预警回看", "预警对应视频", "录像回看", "视频回看区间")
    realtime_markers = ("实时", "正在", "当前", "此刻", "现在", "进行中课堂", "正在上课")
    daily_markers = ("今日", "当天", "汇总", "已结束", "已完成AI巡查", "已巡查", "今日课堂")
    patrol_daily_markers = ("非课表", "今日", "已上", "当天", "汇总", "已结束")
    patrol_realtime_markers = ("实时", "正在", "当前节次", "课表时间段", "进行中", "此刻", "现在", "正在上课")

    if _contains_any(q, strategy_effect_keywords):
        return "strategy_effect"
    # 5 预警消息推送（含阈值、渠道）
    if _contains_any(q, push_keywords) or _contains_any(q, push_threshold_keywords):
        return "push_preview"
    if _contains_any(q, warning_handle_keywords):
        return "warning_handle"
    if _contains_any(q, warning_trend_keywords):
        return "warning_trend"
    if _contains_any(q, teacher_risk_keywords):
        return "teacher_risk"
    if _contains_any(q, classroom_health_keywords):
        return "classroom_health"
    if _contains_any(q, device_ops_keywords):
        return "device_ops"
    if _contains_any(q, sensitive_word_keywords):
        return "sensitive_word"
    if _contains_any(q, warning_video_keywords):
        return "warning_video_trace"
    # 3 实时课堂预警
    if "预警" in q or "告警" in q:
        if _contains_any(q, realtime_markers):
            return "realtime_warning"
        # 4 今日课堂预警（无「实时/正在」等词时默认走今日汇总）
        if _contains_any(q, daily_markers):
            return "daily_warning"
        return "daily_warning"
    # 1 / 2 智能AI巡课（不含预警）：兼容用户继续使用旧口径“巡课/巡查”提问。
    if any(k in q for k in ("AI巡课", "AI巡查", "智能AI巡课", "巡课", "巡查", "智能巡课")):
        # 先判断“非课表/今日汇总”口径，避免“非课表”误命中“课表”实时分支
        if _contains_any(q, patrol_daily_markers):
            return "daily_patrol"
        if _contains_any(q, patrol_realtime_markers):
            return "realtime_patrol"
        return "realtime_patrol"
    return "general"


def _try_simple_bucket_answer(tenant_id: str, bucket: str) -> dict[str, Any] | None:
    """命中分桶时先查真实数据，再由 LLM 按数据总结回答。"""
    if bucket == "general":
        return None
    try:
        if bucket == "realtime_patrol":
            data = get_realtime_patrol_brief(tenant_id, synthesize=True)
        elif bucket == "daily_patrol":
            data = get_daily_patrol_brief(tenant_id, synthesize=True)
        elif bucket == "realtime_warning":
            data = get_realtime_warning_brief(tenant_id, synthesize=True)
        elif bucket == "daily_warning":
            data = get_daily_warning_brief(tenant_id, synthesize=True)
        elif bucket == "push_preview":
            data = get_push_strategy_preview(tenant_id, None, synthesize=True)
        elif bucket == "warning_handle":
            data = get_warning_handle_overview_brief(tenant_id, synthesize=True)
        elif bucket == "warning_trend":
            data = get_warning_trend_top_brief(tenant_id, synthesize=True)
        elif bucket == "strategy_effect":
            data = get_alarm_strategy_effect_brief(tenant_id, synthesize=True)
        elif bucket == "teacher_risk":
            data = get_teacher_risk_profile_brief(tenant_id, synthesize=True)
        elif bucket == "classroom_health":
            data = get_classroom_health_brief(tenant_id, synthesize=True)
        elif bucket == "device_ops":
            data = get_device_ops_brief(tenant_id, synthesize=True)
        elif bucket == "sensitive_word":
            data = get_sensitive_word_brief(tenant_id, synthesize=True)
        elif bucket == "warning_video_trace":
            data = get_warning_video_trace_brief(tenant_id, synthesize=True)
        else:
            return None
    except Exception as ex:
        err_type = type(ex).__name__
        err_msg = str(ex)[:500]
        return {
            "intent": bucket,
            "answer": "业务数据暂无法查询，请稍后重试，或联系管理员检查数据源连接状态。",
            "data": {"error_type": err_type, "error": err_msg},
            "source": "patrol_api_error",
        }
    answer = str(data.get("brief") or "").strip()
    if not answer:
        return None
    return {
        "intent": bucket,
        "answer": answer,
        "data": data,
        "source": "patrol_api",
    }


def _fetch_patrol_round_metrics(tenant_id: str, now: datetime) -> dict[str, Any]:
    """当日轮次总数与当前节次轮次：优先课表库 t_course，连接失败时回退AI巡课库 t_tias_course。"""
    schedule_metrics = _fetch_patrol_round_metrics_from_schedule(tenant_id, now)
    if schedule_metrics is not None:
        return schedule_metrics
    return _fetch_patrol_round_metrics_from_tias(tenant_id, now)


def _resolve_schedule_tenant_org_code(tenant_id: str) -> str:
    fixed = (settings.schedule_tenant_org_code or "").strip()
    if fixed:
        return fixed
    return tenant_id


def _fetch_patrol_round_metrics_from_schedule(tenant_id: str, now: datetime) -> dict[str, Any] | None:
    tenant_org_code = _resolve_schedule_tenant_org_code(tenant_id)
    try:
        row = _fetch_schedule_one(
            """
            SELECT
              COALESCE(MAX(COALESCE(lt.leti_number, 0)), 0) AS max_leti,
              COALESCE(COUNT(DISTINCT lt.leti_number), 0) AS distinct_leti,
              COALESCE(
                MIN(
                  CASE
                    WHEN c.cour_begin_time <= %(now)s AND c.cour_end_time >= %(now)s
                    THEN COALESCE(lt.leti_number, 0)
                    ELSE NULL
                  END
                ),
                0
              ) AS current_live_leti,
              COALESCE(SUM(CASE WHEN c.cour_end_time < %(now)s THEN 1 ELSE 0 END), 0) AS completed_count,
              COUNT(*) AS total_count
            FROM t_course c
            LEFT JOIN t_lesson_time lt
              ON lt.id = c.leti_id
             AND COALESCE(lt.recycle_sign, 0) = 0
             AND (lt.tenant_org_code = c.tenant_org_code OR lt.tenant_org_code IS NULL)
            WHERE COALESCE(c.recycle_sign, 0) = 0
              AND c.tenant_org_code = %(tenant_org_code)s
              AND DATE(c.cour_begin_time) = DATE(%(now)s)
              AND COALESCE(c.clro_enable, 1) = 1
            """,
            {"tenant_org_code": tenant_org_code, "now": now},
        )
    except Exception:
        return None
    return _format_round_metrics(row, source="schedule")


def _fetch_today_course_overview(tenant_id: str, now: datetime) -> dict[str, Any]:
    schedule_overview = _fetch_today_course_overview_from_schedule(tenant_id, now)
    if schedule_overview is not None:
        return schedule_overview
    return _fetch_today_course_overview_from_tias(tenant_id, now)


def _fetch_today_course_overview_from_schedule(tenant_id: str, now: datetime) -> dict[str, Any] | None:
    tenant_org_code = _resolve_schedule_tenant_org_code(tenant_id)
    try:
        row = _fetch_schedule_one(
            """
            SELECT
              COUNT(*) AS total_course_count,
              COALESCE(MAX(COALESCE(lt.leti_number, 0)), 0) AS max_leti,
              COALESCE(COUNT(DISTINCT lt.leti_number), 0) AS distinct_leti,
              COALESCE(SUM(CASE WHEN c.cour_end_time < %(now)s THEN 1 ELSE 0 END), 0) AS completed_course_count,
              COALESCE(SUM(CASE WHEN c.cour_begin_time <= %(now)s AND c.cour_end_time >= %(now)s THEN 1 ELSE 0 END), 0) AS live_course_count,
              COALESCE(COUNT(DISTINCT CASE WHEN c.cour_end_time < %(now)s THEN lt.leti_number END), 0) AS finished_section_count
            FROM t_course c
            LEFT JOIN t_lesson_time lt
              ON lt.id = c.leti_id
             AND COALESCE(lt.recycle_sign, 0) = 0
             AND (lt.tenant_org_code = c.tenant_org_code OR lt.tenant_org_code IS NULL)
            WHERE COALESCE(c.recycle_sign, 0) = 0
              AND c.tenant_org_code = %(tenant_org_code)s
              AND DATE(c.cour_begin_time) = DATE(%(now)s)
              AND COALESCE(c.clro_enable, 1) = 1
            """,
            {"tenant_org_code": tenant_org_code, "now": now},
        )
    except Exception:
        return None
    max_leti = _to_int(row.get("max_leti"))
    distinct_leti = _to_int(row.get("distinct_leti"))
    return {
        "today_scheduled_classroom_count": _to_int(row.get("total_course_count")),
        "today_scheduled_section_count": max(max_leti, distinct_leti),
        "today_scheduled_section_max": max_leti,
        "today_scheduled_section_distinct": distinct_leti,
        "today_finished_section_count": _to_int(row.get("finished_section_count")),
        "today_completed_classroom_count": _to_int(row.get("completed_course_count")),
        "today_live_classroom_count": _to_int(row.get("live_course_count")),
        "today_schedule_source": "schedule",
    }


def _fetch_today_course_overview_from_tias(tenant_id: str, now: datetime) -> dict[str, Any]:
    row = _fetch_one(
        """
        SELECT
          COUNT(*) AS total_course_count,
          COALESCE(MAX(COALESCE(leti_number, 0)), 0) AS max_leti,
          COALESCE(COUNT(DISTINCT leti_number), 0) AS distinct_leti,
          COALESCE(SUM(CASE WHEN course_end_time < %(now)s THEN 1 ELSE 0 END), 0) AS completed_course_count,
          COALESCE(SUM(CASE WHEN course_start_time <= %(now)s AND course_end_time >= %(now)s THEN 1 ELSE 0 END), 0) AS live_course_count,
          COALESCE(COUNT(DISTINCT CASE WHEN course_end_time < %(now)s THEN leti_number END), 0) AS finished_section_count
        FROM t_tias_course
        WHERE delete_flag = 0
          AND tenant_id = %(tenant_id)s
          AND DATE(course_start_time) = DATE(%(now)s)
          AND EXISTS (
            SELECT 1
            FROM t_tias_classroom cls
            WHERE cls.delete_flag = 0
              AND cls.tenant_id = %(tenant_id)s
              AND cls.classroom_id = t_tias_course.classroom_id
              AND cls.has_course = 1
              AND cls.begin_time <= t_tias_course.course_end_time
              AND cls.end_time >= t_tias_course.course_start_time
          )
        """,
        {"tenant_id": tenant_id, "now": now},
    )
    max_leti = _to_int(row.get("max_leti"))
    distinct_leti = _to_int(row.get("distinct_leti"))
    return {
        "today_scheduled_classroom_count": _to_int(row.get("total_course_count")),
        "today_scheduled_section_count": max(max_leti, distinct_leti),
        "today_scheduled_section_max": max_leti,
        "today_scheduled_section_distinct": distinct_leti,
        "today_finished_section_count": _to_int(row.get("finished_section_count")),
        "today_completed_classroom_count": _to_int(row.get("completed_course_count")),
        "today_live_classroom_count": _to_int(row.get("live_course_count")),
        "today_schedule_source": "tias",
    }


def _fetch_patrol_round_metrics_from_tias(tenant_id: str, now: datetime) -> dict[str, Any]:
    row = _fetch_one(
        """
        SELECT
          COALESCE(daily.max_leti, 0) AS max_leti,
          COALESCE(daily.distinct_leti, 0) AS distinct_leti,
          COALESCE(live.min_live_leti, 0) AS current_live_leti,
          COALESCE(progress.completed_count, 0) AS completed_count,
          COALESCE(progress.total_count, 0) AS total_count
        FROM (
          SELECT
            MAX(leti_number) AS max_leti,
            COUNT(DISTINCT leti_number) AS distinct_leti
          FROM t_tias_course
          WHERE delete_flag = 0
            AND tenant_id = %(tenant_id)s
            AND DATE(course_start_time) = DATE(%(now)s)
            AND leti_number IS NOT NULL
            AND EXISTS (
              SELECT 1
              FROM t_tias_classroom cls
              WHERE cls.delete_flag = 0
                AND cls.tenant_id = %(tenant_id)s
                AND cls.classroom_id = t_tias_course.classroom_id
                AND cls.has_course = 1
                AND cls.begin_time <= t_tias_course.course_end_time
                AND cls.end_time >= t_tias_course.course_start_time
            )
        ) daily
        CROSS JOIN (
          SELECT MIN(leti_number) AS min_live_leti
          FROM t_tias_course
          WHERE delete_flag = 0
            AND tenant_id = %(tenant_id)s
            AND leti_number IS NOT NULL
            AND course_start_time <= %(now)s
            AND course_end_time >= %(now)s
            AND EXISTS (
              SELECT 1
              FROM t_tias_classroom cls
              WHERE cls.delete_flag = 0
                AND cls.tenant_id = %(tenant_id)s
                AND cls.classroom_id = t_tias_course.classroom_id
                AND cls.has_course = 1
                AND cls.begin_time <= %(now)s
                AND cls.end_time >= %(now)s
            )
        ) live
        CROSS JOIN (
          SELECT
            SUM(CASE WHEN course_end_time < %(now)s THEN 1 ELSE 0 END) AS completed_count,
            COUNT(*) AS total_count
          FROM t_tias_course
          WHERE delete_flag = 0
            AND tenant_id = %(tenant_id)s
            AND DATE(course_start_time) = DATE(%(now)s)
            AND EXISTS (
              SELECT 1
              FROM t_tias_classroom cls
              WHERE cls.delete_flag = 0
                AND cls.tenant_id = %(tenant_id)s
                AND cls.classroom_id = t_tias_course.classroom_id
                AND cls.has_course = 1
                AND cls.begin_time <= t_tias_course.course_end_time
                AND cls.end_time >= t_tias_course.course_start_time
            )
        ) progress
        """,
        {"tenant_id": tenant_id, "now": now},
    )
    return _format_round_metrics(row, source="tias")


def _format_round_metrics(row: dict[str, Any], *, source: str) -> dict[str, Any]:
    mx = _to_int(row.get("max_leti"))
    dc = _to_int(row.get("distinct_leti"))
    cur = _to_int(row.get("current_live_leti"))
    daily_total = max(mx, dc)
    completed_count = _to_int(row.get("completed_count"))
    total_count = _to_int(row.get("total_count"))
    progress_pct = min(100, int(round(completed_count / total_count * 100))) if total_count > 0 else 0
    return {
        "daily_round_total": daily_total,
        "current_round_number": cur,
        "patrol_round_progress": f"{progress_pct}%",
        "completed_classroom_count": completed_count,
        "daily_classroom_total": total_count,
        "round_data_source": source,
    }


def _fetch_finished_sections_from_schedule(tenant_id: str, now: datetime) -> int | None:
    tenant_org_code = _resolve_schedule_tenant_org_code(tenant_id)
    try:
        row = _fetch_schedule_one(
            """
            SELECT
              COUNT(DISTINCT lt.leti_number) AS finished_section_count
            FROM t_course c
            LEFT JOIN t_lesson_time lt
              ON lt.id = c.leti_id
             AND COALESCE(lt.recycle_sign, 0) = 0
             AND (lt.tenant_org_code = c.tenant_org_code OR lt.tenant_org_code IS NULL)
            WHERE COALESCE(c.recycle_sign, 0) = 0
              AND c.tenant_org_code = %(tenant_org_code)s
              AND DATE(c.cour_begin_time) = DATE(%(now)s)
              AND c.cour_end_time < %(now)s
              AND COALESCE(c.clro_enable, 1) = 1
            """,
            {"tenant_org_code": tenant_org_code, "now": now},
        )
    except Exception:
        return None
    return _to_int(row.get("finished_section_count"))


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


def _warning_level_name(level: int | None) -> str:
    if level is None:
        return "未知"
    level_int = int(level)
    if level_int <= 0:
        return "未知"
    mapping = {
        1: "高",
        2: "中",
        3: "低",
        4: "提示",
    }
    return mapping.get(level_int, f"L{level_int}")


def get_realtime_patrol_brief(tenant_id: str, *, synthesize: bool = True) -> dict[str, Any]:
    now = datetime.now()
    rounds = _fetch_patrol_round_metrics(tenant_id, now)
    threshold_params = _patrol_threshold_params()
    focus_attendance_lt = threshold_params["focus_attendance_lt"]
    focus_front_full_lt = threshold_params["focus_front_full_lt"]
    focus_rise_lt = threshold_params["focus_rise_lt"]
    vitality_attendance_gte = threshold_params["vitality_attendance_gte"]
    vitality_front_full_gte = threshold_params["vitality_front_full_gte"]
    vitality_rise_gte = threshold_params["vitality_rise_gte"]
    row = _fetch_one(
        """
        SELECT
          live.current_section,
          live.classroom_count,
          live.avg_attendance,
          live.avg_front_full,
          live.avg_rise,
          live.low_attendance_count,
          live.low_front_full_count,
          live.low_rise_count,
          live.over_attendance_count,
          live.focus_classroom_count,
          live.high_vitality_count
        FROM (
          SELECT
            COALESCE(MIN(leti_name), '-') AS current_section,
            COUNT(*) AS classroom_count,
            COALESCE(ROUND(AVG(tias_att_percent), 2), 0) AS avg_attendance,
            COALESCE(ROUND(AVG(tias_front_full_percent), 2), 0) AS avg_front_full,
            COALESCE(ROUND(AVG(tias_rise_percent), 2), 0) AS avg_rise,
            SUM(CASE WHEN COALESCE(tias_att_percent, 100) < %(focus_attendance_lt)s THEN 1 ELSE 0 END) AS low_attendance_count,
            SUM(CASE WHEN COALESCE(tias_front_full_percent, 100) < %(focus_front_full_lt)s THEN 1 ELSE 0 END) AS low_front_full_count,
            SUM(CASE WHEN COALESCE(tias_rise_percent, 100) < %(focus_rise_lt)s THEN 1 ELSE 0 END) AS low_rise_count,
            SUM(CASE WHEN COALESCE(tias_att_percent, 0) > 100 THEN 1 ELSE 0 END) AS over_attendance_count,
            SUM(CASE WHEN COALESCE(tias_att_percent, 100) < %(focus_attendance_lt)s
                          AND COALESCE(tias_front_full_percent, 100) < %(focus_front_full_lt)s
                          AND COALESCE(tias_rise_percent, 100) < %(focus_rise_lt)s
                     THEN 1 ELSE 0 END) AS focus_classroom_count,
            SUM(CASE WHEN COALESCE(tias_att_percent, 0) >= %(vitality_attendance_gte)s
                          AND COALESCE(tias_front_full_percent, 0) >= %(vitality_front_full_gte)s
                          AND COALESCE(tias_rise_percent, 0) >= %(vitality_rise_gte)s
                     THEN 1 ELSE 0 END) AS high_vitality_count
          FROM t_tias_course
          WHERE delete_flag = 0
            AND tenant_id = %(tenant_id)s
            AND course_start_time <= %(now)s
            AND course_end_time >= %(now)s
            AND EXISTS (
              SELECT 1
              FROM t_tias_classroom cls
              WHERE cls.delete_flag = 0
                AND cls.tenant_id = %(tenant_id)s
                AND cls.classroom_id = t_tias_course.classroom_id
                AND cls.has_course = 1
                AND cls.begin_time <= %(now)s
                AND cls.end_time >= %(now)s
            )
        ) live
        """,
        {"tenant_id": tenant_id, "now": now, **threshold_params},
    )
    org_rows = _fetch_all(
        """
        SELECT
          COALESCE(tecl_org_name, '未知学院') AS org_name,
          COUNT(*) AS class_count,
          COALESCE(ROUND(AVG(tias_att_percent), 2), 0) AS avg_attendance,
          SUM(
            CASE WHEN COALESCE(tias_att_percent, 100) < %(focus_attendance_lt)s
                      AND COALESCE(tias_front_full_percent, 100) < %(focus_front_full_lt)s
                      AND COALESCE(tias_rise_percent, 100) < %(focus_rise_lt)s
                 THEN 1 ELSE 0 END
          ) AS focus_count
        FROM t_tias_course
        WHERE delete_flag = 0
          AND tenant_id = %(tenant_id)s
          AND course_start_time <= %(now)s
          AND course_end_time >= %(now)s
          AND EXISTS (
            SELECT 1
            FROM t_tias_classroom cls
            WHERE cls.delete_flag = 0
              AND cls.tenant_id = %(tenant_id)s
              AND cls.classroom_id = t_tias_course.classroom_id
              AND cls.has_course = 1
              AND cls.begin_time <= %(now)s
              AND cls.end_time >= %(now)s
          )
        GROUP BY COALESCE(tecl_org_name, '未知学院')
        ORDER BY focus_count DESC, class_count DESC, avg_attendance ASC
        LIMIT 10
        """,
        {"tenant_id": tenant_id, "now": now, **threshold_params},
    )
    focus_top_rows = _fetch_all(
        """
        SELECT
          COALESCE(subject_name, teaching_class_name, CONCAT('课程#', course_id)) AS course_name,
          COALESCE(teacher_names, '未知教师') AS teacher_names,
          COALESCE(classroom_name, '未知教室') AS classroom_name,
          COALESCE(leti_name, CONCAT('第', COALESCE(leti_number, 0), '节')) AS leti_name,
          COALESCE(leti_number, 0) AS leti_number,
          COALESCE(tecl_org_name, '未知学院') AS org_name,
          COALESCE(tias_att_percent, 0) AS att_percent,
          COALESCE(tias_front_full_percent, 0) AS front_full_percent,
          COALESCE(tias_rise_percent, 0) AS rise_percent,
          (
            CASE WHEN COALESCE(tias_att_percent, 100) < %(focus_attendance_lt)s THEN 1 ELSE 0 END +
            CASE WHEN COALESCE(tias_front_full_percent, 100) < %(focus_front_full_lt)s THEN 1 ELSE 0 END +
            CASE WHEN COALESCE(tias_rise_percent, 100) < %(focus_rise_lt)s THEN 1 ELSE 0 END
          ) AS risk_flag_count
        FROM t_tias_course
        WHERE delete_flag = 0
          AND tenant_id = %(tenant_id)s
          AND course_start_time <= %(now)s
          AND course_end_time >= %(now)s
          AND COALESCE(tias_att_percent, 100) < %(focus_attendance_lt)s
          AND COALESCE(tias_front_full_percent, 100) < %(focus_front_full_lt)s
          AND COALESCE(tias_rise_percent, 100) < %(focus_rise_lt)s
          AND EXISTS (
            SELECT 1
            FROM t_tias_classroom cls
            WHERE cls.delete_flag = 0
              AND cls.tenant_id = %(tenant_id)s
              AND cls.classroom_id = t_tias_course.classroom_id
              AND cls.has_course = 1
              AND cls.begin_time <= %(now)s
              AND cls.end_time >= %(now)s
          )
        ORDER BY risk_flag_count DESC, att_percent ASC, rise_percent ASC, front_full_percent ASC
        LIMIT 10
        """,
        {"tenant_id": tenant_id, "now": now, **threshold_params},
    )
    vitality_top_rows = _fetch_all(
        """
        SELECT
          COALESCE(subject_name, teaching_class_name, CONCAT('课程#', course_id)) AS course_name,
          COALESCE(teacher_names, '未知教师') AS teacher_names,
          COALESCE(classroom_name, '未知教室') AS classroom_name,
          COALESCE(leti_name, CONCAT('第', COALESCE(leti_number, 0), '节')) AS leti_name,
          COALESCE(leti_number, 0) AS leti_number,
          COALESCE(tecl_org_name, '未知学院') AS org_name,
          COALESCE(tias_att_percent, 0) AS att_percent,
          COALESCE(tias_front_full_percent, 0) AS front_full_percent,
          COALESCE(tias_rise_percent, 0) AS rise_percent
        FROM t_tias_course
        WHERE delete_flag = 0
          AND tenant_id = %(tenant_id)s
          AND course_start_time <= %(now)s
          AND course_end_time >= %(now)s
          AND COALESCE(tias_att_percent, 0) >= %(vitality_attendance_gte)s
          AND COALESCE(tias_front_full_percent, 0) >= %(vitality_front_full_gte)s
          AND COALESCE(tias_rise_percent, 0) >= %(vitality_rise_gte)s
          AND EXISTS (
            SELECT 1
            FROM t_tias_classroom cls
            WHERE cls.delete_flag = 0
              AND cls.tenant_id = %(tenant_id)s
              AND cls.classroom_id = t_tias_course.classroom_id
              AND cls.has_course = 1
              AND cls.begin_time <= %(now)s
              AND cls.end_time >= %(now)s
          )
        ORDER BY att_percent DESC, front_full_percent DESC, rise_percent DESC
        LIMIT 10
        """,
        {"tenant_id": tenant_id, "now": now, **threshold_params},
    )
    payload = {
        "current_section": row["current_section"],
        "classroom_count": _to_int(row["classroom_count"]),
        "patrol_round": rounds["current_round_number"],
        "daily_round_total": rounds["daily_round_total"],
        "patrol_round_progress": rounds["patrol_round_progress"],
        "completed_classroom_count": rounds["completed_classroom_count"],
        "daily_classroom_total": rounds["daily_classroom_total"],
        "round_data_source": rounds.get("round_data_source", "tias"),
        "round_definition_kb": PATROL_ROUND_KNOWLEDGE_BASE,
        "avg_attendance": _to_float(row["avg_attendance"]),
        "avg_front_full": _to_float(row["avg_front_full"]),
        "avg_rise": _to_float(row["avg_rise"]),
        "low_attendance_count": _to_int(row.get("low_attendance_count")),
        "low_front_full_count": _to_int(row.get("low_front_full_count")),
        "low_rise_count": _to_int(row.get("low_rise_count")),
        "over_attendance_count": _to_int(row.get("over_attendance_count")),
        "focus_classroom_count": _to_int(row["focus_classroom_count"]),
        "high_vitality_count": _to_int(row["high_vitality_count"]),
        "focus_ratio": 0.0,
        "high_vitality_ratio": 0.0,
        "org_focus_top10": org_rows,
        "focus_course_top10": focus_top_rows,
        "high_vitality_course_top10": vitality_top_rows,
        "generated_at": now.isoformat(timespec="seconds"),
    }
    if payload["classroom_count"] > 0:
        payload["focus_ratio"] = round(payload["focus_classroom_count"] / payload["classroom_count"] * 100, 2)
        payload["high_vitality_ratio"] = round(payload["high_vitality_count"] / payload["classroom_count"] * 100, 2)

    if payload["classroom_count"] <= 0:
        payload["brief"] = (
            "【实时AI巡课简报】\n"
            f"当前节次：{payload['current_section']}；当前未检索到在课课堂。\n"
            f"当前轮次：第{payload['patrol_round']}/{payload['daily_round_total']}轮，AI巡查进度{payload['patrol_round_progress']}。\n"
            "【可能原因】当前非课表时段/课表同步延迟/AI巡课数据尚未入库。\n"
            "【建议】可改问“今日AI巡课汇总”，或确认课表库与AI巡课库连接状态。"
        )
        return payload

    round_txt = (
        f"第{payload['patrol_round']}/{payload['daily_round_total']}轮"
        if payload["daily_round_total"]
        else f"第{payload['patrol_round']}轮"
    )
    summary_fallback = (
        f"当前在课{payload['classroom_count']}个课堂，AI巡查进度{payload['patrol_round_progress']}；"
        f"到课率{payload['avg_attendance']}%、抬头率{payload['avg_rise']}%，建议优先关注低到课与低抬头课堂。"
    )
    summary = (
        _summarize(
            "请输出1句易懂的实时AI巡课结论（25-60字，先说当前状态，再说优先关注方向）。",
            payload,
            summary_fallback,
        )
        if synthesize
        else summary_fallback
    )
    summary = summary.replace("\n", " ").strip()

    def _course_metric_line(idx: int, course_row: dict[str, Any]) -> str:
        identity = _course_top_identity(course_row)
        return (
            f"{idx}. {identity}："
            f"到课{_to_float(course_row.get('att_percent'))}%，"
            f"前排{_to_float(course_row.get('front_full_percent'))}%，"
            f"抬头{_to_float(course_row.get('rise_percent'))}%"
        )

    org_text = (
        "；".join(f"{idx + 1}.{str(r.get('org_name') or '未知学院')}({_to_int(r.get('focus_count'))})" for idx, r in enumerate(org_rows[:5]))
        if org_rows
        else "暂无"
    )
    focus_lines = [_course_metric_line(idx, r) for idx, r in enumerate(focus_top_rows[:5], start=1)]
    focus_text = "\n".join(focus_lines) if focus_lines else "暂无"
    vitality_lines = [_course_metric_line(idx, r) for idx, r in enumerate(vitality_top_rows[:5], start=1)]
    vitality_text = "\n".join(vitality_lines) if vitality_lines else "暂无"

    suggestions: list[str] = []
    if payload["low_attendance_count"] > 0:
        suggestions.append(
            f"优先核查到课率低于{_fmt_threshold(focus_attendance_lt)}%的课堂，确认是否存在缺勤集中、调停课或课表人数异常。"
        )
    if payload["low_rise_count"] > 0:
        suggestions.append("对抬头率偏低课堂开展现场或视频复核，重点查看互动组织与课堂节奏。")
    if org_rows and _to_int(org_rows[0].get("focus_count")) > 0:
        suggestions.append("对重点关注课堂集中的学院优先发起回访，按学院推进课堂改进闭环。")
    if payload["over_attendance_count"] > 0:
        suggestions.append("对到课率超过100%的课堂核查合班、旁听与应到人数同步情况。")
    if not suggestions:
        suggestions.append("整体运行平稳，建议保持AI巡查频率并持续跟踪边缘风险课堂。")

    suggestion_text = "\n".join(f"{idx}. {text}" for idx, text in enumerate(suggestions[:4], start=1))

    focus_reason_text = (
        f"到课率偏低{payload['low_attendance_count']}个；"
        f"前排满座率偏低{payload['low_front_full_count']}个；"
        f"抬头率偏低{payload['low_rise_count']}个。"
    )

    data_notes = [
        "统计范围为当前在课且已产生AI巡课数据的课堂。",
        (
            "重点关注课堂阈值："
            f"到课率<{_fmt_threshold(focus_attendance_lt)}% 且 "
            f"前排满座率<{_fmt_threshold(focus_front_full_lt)}% 且 "
            f"抬头率<{_fmt_threshold(focus_rise_lt)}%。"
        ),
        (
            "活力较高课堂阈值："
            f"到课率≥{_fmt_threshold(vitality_attendance_gte)}% 且 "
            f"前排满座率≥{_fmt_threshold(vitality_front_full_gte)}% 且 "
            f"抬头率≥{_fmt_threshold(vitality_rise_gte)}%。"
        ),
    ]
    if payload["over_attendance_count"] > 0:
        data_notes.append(
            f"当前有{payload['over_attendance_count']}个课堂到课率超过100%，可能与旁听、合班、应到人数未同步或识别误差有关。"
        )
    notes_text = "\n".join(f"- {item}" for item in data_notes)

    suggestion_section_title = "【五、建议动作】"
    notes_section_title = "【六、数据说明】"
    vitality_metric_line = ""
    vitality_block = ""
    if payload["high_vitality_count"] > 0:
        vitality_metric_line = f"- 活力较高课堂：{payload['high_vitality_count']}个（占在课{payload['high_vitality_ratio']}%）\n"
        vitality_block = "【五、活力较高课堂Top5】\n" f"{vitality_text}\n"
        suggestion_section_title = "【六、建议动作】"
        notes_section_title = "【七、数据说明】"

    payload["brief"] = (
        "【实时AI巡课简报】\n"
        f"【总体结论】{summary}\n"
        "【一、总体概览】\n"
        f"- 当前节次：{payload['current_section']}\n"
        f"- 在课课堂：{payload['classroom_count']}个\n"
        f"- AI巡查轮次：{round_txt}（进度{payload['patrol_round_progress']}）\n"
        "【二、核心指标】\n"
        f"- 平均到课率：{payload['avg_attendance']}%\n"
        f"- 平均前排满座率：{payload['avg_front_full']}%\n"
        f"- 平均抬头率：{payload['avg_rise']}%\n"
        f"- 重点关注课堂：{payload['focus_classroom_count']}个（占在课{payload['focus_ratio']}%）\n"
        f"{vitality_metric_line}"
        "【三、重点关注情况】\n"
        f"- 触发原因拆分：{focus_reason_text}\n"
        f"- 学院风险Top5：{org_text}\n"
        "【四、重点关注课堂Top5】\n"
        f"{focus_text}\n"
        f"{vitality_block}"
        f"{suggestion_section_title}\n"
        f"{suggestion_text}\n"
        f"{notes_section_title}\n"
        f"{notes_text}"
    )
    return payload


def get_daily_patrol_brief(tenant_id: str, *, synthesize: bool = True) -> dict[str, Any]:
    now = datetime.now()
    today = now.date()
    threshold_params = _patrol_threshold_params()
    focus_attendance_lt = threshold_params["focus_attendance_lt"]
    focus_front_full_lt = threshold_params["focus_front_full_lt"]
    focus_rise_lt = threshold_params["focus_rise_lt"]
    vitality_attendance_gte = threshold_params["vitality_attendance_gte"]
    vitality_front_full_gte = threshold_params["vitality_front_full_gte"]
    vitality_rise_gte = threshold_params["vitality_rise_gte"]
    row = _fetch_one(
        """
        SELECT
          COUNT(*) AS classroom_count,
          COUNT(DISTINCT leti_number) AS finished_section_count,
          COALESCE(ROUND(AVG(tias_att_percent), 2), 0) AS avg_attendance,
          COALESCE(ROUND(AVG(tias_front_full_percent), 2), 0) AS avg_front_full,
          COALESCE(ROUND(AVG(tias_rise_percent), 2), 0) AS avg_rise,
          COALESCE(ROUND(SUM(COALESCE(tias_avg_concentration, 0)), 2), 0) AS activity_data,
          SUM(CASE WHEN COALESCE(tias_att_percent, 100) < %(focus_attendance_lt)s THEN 1 ELSE 0 END) AS low_attendance_count,
          SUM(CASE WHEN COALESCE(tias_front_full_percent, 100) < %(focus_front_full_lt)s THEN 1 ELSE 0 END) AS low_front_full_count,
          SUM(CASE WHEN COALESCE(tias_rise_percent, 100) < %(focus_rise_lt)s THEN 1 ELSE 0 END) AS low_rise_count,
          SUM(CASE WHEN COALESCE(tias_att_percent, 0) > 100 THEN 1 ELSE 0 END) AS over_attendance_count,
          SUM(CASE WHEN COALESCE(tias_att_percent, 100) < %(focus_attendance_lt)s
                        AND COALESCE(tias_front_full_percent, 100) < %(focus_front_full_lt)s
                        AND COALESCE(tias_rise_percent, 100) < %(focus_rise_lt)s
                   THEN 1 ELSE 0 END) AS focus_classroom_count,
          SUM(CASE WHEN COALESCE(tias_att_percent, 0) >= %(vitality_attendance_gte)s
                        AND COALESCE(tias_front_full_percent, 0) >= %(vitality_front_full_gte)s
                        AND COALESCE(tias_rise_percent, 0) >= %(vitality_rise_gte)s
                   THEN 1 ELSE 0 END) AS high_vitality_count
        FROM t_tias_course
        WHERE delete_flag = 0
          AND tenant_id = %(tenant_id)s
          AND DATE(course_start_time) = %(today)s
          AND course_end_time < %(now)s
          AND EXISTS (
            SELECT 1
            FROM t_tias_classroom cls
            WHERE cls.delete_flag = 0
              AND cls.tenant_id = %(tenant_id)s
              AND cls.classroom_id = t_tias_course.classroom_id
              AND cls.has_course = 1
              AND cls.begin_time <= t_tias_course.course_end_time
              AND cls.end_time >= t_tias_course.course_start_time
          )
        """,
        {"tenant_id": tenant_id, "today": today, "now": now, **threshold_params},
    )
    org_rows = _fetch_all(
        """
        SELECT
          COALESCE(tecl_org_name, '未知学院') AS org_name,
          COUNT(*) AS class_count,
          COALESCE(ROUND(AVG(tias_att_percent), 2), 0) AS avg_attendance,
          COALESCE(ROUND(AVG(tias_front_full_percent), 2), 0) AS avg_front_full,
          COALESCE(ROUND(AVG(tias_rise_percent), 2), 0) AS avg_rise,
          SUM(
            CASE WHEN COALESCE(tias_att_percent, 100) < %(focus_attendance_lt)s
                      AND COALESCE(tias_front_full_percent, 100) < %(focus_front_full_lt)s
                      AND COALESCE(tias_rise_percent, 100) < %(focus_rise_lt)s
                 THEN 1 ELSE 0 END
          ) AS focus_count
        FROM t_tias_course
        WHERE delete_flag = 0
          AND tenant_id = %(tenant_id)s
          AND DATE(course_start_time) = %(today)s
          AND course_end_time < %(now)s
          AND EXISTS (
            SELECT 1
            FROM t_tias_classroom cls
            WHERE cls.delete_flag = 0
              AND cls.tenant_id = %(tenant_id)s
              AND cls.classroom_id = t_tias_course.classroom_id
              AND cls.has_course = 1
              AND cls.begin_time <= t_tias_course.course_end_time
              AND cls.end_time >= t_tias_course.course_start_time
          )
        GROUP BY COALESCE(tecl_org_name, '未知学院')
        ORDER BY focus_count DESC, class_count DESC, avg_attendance ASC
        LIMIT 10
        """,
        {"tenant_id": tenant_id, "today": today, "now": now, **threshold_params},
    )
    section_rows = _fetch_all(
        """
        SELECT
          COALESCE(leti_number, 0) AS leti_number,
          COALESCE(leti_name, CONCAT('第', COALESCE(leti_number, 0), '节')) AS section_name,
          COUNT(*) AS class_count,
          COALESCE(ROUND(AVG(tias_att_percent), 2), 0) AS avg_attendance
        FROM t_tias_course
        WHERE delete_flag = 0
          AND tenant_id = %(tenant_id)s
          AND DATE(course_start_time) = %(today)s
          AND course_end_time < %(now)s
          AND COALESCE(tias_att_percent, 100) < %(focus_attendance_lt)s
          AND COALESCE(tias_front_full_percent, 100) < %(focus_front_full_lt)s
          AND COALESCE(tias_rise_percent, 100) < %(focus_rise_lt)s
          AND EXISTS (
            SELECT 1
            FROM t_tias_classroom cls
            WHERE cls.delete_flag = 0
              AND cls.tenant_id = %(tenant_id)s
              AND cls.classroom_id = t_tias_course.classroom_id
              AND cls.has_course = 1
              AND cls.begin_time <= t_tias_course.course_end_time
              AND cls.end_time >= t_tias_course.course_start_time
          )
        GROUP BY COALESCE(leti_number, 0), COALESCE(leti_name, CONCAT('第', COALESCE(leti_number, 0), '节'))
        ORDER BY COALESCE(leti_number, 0) ASC, class_count DESC
        LIMIT 10
        """,
        {"tenant_id": tenant_id, "today": today, "now": now, **threshold_params},
    )
    focus_top_rows = _fetch_all(
        """
        SELECT
          COALESCE(subject_name, teaching_class_name, CONCAT('课程#', course_id)) AS course_name,
          COALESCE(teacher_names, '未知教师') AS teacher_names,
          COALESCE(classroom_name, '未知教室') AS classroom_name,
          COALESCE(leti_name, CONCAT('第', COALESCE(leti_number, 0), '节')) AS leti_name,
          COALESCE(leti_number, 0) AS leti_number,
          COALESCE(tecl_org_name, '未知学院') AS org_name,
          COALESCE(tias_att_percent, 0) AS att_percent,
          COALESCE(tias_front_full_percent, 0) AS front_full_percent,
          COALESCE(tias_rise_percent, 0) AS rise_percent,
          (
            CASE WHEN COALESCE(tias_att_percent, 100) < %(focus_attendance_lt)s THEN 1 ELSE 0 END +
            CASE WHEN COALESCE(tias_front_full_percent, 100) < %(focus_front_full_lt)s THEN 1 ELSE 0 END +
            CASE WHEN COALESCE(tias_rise_percent, 100) < %(focus_rise_lt)s THEN 1 ELSE 0 END
          ) AS risk_flag_count
        FROM t_tias_course
        WHERE delete_flag = 0
          AND tenant_id = %(tenant_id)s
          AND DATE(course_start_time) = %(today)s
          AND course_end_time < %(now)s
          AND COALESCE(tias_att_percent, 100) < %(focus_attendance_lt)s
          AND COALESCE(tias_front_full_percent, 100) < %(focus_front_full_lt)s
          AND COALESCE(tias_rise_percent, 100) < %(focus_rise_lt)s
          AND EXISTS (
            SELECT 1
            FROM t_tias_classroom cls
            WHERE cls.delete_flag = 0
              AND cls.tenant_id = %(tenant_id)s
              AND cls.classroom_id = t_tias_course.classroom_id
              AND cls.has_course = 1
              AND cls.begin_time <= t_tias_course.course_end_time
              AND cls.end_time >= t_tias_course.course_start_time
          )
        ORDER BY risk_flag_count DESC, att_percent ASC, rise_percent ASC, front_full_percent ASC
        LIMIT 10
        """,
        {"tenant_id": tenant_id, "today": today, "now": now, **threshold_params},
    )
    vitality_top_rows = _fetch_all(
        """
        SELECT
          COALESCE(subject_name, teaching_class_name, CONCAT('课程#', course_id)) AS course_name,
          COALESCE(teacher_names, '未知教师') AS teacher_names,
          COALESCE(classroom_name, '未知教室') AS classroom_name,
          COALESCE(leti_name, CONCAT('第', COALESCE(leti_number, 0), '节')) AS leti_name,
          COALESCE(leti_number, 0) AS leti_number,
          COALESCE(tecl_org_name, '未知学院') AS org_name,
          COALESCE(tias_att_percent, 0) AS att_percent,
          COALESCE(tias_front_full_percent, 0) AS front_full_percent,
          COALESCE(tias_rise_percent, 0) AS rise_percent
        FROM t_tias_course
        WHERE delete_flag = 0
          AND tenant_id = %(tenant_id)s
          AND DATE(course_start_time) = %(today)s
          AND course_end_time < %(now)s
          AND COALESCE(tias_att_percent, 0) >= %(vitality_attendance_gte)s
          AND COALESCE(tias_front_full_percent, 0) >= %(vitality_front_full_gte)s
          AND COALESCE(tias_rise_percent, 0) >= %(vitality_rise_gte)s
          AND EXISTS (
            SELECT 1
            FROM t_tias_classroom cls
            WHERE cls.delete_flag = 0
              AND cls.tenant_id = %(tenant_id)s
              AND cls.classroom_id = t_tias_course.classroom_id
              AND cls.has_course = 1
              AND cls.begin_time <= t_tias_course.course_end_time
              AND cls.end_time >= t_tias_course.course_start_time
          )
        ORDER BY att_percent DESC, front_full_percent DESC, rise_percent DESC
        LIMIT 10
        """,
        {"tenant_id": tenant_id, "today": today, "now": now, **threshold_params},
    )
    today_overview = _fetch_today_course_overview(tenant_id, now)
    finished_sections = _to_int(today_overview.get("today_finished_section_count"))
    finished_source = str(today_overview.get("today_schedule_source") or "tias")
    scheduled_classroom_count = _to_int(today_overview.get("today_scheduled_classroom_count"))
    scheduled_section_count = _to_int(today_overview.get("today_scheduled_section_count"))
    payload = {
        "classroom_count": _to_int(row["classroom_count"]),
        "finished_section_count": finished_sections,
        "finished_section_source": finished_source,
        "today_scheduled_classroom_count": scheduled_classroom_count,
        "today_scheduled_section_count": scheduled_section_count,
        "today_scheduled_section_max": _to_int(today_overview.get("today_scheduled_section_max")),
        "today_scheduled_section_distinct": _to_int(today_overview.get("today_scheduled_section_distinct")),
        "today_completed_classroom_count": _to_int(today_overview.get("today_completed_classroom_count")),
        "today_live_classroom_count": _to_int(today_overview.get("today_live_classroom_count")),
        "today_schedule_source": finished_source,
        "avg_attendance": _to_float(row["avg_attendance"]),
        "avg_front_full": _to_float(row["avg_front_full"]),
        "avg_rise": _to_float(row["avg_rise"]),
        "activity_data": _to_float(row["activity_data"]),
        "low_attendance_count": _to_int(row.get("low_attendance_count")),
        "low_front_full_count": _to_int(row.get("low_front_full_count")),
        "low_rise_count": _to_int(row.get("low_rise_count")),
        "over_attendance_count": _to_int(row.get("over_attendance_count")),
        "focus_classroom_count": _to_int(row["focus_classroom_count"]),
        "high_vitality_count": _to_int(row["high_vitality_count"]),
        "focus_ratio": 0.0,
        "high_vitality_ratio": 0.0,
        "inspection_coverage_ratio": 0.0,
        "org_focus_top10": org_rows,
        "section_distribution": section_rows,
        "focus_course_top10": focus_top_rows,
        "high_vitality_course_top10": vitality_top_rows,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    if payload["classroom_count"] > 0:
        payload["focus_ratio"] = round(payload["focus_classroom_count"] / payload["classroom_count"] * 100, 2)
        payload["high_vitality_ratio"] = round(payload["high_vitality_count"] / payload["classroom_count"] * 100, 2)
    if payload["today_scheduled_classroom_count"] > 0:
        payload["inspection_coverage_ratio"] = round(
            payload["classroom_count"] / payload["today_scheduled_classroom_count"] * 100,
            2,
        )
    # 兼容旧字段名的同时，给 LLM 总结使用语义更清晰的课程节次口径，避免误写为“间教室”。
    payload["inspected_course_count"] = payload["classroom_count"]
    payload["today_scheduled_course_count"] = payload["today_scheduled_classroom_count"]
    payload["today_completed_course_count"] = payload["today_completed_classroom_count"]
    payload["today_live_course_count"] = payload["today_live_classroom_count"]

    if payload["classroom_count"] <= 0:
        payload["brief"] = (
            "【今日AI巡课简报】\n"
            "当前未检索到今日已完成课堂的AI巡课数据。\n"
            f"【课表概览】今日排课{payload['today_scheduled_course_count']}节课程，"
            f"AI巡查覆盖率{payload['inspection_coverage_ratio']}%（已完成AI巡查课程节次/今日排课课程节次）。"
            f"今日节次进度：{payload['finished_section_count']}/{payload['today_scheduled_section_count']}。\n"
            "【可能原因】今日暂无排课/课程尚未结束/AI巡课数据延迟入库。\n"
            "【建议】可稍后重试，或查询“实时AI巡课简报”确认当前在课情况。"
        )
        return payload

    summary_fallback = (
        f"今日AI巡课覆盖率{payload['inspection_coverage_ratio']}%，"
        f"已完成AI巡查课程节次平均到课率{payload['avg_attendance']}%、抬头率{payload['avg_rise']}%，"
        f"重点关注课堂较多，建议优先跟进到课率和抬头率偏低课程。"
    )
    summary_payload = {
        "统计口径": "非课表时间段今日AI巡课汇总，范围为今日已结束且已产生AI巡课数据的课程节次。",
        "单位说明": "今日排课数、已完成AI巡查数的单位是“节课程/课程节次”，不是“间教室”。",
        "today_scheduled_course_count": payload["today_scheduled_course_count"],
        "inspected_course_count": payload["inspected_course_count"],
        "inspection_coverage_ratio": payload["inspection_coverage_ratio"],
        "finished_section_count": payload["finished_section_count"],
        "today_scheduled_section_count": payload["today_scheduled_section_count"],
        "avg_attendance": payload["avg_attendance"],
        "avg_front_full": payload["avg_front_full"],
        "avg_rise": payload["avg_rise"],
        "focus_course_count": payload["focus_classroom_count"],
        "high_vitality_course_count": payload["high_vitality_count"],
        "low_attendance_course_count": payload["low_attendance_count"],
        "low_rise_course_count": payload["low_rise_count"],
    }
    summary = (
        _summarize(
            "请输出1句易懂的今日AI巡课总体结论（25-60字，先说整体情况，再说优先跟进方向，避免过度风险化）。注意：排课和AI巡查数量必须写成“节课程/课程节次”，不得写成“间教室”。",
            summary_payload,
            summary_fallback,
        )
        if synthesize
        else summary_fallback
    )
    summary = summary.replace("\n", " ").strip()

    def _display_section_name(section_name: Any, leti_number: int) -> str:
        if leti_number > 0:
            return f"第{leti_number}节"
        raw = str(section_name or "").strip()
        if raw and "不区分" not in raw:
            return raw
        return "未知节次"

    def _course_metric_line(idx: int, course_row: dict[str, Any]) -> str:
        identity = _course_top_identity(course_row)
        return (
            f"{idx}. {identity}："
            f"到课{_to_float(course_row.get('att_percent'))}%，"
            f"前排{_to_float(course_row.get('front_full_percent'))}%，"
            f"抬头{_to_float(course_row.get('rise_percent'))}%"
        )

    org_text = (
        "；".join(f"{idx + 1}.{str(r.get('org_name') or '未知学院')}({_to_int(r.get('focus_count'))})" for idx, r in enumerate(org_rows[:5]))
        if org_rows
        else "暂无"
    )
    section_lines = []
    for idx, section_row in enumerate(section_rows[:5], start=1):
        leti_number = _to_int(section_row.get("leti_number"))
        section_name = _display_section_name(section_row.get("section_name"), leti_number)
        section_lines.append(
            f"{idx}. {section_name}：{_to_int(section_row.get('class_count'))}节课程，平均到课率{_to_float(section_row.get('avg_attendance'))}%"
        )
    section_text = "\n".join(section_lines) if section_lines else "暂无"

    focus_lines = [_course_metric_line(idx, r) for idx, r in enumerate(focus_top_rows[:5], start=1)]
    focus_text = "\n".join(focus_lines) if focus_lines else "暂无"
    vitality_lines = [_course_metric_line(idx, r) for idx, r in enumerate(vitality_top_rows[:5], start=1)]
    vitality_text = "\n".join(vitality_lines) if vitality_lines else "暂无"

    suggestions: list[str] = []
    if payload["low_attendance_count"] > 0:
        suggestions.append(
            f"优先核查到课率低于{_fmt_threshold(focus_attendance_lt)}%的课堂，确认是否存在调停课、合班或应到人数异常。"
        )
    if payload["low_rise_count"] > 0:
        suggestions.append("对抬头率偏低课堂开展教学互动复核，建议结合课堂录像或督导记录跟进。")
    if org_rows and _to_int(org_rows[0].get("focus_count")) > 0:
        suggestions.append("对重点关注课堂集中的学院形成问题清单，按学院开展回访闭环。")
    if payload["over_attendance_count"] > 0:
        suggestions.append("对到课率超过100%的课堂核查课表人数、旁听和识别口径，避免误判。")
    if not suggestions:
        suggestions.append("整体运行平稳，建议持续抽检边缘风险课堂并复用高表现课堂经验。")

    suggestion_text = "\n".join(f"{idx}. {text}" for idx, text in enumerate(suggestions[:4], start=1))

    focus_reason_text = (
        f"到课率偏低{payload['low_attendance_count']}个；"
        f"前排满座率偏低{payload['low_front_full_count']}个；"
        f"抬头率偏低{payload['low_rise_count']}个。"
    )

    data_notes: list[str] = [
        "统计范围为今日已结束且已产生AI巡课数据的课程节次。",
        (
            "重点关注课堂阈值："
            f"到课率<{_fmt_threshold(focus_attendance_lt)}% 且 "
            f"前排满座率<{_fmt_threshold(focus_front_full_lt)}% 且 "
            f"抬头率<{_fmt_threshold(focus_rise_lt)}%。"
        ),
        (
            "活力较高课堂阈值："
            f"到课率≥{_fmt_threshold(vitality_attendance_gte)}% 且 "
            f"前排满座率≥{_fmt_threshold(vitality_front_full_gte)}% 且 "
            f"抬头率≥{_fmt_threshold(vitality_rise_gte)}%。"
        ),
    ]
    if payload["today_scheduled_section_count"] <= 0 and payload["classroom_count"] > 0:
        data_notes.append("部分课表节次暂未识别，本报告已按实际AI巡课记录统计。")
    if payload["activity_data"] <= 0:
        data_notes.append("课堂活动指数当前为0，可能为今日暂无有效记录或该指标尚未完整接入。")
    if payload["over_attendance_count"] > 0:
        data_notes.append(
            f"有{payload['over_attendance_count']}个课堂到课率超过100%，可能与旁听、合班、应到人数未同步或识别误差有关。"
        )

    notes_text = "\n".join(f"- {item}" for item in data_notes)

    overview_line = (
        f"今日排课{payload['today_scheduled_course_count']}节课程，已完成AI巡查{payload['inspected_course_count']}节课程，"
        f"AI巡查覆盖率{payload['inspection_coverage_ratio']}%（已完成AI巡查课程节次/今日排课课程节次）。"
    )
    if payload["today_scheduled_section_count"] > 0:
        overview_line += (
            f" 今日节次进度：{payload['finished_section_count']}/{payload['today_scheduled_section_count']}。"
        )

    suggestion_section_title = "【六、建议动作】"
    notes_section_title = "【七、数据说明】"
    vitality_metric_line = ""
    vitality_block = ""
    if payload["high_vitality_count"] > 0:
        vitality_metric_line = (
            f"- 活力较高课堂：{payload['high_vitality_count']}个（占已完成AI巡查课程节次{payload['high_vitality_ratio']}%）\n"
        )
        vitality_block = "【六、活力较高课堂Top5】\n" f"{vitality_text}\n"
        suggestion_section_title = "【七、建议动作】"
        notes_section_title = "【八、数据说明】"

    payload["brief"] = (
        "【今日AI巡课简报】\n"
        f"【总体结论】{summary}\n"
        "【一、总体概览】\n"
        f"- {overview_line}\n"
        "【二、核心指标】\n"
        f"- 平均到课率：{payload['avg_attendance']}%\n"
        f"- 平均前排满座率：{payload['avg_front_full']}%\n"
        f"- 平均抬头率：{payload['avg_rise']}%\n"
        f"- 课堂活动指数：{payload['activity_data']}\n"
        f"- 重点关注课堂：{payload['focus_classroom_count']}个（占已完成AI巡查课程节次{payload['focus_ratio']}%）\n"
        f"{vitality_metric_line}"
        "【三、重点关注情况】\n"
        f"- 触发原因拆分：{focus_reason_text}\n"
        f"- 学院风险Top5：{org_text}\n"
        "【四、节次分布】\n"
        f"{section_text}\n"
        "【五、重点关注课堂Top5】\n"
        f"{focus_text}\n"
        f"{vitality_block}"
        f"{suggestion_section_title}\n"
        f"{suggestion_text}\n"
        f"{notes_section_title}\n"
        f"{notes_text}"
    )
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
          COALESCE(warn.warning_record_count, 0) AS warning_record_count,
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
            AND EXISTS (
              SELECT 1
              FROM t_tias_classroom cls
              WHERE cls.delete_flag = 0
                AND cls.tenant_id = %(tenant_id)s
                AND cls.classroom_id = t_tias_course.classroom_id
                AND cls.has_course = 1
                AND cls.begin_time <= %(now)s
                AND cls.end_time >= %(now)s
            )
        ) sec
        LEFT JOIN (
          SELECT
            COUNT(DISTINCT w.course_id) AS warning_classroom_count,
            COUNT(*) AS warning_record_count,
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
              AND EXISTS (
                SELECT 1
                FROM t_tias_classroom cls
                WHERE cls.delete_flag = 0
                  AND cls.tenant_id = %(tenant_id)s
                  AND cls.classroom_id = c.classroom_id
                  AND cls.has_course = 1
                  AND cls.begin_time <= %(now)s
                  AND cls.end_time >= %(now)s
              )
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
              AND EXISTS (
                SELECT 1
                FROM t_tias_classroom cls
                WHERE cls.delete_flag = 0
                  AND cls.tenant_id = %(tenant_id)s
                  AND cls.classroom_id = c.classroom_id
                  AND cls.has_course = 1
                  AND cls.begin_time <= %(now)s
                  AND cls.end_time >= %(now)s
              )
          ) w
        ) warn ON 1 = 1
        """,
        {"tenant_id": tenant_id, "now": now},
    )
    level_rows = _fetch_all(
        """
        SELECT
          x.warning_level,
          COUNT(*) AS warning_count
        FROM (
          SELECT r.warning_level
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
            AND EXISTS (
              SELECT 1
              FROM t_tias_classroom cls
              WHERE cls.delete_flag = 0
                AND cls.tenant_id = %(tenant_id)s
                AND cls.classroom_id = c.classroom_id
                AND cls.has_course = 1
                AND cls.begin_time <= %(now)s
                AND cls.end_time >= %(now)s
            )
          UNION ALL
          SELECT r.warning_level
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
            AND EXISTS (
              SELECT 1
              FROM t_tias_classroom cls
              WHERE cls.delete_flag = 0
                AND cls.tenant_id = %(tenant_id)s
                AND cls.classroom_id = c.classroom_id
                AND cls.has_course = 1
                AND cls.begin_time <= %(now)s
                AND cls.end_time >= %(now)s
            )
        ) x
        GROUP BY x.warning_level
        ORDER BY x.warning_level
        """,
        {"tenant_id": tenant_id, "now": now},
    )
    type_rows = _fetch_all(
        """
        SELECT
          COALESCE(x.indicator_name, '未知类型') AS indicator_name,
          COUNT(*) AS warning_count
        FROM (
          SELECT r.indicator_name
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
            AND EXISTS (
              SELECT 1
              FROM t_tias_classroom cls
              WHERE cls.delete_flag = 0
                AND cls.tenant_id = %(tenant_id)s
                AND cls.classroom_id = c.classroom_id
                AND cls.has_course = 1
                AND cls.begin_time <= %(now)s
                AND cls.end_time >= %(now)s
            )
          UNION ALL
          SELECT r.indicator_name
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
            AND EXISTS (
              SELECT 1
              FROM t_tias_classroom cls
              WHERE cls.delete_flag = 0
                AND cls.tenant_id = %(tenant_id)s
                AND cls.classroom_id = c.classroom_id
                AND cls.has_course = 1
                AND cls.begin_time <= %(now)s
                AND cls.end_time >= %(now)s
            )
        ) x
        GROUP BY COALESCE(x.indicator_name, '未知类型')
        ORDER BY warning_count DESC, indicator_name
        LIMIT 10
        """,
        {"tenant_id": tenant_id, "now": now},
    )
    warning_course_rows = _fetch_all(
        """
        SELECT
          COALESCE(x.course_name, CONCAT('课程#', x.course_id)) AS course_name,
          COALESCE(x.clro_name, '未知教室') AS classroom_name,
          COALESCE(x.teacher_names, '未知教师') AS teacher_names,
          COALESCE(x.leti_name, CONCAT('第', COALESCE(x.leti_number, 0), '节')) AS leti_name,
          COALESCE(x.leti_number, 0) AS leti_number,
          COALESCE(x.org_name, '未知学院') AS org_name,
          COUNT(*) AS warning_count,
          COUNT(DISTINCT x.indicator_name) AS indicator_type_count,
          MIN(x.warning_level) AS worst_warning_level,
          MAX(x.warning_time) AS latest_warning_time
        FROM (
          SELECT
            r.course_id,
            r.course_name,
            r.clro_name,
            r.org_name,
            COALESCE(c.teacher_names, '未知教师') AS teacher_names,
            COALESCE(c.leti_name, CONCAT('第', COALESCE(c.leti_number, 0), '节')) AS leti_name,
            COALESCE(c.leti_number, 0) AS leti_number,
            r.indicator_name,
            r.warning_level,
            r.warning_time
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
            AND EXISTS (
              SELECT 1
              FROM t_tias_classroom cls
              WHERE cls.delete_flag = 0
                AND cls.tenant_id = %(tenant_id)s
                AND cls.classroom_id = c.classroom_id
                AND cls.has_course = 1
                AND cls.begin_time <= %(now)s
                AND cls.end_time >= %(now)s
            )
          UNION ALL
          SELECT
            r.course_id,
            r.course_name,
            r.clro_name,
            r.org_name,
            COALESCE(c.teacher_names, '未知教师') AS teacher_names,
            COALESCE(c.leti_name, CONCAT('第', COALESCE(c.leti_number, 0), '节')) AS leti_name,
            COALESCE(c.leti_number, 0) AS leti_number,
            r.indicator_name,
            r.warning_level,
            r.warning_time
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
            AND EXISTS (
              SELECT 1
              FROM t_tias_classroom cls
              WHERE cls.delete_flag = 0
                AND cls.tenant_id = %(tenant_id)s
                AND cls.classroom_id = c.classroom_id
                AND cls.has_course = 1
                AND cls.begin_time <= %(now)s
                AND cls.end_time >= %(now)s
            )
        ) x
        GROUP BY
          x.course_id,
          COALESCE(x.course_name, CONCAT('课程#', x.course_id)),
          COALESCE(x.clro_name, '未知教室'),
          COALESCE(x.teacher_names, '未知教师'),
          COALESCE(x.leti_name, CONCAT('第', COALESCE(x.leti_number, 0), '节')),
          COALESCE(x.leti_number, 0),
          COALESCE(x.org_name, '未知学院')
        ORDER BY warning_count DESC, worst_warning_level ASC, latest_warning_time DESC
        LIMIT 10
        """,
        {"tenant_id": tenant_id, "now": now},
    )
    warning_org_rows = _fetch_all(
        """
        SELECT
          COALESCE(x.org_name, '未知学院') AS org_name,
          COUNT(*) AS warning_count,
          COUNT(DISTINCT x.course_id) AS warning_course_count,
          MIN(x.warning_level) AS worst_warning_level
        FROM (
          SELECT r.course_id, r.org_name, r.warning_level, r.warning_time
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
            AND EXISTS (
              SELECT 1
              FROM t_tias_classroom cls
              WHERE cls.delete_flag = 0
                AND cls.tenant_id = %(tenant_id)s
                AND cls.classroom_id = c.classroom_id
                AND cls.has_course = 1
                AND cls.begin_time <= %(now)s
                AND cls.end_time >= %(now)s
            )
          UNION ALL
          SELECT r.course_id, r.org_name, r.warning_level, r.warning_time
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
            AND EXISTS (
              SELECT 1
              FROM t_tias_classroom cls
              WHERE cls.delete_flag = 0
                AND cls.tenant_id = %(tenant_id)s
                AND cls.classroom_id = c.classroom_id
                AND cls.has_course = 1
                AND cls.begin_time <= %(now)s
                AND cls.end_time >= %(now)s
            )
        ) x
        GROUP BY COALESCE(x.org_name, '未知学院')
        ORDER BY warning_count DESC, worst_warning_level ASC
        LIMIT 10
        """,
        {"tenant_id": tenant_id, "now": now},
    )
    class_count = _to_int(row["class_count"])
    warning_count = _to_int(row["warning_classroom_count"])
    warning_record_count = _to_int(row.get("warning_record_count"))
    if warning_record_count <= 0:
        warning_record_count = sum(_to_int(r.get("warning_count")) for r in level_rows)
    ratio = round((warning_count / class_count * 100), 2) if class_count else 0.0
    warning_type_top10 = [
        {
            "indicator_name": str(r.get("indicator_name") or "未知类型"),
            "warning_count": _to_int(r.get("warning_count")),
            "warning_ratio": (
                round(_to_int(r.get("warning_count")) / warning_record_count * 100, 2)
                if warning_record_count
                else 0.0
            ),
        }
        for r in type_rows
    ]
    warning_type_top = warning_type_top10[:3]
    level_total = sum(_to_int(r.get("warning_count")) for r in level_rows)
    warning_level_distribution = []
    for r in level_rows:
        level = _to_int(r.get("warning_level"))
        label = _warning_level_name(level)
        cnt = _to_int(r.get("warning_count"))
        warning_level_distribution.append(
            {
                "warning_level": level,
                "warning_level_name": label,
                "warning_count": cnt,
                "warning_ratio": round(cnt / level_total * 100, 2) if level_total else 0.0,
            }
        )
    high_level_count = 0
    for item in warning_level_distribution:
        if _to_int(item.get("warning_level")) == 1:
            high_level_count = _to_int(item.get("warning_count"))
            break
    high_level_ratio = round(high_level_count / warning_record_count * 100, 2) if warning_record_count else 0.0
    warning_type_top_text = (
        "；".join(
            f"{idx + 1}.{x['indicator_name']}({x['warning_count']}条,{x['warning_ratio']}%)"
            for idx, x in enumerate(warning_type_top10[:5])
        )
        if warning_type_top10
        else "暂无"
    )
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
        "round_data_source": rounds.get("round_data_source", "tias"),
        "round_definition_kb": PATROL_ROUND_KNOWLEDGE_BASE,
        "current_section": row["current_section"],
        "class_count": class_count,
        "warning_classroom_count": warning_count,
        "warning_record_count": warning_record_count,
        "warning_ratio": ratio,
        "worst_warning_level": _to_int(worst) if worst is not None else None,
        "avg_warning_level": round(_to_float(avg_lvl), 3) if avg_lvl is not None else None,
        "overall_warning_risk": risk,
        "warning_types": row["warning_types"] or "暂无",
        "warning_type_top3": warning_type_top,
        "warning_type_top10": warning_type_top10,
        "warning_level_distribution": warning_level_distribution,
        "warning_course_top10": warning_course_rows,
        "warning_org_top10": warning_org_rows,
        "high_level_warning_count": high_level_count,
        "high_level_warning_ratio": high_level_ratio,
        "risk_level_rule": (
            "整体风险由最严重预警等级、平均预警等级与预警课堂占比共同计算得出。"
        ),
        "generated_at": now.isoformat(timespec="seconds"),
    }
    if class_count <= 0:
        payload["brief"] = (
            "【实时预警简报】\n"
            f"当前节次：{payload['current_section']}；当前未检索到在课课堂。\n"
            "【可能原因】当前非课表时段、课表同步延迟，或在课课堂尚未产生AI巡课记录。\n"
            "【建议】可查询“今日预警汇总”查看当天已结束课堂风险。"
        )
        return payload

    round_txt = (
        f"第{payload['patrol_round']}/{payload['daily_round_total']}轮"
        if payload["daily_round_total"]
        else f"第{payload['patrol_round']}轮"
    )
    summary_fallback = (
        f"{round_txt}中在课{payload['class_count']}个，预警课堂占比{payload['warning_ratio']}%，"
        f"整体风险{payload['overall_warning_risk']}。"
    )
    summary = (
        _summarize(
            "请输出1句实时预警结论（20-50字，必须包含风险等级或预警占比）。",
            payload,
            summary_fallback,
        )
        if synthesize
        else summary_fallback
    )
    level_text = (
        "；".join(
            f"{idx + 1}.{str(x.get('warning_level_name') or '未知')}({_to_int(x.get('warning_count'))}条,{_to_float(x.get('warning_ratio'))}%)"
            for idx, x in enumerate(warning_level_distribution)
        )
        if warning_level_distribution
        else "暂无"
    )
    course_text = (
        "；".join(
            f"{idx + 1}.{_course_top_identity(r)}"
            f"(预警{_to_int(r.get('warning_count'))}条,最严重{_warning_level_name(_to_int(r.get('worst_warning_level')))})"
            for idx, r in enumerate(warning_course_rows[:10])
        )
        if warning_course_rows
        else "暂无"
    )
    org_text = (
        "；".join(
            f"{idx + 1}.{str(r.get('org_name') or '未知学院')}({_to_int(r.get('warning_count'))}条/{_to_int(r.get('warning_course_count'))}节次)"
            for idx, r in enumerate(warning_org_rows[:5])
        )
        if warning_org_rows
        else "暂无"
    )
    suggestions: list[str] = []
    if warning_count <= 0:
        suggestions.append("当前轮次未发现预警课堂，建议保持AI巡查频率并关注下一轮波动。")
    else:
        if payload["overall_warning_risk"] == "高" or payload["warning_ratio"] >= 30:
            suggestions.append("整体风险偏高，建议按Top课堂立即触发院系与任课教师双线处置。")
        if high_level_count > 0:
            suggestions.append("存在高等级预警，建议优先处理高等级课堂并在10分钟内复核。")
        if payload["warning_ratio"] >= 15:
            suggestions.append("预警覆盖面较大，建议按预警类型分组派单，提升闭环效率。")
    if not suggestions:
        suggestions.append("预警规模可控，建议持续跟踪Top类型并做课堂改进复盘。")
    payload["brief"] = (
        "【实时预警简报】\n"
        f"【结论】{summary}\n"
        f"【核心指标】{round_txt}（进度{payload['patrol_round_progress']}），当前节次{payload['current_section']}，在课{payload['class_count']}个。"
        f"预警课堂{payload['warning_classroom_count']}个（{payload['warning_ratio']}%），预警记录{payload['warning_record_count']}条，"
        f"高等级预警{payload['high_level_warning_count']}条（{payload['high_level_warning_ratio']}%），整体风险{payload['overall_warning_risk']}。\n"
        f"【预警等级分布】{level_text}\n"
        f"【预警类型Top5】{warning_type_top_text}\n"
        f"【高风险课堂Top10】{course_text}\n"
        f"【学院风险Top5】{org_text}\n"
        f"【建议动作】{' '.join(suggestions)}\n"
        "【口径】实时预警按近2小时内的学情和教情预警统计；整体风险由最严重等级、平均等级与预警课堂占比综合判断。"
    )
    return payload


def get_daily_warning_brief(tenant_id: str, *, synthesize: bool = True) -> dict[str, Any]:
    now = datetime.now()
    today = now.date()
    row = _fetch_one(
        """
        SELECT
          base.inspected_classroom_count,
          COALESCE(warn.warning_classroom_count, 0) AS warning_classroom_count,
          COALESCE(warn.warning_record_count, 0) AS warning_record_count,
          warn.warning_types,
          warn.worst_warning_level,
          warn.avg_warning_level
        FROM (
          SELECT COUNT(DISTINCT course_id) AS inspected_classroom_count
          FROM t_tias_course
          WHERE delete_flag = 0
            AND tenant_id = %(tenant_id)s
            AND DATE(course_start_time) = %(today)s
            AND course_end_time < %(now)s
            AND EXISTS (
              SELECT 1
              FROM t_tias_classroom cls
              WHERE cls.delete_flag = 0
                AND cls.tenant_id = %(tenant_id)s
                AND cls.classroom_id = t_tias_course.classroom_id
                AND cls.has_course = 1
                AND cls.begin_time <= t_tias_course.course_end_time
                AND cls.end_time >= t_tias_course.course_start_time
            )
        ) base
        LEFT JOIN (
          SELECT
            COUNT(DISTINCT w.course_id) AS warning_classroom_count,
            COUNT(*) AS warning_record_count,
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
              AND c.course_end_time < %(now)s
              AND DATE(r.warning_time) = %(today)s
              AND EXISTS (
                SELECT 1
                FROM t_tias_classroom cls
                WHERE cls.delete_flag = 0
                  AND cls.tenant_id = %(tenant_id)s
                  AND cls.classroom_id = c.classroom_id
                  AND cls.has_course = 1
                  AND cls.begin_time <= c.course_end_time
                  AND cls.end_time >= c.course_start_time
              )
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
              AND c.course_end_time < %(now)s
              AND DATE(r.warning_time) = %(today)s
              AND EXISTS (
                SELECT 1
                FROM t_tias_classroom cls
                WHERE cls.delete_flag = 0
                  AND cls.tenant_id = %(tenant_id)s
                  AND cls.classroom_id = c.classroom_id
                  AND cls.has_course = 1
                  AND cls.begin_time <= c.course_end_time
                  AND cls.end_time >= c.course_start_time
              )
          ) w
        ) warn ON 1 = 1
        """,
        {"tenant_id": tenant_id, "today": today, "now": now},
    )
    level_rows = _fetch_all(
        """
        SELECT
          x.warning_level,
          COUNT(*) AS warning_count
        FROM (
          SELECT r.warning_level
          FROM t_warning_study_record r
          INNER JOIN t_tias_course c
            ON c.course_id = r.course_id
           AND c.tenant_id = r.tenant_id
          WHERE r.delete_flag = 0
            AND r.tenant_id = %(tenant_id)s
            AND c.delete_flag = 0
            AND DATE(c.course_start_time) = %(today)s
            AND c.course_end_time < %(now)s
            AND DATE(r.warning_time) = %(today)s
            AND EXISTS (
              SELECT 1
              FROM t_tias_classroom cls
              WHERE cls.delete_flag = 0
                AND cls.tenant_id = %(tenant_id)s
                AND cls.classroom_id = c.classroom_id
                AND cls.has_course = 1
                AND cls.begin_time <= c.course_end_time
                AND cls.end_time >= c.course_start_time
            )
          UNION ALL
          SELECT r.warning_level
          FROM t_warning_teaching_record r
          INNER JOIN t_tias_course c
            ON c.course_id = r.course_id
           AND c.tenant_id = r.tenant_id
          WHERE r.delete_flag = 0
            AND r.tenant_id = %(tenant_id)s
            AND c.delete_flag = 0
            AND DATE(c.course_start_time) = %(today)s
            AND c.course_end_time < %(now)s
            AND DATE(r.warning_time) = %(today)s
            AND EXISTS (
              SELECT 1
              FROM t_tias_classroom cls
              WHERE cls.delete_flag = 0
                AND cls.tenant_id = %(tenant_id)s
                AND cls.classroom_id = c.classroom_id
                AND cls.has_course = 1
                AND cls.begin_time <= c.course_end_time
                AND cls.end_time >= c.course_start_time
            )
        ) x
        GROUP BY x.warning_level
        ORDER BY x.warning_level
        """,
        {"tenant_id": tenant_id, "today": today, "now": now},
    )
    type_rows = _fetch_all(
        """
        SELECT
          COALESCE(x.indicator_name, '未知类型') AS indicator_name,
          COUNT(*) AS warning_count
        FROM (
          SELECT r.indicator_name
          FROM t_warning_study_record r
          INNER JOIN t_tias_course c
            ON c.course_id = r.course_id
           AND c.tenant_id = r.tenant_id
          WHERE r.delete_flag = 0
            AND r.tenant_id = %(tenant_id)s
            AND c.delete_flag = 0
            AND DATE(c.course_start_time) = %(today)s
            AND c.course_end_time < %(now)s
            AND DATE(r.warning_time) = %(today)s
            AND EXISTS (
              SELECT 1
              FROM t_tias_classroom cls
              WHERE cls.delete_flag = 0
                AND cls.tenant_id = %(tenant_id)s
                AND cls.classroom_id = c.classroom_id
                AND cls.has_course = 1
                AND cls.begin_time <= c.course_end_time
                AND cls.end_time >= c.course_start_time
            )
          UNION ALL
          SELECT r.indicator_name
          FROM t_warning_teaching_record r
          INNER JOIN t_tias_course c
            ON c.course_id = r.course_id
           AND c.tenant_id = r.tenant_id
          WHERE r.delete_flag = 0
            AND r.tenant_id = %(tenant_id)s
            AND c.delete_flag = 0
            AND DATE(c.course_start_time) = %(today)s
            AND c.course_end_time < %(now)s
            AND DATE(r.warning_time) = %(today)s
            AND EXISTS (
              SELECT 1
              FROM t_tias_classroom cls
              WHERE cls.delete_flag = 0
                AND cls.tenant_id = %(tenant_id)s
                AND cls.classroom_id = c.classroom_id
                AND cls.has_course = 1
                AND cls.begin_time <= c.course_end_time
                AND cls.end_time >= c.course_start_time
            )
        ) x
        GROUP BY COALESCE(x.indicator_name, '未知类型')
        ORDER BY warning_count DESC, indicator_name
        LIMIT 10
        """,
        {"tenant_id": tenant_id, "today": today, "now": now},
    )
    warning_course_rows = _fetch_all(
        """
        SELECT
          COALESCE(x.course_name, CONCAT('课程#', x.course_id)) AS course_name,
          COALESCE(x.clro_name, '未知教室') AS classroom_name,
          COALESCE(x.teacher_names, '未知教师') AS teacher_names,
          COALESCE(x.leti_name, CONCAT('第', COALESCE(x.leti_number, 0), '节')) AS leti_name,
          COALESCE(x.leti_number, 0) AS leti_number,
          COALESCE(x.org_name, '未知学院') AS org_name,
          COUNT(*) AS warning_count,
          COUNT(DISTINCT x.indicator_name) AS indicator_type_count,
          MIN(x.warning_level) AS worst_warning_level,
          MAX(x.warning_time) AS latest_warning_time
        FROM (
          SELECT
            r.course_id,
            r.course_name,
            r.clro_name,
            r.org_name,
            COALESCE(c.teacher_names, '未知教师') AS teacher_names,
            COALESCE(c.leti_name, CONCAT('第', COALESCE(c.leti_number, 0), '节')) AS leti_name,
            COALESCE(c.leti_number, 0) AS leti_number,
            r.indicator_name,
            r.warning_level,
            r.warning_time
          FROM t_warning_study_record r
          INNER JOIN t_tias_course c
            ON c.course_id = r.course_id
           AND c.tenant_id = r.tenant_id
          WHERE r.delete_flag = 0
            AND r.tenant_id = %(tenant_id)s
            AND c.delete_flag = 0
            AND DATE(c.course_start_time) = %(today)s
            AND c.course_end_time < %(now)s
            AND DATE(r.warning_time) = %(today)s
            AND EXISTS (
              SELECT 1
              FROM t_tias_classroom cls
              WHERE cls.delete_flag = 0
                AND cls.tenant_id = %(tenant_id)s
                AND cls.classroom_id = c.classroom_id
                AND cls.has_course = 1
                AND cls.begin_time <= c.course_end_time
                AND cls.end_time >= c.course_start_time
            )
          UNION ALL
          SELECT
            r.course_id,
            r.course_name,
            r.clro_name,
            r.org_name,
            COALESCE(c.teacher_names, '未知教师') AS teacher_names,
            COALESCE(c.leti_name, CONCAT('第', COALESCE(c.leti_number, 0), '节')) AS leti_name,
            COALESCE(c.leti_number, 0) AS leti_number,
            r.indicator_name,
            r.warning_level,
            r.warning_time
          FROM t_warning_teaching_record r
          INNER JOIN t_tias_course c
            ON c.course_id = r.course_id
           AND c.tenant_id = r.tenant_id
          WHERE r.delete_flag = 0
            AND r.tenant_id = %(tenant_id)s
            AND c.delete_flag = 0
            AND DATE(c.course_start_time) = %(today)s
            AND c.course_end_time < %(now)s
            AND DATE(r.warning_time) = %(today)s
            AND EXISTS (
              SELECT 1
              FROM t_tias_classroom cls
              WHERE cls.delete_flag = 0
                AND cls.tenant_id = %(tenant_id)s
                AND cls.classroom_id = c.classroom_id
                AND cls.has_course = 1
                AND cls.begin_time <= c.course_end_time
                AND cls.end_time >= c.course_start_time
            )
        ) x
        GROUP BY
          x.course_id,
          COALESCE(x.course_name, CONCAT('课程#', x.course_id)),
          COALESCE(x.clro_name, '未知教室'),
          COALESCE(x.teacher_names, '未知教师'),
          COALESCE(x.leti_name, CONCAT('第', COALESCE(x.leti_number, 0), '节')),
          COALESCE(x.leti_number, 0),
          COALESCE(x.org_name, '未知学院')
        ORDER BY warning_count DESC, worst_warning_level ASC, latest_warning_time DESC
        LIMIT 10
        """,
        {"tenant_id": tenant_id, "today": today, "now": now},
    )
    warning_org_rows = _fetch_all(
        """
        SELECT
          COALESCE(x.org_name, '未知学院') AS org_name,
          COUNT(*) AS warning_count,
          COUNT(DISTINCT x.course_id) AS warning_course_count,
          MIN(x.warning_level) AS worst_warning_level
        FROM (
          SELECT r.course_id, r.org_name, r.warning_level, r.warning_time
          FROM t_warning_study_record r
          INNER JOIN t_tias_course c
            ON c.course_id = r.course_id
           AND c.tenant_id = r.tenant_id
          WHERE r.delete_flag = 0
            AND r.tenant_id = %(tenant_id)s
            AND c.delete_flag = 0
            AND DATE(c.course_start_time) = %(today)s
            AND c.course_end_time < %(now)s
            AND DATE(r.warning_time) = %(today)s
            AND EXISTS (
              SELECT 1
              FROM t_tias_classroom cls
              WHERE cls.delete_flag = 0
                AND cls.tenant_id = %(tenant_id)s
                AND cls.classroom_id = c.classroom_id
                AND cls.has_course = 1
                AND cls.begin_time <= c.course_end_time
                AND cls.end_time >= c.course_start_time
            )
          UNION ALL
          SELECT r.course_id, r.org_name, r.warning_level, r.warning_time
          FROM t_warning_teaching_record r
          INNER JOIN t_tias_course c
            ON c.course_id = r.course_id
           AND c.tenant_id = r.tenant_id
          WHERE r.delete_flag = 0
            AND r.tenant_id = %(tenant_id)s
            AND c.delete_flag = 0
            AND DATE(c.course_start_time) = %(today)s
            AND c.course_end_time < %(now)s
            AND DATE(r.warning_time) = %(today)s
            AND EXISTS (
              SELECT 1
              FROM t_tias_classroom cls
              WHERE cls.delete_flag = 0
                AND cls.tenant_id = %(tenant_id)s
                AND cls.classroom_id = c.classroom_id
                AND cls.has_course = 1
                AND cls.begin_time <= c.course_end_time
                AND cls.end_time >= c.course_start_time
            )
        ) x
        GROUP BY COALESCE(x.org_name, '未知学院')
        ORDER BY warning_count DESC, worst_warning_level ASC
        LIMIT 10
        """,
        {"tenant_id": tenant_id, "today": today, "now": now},
    )
    period_rows = _fetch_all(
        """
        SELECT
          CASE
            WHEN HOUR(x.warning_time) < 12 THEN '上午'
            WHEN HOUR(x.warning_time) < 18 THEN '下午'
            ELSE '晚上'
          END AS period_name,
          COUNT(*) AS warning_count
        FROM (
          SELECT r.warning_time
          FROM t_warning_study_record r
          INNER JOIN t_tias_course c
            ON c.course_id = r.course_id
           AND c.tenant_id = r.tenant_id
          WHERE r.delete_flag = 0
            AND r.tenant_id = %(tenant_id)s
            AND c.delete_flag = 0
            AND DATE(c.course_start_time) = %(today)s
            AND c.course_end_time < %(now)s
            AND DATE(r.warning_time) = %(today)s
            AND EXISTS (
              SELECT 1
              FROM t_tias_classroom cls
              WHERE cls.delete_flag = 0
                AND cls.tenant_id = %(tenant_id)s
                AND cls.classroom_id = c.classroom_id
                AND cls.has_course = 1
                AND cls.begin_time <= c.course_end_time
                AND cls.end_time >= c.course_start_time
            )
          UNION ALL
          SELECT r.warning_time
          FROM t_warning_teaching_record r
          INNER JOIN t_tias_course c
            ON c.course_id = r.course_id
           AND c.tenant_id = r.tenant_id
          WHERE r.delete_flag = 0
            AND r.tenant_id = %(tenant_id)s
            AND c.delete_flag = 0
            AND DATE(c.course_start_time) = %(today)s
            AND c.course_end_time < %(now)s
            AND DATE(r.warning_time) = %(today)s
            AND EXISTS (
              SELECT 1
              FROM t_tias_classroom cls
              WHERE cls.delete_flag = 0
                AND cls.tenant_id = %(tenant_id)s
                AND cls.classroom_id = c.classroom_id
                AND cls.has_course = 1
                AND cls.begin_time <= c.course_end_time
                AND cls.end_time >= c.course_start_time
            )
        ) x
        GROUP BY
          CASE
            WHEN HOUR(x.warning_time) < 12 THEN '上午'
            WHEN HOUR(x.warning_time) < 18 THEN '下午'
            ELSE '晚上'
          END
        ORDER BY warning_count DESC
        """,
        {"tenant_id": tenant_id, "today": today, "now": now},
    )
    inspected = _to_int(row["inspected_classroom_count"])
    warning = _to_int(row["warning_classroom_count"])
    warning_record_count = _to_int(row.get("warning_record_count"))
    if warning_record_count <= 0:
        warning_record_count = sum(_to_int(r.get("warning_count")) for r in level_rows)
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
        "warning_record_count": warning_record_count,
        "warning_ratio": ratio,
        "worst_warning_level": _to_int(worst) if worst is not None else None,
        "avg_warning_level": round(_to_float(avg_lvl), 3) if avg_lvl is not None else None,
        "overall_warning_risk": risk,
        "warning_types": row["warning_types"] or "暂无",
        "warning_level_distribution": [],
        "warning_type_top3": [],
        "warning_type_top10": [],
        "warning_course_top10": warning_course_rows,
        "warning_org_top10": warning_org_rows,
        "warning_period_distribution": period_rows,
        "high_level_warning_count": 0,
        "high_level_warning_ratio": 0.0,
        "risk_level_rule": (
            "整体风险由当日学情和教情预警的严重程度、平均水平与预警课堂占比综合判断。"
        ),
        "round_definition_kb": PATROL_ROUND_KNOWLEDGE_BASE,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    level_total = sum(_to_int(r.get("warning_count")) for r in level_rows)
    warning_level_distribution = []
    for r in level_rows:
        level = _to_int(r.get("warning_level"))
        cnt = _to_int(r.get("warning_count"))
        warning_level_distribution.append(
            {
                "warning_level": level,
                "warning_level_name": _warning_level_name(level),
                "warning_count": cnt,
                "warning_ratio": round(cnt / level_total * 100, 2) if level_total else 0.0,
            }
        )
    warning_type_top10 = [
        {
            "indicator_name": str(r.get("indicator_name") or "未知类型"),
            "warning_count": _to_int(r.get("warning_count")),
            "warning_ratio": (
                round(_to_int(r.get("warning_count")) / warning_record_count * 100, 2)
                if warning_record_count
                else 0.0
            ),
        }
        for r in type_rows
    ]
    warning_type_top3 = warning_type_top10[:3]
    high_level_count = 0
    for x in warning_level_distribution:
        if _to_int(x.get("warning_level")) == 1:
            high_level_count = _to_int(x.get("warning_count"))
            break
    high_level_ratio = round(high_level_count / warning_record_count * 100, 2) if warning_record_count else 0.0
    payload["warning_level_distribution"] = warning_level_distribution
    payload["warning_type_top3"] = warning_type_top3
    payload["warning_type_top10"] = warning_type_top10
    payload["high_level_warning_count"] = high_level_count
    payload["high_level_warning_ratio"] = high_level_ratio

    if inspected <= 0:
        payload["brief"] = (
            "【今日预警简报】\n"
            "当前未检索到今日已完成课堂的AI巡查数据。\n"
            "【可能原因】今日暂无已结束课程/AI巡查数据尚未入库。\n"
            "【建议】可先查询“实时预警简报”查看在课风险。"
        )
        return payload

    summary_fallback = (
        f"今日已完成AI巡查{inspected}个课堂，预警课堂{warning}个（{ratio}%），"
        f"整体风险{risk}，建议优先跟进高频预警类型与高风险课堂。"
    )
    summary = (
        _summarize(
            "请输出1句易懂的今日预警结论（25-60字，先给整体风险，再给优先处置方向）。",
            payload,
            summary_fallback,
        )
        if synthesize
        else summary_fallback
    )
    summary = summary.replace("\n", " ").strip()

    level_lines = [
        f"{idx}. {str(x.get('warning_level_name') or '未知')}：{_to_int(x.get('warning_count'))}条（{_to_float(x.get('warning_ratio'))}%）"
        for idx, x in enumerate(warning_level_distribution, start=1)
    ]
    level_text = "\n".join(level_lines) if level_lines else "暂无"

    type_lines = [
        f"{idx}. {x['indicator_name']}：{x['warning_count']}条（{x['warning_ratio']}%）"
        for idx, x in enumerate(warning_type_top10[:5], start=1)
    ]
    type_text = "\n".join(type_lines) if type_lines else "暂无"

    course_lines = [
        (
            f"{idx}. {_course_top_identity(r)}："
            f"预警{_to_int(r.get('warning_count'))}条，涉及{_to_int(r.get('indicator_type_count'))}类，"
            f"最严重等级{_warning_level_name(_to_int(r.get('worst_warning_level')))}"
        )
        for idx, r in enumerate(warning_course_rows[:5], start=1)
    ]
    course_text = "\n".join(course_lines) if course_lines else "暂无"

    org_lines = [
        (
            f"{idx}. {str(r.get('org_name') or '未知学院')}："
            f"{_to_int(r.get('warning_count'))}条预警 / {_to_int(r.get('warning_course_count'))}个节次"
        )
        for idx, r in enumerate(warning_org_rows[:5], start=1)
    ]
    org_text = "\n".join(org_lines) if org_lines else "暂无"

    period_lines = [
        f"{idx}. {str(r.get('period_name') or '未知时段')}：{_to_int(r.get('warning_count'))}条"
        for idx, r in enumerate(period_rows[:3], start=1)
    ]
    period_text = "\n".join(period_lines) if period_lines else "暂无"

    suggestions: list[str] = []
    if warning <= 0:
        suggestions.append("今日未检出预警课堂，建议保留关键时段抽检，验证稳定性。")
    else:
        if risk == "高" or ratio >= 30:
            suggestions.append("整体风险偏高，建议优先处置高风险课堂Top5，并同步学院负责人当日跟进。")
        if high_level_count > 0:
            suggestions.append("存在高等级预警，建议优先复盘对应课堂并在30分钟内反馈处置结果。")
        if ratio >= 15:
            suggestions.append("预警覆盖面较大，建议按预警类型拆分责任人并设置处理时限。")
        if warning_type_top10:
            suggestions.append(f"首要预警类型为“{warning_type_top10[0]['indicator_name']}”，建议针对该类型制定专项改进动作。")
    if not suggestions:
        suggestions.append("风险总体可控，建议沉淀低风险课堂治理经验并持续周度跟踪。")

    suggestion_text = "\n".join(f"{idx}. {text}" for idx, text in enumerate(suggestions[:4], start=1))

    data_notes = [
        "统计范围为今日已结束且已完成AI巡查课堂的学情和教情预警数据。",
        "整体风险等级由预警最严重等级、平均等级与预警课堂占比综合判断，并非人工填写结果。",
    ]
    if warning_record_count <= 0:
        data_notes.append("今日暂未检出有效预警记录。")
    notes_text = "\n".join(f"- {item}" for item in data_notes)

    main_type = warning_type_top10[0]["indicator_name"] if warning_type_top10 else "暂无"
    payload["brief"] = (
        "【今日预警简报】\n"
        f"【总体结论】{summary}\n"
        "【一、总体概览】\n"
        f"- 今日已完成AI巡查课堂：{inspected}个\n"
        f"- 预警课堂：{warning}个（占比{ratio}%）\n"
        f"- 整体风险等级：{risk}\n"
        "【二、核心指标】\n"
        f"- 预警记录总数：{warning_record_count}条\n"
        f"- 高等级预警：{high_level_count}条（占记录{high_level_ratio}%）\n"
        f"- 平均预警等级：{payload['avg_warning_level'] if payload['avg_warning_level'] is not None else '暂无'}\n"
        f"- 主要预警类型：{main_type}\n"
        "【三、预警分布】\n"
        f"- 时段分布Top3：\n{period_text}\n"
        f"- 等级分布：\n{level_text}\n"
        f"- 类型Top5：\n{type_text}\n"
        "【四、高风险课堂Top5】\n"
        f"{course_text}\n"
        "【五、学院风险Top5】\n"
        f"{org_text}\n"
        "【六、建议动作】\n"
        f"{suggestion_text}\n"
        "【七、数据说明】\n"
        f"{notes_text}"
    )
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
          AND EXISTS (
            SELECT 1
            FROM t_tias_classroom cls
            WHERE cls.delete_flag = 0
              AND cls.tenant_id = %(tenant_id)s
              AND cls.classroom_id = t_tias_course.classroom_id
              AND cls.has_course = 1
              AND cls.begin_time <= %(now)s
              AND cls.end_time >= %(now)s
          )
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
            f"本科课堂节次{payload['undergrad_course_count']}个，平均到课率{payload['undergrad_att']}%，抬头率{payload['undergrad_rise']}%；"
            f"研究生课堂节次{payload['graduate_course_count']}个，平均到课率{payload['graduate_att']}%，抬头率{payload['graduate_rise']}%。"
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
            f"{payload['teacher_name']}相关课堂共{payload['course_count']}个节次，平均到课率{payload['avg_attendance']}%，"
            f"抬头率{payload['avg_rise']}%，前排满座率{payload['avg_front_full']}%。"
        ),
    )
    return payload


def get_warning_handle_overview_brief(tenant_id: str, *, synthesize: bool = True) -> dict[str, Any]:
    today = datetime.now().date()
    row = _fetch_one(
        """
        SELECT
          COUNT(*) AS total_warning_count,
          SUM(CASE WHEN handle_status = 1 THEN 1 ELSE 0 END) AS pending_count,
          SUM(CASE WHEN handle_status = 2 THEN 1 ELSE 0 END) AS hang_count,
          SUM(CASE WHEN handle_status IN (3,4) THEN 1 ELSE 0 END) AS closed_count
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
        """,
        {"tenant_id": tenant_id, "today": today},
    )
    type_rows = _fetch_all(
        """
        SELECT
          COALESCE(indicator_name, '未知类型') AS indicator_name,
          COUNT(*) AS warning_count,
          SUM(CASE WHEN handle_status = 1 THEN 1 ELSE 0 END) AS pending_count,
          SUM(CASE WHEN handle_status = 2 THEN 1 ELSE 0 END) AS hang_count,
          SUM(CASE WHEN handle_status IN (3,4) THEN 1 ELSE 0 END) AS closed_count
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
        GROUP BY COALESCE(indicator_name, '未知类型')
        ORDER BY pending_count DESC, warning_count DESC
        LIMIT 5
        """,
        {"tenant_id": tenant_id, "today": today},
    )
    org_rows = _fetch_all(
        """
        SELECT
          COALESCE(org_name, '未知学院') AS org_name,
          COUNT(*) AS warning_count,
          COUNT(DISTINCT course_id) AS course_count,
          SUM(CASE WHEN handle_status = 1 THEN 1 ELSE 0 END) AS pending_count
        FROM (
          SELECT org_name, course_id, handle_status
          FROM t_warning_study_record
          WHERE delete_flag = 0
            AND tenant_id = %(tenant_id)s
            AND DATE(warning_time) = %(today)s
          UNION ALL
          SELECT org_name, course_id, handle_status
          FROM t_warning_teaching_record
          WHERE delete_flag = 0
            AND tenant_id = %(tenant_id)s
            AND DATE(warning_time) = %(today)s
        ) w
        GROUP BY COALESCE(org_name, '未知学院')
        ORDER BY pending_count DESC, warning_count DESC
        LIMIT 5
        """,
        {"tenant_id": tenant_id, "today": today},
    )
    level_rows = _fetch_all(
        """
        SELECT warning_level, COUNT(*) AS warning_count
        FROM (
          SELECT warning_level
          FROM t_warning_study_record
          WHERE delete_flag = 0
            AND tenant_id = %(tenant_id)s
            AND DATE(warning_time) = %(today)s
          UNION ALL
          SELECT warning_level
          FROM t_warning_teaching_record
          WHERE delete_flag = 0
            AND tenant_id = %(tenant_id)s
            AND DATE(warning_time) = %(today)s
        ) w
        GROUP BY warning_level
        ORDER BY warning_level ASC
        """,
        {"tenant_id": tenant_id, "today": today},
    )
    total = _to_int(row.get("total_warning_count"))
    pending = _to_int(row.get("pending_count"))
    hang = _to_int(row.get("hang_count"))
    closed = _to_int(row.get("closed_count"))
    pending_ratio = round((pending / total * 100), 2) if total else 0.0
    closed_ratio = round((closed / total * 100), 2) if total else 0.0
    status_rows = [
        {"status": "待处理", "count": pending, "ratio": pending_ratio},
        {"status": "挂起", "count": hang, "ratio": round((hang / total * 100), 2) if total else 0.0},
        {"status": "已闭环", "count": closed, "ratio": closed_ratio},
    ]
    type_top5 = [
        {
            "indicator_name": str(r.get("indicator_name") or "未知类型"),
            "warning_count": _to_int(r.get("warning_count")),
            "pending_count": _to_int(r.get("pending_count")),
            "hang_count": _to_int(r.get("hang_count")),
            "closed_count": _to_int(r.get("closed_count")),
        }
        for r in type_rows
    ]
    org_pending_top5 = [
        {
            "org_name": str(r.get("org_name") or "未知学院"),
            "warning_count": _to_int(r.get("warning_count")),
            "course_count": _to_int(r.get("course_count")),
            "pending_count": _to_int(r.get("pending_count")),
        }
        for r in org_rows
    ]
    level_distribution = [
        {
            "warning_level": _to_int(r.get("warning_level")),
            "warning_level_name": _warning_level_name(_to_int(r.get("warning_level"))),
            "warning_count": _to_int(r.get("warning_count")),
        }
        for r in level_rows
    ]
    payload = {
        "total_warning_count": total,
        "pending_count": pending,
        "hang_count": hang,
        "closed_count": closed,
        "pending_ratio": pending_ratio,
        "closed_ratio": closed_ratio,
        "status_distribution": status_rows,
        "type_handle_top5": type_top5,
        "org_pending_top5": org_pending_top5,
        "warning_level_distribution": level_distribution,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    type_text = (
        "\n".join(
            f"{idx}. {x['indicator_name']}：待处理{x['pending_count']}条 / 总{x['warning_count']}条"
            for idx, x in enumerate(type_top5, start=1)
        )
        if type_top5
        else "暂无"
    )
    org_text = (
        "\n".join(
            f"{idx}. {x['org_name']}：待处理{x['pending_count']}条，涉及{x['course_count']}个节次"
            for idx, x in enumerate(org_pending_top5, start=1)
        )
        if org_pending_top5
        else "暂无"
    )
    level_text = (
        "；".join(f"{x['warning_level_name']} {x['warning_count']}条" for x in level_distribution)
        if level_distribution
        else "暂无"
    )
    suggestions: list[str] = []
    if pending > 0:
        suggestions.append("优先处理待处理数量最高的预警类型，并按学院形成当日闭环清单。")
    if hang > 0:
        suggestions.append("对挂起预警补充挂起原因和预计处理时间，避免长期滞留。")
    if closed_ratio < 60 and total > 0:
        suggestions.append("今日闭环率偏低，建议按Top学院逐项推进反馈。")
    if not suggestions:
        suggestions.append("当前处置压力较低，建议保留重点类型复盘。")
    suggestion_text = "\n".join(f"{idx}. {text}" for idx, text in enumerate(suggestions[:3], start=1))
    payload["brief"] = (
        "【今日预警处置闭环】\n"
        f"【总体结论】今日预警{total}条，待处理{pending}条（{pending_ratio}%），已闭环{closed}条（{closed_ratio}%）。\n"
        "【一、处置概览】\n"
        f"- 待处理：{pending}条\n"
        f"- 挂起：{hang}条\n"
        f"- 已闭环：{closed}条\n"
        f"- 等级分布：{level_text}\n"
        "【二、待处理类型Top5】\n"
        f"{type_text}\n"
        "【三、学院待处理Top5】\n"
        f"{org_text}\n"
        "【四、建议动作】\n"
        f"{suggestion_text}\n"
        "【五、数据说明】\n"
        "- 统计范围为今日学情和教情预警记录。\n"
        "- 处置状态按当前流转结果分为待处理、挂起、已闭环；已闭环包含已处理和已确认完成的预警。"
    )
    return payload


def get_warning_trend_top_brief(tenant_id: str, *, synthesize: bool = True) -> dict[str, Any]:
    rows = _fetch_all(
        """
        SELECT
          DATE(warning_time) AS day,
          COUNT(*) AS warning_count
        FROM (
          SELECT warning_time
          FROM t_warning_study_record
          WHERE delete_flag = 0
            AND tenant_id = %(tenant_id)s
            AND warning_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
          UNION ALL
          SELECT warning_time
          FROM t_warning_teaching_record
          WHERE delete_flag = 0
            AND tenant_id = %(tenant_id)s
            AND warning_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        ) w
        GROUP BY DATE(warning_time)
        ORDER BY day
        """,
        {"tenant_id": tenant_id},
    )
    top_rows = _fetch_all(
        """
        SELECT
          COALESCE(indicator_name, '未知类型') AS indicator_name,
          COUNT(*) AS warning_count
        FROM (
          SELECT indicator_name, warning_time
          FROM t_warning_study_record
          WHERE delete_flag = 0
            AND tenant_id = %(tenant_id)s
            AND warning_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
          UNION ALL
          SELECT indicator_name, warning_time
          FROM t_warning_teaching_record
          WHERE delete_flag = 0
            AND tenant_id = %(tenant_id)s
            AND warning_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        ) w
        GROUP BY indicator_name
        ORDER BY warning_count DESC
        LIMIT 3
        """,
        {"tenant_id": tenant_id},
    )
    org_rows = _fetch_all(
        """
        SELECT
          COALESCE(org_name, '未知学院') AS org_name,
          COUNT(*) AS warning_count,
          COUNT(DISTINCT course_id) AS course_count
        FROM (
          SELECT org_name, course_id, warning_time
          FROM t_warning_study_record
          WHERE delete_flag = 0
            AND tenant_id = %(tenant_id)s
            AND warning_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
          UNION ALL
          SELECT org_name, course_id, warning_time
          FROM t_warning_teaching_record
          WHERE delete_flag = 0
            AND tenant_id = %(tenant_id)s
            AND warning_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        ) w
        GROUP BY COALESCE(org_name, '未知学院')
        ORDER BY warning_count DESC
        LIMIT 5
        """,
        {"tenant_id": tenant_id},
    )
    level_rows = _fetch_all(
        """
        SELECT warning_level, COUNT(*) AS warning_count
        FROM (
          SELECT warning_level, warning_time
          FROM t_warning_study_record
          WHERE delete_flag = 0
            AND tenant_id = %(tenant_id)s
            AND warning_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
          UNION ALL
          SELECT warning_level, warning_time
          FROM t_warning_teaching_record
          WHERE delete_flag = 0
            AND tenant_id = %(tenant_id)s
            AND warning_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        ) w
        GROUP BY warning_level
        ORDER BY warning_level ASC
        """,
        {"tenant_id": tenant_id},
    )
    trend = [{"day": str(r.get("day")), "warning_count": _to_int(r.get("warning_count"))} for r in rows]
    top3 = [{"indicator_name": r.get("indicator_name"), "warning_count": _to_int(r.get("warning_count"))} for r in top_rows]
    org_top5 = [
        {
            "org_name": str(r.get("org_name") or "未知学院"),
            "warning_count": _to_int(r.get("warning_count")),
            "course_count": _to_int(r.get("course_count")),
        }
        for r in org_rows
    ]
    level_distribution = [
        {
            "warning_level": _to_int(r.get("warning_level")),
            "warning_level_name": _warning_level_name(_to_int(r.get("warning_level"))),
            "warning_count": _to_int(r.get("warning_count")),
        }
        for r in level_rows
    ]
    total_7d = sum(x["warning_count"] for x in trend)
    avg_daily = round(total_7d / 7, 2)
    peak = max(trend, key=lambda x: x["warning_count"], default={"day": "-", "warning_count": 0})
    latest = trend[-1] if trend else {"day": "-", "warning_count": 0}
    payload = {
        "trend_7d": trend,
        "top3_indicators": top3,
        "org_top5": org_top5,
        "warning_level_distribution": level_distribution,
        "total_warning_count_7d": total_7d,
        "avg_daily_warning_count_7d": avg_daily,
        "peak_day": peak,
        "latest_day": latest,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    trend_text = "\n".join(f"{idx}. {x['day']}：{x['warning_count']}条" for idx, x in enumerate(trend, start=1)) or "暂无"
    top_text = "\n".join(
        f"{idx}. {x['indicator_name']}：{x['warning_count']}条" for idx, x in enumerate(top3, start=1)
    ) or "暂无"
    org_text = "\n".join(
        f"{idx}. {x['org_name']}：{x['warning_count']}条，涉及{x['course_count']}个节次"
        for idx, x in enumerate(org_top5, start=1)
    ) or "暂无"
    level_text = (
        "；".join(f"{x['warning_level_name']} {x['warning_count']}条" for x in level_distribution)
        if level_distribution
        else "暂无"
    )
    trend_direction = "暂无趋势"
    if len(trend) >= 2:
        delta = latest["warning_count"] - trend[-2]["warning_count"]
        trend_direction = "较前一日上升" if delta > 0 else "较前一日下降" if delta < 0 else "较前一日持平"
    payload["brief"] = (
        "【近7天预警趋势】\n"
        f"【总体结论】近7天共{total_7d}条预警，日均{avg_daily}条，峰值出现在{peak['day']}（{peak['warning_count']}条），最新一天{trend_direction}。\n"
        "【一、每日趋势】\n"
        f"{trend_text}\n"
        "【二、风险类型Top3】\n"
        f"{top_text}\n"
        "【三、学院风险Top5】\n"
        f"{org_text}\n"
        "【四、等级分布】\n"
        f"{level_text}\n"
        "【五、建议动作】\n"
        "1. 优先复盘峰值日期对应课程与高频预警类型。\n"
        "2. 对连续高发学院建立周度跟进清单。\n"
        "【六、数据说明】\n"
        "- 统计范围为近7天学情和教情预警记录。"
    )
    return payload


def get_alarm_strategy_effect_brief(tenant_id: str, *, synthesize: bool = True) -> dict[str, Any]:
    rule_row = _fetch_one(
        """
        SELECT COUNT(*) AS rule_count
        FROM t_patrol_alarm_event
        WHERE delete_flag = 0
          AND tenant_id = %(tenant_id)s
        """,
        {"tenant_id": tenant_id},
    )
    event_rows = _fetch_all(
        """
        SELECT
          e.indicator_id,
          COALESCE(i.indicator_name, e.alarm_desc, '未知规则') AS indicator_name,
          e.alarm_desc,
          e.rules_json
        FROM t_patrol_alarm_event e
        LEFT JOIN t_patrol_indicator_type i
          ON i.id = e.indicator_id
         AND i.tenant_id = e.tenant_id
         AND i.delete_flag = 0
        WHERE e.delete_flag = 0
          AND e.tenant_id = %(tenant_id)s
        ORDER BY e.id
        LIMIT 20
        """,
        {"tenant_id": tenant_id},
    )
    trigger_rows = _fetch_all(
        """
        SELECT
          COALESCE(indicator_name, '未知类型') AS indicator_name,
          COUNT(*) AS warning_count,
          COUNT(DISTINCT course_id) AS course_count
        FROM (
          SELECT indicator_name, course_id, warning_time
          FROM t_warning_study_record
          WHERE delete_flag = 0
            AND tenant_id = %(tenant_id)s
            AND warning_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
          UNION ALL
          SELECT indicator_name, course_id, warning_time
          FROM t_warning_teaching_record
          WHERE delete_flag = 0
            AND tenant_id = %(tenant_id)s
            AND warning_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        ) w
        GROUP BY COALESCE(indicator_name, '未知类型')
        ORDER BY warning_count DESC
        LIMIT 5
        """,
        {"tenant_id": tenant_id},
    )
    effect_list: list[dict[str, Any]] = []
    for ev in event_rows:
        indicator_id = _to_int(ev.get("indicator_id"))
        cnt_row = _fetch_one(
            """
            SELECT COUNT(*) AS trigger_count
            FROM (
              SELECT indicator_id, warning_time
              FROM t_warning_study_record
              WHERE delete_flag = 0
                AND tenant_id = %(tenant_id)s
                AND warning_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
              UNION ALL
              SELECT indicator_id, warning_time
              FROM t_warning_teaching_record
              WHERE delete_flag = 0
                AND tenant_id = %(tenant_id)s
                AND warning_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            ) w
            WHERE w.indicator_id = %(indicator_id)s
            """,
            {"tenant_id": tenant_id, "indicator_id": indicator_id},
        )
        effect_list.append(
            {
                "indicator_id": indicator_id,
                "indicator_name": ev.get("indicator_name"),
                "alarm_desc": ev.get("alarm_desc"),
                "rules_json": ev.get("rules_json"),
                "trigger_count_7d": _to_int(cnt_row.get("trigger_count")),
            }
        )
    sorted_effect_list = sorted(effect_list, key=lambda x: x["trigger_count_7d"], reverse=True)
    total_trigger_count = sum(_to_int(x.get("trigger_count_7d")) for x in sorted_effect_list)
    triggered_rule_count = sum(1 for x in sorted_effect_list if _to_int(x.get("trigger_count_7d")) > 0)
    zero_trigger_rule_count = max(len(sorted_effect_list) - triggered_rule_count, 0)
    effect_list = sorted_effect_list[:5]
    trigger_type_top5 = [
        {
            "indicator_name": str(r.get("indicator_name") or "未知类型"),
            "warning_count": _to_int(r.get("warning_count")),
            "course_count": _to_int(r.get("course_count")),
        }
        for r in trigger_rows
    ]
    payload = {
        "rule_count": _to_int(rule_row.get("rule_count")),
        "triggered_rule_count_7d": triggered_rule_count,
        "zero_trigger_rule_count": zero_trigger_rule_count,
        "sampled_rule_count": len(event_rows),
        "top_trigger_type_7d": trigger_type_top5,
        "top_strategy_effect": effect_list,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    effect_text = (
        "\n".join(
            f"{idx}. {str(x.get('indicator_name') or '未知规则')}：近7天触发{_to_int(x.get('trigger_count_7d'))}次"
            for idx, x in enumerate(effect_list, start=1)
        )
        if effect_list
        else "暂无"
    )
    trigger_text = (
        "\n".join(
            f"{idx}. {x['indicator_name']}：{x['warning_count']}条，涉及{x['course_count']}个节次"
            for idx, x in enumerate(trigger_type_top5, start=1)
        )
        if trigger_type_top5
        else "暂无"
    )
    payload["brief"] = (
        "【告警策略阈值效果】\n"
        f"【总体结论】当前配置{payload['rule_count']}条告警规则，本次抽样{payload['sampled_rule_count']}条，近7天合计触发{total_trigger_count}次，"
        f"其中{triggered_rule_count}条规则有触发记录。\n"
        "【一、规则触发Top5】\n"
        f"{effect_text}\n"
        "【二、预警类型触发Top5】\n"
        f"{trigger_text}\n"
        "【三、策略健康度】\n"
        f"- 规则总数：{payload['rule_count']}条\n"
        f"- 抽样规则数：{payload['sampled_rule_count']}条\n"
        f"- 近7天有触发规则：{triggered_rule_count}条\n"
        f"- 样本中暂无触发规则：{zero_trigger_rule_count}条\n"
        "【四、建议动作】\n"
        "1. 对高频触发规则复核阈值是否过严，避免低价值预警过多。\n"
        "2. 对长期无触发规则检查是否停用、阈值过宽或指标未接入。\n"
        "【五、数据说明】\n"
        "- 告警规则以当前启用配置为准，触发效果根据近7天学情和教情预警记录统计。"
    )
    return payload


def get_teacher_risk_profile_brief(tenant_id: str, *, synthesize: bool = True) -> dict[str, Any]:
    rows = _fetch_all(
        """
        SELECT
          c.teacher_names,
          COUNT(*) AS warning_count,
          COUNT(DISTINCT r.course_id) AS course_count,
          COUNT(DISTINCT r.indicator_name) AS indicator_type_count,
          MIN(r.warning_level) AS worst_warning_level,
          MAX(r.warning_time) AS latest_warning_time
        FROM (
          SELECT course_id, tenant_id, indicator_name, warning_level, warning_time
          FROM t_warning_study_record
          WHERE delete_flag = 0
            AND tenant_id = %(tenant_id)s
            AND warning_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
          UNION ALL
          SELECT course_id, tenant_id, indicator_name, warning_level, warning_time
          FROM t_warning_teaching_record
          WHERE delete_flag = 0
            AND tenant_id = %(tenant_id)s
            AND warning_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        ) r
        LEFT JOIN t_tias_course c
          ON c.course_id = r.course_id
         AND c.tenant_id = r.tenant_id
         AND c.delete_flag = 0
        GROUP BY c.teacher_names
        ORDER BY warning_count DESC
        LIMIT 5
        """,
        {"tenant_id": tenant_id},
    )
    type_rows = _fetch_all(
        """
        SELECT
          COALESCE(indicator_name, '未知类型') AS indicator_name,
          COUNT(*) AS warning_count,
          COUNT(DISTINCT teacher_names) AS teacher_count
        FROM (
          SELECT r.indicator_name, c.teacher_names
          FROM t_warning_study_record r
          LEFT JOIN t_tias_course c
            ON c.course_id = r.course_id
           AND c.tenant_id = r.tenant_id
           AND c.delete_flag = 0
          WHERE r.delete_flag = 0
            AND r.tenant_id = %(tenant_id)s
            AND r.warning_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
          UNION ALL
          SELECT r.indicator_name, c.teacher_names
          FROM t_warning_teaching_record r
          LEFT JOIN t_tias_course c
            ON c.course_id = r.course_id
           AND c.tenant_id = r.tenant_id
           AND c.delete_flag = 0
          WHERE r.delete_flag = 0
            AND r.tenant_id = %(tenant_id)s
            AND r.warning_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        ) w
        GROUP BY COALESCE(indicator_name, '未知类型')
        ORDER BY warning_count DESC
        LIMIT 5
        """,
        {"tenant_id": tenant_id},
    )
    top = [
        {
            "teacher_names": r.get("teacher_names") or "未知教师",
            "warning_count": _to_int(r.get("warning_count")),
            "course_count": _to_int(r.get("course_count")),
            "indicator_type_count": _to_int(r.get("indicator_type_count")),
            "worst_warning_level": _to_int(r.get("worst_warning_level")),
            "worst_warning_level_name": _warning_level_name(_to_int(r.get("worst_warning_level"))),
            "latest_warning_time": (
                r.get("latest_warning_time").isoformat(sep=" ", timespec="seconds")
                if r.get("latest_warning_time")
                else None
            ),
        }
        for r in rows
    ]
    type_top5 = [
        {
            "indicator_name": str(r.get("indicator_name") or "未知类型"),
            "warning_count": _to_int(r.get("warning_count")),
            "teacher_count": _to_int(r.get("teacher_count")),
        }
        for r in type_rows
    ]
    payload = {
        "teacher_risk_top5": top,
        "teacher_warning_type_top5": type_top5,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    teacher_text = (
        "\n".join(
            f"{idx}. {x['teacher_names']}：预警{x['warning_count']}条，涉及{x['course_count']}个节次、{x['indicator_type_count']}类指标，最严重{x['worst_warning_level_name']}"
            for idx, x in enumerate(top, start=1)
        )
        if top
        else "暂无"
    )
    type_text = (
        "\n".join(
            f"{idx}. {x['indicator_name']}：{x['warning_count']}条，涉及{x['teacher_count']}位教师"
            for idx, x in enumerate(type_top5, start=1)
        )
        if type_top5
        else "暂无"
    )
    payload["brief"] = (
        "【近7天教师风险画像】\n"
        f"【总体结论】近7天共识别{len(top)}位高频预警教师，"
        f"最高为{top[0]['teacher_names']}（{top[0]['warning_count']}条）。\n" if top else
        "【近7天教师风险画像】\n【总体结论】近7天暂无教师预警记录。\n"
    )
    if top:
        payload["brief"] += (
            "【一、教师风险Top5】\n"
            f"{teacher_text}\n"
            "【二、高频预警类型Top5】\n"
            f"{type_text}\n"
            "【三、建议动作】\n"
            "1. 优先对Top教师关联课程做课堂录像或督导记录复核。\n"
            "2. 对同一教师多指标触发的情况，建议按课程形成改进清单。\n"
            "【四、数据说明】\n"
            "- 统计范围为近7天学情和教情预警，并按课程对应关系归集到任课教师。"
        )
    return payload


def get_classroom_health_brief(tenant_id: str, *, synthesize: bool = True) -> dict[str, Any]:
    row = _fetch_one(
        """
        SELECT
          COUNT(*) AS classroom_count,
          SUM(CASE WHEN has_people = 1 THEN 1 ELSE 0 END) AS active_classroom_count,
          COALESCE(ROUND(AVG(COALESCE(tias_seat_percent, 0)), 2), 0) AS avg_seat_percent
        FROM t_patrol_classroom_status
        WHERE delete_flag = 0
          AND tenant_id = %(tenant_id)s
          AND tias_event_time >= DATE_SUB(NOW(), INTERVAL 2 HOUR)
        """,
        {"tenant_id": tenant_id},
    )
    payload = {
        "classroom_count": _to_int(row.get("classroom_count")),
        "active_classroom_count": _to_int(row.get("active_classroom_count")),
        "avg_seat_percent": _to_float(row.get("avg_seat_percent")),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    fallback = (
        f"近2小时教室状态共{payload['classroom_count']}间，"
        f"有人课堂{payload['active_classroom_count']}间，平均就座率{payload['avg_seat_percent']}%。"
    )
    payload["brief"] = (
        _summarize(
            "输出教室健康度与空闲异常简报。",
            payload,
            fallback,
            field_labels={
                "classroom_count": "近2小时教室状态记录数（间）",
                "active_classroom_count": "近2小时有人教室数（间）",
            },
        )
        if synthesize
        else fallback
    )
    return payload


def get_device_ops_brief(tenant_id: str, *, synthesize: bool = True) -> dict[str, Any]:
    row = _fetch_one(
        """
        SELECT
          COUNT(*) AS total_check,
          SUM(CASE WHEN result_status = 1 THEN 1 ELSE 0 END) AS ok_count,
          SUM(CASE WHEN result_status = 2 THEN 1 ELSE 0 END) AS abnormal_count
        FROM t_ops_check_device_result
        WHERE delete_flag = 0
          AND tenant_id = %(tenant_id)s
          AND execute_start_time >= DATE_SUB(NOW(), INTERVAL 3 DAY)
        """,
        {"tenant_id": tenant_id},
    )
    total = _to_int(row.get("total_check"))
    ok_count = _to_int(row.get("ok_count"))
    abnormal = _to_int(row.get("abnormal_count"))
    ok_ratio = round((ok_count / total * 100), 2) if total else 0.0
    payload = {
        "total_check_3d": total,
        "ok_count_3d": ok_count,
        "abnormal_count_3d": abnormal,
        "ok_ratio_3d": ok_ratio,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    fallback = f"近3天设备巡检{total}次，成功{ok_count}次，异常{abnormal}次，成功率{ok_ratio}%。"
    payload["brief"] = _summarize("输出设备运维质量简报。", payload, fallback) if synthesize else fallback
    return payload


def get_sensitive_word_brief(tenant_id: str, *, synthesize: bool = True) -> dict[str, Any]:
    dict_row = _fetch_one(
        """
        SELECT COUNT(*) AS sensitive_word_count
        FROM t_patrol_sensitive_words
        WHERE delete_flag = 0
          AND tenant_id = %(tenant_id)s
        """,
        {"tenant_id": tenant_id},
    )
    warn_row = _fetch_one(
        """
        SELECT COUNT(*) AS warning_count
        FROM t_warning_teaching_record
        WHERE delete_flag = 0
          AND tenant_id = %(tenant_id)s
          AND warning_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
          AND (
            indicator_name LIKE '%%敏感词%%'
            OR indicator_code LIKE '%%sensitive%%'
          )
        """,
        {"tenant_id": tenant_id},
    )
    type_rows = _fetch_all(
        """
        SELECT
          COALESCE(indicator_name, '敏感词相关预警') AS indicator_name,
          COUNT(*) AS warning_count,
          COUNT(DISTINCT course_id) AS course_count
        FROM t_warning_teaching_record
        WHERE delete_flag = 0
          AND tenant_id = %(tenant_id)s
          AND warning_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
          AND (
            indicator_name LIKE '%%敏感词%%'
            OR indicator_code LIKE '%%sensitive%%'
          )
        GROUP BY COALESCE(indicator_name, '敏感词相关预警')
        ORDER BY warning_count DESC
        LIMIT 5
        """,
        {"tenant_id": tenant_id},
    )
    course_rows = _fetch_all(
        """
        SELECT
          COALESCE(course_name, CONCAT('课程#', course_id)) AS course_name,
          COALESCE(org_name, '未知学院') AS org_name,
          COALESCE(clro_name, '未知教室') AS classroom_name,
          COUNT(*) AS warning_count,
          MAX(warning_time) AS latest_warning_time
        FROM t_warning_teaching_record
        WHERE delete_flag = 0
          AND tenant_id = %(tenant_id)s
          AND warning_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
          AND (
            indicator_name LIKE '%%敏感词%%'
            OR indicator_code LIKE '%%sensitive%%'
          )
        GROUP BY
          COALESCE(course_name, CONCAT('课程#', course_id)),
          COALESCE(org_name, '未知学院'),
          COALESCE(clro_name, '未知教室')
        ORDER BY warning_count DESC, latest_warning_time DESC
        LIMIT 5
        """,
        {"tenant_id": tenant_id},
    )
    latest_row = _fetch_one(
        """
        SELECT
          COALESCE(course_name, CONCAT('课程#', course_id)) AS course_name,
          COALESCE(org_name, '未知学院') AS org_name,
          COALESCE(clro_name, '未知教室') AS classroom_name,
          COALESCE(indicator_name, '敏感词相关预警') AS indicator_name,
          warning_level,
          warning_time
        FROM t_warning_teaching_record
        WHERE delete_flag = 0
          AND tenant_id = %(tenant_id)s
          AND warning_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
          AND (
            indicator_name LIKE '%%敏感词%%'
            OR indicator_code LIKE '%%sensitive%%'
          )
        ORDER BY warning_time DESC
        LIMIT 1
        """,
        {"tenant_id": tenant_id},
    )
    payload = {
        "sensitive_word_dict_count": _to_int(dict_row.get("sensitive_word_count")),
        "sensitive_warning_count_30d": _to_int(warn_row.get("warning_count")),
        "sensitive_type_top5": [
            {
                "indicator_name": str(r.get("indicator_name") or "敏感词相关预警"),
                "warning_count": _to_int(r.get("warning_count")),
                "course_count": _to_int(r.get("course_count")),
            }
            for r in type_rows
        ],
        "sensitive_course_top5": [
            {
                "course_name": str(r.get("course_name") or "未知课程"),
                "org_name": str(r.get("org_name") or "未知学院"),
                "classroom_name": str(r.get("classroom_name") or "未知教室"),
                "warning_count": _to_int(r.get("warning_count")),
                "latest_warning_time": (
                    r.get("latest_warning_time").isoformat(sep=" ", timespec="seconds")
                    if r.get("latest_warning_time")
                    else None
                ),
            }
            for r in course_rows
        ],
        "latest_sensitive_warning": {
            "course_name": latest_row.get("course_name"),
            "org_name": latest_row.get("org_name"),
            "classroom_name": latest_row.get("classroom_name"),
            "indicator_name": latest_row.get("indicator_name"),
            "warning_level": _to_int(latest_row.get("warning_level")),
            "warning_level_name": _warning_level_name(_to_int(latest_row.get("warning_level"))),
            "warning_time": (
                latest_row.get("warning_time").isoformat(sep=" ", timespec="seconds")
                if latest_row.get("warning_time")
                else None
            ),
        },
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    type_text = (
        "\n".join(
            f"{idx}. {x['indicator_name']}：{x['warning_count']}条，涉及{x['course_count']}个节次"
            for idx, x in enumerate(payload["sensitive_type_top5"], start=1)
        )
        if payload["sensitive_type_top5"]
        else "暂无"
    )
    course_text = (
        "\n".join(
            f"{idx}. {x['course_name']}（{x['org_name']}｜{x['classroom_name']}）：{x['warning_count']}条"
            for idx, x in enumerate(payload["sensitive_course_top5"], start=1)
        )
        if payload["sensitive_course_top5"]
        else "暂无"
    )
    latest = payload["latest_sensitive_warning"]
    latest_text = (
        f"{latest['warning_time']}，{latest['org_name']}《{latest['course_name']}》"
        f"（{latest['classroom_name']}）触发{latest['indicator_name']}，等级{latest['warning_level_name']}。"
        if latest.get("warning_time")
        else "暂无近30天敏感词相关最新预警。"
    )
    payload["brief"] = (
        "【敏感词预警专项】\n"
        f"【总体结论】当前敏感词词库{payload['sensitive_word_dict_count']}个词，近30天敏感词相关预警{payload['sensitive_warning_count_30d']}条。\n"
        "【一、预警类型Top5】\n"
        f"{type_text}\n"
        "【二、课程触发Top5】\n"
        f"{course_text}\n"
        "【三、最近一条记录】\n"
        f"{latest_text}\n"
        "【四、建议动作】\n"
        "1. 对Top课程核查课堂话术、讨论内容与预警上下文。\n"
        "2. 对误报词建议加入审核流程，避免影响正常教学表达。\n"
        "【五、数据说明】\n"
        "- 统计范围为近30天教情预警中被系统归类为敏感词相关的记录。"
    )
    return payload


def get_warning_video_trace_brief(tenant_id: str, *, synthesize: bool = True) -> dict[str, Any]:
    row = _fetch_one(
        """
        SELECT
          x.course_id,
          COALESCE(c.subject_name, c.teaching_class_name, x.course_name, CONCAT('课程#', x.course_id)) AS course_name,
          COALESCE(c.teacher_names, '未知教师') AS teacher_names,
          COALESCE(c.classroom_name, x.clro_name, '未知教室') AS classroom_name,
          COALESCE(c.leti_name, CONCAT('第', COALESCE(c.leti_number, 0), '节')) AS leti_name,
          COALESCE(c.leti_number, 0) AS leti_number,
          COALESCE(x.org_name, c.tecl_org_name, '未知学院') AS org_name,
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
        """,
        {"tenant_id": tenant_id},
    )
    warning_time = row.get("warning_time")
    if warning_time:
        video_row = _fetch_one(
            """
            SELECT record_id, vod_start_time, vod_end_time, file_url
            FROM t_media_video_record
            WHERE delete_flag = 0
              AND tenant_id = %(tenant_id)s
              AND vod_start_time <= %(warning_time)s
              AND vod_end_time >= %(warning_time)s
            ORDER BY vod_start_time DESC
            LIMIT 1
            """,
            {"tenant_id": tenant_id, "warning_time": warning_time},
        )
    else:
        video_row = {}
    duration_sec = 0
    if video_row.get("vod_start_time") and video_row.get("vod_end_time"):
        duration_sec = int((video_row.get("vod_end_time") - video_row.get("vod_start_time")).total_seconds())
    payload = {
        "latest_warning": {
            "course_id": row.get("course_id"),
            "course_name": row.get("course_name"),
            "teacher_names": row.get("teacher_names"),
            "classroom_name": row.get("classroom_name"),
            "leti_name": row.get("leti_name"),
            "leti_number": _to_int(row.get("leti_number")),
            "org_name": row.get("org_name"),
            "indicator_name": row.get("indicator_name"),
            "warning_level": _to_int(row.get("warning_level")),
            "warning_level_name": _warning_level_name(_to_int(row.get("warning_level"))),
        },
        "latest_warning_time": warning_time.isoformat(sep=" ", timespec="seconds") if warning_time else None,
        "record_id": video_row.get("record_id"),
        "vod_start_time": (
            video_row.get("vod_start_time").isoformat(sep=" ", timespec="seconds")
            if video_row.get("vod_start_time")
            else None
        ),
        "vod_end_time": (
            video_row.get("vod_end_time").isoformat(sep=" ", timespec="seconds")
            if video_row.get("vod_end_time")
            else None
        ),
        "file_url": video_row.get("file_url"),
        "video_duration_sec": duration_sec,
        "matched_video": bool(video_row.get("record_id")),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    warn = payload["latest_warning"]
    if not warning_time:
        payload["brief"] = (
            "【预警视频回看】\n"
            "当前未检索到可关联的预警记录。\n"
            "【建议】可先查询今日预警汇总，确认预警数据是否已入库。"
        )
        return payload
    if payload["matched_video"]:
        video_text = (
            f"已匹配录像片段：{payload['vod_start_time']} 至 {payload['vod_end_time']}，"
            f"时长{duration_sec}秒，录像编号为{payload['record_id']}。"
        )
    else:
        video_text = "未匹配到覆盖该预警时间点的录像片段。"
    payload["brief"] = (
        "【预警视频回看】\n"
        f"【总体结论】最近一条预警发生于{payload['latest_warning_time']}，"
        f"{'已定位对应录像片段' if payload['matched_video'] else '暂未定位到对应录像片段'}。\n"
        "【一、预警信息】\n"
        f"- 课程：{warn['course_name']}\n"
        f"- 教师：{warn['teacher_names']}\n"
        f"- 节次/教室：{warn['leti_name']}｜{warn['classroom_name']}\n"
        f"- 学院：{warn['org_name']}\n"
        f"- 预警类型：{warn['indicator_name']}（{warn['warning_level_name']}）\n"
        "【二、视频匹配】\n"
        f"{video_text}\n"
        "【三、建议动作】\n"
        "1. 若已匹配录像，建议从预警时间点前后各2分钟复核课堂现场。\n"
        "2. 若未匹配录像，建议检查视频入库延迟、录像时间范围和教室绑定关系。\n"
        "【四、数据说明】\n"
        "- 预警取学情和教情中的最新记录；录像按预警发生时间是否落在录像片段时间范围内匹配。"
    )
    return payload


def route_assistant_query(
    question: str,
    tenant_id: str,
    trace_id: str | None = None,
) -> dict[str, Any]:
    """轻量关键词分桶：五类AI巡课/预警/推送走库表简报；其余走大模型通用回答。"""
    text = (question or "").strip()
    if not text:
        trace_emit(trace_id, "branch_empty_question")
        return {
            "intent": "",
            "answer": (
                "请输入问题。示例：「当前节次实时AI巡课简报」「今日AI巡课汇总」「实时预警简报」"
                "「今日预警汇总」「预警推送阈值」；其它问题也会尽量简短回答。"
            ),
            "data": {},
            "source": "none",
        }
    local_answer = _lookup_local_assistant_answer(text)
    if local_answer:
        trace_emit(trace_id, "local_assistant_qa_hit")
        return {
            "intent": "local_assistant_qa",
            "answer": local_answer,
            "data": {"knowledge_base": "assistant_basic_qa"},
            "source": "local",
        }
    kb_answer = _lookup_metric_kb_answer(text)
    if kb_answer:
        trace_emit(trace_id, "metric_kb_hit")
        return {
            "intent": "metric_kb",
            "answer": kb_answer,
            "data": {"knowledge_base": "metric_definitions"},
            "source": "kb",
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
        "你是高校AI巡课与学情预警场景的 AI 助教。回答务必简短（尽量 120 字内）。"
        "打招呼、常识、与业务无关的问题用通用能力直接答，不编造数据库指标。"
        "若用户要实时到课率、预警占比等具体数，请提示可说「实时AI巡课简报」「今日预警汇总」等以便系统拉数。"
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


def _patrol_threshold_params() -> dict[str, float]:
    return {
        "focus_attendance_lt": float(settings.patrol_focus_attendance_lt),
        "focus_front_full_lt": float(settings.patrol_focus_front_full_lt),
        "focus_rise_lt": float(settings.patrol_focus_rise_lt),
        "vitality_attendance_gte": float(settings.patrol_vitality_attendance_gte),
        "vitality_front_full_gte": float(settings.patrol_vitality_front_full_gte),
        "vitality_rise_gte": float(settings.patrol_vitality_rise_gte),
    }


def _fmt_threshold(v: float) -> str:
    return f"{v:g}"


def _course_section_text(course_row: dict[str, Any]) -> str:
    raw = str(course_row.get("section_name") or course_row.get("leti_name") or "").strip()
    if raw and "不区分" not in raw:
        return raw
    leti_number = _to_int(course_row.get("leti_number"))
    if leti_number > 0:
        return f"第{leti_number}节"
    if raw:
        return raw
    return "未知节次"


def _course_teacher_text(course_row: dict[str, Any]) -> str:
    teacher = str(course_row.get("teacher_names") or course_row.get("teacher_name") or "").strip()
    return teacher or "未知教师"


def _course_classroom_text(course_row: dict[str, Any]) -> str:
    classroom = str(course_row.get("classroom_name") or course_row.get("clro_name") or "").strip()
    return classroom or "未知教室"


def _course_top_identity(course_row: dict[str, Any]) -> str:
    course_name = str(course_row.get("course_name") or "未知课程")
    teacher = _course_teacher_text(course_row)
    section = _course_section_text(course_row)
    classroom = _course_classroom_text(course_row)
    return f"{course_name}（{teacher}｜{section}｜{classroom}）"


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


def _is_read_only_sql(sql: str) -> bool:
    normalized = (sql or "").lstrip().lower()
    return normalized.startswith(("select", "show", "describe", "desc", "explain", "with"))


def _assert_read_only_sql(sql: str) -> None:
    if _is_read_only_sql(sql):
        return
    raise ValueError("schedule db only allows SELECT/SHOW/DESCRIBE/EXPLAIN/WITH queries")


def _fetch_schedule_one(sql: str, params: dict[str, Any]) -> dict[str, Any]:
    _assert_read_only_sql(sql)
    with get_schedule_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            result = cursor.fetchone() or {}
    return result


def _to_llm_named_data(value: Any, field_labels: dict[str, str] | None = None) -> Any:
    labels = field_labels or {}
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for raw_key, raw_value in value.items():
            key = str(raw_key)
            llm_key = labels.get(key) or LLM_FIELD_LABELS.get(key) or key
            if llm_key in result:
                llm_key = f"{llm_key}（{key}）"
            result[llm_key] = _to_llm_named_data(raw_value, labels)
        return result
    if isinstance(value, list):
        return [_to_llm_named_data(item, labels) for item in value]
    return value


def _summarize(
    task: str,
    data: dict[str, Any],
    fallback: str,
    *,
    field_labels: dict[str, str] | None = None,
) -> str:
    llm_data = _to_llm_named_data(data, field_labels)
    prompt = (
        "你是高校AI助教AI巡课助手，请基于给定结构化数据生成简洁专业的中文简报，不要编造不存在的数据。\n"
        "字段说明：数据字段已转换为业务字段名，请严格按字段名中的单位表述；"
        "除非字段明确写为“教室数（间）”，不要把课堂数或课程节次数写成“间教室”。\n"
        f"任务: {task}\n"
        f"数据: {json.dumps(llm_data, ensure_ascii=False, default=str)}\n"
        "输出要求：1-3句话。"
    )
    llm_url = f"{settings.llm_base_url.rstrip('/')}/chat/completions"
    payload: dict[str, object] = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": "你是高校AI巡课数据分析助手。"},
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
