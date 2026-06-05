from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterator
from copy import deepcopy
from datetime import datetime
from threading import Lock
from time import monotonic
from typing import Any
from urllib import error, request

from app.assistant_trace import trace_emit, redact_sensitive_text
from app.config import merge_llm_chat_template_kwargs, settings
from app.db import get_connection, get_schedule_connection
from app.semantic_executor import execute_semantic_plan
from app.semantic_planner import plan_auto_query
from app.semantic_report import _build_report_context, _fallback_report, _json_default, compose_semantic_report

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

ASSISTANT_ROUTE_INTENTS = (
    "realtime_patrol",
    "daily_patrol",
    "realtime_warning",
    "daily_warning",
    "push_preview",
    "warning_handle",
    "warning_trend",
    "strategy_effect",
    "teacher_risk",
    "classroom_health",
    "device_ops",
    "sensitive_word",
    "warning_video_trace",
    "general",
)
ASSISTANT_ROUTE_INTENT_SET = set(ASSISTANT_ROUTE_INTENTS)
StreamCallback = Callable[[str], None]
ASSISTANT_ROUTE_INTENT_ALIAS_MAP = {
    "realtimepatrol": "realtime_patrol",
    "realtime_patrol": "realtime_patrol",
    "实时巡课": "realtime_patrol",
    "实时ai巡课": "realtime_patrol",
    "实时ai巡查": "realtime_patrol",
    "dailypatrol": "daily_patrol",
    "daily_patrol": "daily_patrol",
    "今日巡课": "daily_patrol",
    "今日ai巡课": "daily_patrol",
    "realtimewarning": "realtime_warning",
    "realtime_warning": "realtime_warning",
    "实时预警": "realtime_warning",
    "dailywarning": "daily_warning",
    "daily_warning": "daily_warning",
    "今日预警": "daily_warning",
    "pushpreview": "push_preview",
    "push_preview": "push_preview",
    "预警推送": "push_preview",
    "warninghandle": "warning_handle",
    "warning_handle": "warning_handle",
    "处置闭环": "warning_handle",
    "warningtrend": "warning_trend",
    "warning_trend": "warning_trend",
    "预警趋势": "warning_trend",
    "strategyeffect": "strategy_effect",
    "strategy_effect": "strategy_effect",
    "阈值效果": "strategy_effect",
    "teacherrisk": "teacher_risk",
    "teacher_risk": "teacher_risk",
    "教师风险画像": "teacher_risk",
    "classroomhealth": "classroom_health",
    "classroom_health": "classroom_health",
    "教室健康度": "classroom_health",
    "deviceops": "device_ops",
    "device_ops": "device_ops",
    "设备运维": "device_ops",
    "sensitiveword": "sensitive_word",
    "sensitive_word": "sensitive_word",
    "敏感词": "sensitive_word",
    "warningvideotrace": "warning_video_trace",
    "warning_video_trace": "warning_video_trace",
    "预警回看": "warning_video_trace",
    "general": "general",
    "通用": "general",
    "闲聊": "general",
}
ASSISTANT_DEFAULT_TOP_N = max(1, int(getattr(settings, "assistant_default_top_n", 5) or 5))
ASSISTANT_MAX_TOP_N = max(
    ASSISTANT_DEFAULT_TOP_N,
    int(getattr(settings, "assistant_max_top_n", 20) or 20),
)
_CN_SMALL_NUMBER_MAP = {
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}
_ASSISTANT_CONTEXT_LOCK = Lock()
_ASSISTANT_CONTEXT_STORE: dict[str, dict[str, Any]] = {}
_ASSISTANT_RESULT_CACHE_LOCK = Lock()
_ASSISTANT_RESULT_CACHE: dict[str, dict[str, Any]] = {}
_ASSISTANT_CONTEXT_FOLLOWUP_MARKERS = (
    "改成",
    "改为",
    "换成",
    "换为",
    "只看",
    "仅看",
    "只统计",
    "仅统计",
    "只保留",
    "再看",
    "继续",
    "同样口径",
    "同口径",
    "按刚才",
    "上一条",
    "上一个",
    "这个口径",
    "重置",
    "清空",
    "取消筛选",
    "恢复默认",
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
        "AI巡查覆盖率=已完成AI巡查课堂数/今日排课课堂数×100%，用于观察今日排课中已有AI巡查结果的比例。",
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


def _iter_text_chunks(text: str, chunk_size: int = 8) -> Iterator[str]:
    buf = ""
    for ch in text or "":
        buf += ch
        if len(buf) >= chunk_size or ch in "\n。！？!?；;":
            yield buf
            buf = ""
    if buf:
        yield buf


def _stream_fixed_answer(stream_callback: StreamCallback | None, answer: str, *, chunk_size: int = 8) -> None:
    if not stream_callback:
        return
    for chunk in _iter_text_chunks(answer or "", chunk_size=chunk_size):
        if chunk:
            stream_callback(chunk)


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
            "你好，我是舟小智AI小助手。你可以问我实时AI巡课、今日AI巡课汇总、"
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
            "我是舟小智AI小助手，主要帮助教务、督导和学院管理人员查看AI巡课简报、"
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


def _normalize_top_n(value: Any, default: int = ASSISTANT_DEFAULT_TOP_N) -> int:
    n = _to_int(value)
    if n <= 0:
        n = default
    return max(1, min(ASSISTANT_MAX_TOP_N, n))


def _extract_top_n(question: str) -> tuple[int, bool]:
    q = (question or "").strip()
    if not q:
        return ASSISTANT_DEFAULT_TOP_N, False
    m = re.search(r"(?i)top\s*([0-9]{1,2}|[一二三四五六七八九十两])", q)
    if m:
        token = m.group(1)
        if token.isdigit():
            return _normalize_top_n(token), True
        return _normalize_top_n(_CN_SMALL_NUMBER_MAP.get(token, ASSISTANT_DEFAULT_TOP_N)), True
    m = re.search(r"前\s*([0-9]{1,2})\s*(?:名|个|条|项|位|节|课堂)?", q)
    if m:
        return _normalize_top_n(m.group(1)), True
    m = re.search(r"前\s*([一二三四五六七八九十两])\s*(?:名|个|条|项|位|节|课堂)?", q)
    if m:
        cn = m.group(1)
        return _normalize_top_n(_CN_SMALL_NUMBER_MAP.get(cn, ASSISTANT_DEFAULT_TOP_N)), True
    return ASSISTANT_DEFAULT_TOP_N, False


def _extract_org_keyword(question: str) -> str | None:
    q = (question or "").strip()
    if not q:
        return None
    matches = re.findall(r"([A-Za-z0-9\u4e00-\u9fa5]{2,24}(?:学院|学部|系|中心|部))", q)
    if not matches:
        return None
    cleaned: list[str] = []
    blocked_tokens = ("哪个", "哪些", "哪所", "哪类", "哪几个", "各个", "各学院", "所有", "全部")
    for raw in matches:
        x = re.sub(r"^(今天|今日|当前|请|帮我|给我|只看|看看|查询|统计|按|把)+", "", raw)
        if x and not any(token in x for token in blocked_tokens):
            cleaned.append(x)
    if not cleaned:
        return None
    best = max(cleaned, key=len)
    if best in {"学院", "学部", "系", "中心", "部"}:
        return None
    return best


def _extract_section_range(question: str) -> tuple[int | None, int | None]:
    q = (question or "").strip()
    if not q:
        return None, None
    m = re.search(r"第?\s*([0-9]{1,2})\s*[-~到至]\s*([0-9]{1,2})\s*节?", q)
    if m:
        a = _to_int(m.group(1))
        b = _to_int(m.group(2))
        lo = min(a, b)
        hi = max(a, b)
        if lo > 0 and hi > 0:
            return lo, hi
    singles = [int(x) for x in re.findall(r"第\s*([0-9]{1,2})\s*节", q)]
    if singles:
        lo = min(singles)
        hi = max(singles)
        return lo, hi
    return None, None


def _extract_subject_source(question: str) -> int | None:
    q = (question or "").strip()
    if not q:
        return None
    has_undergrad = "本科" in q
    has_graduate = "研究生" in q
    if has_undergrad and not has_graduate:
        return 1
    if has_graduate and not has_undergrad:
        return 2
    return None


def _extract_teacher_keyword(question: str) -> str | None:
    q = (question or "").strip()
    if not q:
        return None
    m = re.search(r"(?:^|[\s，。；、:：])([A-Za-z\u4e00-\u9fa5·]{2,12})老师", q)
    if not m:
        m = re.search(
            r"(?:老师|教师|任课教师)(?:姓名)?(?:[:：=是为]|查|看)?\s*([A-Za-z\u4e00-\u9fa5·]{2,12}?)(?=(?:近|最|本|一周|过去|风险|预警|的|，|。|；|、|$))",
            q,
        )
        if m:
            teacher = m.group(1).strip()
        else:
            return None
    else:
        teacher = m.group(1).strip()
    blocked = {
        "今天", "今日", "当前", "实时", "重点", "全部", "所有", "课程", "不限", "不看", "不按", "取消",
        "风险", "预警", "画像", "排行", "异常", "类型", "最多", "最高", "最低",
    }
    if teacher in blocked or any(x in teacher for x in ("不限", "不看", "不按", "取消")):
        return None
    return teacher


def _extract_course_keyword(question: str) -> str | None:
    q = (question or "").strip()
    if not q:
        return None
    m = re.search(r"《([^》]{2,40})》", q)
    if m:
        return m.group(1).strip()
    m = re.search(r"([A-Za-z0-9\u4e00-\u9fa5]{2,30})(?:这门课|这门课程)", q)
    if m:
        keyword = m.group(1).strip()
        keyword = re.sub(r"^(请|帮我|麻烦|查看|看一下|看下|看看|统计|分析|查一下|查下)+", "", keyword)
        if keyword:
            return keyword
    m = re.search(r"(?:课程|课名|科目)[:：是为叫]?\s*([A-Za-z0-9\u4e00-\u9fa5]{2,30})", q)
    if not m:
        return None
    keyword = m.group(1).strip()
    blocked = {"实时", "今日", "汇总", "简报", "预警", "巡课", "巡查", "全部", "所有", "不限", "不看", "不按", "取消"}
    if keyword in blocked or any(x in keyword for x in ("不限", "不看", "不按", "取消")):
        return None
    return keyword


def _extract_classroom_keyword(question: str) -> str | None:
    q = (question or "").strip()
    if not q:
        return None
    m = re.search(r"([A-Za-z0-9\u4e00-\u9fa5\-]{2,20})教室", q)
    if not m:
        m = re.search(r"教室[:：]?\s*([A-Za-z0-9\u4e00-\u9fa5\-]{2,20})", q)
    if not m:
        return None
    room = m.group(1).strip()
    blocked = {"实时", "今日", "全部", "所有", "当前", "课堂", "不限", "不看", "不按", "取消"}
    if room in blocked or any(x in room for x in ("不限", "不看", "不按", "取消")):
        return None
    return room


def _extract_clear_flags(question: str) -> dict[str, bool]:
    q = (question or "").strip()
    compact = "".join(q.split())
    if not compact:
        return {
            "reset_all": False,
            "clear_org_keyword": False,
            "clear_leti": False,
            "clear_subject_source": False,
            "clear_teacher_keyword": False,
            "clear_course_keyword": False,
            "clear_classroom_keyword": False,
        }

    reset_all = any(x in compact for x in ("重置", "清空条件", "清空筛选", "恢复默认", "取消所有筛选", "全部取消筛选"))
    clear_org = any(x in compact for x in ("不限学院", "学院不限", "取消学院筛选", "不看学院", "不按学院"))
    clear_leti = any(x in compact for x in ("不限节次", "节次不限", "取消节次筛选", "不看节次", "不按节次"))
    clear_subject = any(
        x in compact
        for x in ("不限学段", "学段不限", "取消学段筛选", "不区分本科研究生", "不限本科研究生", "不分本科研究生")
    )
    clear_teacher = any(x in compact for x in ("不限老师", "老师不限", "取消老师筛选", "不看老师", "不按老师"))
    clear_course = any(x in compact for x in ("不限课程", "课程不限", "取消课程筛选", "不看课程", "不按课程"))
    clear_classroom = any(x in compact for x in ("不限教室", "教室不限", "取消教室筛选", "不看教室", "不按教室"))
    return {
        "reset_all": reset_all,
        "clear_org_keyword": clear_org,
        "clear_leti": clear_leti,
        "clear_subject_source": clear_subject,
        "clear_teacher_keyword": clear_teacher,
        "clear_course_keyword": clear_course,
        "clear_classroom_keyword": clear_classroom,
    }


def _extract_query_options(question: str) -> dict[str, Any]:
    org_keyword = _extract_org_keyword(question)
    leti_min, leti_max = _extract_section_range(question)
    subject_source = _extract_subject_source(question)
    teacher_keyword = _extract_teacher_keyword(question)
    course_keyword = _extract_course_keyword(question)
    classroom_keyword = _extract_classroom_keyword(question)
    clear_flags = _extract_clear_flags(question)
    top_n, top_n_explicit = _extract_top_n(question)
    return {
        "top_n": top_n,
        "top_n_explicit": top_n_explicit,
        "org_keyword": org_keyword,
        "leti_min": leti_min,
        "leti_max": leti_max,
        "subject_source": subject_source,
        "teacher_keyword": teacher_keyword,
        "course_keyword": course_keyword,
        "classroom_keyword": classroom_keyword,
        **clear_flags,
    }


def _normalized_query_options(options: dict[str, Any]) -> dict[str, Any]:
    org_keyword = str(options.get("org_keyword") or "").strip()
    teacher_keyword = str(options.get("teacher_keyword") or "").strip()
    course_keyword = str(options.get("course_keyword") or "").strip()
    classroom_keyword = str(options.get("classroom_keyword") or "").strip()
    leti_min = _to_int(options.get("leti_min")) if options.get("leti_min") is not None else 0
    leti_max = _to_int(options.get("leti_max")) if options.get("leti_max") is not None else 0
    subject_source = _to_int(options.get("subject_source")) if options.get("subject_source") is not None else 0
    if subject_source not in (1, 2):
        subject_source = 0
    reset_all = bool(options.get("reset_all"))
    normalized = {
        "top_n": _normalize_top_n(options.get("top_n")),
        "top_n_explicit": bool(options.get("top_n_explicit")),
        "org_keyword": org_keyword or None,
        "teacher_keyword": teacher_keyword or None,
        "course_keyword": course_keyword or None,
        "classroom_keyword": classroom_keyword or None,
        "leti_min": leti_min if leti_min > 0 else None,
        "leti_max": leti_max if leti_max > 0 else None,
        "subject_source": subject_source if subject_source in (1, 2) else None,
        "reset_all": reset_all,
        "clear_org_keyword": bool(options.get("clear_org_keyword")),
        "clear_leti": bool(options.get("clear_leti")),
        "clear_subject_source": bool(options.get("clear_subject_source")),
        "clear_teacher_keyword": bool(options.get("clear_teacher_keyword")),
        "clear_course_keyword": bool(options.get("clear_course_keyword")),
        "clear_classroom_keyword": bool(options.get("clear_classroom_keyword")),
    }
    if reset_all:
        normalized["top_n"] = _normalize_top_n(ASSISTANT_DEFAULT_TOP_N)
        normalized["top_n_explicit"] = False
        normalized["org_keyword"] = None
        normalized["teacher_keyword"] = None
        normalized["course_keyword"] = None
        normalized["classroom_keyword"] = None
        normalized["leti_min"] = None
        normalized["leti_max"] = None
        normalized["subject_source"] = None
    if normalized["leti_min"] and normalized["leti_max"] and normalized["leti_min"] > normalized["leti_max"]:
        normalized["leti_min"], normalized["leti_max"] = normalized["leti_max"], normalized["leti_min"]
    return normalized


def _has_option_cue(options: dict[str, Any]) -> bool:
    return bool(
        options.get("top_n_explicit")
        or options.get("org_keyword")
        or options.get("teacher_keyword")
        or options.get("course_keyword")
        or options.get("classroom_keyword")
        or options.get("leti_min") is not None
        or options.get("leti_max") is not None
        or options.get("subject_source") is not None
        or options.get("reset_all")
        or options.get("clear_org_keyword")
        or options.get("clear_leti")
        or options.get("clear_subject_source")
        or options.get("clear_teacher_keyword")
        or options.get("clear_course_keyword")
        or options.get("clear_classroom_keyword")
    )


def _is_followup_refine_question(question: str, options: dict[str, Any]) -> bool:
    compact = "".join((question or "").strip().split())
    if not compact:
        return False
    if any(marker in compact for marker in _ASSISTANT_CONTEXT_FOLLOWUP_MARKERS):
        return True
    if _has_option_cue(options):
        return True
    if len(compact) <= 12 and any(token in compact for token in ("呢", "吗", "么", "继续")):
        return True
    return False


def _assistant_context_key(tenant_id: str, session_id: str) -> str:
    return f"{tenant_id}::{session_id}"


def _assistant_context_prune_locked(now_mono: float) -> None:
    ttl_sec = max(60, _to_int(settings.assistant_context_ttl_sec))
    max_entries = max(50, _to_int(settings.assistant_context_max_entries))
    expired: list[str] = []
    for key, value in _ASSISTANT_CONTEXT_STORE.items():
        updated_mono = _safe_float(value.get("updated_mono"), 0.0)
        if updated_mono <= 0.0 or (now_mono - updated_mono) > ttl_sec:
            expired.append(key)
    for key in expired:
        _ASSISTANT_CONTEXT_STORE.pop(key, None)
    overflow = len(_ASSISTANT_CONTEXT_STORE) - max_entries
    if overflow > 0:
        sorted_items = sorted(
            _ASSISTANT_CONTEXT_STORE.items(),
            key=lambda kv: _safe_float(kv[1].get("updated_mono"), 0.0),
        )
        for key, _ in sorted_items[:overflow]:
            _ASSISTANT_CONTEXT_STORE.pop(key, None)


def _assistant_context_get(
    tenant_id: str,
    session_id: str,
    *,
    trace_id: str | None = None,
) -> dict[str, Any] | None:
    if not settings.assistant_context_enabled or not session_id:
        return None
    now_mono = monotonic()
    key = _assistant_context_key(tenant_id, session_id)
    with _ASSISTANT_CONTEXT_LOCK:
        _assistant_context_prune_locked(now_mono)
        value = _ASSISTANT_CONTEXT_STORE.get(key)
        if not value:
            return None
        value["updated_mono"] = now_mono
        snapshot = dict(value)
    trace_emit(
        trace_id,
        "context_hit",
        context_bucket=snapshot.get("bucket"),
        context_session=session_id[:48],
    )
    return snapshot


def _assistant_context_set(
    tenant_id: str,
    session_id: str,
    *,
    bucket: str,
    query_options: dict[str, Any],
    trace_id: str | None = None,
) -> None:
    if not settings.assistant_context_enabled or not session_id or bucket == "general":
        return
    now_mono = monotonic()
    key = _assistant_context_key(tenant_id, session_id)
    options = _normalized_query_options(query_options)
    for transient_key in (
        "top_n_explicit",
        "reset_all",
        "clear_org_keyword",
        "clear_leti",
        "clear_subject_source",
        "clear_teacher_keyword",
        "clear_course_keyword",
        "clear_classroom_keyword",
    ):
        options.pop(transient_key, None)
    payload = {
        "bucket": bucket,
        "query_options": options,
        "updated_mono": now_mono,
    }
    with _ASSISTANT_CONTEXT_LOCK:
        _ASSISTANT_CONTEXT_STORE[key] = payload
        _assistant_context_prune_locked(now_mono)
    trace_emit(
        trace_id,
        "context_saved",
        context_bucket=bucket,
        context_session=session_id[:48],
        context_filters=_summarize_query_options(options, top_n=_normalize_top_n(options.get("top_n"))),
    )


def _assistant_result_cache_prune_locked(now_mono: float) -> None:
    ttl_sec = max(5, int(getattr(settings, "assistant_result_cache_ttl_sec", 20) or 20))
    max_entries = max(100, int(getattr(settings, "assistant_result_cache_max_entries", 1000) or 1000))
    expired: list[str] = []
    for key, value in _ASSISTANT_RESULT_CACHE.items():
        expire_at = _safe_float(value.get("expire_at"), 0.0)
        if expire_at <= 0.0 or expire_at <= now_mono:
            expired.append(key)
    for key in expired:
        _ASSISTANT_RESULT_CACHE.pop(key, None)
    overflow = len(_ASSISTANT_RESULT_CACHE) - max_entries
    if overflow > 0:
        sorted_items = sorted(
            _ASSISTANT_RESULT_CACHE.items(),
            key=lambda kv: _safe_float(kv[1].get("updated_mono"), 0.0),
        )
        for key, _ in sorted_items[:overflow]:
            _ASSISTANT_RESULT_CACHE.pop(key, None)


def _assistant_result_cache_key(tenant_id: str, bucket: str, query_options: dict[str, Any]) -> str:
    options = _normalized_query_options(query_options)
    for transient_key in (
        "top_n_explicit",
        "reset_all",
        "clear_org_keyword",
        "clear_leti",
        "clear_subject_source",
        "clear_teacher_keyword",
        "clear_course_keyword",
        "clear_classroom_keyword",
    ):
        options.pop(transient_key, None)
    raw = json.dumps(options, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"{tenant_id}|{bucket}|{raw}"


def _assistant_result_cache_get(cache_key: str) -> dict[str, Any] | None:
    if not settings.assistant_result_cache_enabled:
        return None
    now_mono = monotonic()
    with _ASSISTANT_RESULT_CACHE_LOCK:
        _assistant_result_cache_prune_locked(now_mono)
        value = _ASSISTANT_RESULT_CACHE.get(cache_key)
        if not value:
            return None
        if _safe_float(value.get("expire_at"), 0.0) <= now_mono:
            _ASSISTANT_RESULT_CACHE.pop(cache_key, None)
            return None
        value["updated_mono"] = now_mono
        result = value.get("result")
    if not isinstance(result, dict):
        return None
    return deepcopy(result)


def _assistant_result_cache_set(cache_key: str, result: dict[str, Any]) -> None:
    if not settings.assistant_result_cache_enabled:
        return
    ttl_sec = max(5, int(getattr(settings, "assistant_result_cache_ttl_sec", 20) or 20))
    now_mono = monotonic()
    with _ASSISTANT_RESULT_CACHE_LOCK:
        _ASSISTANT_RESULT_CACHE[cache_key] = {
            "result": deepcopy(result),
            "updated_mono": now_mono,
            "expire_at": now_mono + ttl_sec,
        }
        _assistant_result_cache_prune_locked(now_mono)


def _should_inherit_context(
    *,
    followup_refine: bool,
    resolved_bucket: str,
    context_bucket: str,
) -> bool:
    if not followup_refine or not context_bucket:
        return False
    if resolved_bucket == "general":
        return True
    return resolved_bucket == context_bucket


def _merge_query_options(
    current_options: dict[str, Any],
    previous_options: dict[str, Any] | None,
    *,
    inherit_context: bool,
) -> dict[str, Any]:
    current = _normalized_query_options(current_options)
    if current.get("reset_all"):
        return current
    if not inherit_context or not previous_options:
        if current.get("clear_org_keyword"):
            current["org_keyword"] = None
        if current.get("clear_leti"):
            current["leti_min"] = None
            current["leti_max"] = None
        if current.get("clear_subject_source"):
            current["subject_source"] = None
        if current.get("clear_teacher_keyword"):
            current["teacher_keyword"] = None
        if current.get("clear_course_keyword"):
            current["course_keyword"] = None
        if current.get("clear_classroom_keyword"):
            current["classroom_keyword"] = None
        return current
    previous = _normalized_query_options(previous_options)
    merged = dict(current)
    if not merged.get("top_n_explicit"):
        merged["top_n"] = _normalize_top_n(previous.get("top_n"))
    if not merged.get("org_keyword") and previous.get("org_keyword"):
        merged["org_keyword"] = previous.get("org_keyword")
    if merged.get("leti_min") is None and previous.get("leti_min") is not None:
        merged["leti_min"] = previous.get("leti_min")
    if merged.get("leti_max") is None and previous.get("leti_max") is not None:
        merged["leti_max"] = previous.get("leti_max")
    if merged.get("subject_source") is None and previous.get("subject_source") is not None:
        merged["subject_source"] = previous.get("subject_source")
    if not merged.get("teacher_keyword") and previous.get("teacher_keyword"):
        merged["teacher_keyword"] = previous.get("teacher_keyword")
    if not merged.get("course_keyword") and previous.get("course_keyword"):
        merged["course_keyword"] = previous.get("course_keyword")
    if not merged.get("classroom_keyword") and previous.get("classroom_keyword"):
        merged["classroom_keyword"] = previous.get("classroom_keyword")
    if merged.get("clear_org_keyword"):
        merged["org_keyword"] = None
    if merged.get("clear_leti"):
        merged["leti_min"] = None
        merged["leti_max"] = None
    if merged.get("clear_subject_source"):
        merged["subject_source"] = None
    if merged.get("clear_teacher_keyword"):
        merged["teacher_keyword"] = None
    if merged.get("clear_course_keyword"):
        merged["course_keyword"] = None
    if merged.get("clear_classroom_keyword"):
        merged["classroom_keyword"] = None
    if merged["leti_min"] and merged["leti_max"] and merged["leti_min"] > merged["leti_max"]:
        merged["leti_min"], merged["leti_max"] = merged["leti_max"], merged["leti_min"]
    return merged


def _summarize_query_options(options: dict[str, Any], *, top_n: int) -> str:
    parts: list[str] = [f"Top{top_n}"]
    org_keyword = str(options.get("org_keyword") or "").strip()
    if org_keyword:
        parts.append(f"学院={org_keyword}")
    teacher_keyword = str(options.get("teacher_keyword") or "").strip()
    if teacher_keyword:
        parts.append(f"教师={teacher_keyword}")
    course_keyword = str(options.get("course_keyword") or "").strip()
    if course_keyword:
        parts.append(f"课程={course_keyword}")
    classroom_keyword = str(options.get("classroom_keyword") or "").strip()
    if classroom_keyword:
        parts.append(f"教室={classroom_keyword}")
    leti_min = _to_int(options.get("leti_min")) if options.get("leti_min") is not None else 0
    leti_max = _to_int(options.get("leti_max")) if options.get("leti_max") is not None else 0
    if leti_min > 0 and leti_max > 0:
        if leti_min == leti_max:
            parts.append(f"节次=第{leti_min}节")
        else:
            parts.append(f"节次=第{leti_min}-{leti_max}节")
    subject_source = _to_int(options.get("subject_source")) if options.get("subject_source") is not None else 0
    if subject_source == 1:
        parts.append("学段=本科")
    elif subject_source == 2:
        parts.append("学段=研究生")
    return "；".join(parts)


def _build_course_scope_filter_sql(alias: str, options: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    alias_prefix = f"{alias}." if alias else ""
    clauses: list[str] = []
    params: dict[str, Any] = {}

    org_keyword = str(options.get("org_keyword") or "").strip()
    if org_keyword:
        params["scope_org_like"] = f"%{org_keyword}%"
        clauses.append(f"COALESCE({alias_prefix}tecl_org_name, '') LIKE %(scope_org_like)s")
    teacher_keyword = str(options.get("teacher_keyword") or "").strip()
    if teacher_keyword:
        params["scope_teacher_like"] = f"%{teacher_keyword}%"
        clauses.append(f"COALESCE({alias_prefix}teacher_names, '') LIKE %(scope_teacher_like)s")
    course_keyword = str(options.get("course_keyword") or "").strip()
    if course_keyword:
        params["scope_course_like"] = f"%{course_keyword}%"
        clauses.append(
            "CONCAT("
            f"COALESCE({alias_prefix}subject_name, ''),"
            f"COALESCE({alias_prefix}teaching_class_name, ''),"
            f"COALESCE({alias_prefix}course_name, '')"
            ") LIKE %(scope_course_like)s"
        )
    classroom_keyword = str(options.get("classroom_keyword") or "").strip()
    if classroom_keyword:
        params["scope_classroom_like"] = f"%{classroom_keyword}%"
        clauses.append(
            "CONCAT("
            f"COALESCE({alias_prefix}classroom_name, ''),"
            f"COALESCE({alias_prefix}clro_name, '')"
            ") LIKE %(scope_classroom_like)s"
        )

    leti_min = _to_int(options.get("leti_min")) if options.get("leti_min") is not None else 0
    leti_max = _to_int(options.get("leti_max")) if options.get("leti_max") is not None else 0
    if leti_min > 0:
        params["scope_leti_min"] = leti_min
        clauses.append(f"COALESCE({alias_prefix}leti_number, 0) >= %(scope_leti_min)s")
    if leti_max > 0:
        params["scope_leti_max"] = leti_max
        clauses.append(f"COALESCE({alias_prefix}leti_number, 0) <= %(scope_leti_max)s")

    subject_source = _to_int(options.get("subject_source")) if options.get("subject_source") is not None else 0
    if subject_source in (1, 2):
        params["scope_subject_source"] = subject_source
        clauses.append(f"COALESCE({alias_prefix}subject_source, 0) = %(scope_subject_source)s")

    if not clauses:
        return "", {}
    return "\n            AND " + "\n            AND ".join(clauses), params


def _normalize_intent_token(value: str) -> str:
    return (
        (value or "")
        .strip()
        .lower()
        .replace(" ", "")
        .replace("-", "")
        .replace("_", "")
    )


def _normalize_route_intent(intent: str) -> str:
    token = _normalize_intent_token(intent)
    return ASSISTANT_ROUTE_INTENT_ALIAS_MAP.get(token, token if token in ASSISTANT_ROUTE_INTENT_SET else "general")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_first_json_object(text: str) -> dict[str, Any] | None:
    raw = (text or "").strip()
    if not raw:
        return None

    candidates = [raw]
    if "```" in raw:
        for seg in raw.split("```"):
            piece = seg.strip()
            if not piece:
                continue
            if piece.lower().startswith("json"):
                piece = piece[4:].strip()
            candidates.append(piece)

    decoder = json.JSONDecoder()
    for candidate in candidates:
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict):
                return obj
        except (json.JSONDecodeError, TypeError):
            pass
        for idx, ch in enumerate(candidate):
            if ch != "{":
                continue
            try:
                obj, _ = decoder.raw_decode(candidate[idx:])
            except ValueError:
                continue
            if isinstance(obj, dict):
                return obj
    return None


def _intent_route_llm_messages(question: str) -> list[dict[str, str]]:
    intents_text = "、".join(ASSISTANT_ROUTE_INTENTS)
    system = (
        "你是高校课堂数据助手的意图路由器。你只做分类，不回答业务内容。"
        f"可选 intent 仅限：{intents_text}。"
        "必须仅输出一个 JSON 对象，不要 markdown。"
        "JSON 字段：intent(string)、confidence(number,0~1)、reason(string)、"
        "time_scope(string)、metrics(array)、dimensions(array)。"
        "如果无法判断，intent=general 且 confidence<=0.5。"
        "问候、寒暄、纯解释类问题统一归为 general。"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": question},
    ]


def _classify_bucket_with_llm(question: str, trace_id: str | None = None) -> dict[str, Any] | None:
    if not settings.assistant_intent_llm_enabled:
        trace_emit(trace_id, "llm_intent_disabled")
        return None
    llm_url = f"{settings.llm_base_url.rstrip('/')}/chat/completions"
    payload: dict[str, object] = {
        "model": settings.llm_model,
        "messages": _intent_route_llm_messages(question),
        "temperature": 0.0,
        "max_tokens": 260,
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
        trace_emit(trace_id, "llm_intent_urlopen_begin", timeout_sec=settings.llm_timeout_sec)
        with request.urlopen(req, timeout=settings.llm_timeout_sec) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        trace_emit(trace_id, "llm_intent_urlopen_done", http_status=getattr(resp, "status", None))
    except (error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as ex:
        trace_emit(
            trace_id,
            "llm_intent_urlopen_failed",
            error_type=type(ex).__name__,
            error=redact_sensitive_text(str(ex), max_len=240),
        )
        return None

    try:
        content = str(body["choices"][0]["message"]["content"] or "").strip()
    except (KeyError, IndexError, TypeError) as ex:
        trace_emit(
            trace_id,
            "llm_intent_parse_failed",
            error_type=type(ex).__name__,
            error=redact_sensitive_text(str(ex), max_len=200),
        )
        return None
    if not content:
        trace_emit(trace_id, "llm_intent_empty_content")
        return None

    parsed = _parse_first_json_object(content)
    if not parsed:
        trace_emit(trace_id, "llm_intent_json_not_found", preview=redact_sensitive_text(content, max_len=180))
        return None
    raw_intent = str(parsed.get("intent") or "").strip()
    bucket = _normalize_route_intent(raw_intent)
    confidence = _safe_float(parsed.get("confidence"), 0.0)
    confidence = max(0.0, min(1.0, confidence))
    result = {
        "bucket": bucket,
        "raw_intent": raw_intent,
        "confidence": confidence,
        "reason": str(parsed.get("reason") or "")[:180],
        "time_scope": str(parsed.get("time_scope") or "")[:80],
        "metrics": parsed.get("metrics") if isinstance(parsed.get("metrics"), list) else [],
        "dimensions": parsed.get("dimensions") if isinstance(parsed.get("dimensions"), list) else [],
    }
    trace_emit(
        trace_id,
        "llm_intent_candidate",
        bucket=bucket,
        raw_intent=raw_intent,
        confidence=confidence,
    )
    return result


def _clarification_llm_messages(
    *,
    question: str,
    bucket: str,
    query_options: dict[str, Any],
) -> list[dict[str, str]]:
    system = (
        "你是高校课堂数据助手的澄清判断器。你只判断用户问题是否信息不足，不回答业务数据。"
        "可查询的业务域只有：AI巡课、课堂AI预警、预警处置、预警趋势、教师风险、教室健康、设备运维、敏感词、预警视频回看。"
        "如果用户问题已经足够确定，就输出 needs_clarification=false。"
        "如果继续查询可能按错误口径回答，则输出 needs_clarification=true，并给出1个最关键的追问。"
        "重点判断：时间范围是否清楚、业务域是否清楚、实体角色是否清楚、排行/Top维度是否清楚、指标是否清楚。"
        "例如“高等数学这门课的情况”缺业务域和时间范围，应追问想看AI巡课还是课堂AI预警、按今日还是近7天。"
        "例如“周霄一周内最多的风险类型”中周霄的实体角色不明确，应追问是教师还是课程/其他对象。"
        "必须仅输出JSON对象，不要markdown。"
        "JSON字段：needs_clarification(boolean)、confidence(number 0~1)、missing_fields(array)、"
        "clarification_question(string)、suggested_replies(array)、reason(string)、detected(object)。"
        "missing_fields只能使用：domain,time_scope,entity_role,dimension,metric。"
        "suggested_replies给2到3个短回复，便于用户直接点击或复制。"
    )
    user_payload = {
        "question": question,
        "rule_bucket": bucket,
        "rule_query_options": query_options,
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
    ]


def _format_llm_clarification_response(
    parsed: dict[str, Any],
    bucket: str,
    query_options: dict[str, Any],
    question_text: str,
) -> dict[str, Any] | None:
    needs_clarification = bool(parsed.get("needs_clarification"))
    confidence = max(0.0, min(1.0, _safe_float(parsed.get("confidence"), 0.0)))
    if not needs_clarification or confidence < float(settings.assistant_clarification_llm_min_confidence):
        return None

    missing_fields_raw = parsed.get("missing_fields") if isinstance(parsed.get("missing_fields"), list) else []
    allowed_fields = {"domain", "time_scope", "entity_role", "dimension", "metric"}
    missing_fields = [str(x) for x in missing_fields_raw if str(x) in allowed_fields]
    if _has_explicit_time_expression(question_text):
        missing_fields = [x for x in missing_fields if x != "time_scope"]
    if _question_has_rank_need(question_text) and not _question_has_dimension_hint(question_text):
        if "dimension" not in missing_fields:
            missing_fields.append("dimension")
        if not _extract_possible_bare_person_name(question_text):
            missing_fields = [x for x in missing_fields if x != "entity_role"]
    question = str(parsed.get("clarification_question") or "").strip()
    if "domain" in missing_fields and "dimension" in missing_fields and _has_explicit_time_expression(question_text):
        question = "你想看哪个业务域，以及按哪个维度排行？例如课堂AI预警按学院/风险类型，或AI巡课按重点关注课堂。"
    if not question:
        if "domain" in missing_fields:
            question = "你想看AI巡课情况，还是课堂AI预警情况？"
        elif "time_scope" in missing_fields:
            question = "你希望统计哪个时间范围？例如今日、近7天、近30天，还是当前实时？"
        elif "entity_role" in missing_fields:
            question = "你提到的对象是教师、课程、学院，还是教室？"
        elif "dimension" in missing_fields:
            question = "你想按哪个维度查看？例如学院、课程、教师、教室、节次或风险类型。"
        else:
            question = "这个问题需要先确认统计口径，你希望按哪个范围查看？"

    suggestions_raw = parsed.get("suggested_replies") if isinstance(parsed.get("suggested_replies"), list) else []
    suggestions = [
        str(x).strip()
        for x in suggestions_raw
        if str(x).strip() and str(x).strip() not in {"其他", "其它"}
    ][:3]
    course_name = str(query_options.get("course_keyword") or "").strip()
    if (
        "domain" in missing_fields
        and "dimension" in missing_fields
        and _has_explicit_time_expression(question_text)
    ):
        suggestions = ["今日课堂AI预警按学院排行", "今日课堂AI预警按风险类型排行", "今日AI巡课重点关注课堂Top5"]
    elif "domain" in missing_fields and "time_scope" in missing_fields:
        if course_name:
            suggestions = [
                f"看今日{course_name}AI巡课情况",
                f"看今日{course_name}课堂AI预警情况",
                f"看近7天{course_name}课堂AI预警情况",
            ]
        else:
            suggestions = ["看今日AI巡课情况", "看今日课堂AI预警情况", "看近7天课堂AI预警情况"]
    elif "entity_role" in missing_fields:
        bare_name = _extract_possible_bare_person_name(question_text)
        if bare_name:
            suggestions = [f"按教师查{bare_name}", f"按课程查{bare_name}"]
    elif "dimension" in missing_fields:
        suggestions = ["按学院排行", "按课程排行", "按风险类型排行"]
    if not suggestions:
        suggestions = ["看今日AI巡课情况", "看今日课堂AI预警情况", "按近7天统计"]
    suggestion_text = "\n".join(f"- {text}" for text in suggestions)
    detected = parsed.get("detected") if isinstance(parsed.get("detected"), dict) else {}
    return {
        "intent": "clarification",
        "answer": (
            "为了避免按错误口径回答，我需要先确认一下：\n"
            f"1. {question}\n"
            "确认后我会继续查询并生成分析报告。\n"
            f"你可以这样回复：\n{suggestion_text}"
        ),
        "data": {
            "clarification": {
                "missing_fields": missing_fields,
                "detected_bucket": bucket,
                "query_options": query_options,
                "confidence": confidence,
                "reason": str(parsed.get("reason") or "")[:240],
                "detected": detected,
                "judge": "llm",
            }
        },
        "source": "clarification_llm",
    }


def _build_llm_clarification_response(
    *,
    question: str,
    bucket: str,
    query_options: dict[str, Any],
    trace_id: str | None = None,
) -> dict[str, Any] | None:
    if not (
        settings.assistant_clarification_enabled
        and settings.assistant_clarification_llm_enabled
    ):
        trace_emit(trace_id, "llm_clarification_disabled")
        return None

    payload: dict[str, object] = {
        "model": settings.llm_model,
        "messages": _clarification_llm_messages(
            question=question,
            bucket=bucket,
            query_options=query_options,
        ),
        "temperature": 0.0,
        "max_tokens": int(settings.assistant_clarification_llm_max_tokens or 420),
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
        clarification_timeout = float(settings.assistant_clarification_llm_timeout_sec or 5)
        trace_emit(trace_id, "llm_clarification_urlopen_begin", timeout_sec=clarification_timeout)
        with request.urlopen(req, timeout=clarification_timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        content = str(body["choices"][0]["message"]["content"] or "").strip()
        trace_emit(trace_id, "llm_clarification_urlopen_done", http_status=getattr(resp, "status", None))
    except (error.URLError, TimeoutError, json.JSONDecodeError, ValueError, KeyError, IndexError, TypeError) as ex:
        trace_emit(
            trace_id,
            "llm_clarification_failed",
            error_type=type(ex).__name__,
            error=redact_sensitive_text(str(ex), max_len=240),
        )
        return None

    parsed = _parse_first_json_object(content)
    if not parsed:
        trace_emit(trace_id, "llm_clarification_json_not_found", preview=redact_sensitive_text(content, max_len=180))
        return None
    result = _format_llm_clarification_response(parsed, bucket, query_options, question)
    trace_emit(
        trace_id,
        "llm_clarification_candidate",
        needs=bool(parsed.get("needs_clarification")),
        confidence=_safe_float(parsed.get("confidence"), 0.0),
        hit=bool(result),
        missing=",".join(result.get("data", {}).get("clarification", {}).get("missing_fields") or []) if result else "",
    )
    return result


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
    daily_markers = ("今天", "今日", "当天", "汇总", "已结束", "已完成AI巡查", "已巡查", "今日课堂")
    patrol_daily_markers = ("非课表", "今天", "今日", "已上", "当天", "汇总", "已结束")
    patrol_realtime_markers = (
        "实时",
        "正在",
        "当前节次",
        "课表时间段",
        "进行中",
        "此刻",
        "现在",
        "正在上课",
        "在上课",
        "当前课堂",
        "上课课堂",
    )
    realtime_classroom_keywords = (
        "有哪些课堂在上课",
        "哪些课堂在上课",
        "现在有哪些课堂",
        "现在上课",
        "当前上课",
        "正在上课",
        "在上课",
        "上课课堂",
    )
    warning_metric_keywords = ("风险等级", "预警占比", "预警类型", "高风险课堂", "风险课堂", "告警类型", "风险类型")
    patrol_metric_keywords = ("到课率", "抬头率", "前排满座率", "重点关注课堂", "活力较高课堂", "课堂活动指数")

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
    if _contains_any(q, warning_metric_keywords):
        if _contains_any(q, realtime_markers):
            return "realtime_warning"
        if _contains_any(q, daily_markers):
            return "daily_warning"
        return "daily_warning"
    if _contains_any(q, patrol_metric_keywords):
        if _contains_any(q, patrol_realtime_markers):
            return "realtime_patrol"
        if _contains_any(q, patrol_daily_markers) or _contains_any(q, daily_markers):
            return "daily_patrol"
        return "daily_patrol"
    # 3 实时课堂预警
    if "预警" in q or "告警" in q:
        if _contains_any(q, realtime_markers):
            return "realtime_warning"
        # 4 今日课堂预警（无「实时/正在」等词时默认走今日汇总）
        if _contains_any(q, daily_markers):
            return "daily_warning"
        return "daily_warning"
    if _contains_any(q, realtime_classroom_keywords):
        return "realtime_patrol"
    # 1 / 2 智能AI巡课（不含预警）：兼容用户继续使用旧口径“巡课/巡查”提问。
    if any(k in q for k in ("AI巡课", "AI巡查", "智能AI巡课", "巡课", "巡查", "智能巡课")):
        # 先判断“非课表/今日汇总”口径，避免“非课表”误命中“课表”实时分支
        if _contains_any(q, patrol_daily_markers):
            return "daily_patrol"
        if _contains_any(q, patrol_realtime_markers):
            return "realtime_patrol"
        return "realtime_patrol"
    return "general"


def _try_simple_bucket_answer(
    tenant_id: str,
    bucket: str,
    *,
    query_options: dict[str, Any] | None = None,
    stream_callback: StreamCallback | None = None,
    trace_id: str | None = None,
) -> dict[str, Any] | None:
    """命中分桶时先查真实数据，再由 LLM 按数据总结回答。"""
    if bucket == "general":
        return None
    query_options = query_options or {}
    cache_key = _assistant_result_cache_key(tenant_id, bucket, query_options)
    cached = _assistant_result_cache_get(cache_key)
    if cached is not None:
        if isinstance(cached.get("data"), dict):
            cached["data"]["cache_hit"] = True
        _stream_fixed_answer(stream_callback, str(cached.get("answer") or ""))
        return cached
    emitted_parts: list[str] = []

    def _record_stream_delta(text: str) -> None:
        if not stream_callback or not text:
            return
        emitted_parts.append(text)
        stream_callback(text)

    local_stream_callback: StreamCallback | None = _record_stream_delta if stream_callback else None
    try:
        if bucket == "realtime_patrol":
            data = get_realtime_patrol_brief(
                tenant_id,
                synthesize=True,
                query_options=query_options,
                stream_callback=local_stream_callback,
                trace_id=trace_id,
            )
        elif bucket == "daily_patrol":
            data = get_daily_patrol_brief(
                tenant_id,
                synthesize=True,
                query_options=query_options,
                stream_callback=local_stream_callback,
                trace_id=trace_id,
            )
        elif bucket == "realtime_warning":
            data = get_realtime_warning_brief(
                tenant_id,
                synthesize=True,
                query_options=query_options,
                stream_callback=local_stream_callback,
                trace_id=trace_id,
            )
        elif bucket == "daily_warning":
            data = get_daily_warning_brief(
                tenant_id,
                synthesize=True,
                query_options=query_options,
                stream_callback=local_stream_callback,
                trace_id=trace_id,
            )
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
        err_msg = redact_sensitive_text(str(ex), max_len=240)
        error_answer = "业务数据暂无法查询，请稍后重试，或联系管理员检查数据源连接状态。"
        _stream_fixed_answer(stream_callback, error_answer)
        return {
            "intent": bucket,
            "answer": error_answer,
            "data": {"error_type": err_type, "error": err_msg},
            "source": "patrol_api_error",
        }
    answer = str(data.get("brief") or "").strip()
    if not answer:
        return None
    if stream_callback and not emitted_parts:
        _stream_fixed_answer(stream_callback, answer)
    result = {
        "intent": bucket,
        "answer": answer,
        "data": data,
        "source": "patrol_api",
    }
    _assistant_result_cache_set(cache_key, result)
    return result


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
        f"""
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
        f"""
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


def get_realtime_patrol_brief(
    tenant_id: str,
    *,
    synthesize: bool = True,
    query_options: dict[str, Any] | None = None,
    stream_callback: StreamCallback | None = None,
    trace_id: str | None = None,
) -> dict[str, Any]:
    now = datetime.now()
    options = query_options or {}
    top_n = _normalize_top_n(options.get("top_n"))
    sql_top_limit = max(top_n, 10)
    filter_summary = _summarize_query_options(options, top_n=top_n)
    course_scope_sql, course_scope_params = _build_course_scope_filter_sql("", options)
    rounds = _fetch_patrol_round_metrics(tenant_id, now)
    threshold_params = _patrol_threshold_params()
    focus_attendance_lt = threshold_params["focus_attendance_lt"]
    focus_front_full_lt = threshold_params["focus_front_full_lt"]
    focus_rise_lt = threshold_params["focus_rise_lt"]
    vitality_attendance_gte = threshold_params["vitality_attendance_gte"]
    vitality_front_full_gte = threshold_params["vitality_front_full_gte"]
    vitality_rise_gte = threshold_params["vitality_rise_gte"]
    row = _fetch_one(
        f"""
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
            {course_scope_sql}
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
        {"tenant_id": tenant_id, "now": now, **threshold_params, **course_scope_params},
    )
    org_rows = _fetch_all(
        f"""
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
          {course_scope_sql}
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
        LIMIT {sql_top_limit}
        """,
        {"tenant_id": tenant_id, "now": now, **threshold_params, **course_scope_params},
    )
    focus_top_rows = _fetch_all(
        f"""
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
          {course_scope_sql}
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
        LIMIT {sql_top_limit}
        """,
        {"tenant_id": tenant_id, "now": now, **threshold_params, **course_scope_params},
    )
    vitality_top_rows = _fetch_all(
        f"""
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
          {course_scope_sql}
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
        LIMIT {sql_top_limit}
        """,
        {"tenant_id": tenant_id, "now": now, **threshold_params, **course_scope_params},
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
        "query_options_summary": filter_summary,
        "generated_at": now.isoformat(timespec="seconds"),
    }
    if payload["classroom_count"] > 0:
        payload["focus_ratio"] = round(payload["focus_classroom_count"] / payload["classroom_count"] * 100, 2)
        payload["high_vitality_ratio"] = round(payload["high_vitality_count"] / payload["classroom_count"] * 100, 2)

    if payload["classroom_count"] <= 0:
        payload["brief"] = (
            "【实时AI巡课简报】\n"
            f"当前节次：{payload['current_section']}；当前未检索到在课课堂。\n"
            f"【筛选条件】{filter_summary}\n"
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
    if synthesize and stream_callback:
        _stream_fixed_answer(stream_callback, "【实时AI巡课简报】\n【总体结论】")
    summary = (
        _summarize(
            "请输出1句易懂的实时AI巡课结论（25-60字，先说当前状态，再说优先关注方向）。",
            payload,
            summary_fallback,
            stream_callback=stream_callback,
            trace_id=trace_id,
        )
        if synthesize
        else summary_fallback
    )
    if not stream_callback:
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
        "；".join(
            f"{idx + 1}.{str(r.get('org_name') or '未知学院')}({_to_int(r.get('focus_count'))})"
            for idx, r in enumerate(org_rows[:top_n])
        )
        if org_rows
        else "暂无"
    )
    focus_lines = [_course_metric_line(idx, r) for idx, r in enumerate(focus_top_rows[:top_n], start=1)]
    focus_text = "\n".join(focus_lines) if focus_lines else "暂无"
    vitality_lines = [_course_metric_line(idx, r) for idx, r in enumerate(vitality_top_rows[:top_n], start=1)]
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
        f"本次展示条件：{filter_summary}。",
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
        vitality_block = f"【五、活力较高课堂Top{top_n}】\n" f"{vitality_text}\n"
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
        f"- 学院风险Top{top_n}：{org_text}\n"
        f"【四、重点关注课堂Top{top_n}】\n"
        f"{focus_text}\n"
        f"{vitality_block}"
        f"{suggestion_section_title}\n"
        f"{suggestion_text}\n"
        f"{notes_section_title}\n"
        f"{notes_text}"
    )
    return payload


def get_daily_patrol_brief(
    tenant_id: str,
    *,
    synthesize: bool = True,
    query_options: dict[str, Any] | None = None,
    stream_callback: StreamCallback | None = None,
    trace_id: str | None = None,
) -> dict[str, Any]:
    now = datetime.now()
    today = now.date()
    options = query_options or {}
    top_n = _normalize_top_n(options.get("top_n"))
    sql_top_limit = max(top_n, 10)
    filter_summary = _summarize_query_options(options, top_n=top_n)
    course_scope_sql, course_scope_params = _build_course_scope_filter_sql("", options)
    threshold_params = _patrol_threshold_params()
    focus_attendance_lt = threshold_params["focus_attendance_lt"]
    focus_front_full_lt = threshold_params["focus_front_full_lt"]
    focus_rise_lt = threshold_params["focus_rise_lt"]
    vitality_attendance_gte = threshold_params["vitality_attendance_gte"]
    vitality_front_full_gte = threshold_params["vitality_front_full_gte"]
    vitality_rise_gte = threshold_params["vitality_rise_gte"]
    row = _fetch_one(
        f"""
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
          {course_scope_sql}
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
        {"tenant_id": tenant_id, "today": today, "now": now, **threshold_params, **course_scope_params},
    )
    org_rows = _fetch_all(
        f"""
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
          {course_scope_sql}
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
        LIMIT {sql_top_limit}
        """,
        {"tenant_id": tenant_id, "today": today, "now": now, **threshold_params, **course_scope_params},
    )
    section_rows = _fetch_all(
        f"""
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
          {course_scope_sql}
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
        LIMIT {sql_top_limit}
        """,
        {"tenant_id": tenant_id, "today": today, "now": now, **threshold_params, **course_scope_params},
    )
    focus_top_rows = _fetch_all(
        f"""
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
          {course_scope_sql}
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
        LIMIT {sql_top_limit}
        """,
        {"tenant_id": tenant_id, "today": today, "now": now, **threshold_params, **course_scope_params},
    )
    vitality_top_rows = _fetch_all(
        f"""
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
          {course_scope_sql}
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
        LIMIT {sql_top_limit}
        """,
        {"tenant_id": tenant_id, "today": today, "now": now, **threshold_params, **course_scope_params},
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
        "query_options_summary": filter_summary,
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

    if payload["classroom_count"] <= 0:
        payload["brief"] = (
            "【今日AI巡课简报】\n"
            "当前未检索到今日已完成课堂的AI巡课数据。\n"
            f"【筛选条件】{filter_summary}\n"
            f"【课表概览】今日排课{payload['today_scheduled_classroom_count']}节，"
            f"AI巡查覆盖率{payload['inspection_coverage_ratio']}%（已完成AI巡查节数/今日排课节数）。"
            f"今日节次进度：{payload['finished_section_count']}/{payload['today_scheduled_section_count']}。\n"
            "【可能原因】今日暂无排课/课程尚未结束/AI巡课数据延迟入库。\n"
            "【建议】可稍后重试，或查询“实时AI巡课简报”确认当前在课情况。"
        )
        return payload

    summary_fallback = (
        f"今日AI巡课覆盖率{payload['inspection_coverage_ratio']}%，"
        f"已完成AI巡查课堂到课率{payload['avg_attendance']}%、抬头率{payload['avg_rise']}%，"
        f"重点关注课堂较多，建议优先跟进到课率和抬头率偏低课程。"
    )
    if synthesize and stream_callback:
        _stream_fixed_answer(stream_callback, "【今日AI巡课简报】\n【总体结论】")
    summary = (
        _summarize(
            "请输出1句易懂的今日AI巡课总体结论（25-60字，先说整体情况，再说优先跟进方向，避免过度风险化）。",
            payload,
            summary_fallback,
            stream_callback=stream_callback,
            trace_id=trace_id,
        )
        if synthesize
        else summary_fallback
    )
    if not stream_callback:
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
        "；".join(
            f"{idx + 1}.{str(r.get('org_name') or '未知学院')}({_to_int(r.get('focus_count'))})"
            for idx, r in enumerate(org_rows[:top_n])
        )
        if org_rows
        else "暂无"
    )
    section_lines = []
    for idx, section_row in enumerate(section_rows[:top_n], start=1):
        leti_number = _to_int(section_row.get("leti_number"))
        section_name = _display_section_name(section_row.get("section_name"), leti_number)
        section_lines.append(
            f"{idx}. {section_name}：{_to_int(section_row.get('class_count'))}个节次，平均到课率{_to_float(section_row.get('avg_attendance'))}%"
        )
    section_text = "\n".join(section_lines) if section_lines else "暂无"

    focus_lines = [_course_metric_line(idx, r) for idx, r in enumerate(focus_top_rows[:top_n], start=1)]
    focus_text = "\n".join(focus_lines) if focus_lines else "暂无"
    vitality_lines = [_course_metric_line(idx, r) for idx, r in enumerate(vitality_top_rows[:top_n], start=1)]
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
        "统计范围为今日已结束且已产生AI巡课数据的课堂。",
        f"本次展示条件：{filter_summary}。",
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
        f"今日排课{payload['today_scheduled_classroom_count']}节，已完成AI巡查{payload['classroom_count']}节，"
        f"AI巡查覆盖率{payload['inspection_coverage_ratio']}%（已完成AI巡查节数/今日排课节数）。"
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
            f"- 活力较高课堂：{payload['high_vitality_count']}个（占已完成AI巡查{payload['high_vitality_ratio']}%）\n"
        )
        vitality_block = f"【六、活力较高课堂Top{top_n}】\n" f"{vitality_text}\n"
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
        f"- 重点关注课堂：{payload['focus_classroom_count']}个（占已完成AI巡查{payload['focus_ratio']}%）\n"
        f"{vitality_metric_line}"
        "【三、重点关注情况】\n"
        f"- 触发原因拆分：{focus_reason_text}\n"
        f"- 学院风险Top{top_n}：{org_text}\n"
        "【四、节次分布】\n"
        f"{section_text}\n"
        f"【五、重点关注课堂Top{top_n}】\n"
        f"{focus_text}\n"
        f"{vitality_block}"
        f"{suggestion_section_title}\n"
        f"{suggestion_text}\n"
        f"{notes_section_title}\n"
        f"{notes_text}"
    )
    return payload


def get_realtime_warning_brief(
    tenant_id: str,
    *,
    synthesize: bool = True,
    query_options: dict[str, Any] | None = None,
    stream_callback: StreamCallback | None = None,
    trace_id: str | None = None,
) -> dict[str, Any]:
    now = datetime.now()
    options = query_options or {}
    top_n = _normalize_top_n(options.get("top_n"))
    sql_top_limit = max(top_n, 10)
    filter_summary = _summarize_query_options(options, top_n=top_n)
    course_scope_sql, course_scope_params = _build_course_scope_filter_sql("", options)
    course_scope_sql_c, course_scope_params_c = _build_course_scope_filter_sql("c", options)
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
            {course_scope_sql}
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
              {course_scope_sql_c}
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
              {course_scope_sql_c}
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
        {"tenant_id": tenant_id, "now": now, **course_scope_params, **course_scope_params_c},
    )
    level_rows = _fetch_all(
        f"""
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
            {course_scope_sql_c}
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
            {course_scope_sql_c}
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
        {"tenant_id": tenant_id, "now": now, **course_scope_params_c},
    )
    type_rows = _fetch_all(
        f"""
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
            {course_scope_sql_c}
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
            {course_scope_sql_c}
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
        LIMIT {sql_top_limit}
        """,
        {"tenant_id": tenant_id, "now": now, **course_scope_params_c},
    )
    warning_course_rows = _fetch_all(
        f"""
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
            {course_scope_sql_c}
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
            {course_scope_sql_c}
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
        LIMIT {sql_top_limit}
        """,
        {"tenant_id": tenant_id, "now": now, **course_scope_params_c},
    )
    warning_org_rows = _fetch_all(
        f"""
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
            {course_scope_sql_c}
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
            {course_scope_sql_c}
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
        LIMIT {sql_top_limit}
        """,
        {"tenant_id": tenant_id, "now": now, **course_scope_params_c},
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
            for idx, x in enumerate(warning_type_top10[:top_n])
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
        "query_options_summary": filter_summary,
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
            f"【筛选条件】{filter_summary}\n"
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
    if synthesize and stream_callback:
        _stream_fixed_answer(stream_callback, "【实时预警简报】\n【结论】")
    summary = (
        _summarize(
            "请输出1句实时预警结论（20-50字，必须包含风险等级或预警占比）。",
            payload,
            summary_fallback,
            stream_callback=stream_callback,
            trace_id=trace_id,
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
            for idx, r in enumerate(warning_course_rows[:top_n])
        )
        if warning_course_rows
        else "暂无"
    )
    org_text = (
        "；".join(
            f"{idx + 1}.{str(r.get('org_name') or '未知学院')}({_to_int(r.get('warning_count'))}条/{_to_int(r.get('warning_course_count'))}节次)"
            for idx, r in enumerate(warning_org_rows[:top_n])
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
        f"【预警类型Top{top_n}】{warning_type_top_text}\n"
        f"【高风险课堂Top{top_n}】{course_text}\n"
        f"【学院风险Top{top_n}】{org_text}\n"
        f"【建议动作】{' '.join(suggestions)}\n"
        f"【口径】实时预警按近2小时内的学情和教情预警统计；整体风险由最严重等级、平均等级与预警课堂占比综合判断；本次展示条件：{filter_summary}。"
    )
    return payload


def get_daily_warning_brief(
    tenant_id: str,
    *,
    synthesize: bool = True,
    query_options: dict[str, Any] | None = None,
    stream_callback: StreamCallback | None = None,
    trace_id: str | None = None,
) -> dict[str, Any]:
    now = datetime.now()
    today = now.date()
    options = query_options or {}
    top_n = _normalize_top_n(options.get("top_n"))
    sql_top_limit = max(top_n, 10)
    filter_summary = _summarize_query_options(options, top_n=top_n)
    course_scope_sql, course_scope_params = _build_course_scope_filter_sql("", options)
    course_scope_sql_c, course_scope_params_c = _build_course_scope_filter_sql("c", options)
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
            {course_scope_sql}
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
              {course_scope_sql_c}
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
              {course_scope_sql_c}
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
        {"tenant_id": tenant_id, "today": today, "now": now, **course_scope_params, **course_scope_params_c},
    )
    level_rows = _fetch_all(
        f"""
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
            {course_scope_sql_c}
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
            {course_scope_sql_c}
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
        {"tenant_id": tenant_id, "today": today, "now": now, **course_scope_params_c},
    )
    type_rows = _fetch_all(
        f"""
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
            {course_scope_sql_c}
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
            {course_scope_sql_c}
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
        LIMIT {sql_top_limit}
        """,
        {"tenant_id": tenant_id, "today": today, "now": now, **course_scope_params_c},
    )
    warning_course_rows = _fetch_all(
        f"""
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
            {course_scope_sql_c}
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
            {course_scope_sql_c}
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
        LIMIT {sql_top_limit}
        """,
        {"tenant_id": tenant_id, "today": today, "now": now, **course_scope_params_c},
    )
    warning_org_rows = _fetch_all(
        f"""
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
            {course_scope_sql_c}
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
            {course_scope_sql_c}
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
        LIMIT {sql_top_limit}
        """,
        {"tenant_id": tenant_id, "today": today, "now": now, **course_scope_params_c},
    )
    period_rows = _fetch_all(
        f"""
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
            {course_scope_sql_c}
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
            {course_scope_sql_c}
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
        {"tenant_id": tenant_id, "today": today, "now": now, **course_scope_params_c},
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
        "query_options_summary": filter_summary,
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
            f"【筛选条件】{filter_summary}\n"
            "【可能原因】今日暂无已结束课程/AI巡查数据尚未入库。\n"
            "【建议】可先查询“实时预警简报”查看在课风险。"
        )
        return payload

    summary_fallback = (
        f"今日已完成AI巡查{inspected}个课堂，预警课堂{warning}个（{ratio}%），"
        f"整体风险{risk}，建议优先跟进高频预警类型与高风险课堂。"
    )
    if synthesize and stream_callback:
        _stream_fixed_answer(stream_callback, "【今日预警简报】\n【总体结论】")
    summary = (
        _summarize(
            "请输出1句易懂的今日预警结论（25-60字，先给整体风险，再给优先处置方向）。",
            payload,
            summary_fallback,
            stream_callback=stream_callback,
            trace_id=trace_id,
        )
        if synthesize
        else summary_fallback
    )
    if not stream_callback:
        summary = summary.replace("\n", " ").strip()

    level_lines = [
        f"{idx}. {str(x.get('warning_level_name') or '未知')}：{_to_int(x.get('warning_count'))}条（{_to_float(x.get('warning_ratio'))}%）"
        for idx, x in enumerate(warning_level_distribution, start=1)
    ]
    level_text = "\n".join(level_lines) if level_lines else "暂无"

    type_lines = [
        f"{idx}. {x['indicator_name']}：{x['warning_count']}条（{x['warning_ratio']}%）"
        for idx, x in enumerate(warning_type_top10[:top_n], start=1)
    ]
    type_text = "\n".join(type_lines) if type_lines else "暂无"

    course_lines = [
        (
            f"{idx}. {_course_top_identity(r)}："
            f"预警{_to_int(r.get('warning_count'))}条，涉及{_to_int(r.get('indicator_type_count'))}类，"
            f"最严重等级{_warning_level_name(_to_int(r.get('worst_warning_level')))}"
        )
        for idx, r in enumerate(warning_course_rows[:top_n], start=1)
    ]
    course_text = "\n".join(course_lines) if course_lines else "暂无"

    org_lines = [
        (
            f"{idx}. {str(r.get('org_name') or '未知学院')}："
            f"{_to_int(r.get('warning_count'))}条预警 / {_to_int(r.get('warning_course_count'))}个节次"
        )
        for idx, r in enumerate(warning_org_rows[:top_n], start=1)
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
            suggestions.append(f"整体风险偏高，建议优先处置高风险课堂Top{top_n}，并同步学院负责人当日跟进。")
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
        f"本次展示条件：{filter_summary}。",
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
        f"- 类型Top{top_n}：\n{type_text}\n"
        f"【四、高风险课堂Top{top_n}】\n"
        f"{course_text}\n"
        f"【五、学院风险Top{top_n}】\n"
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
    payload["brief"] = _summarize("输出教室健康度与空闲异常简报。", payload, fallback) if synthesize else fallback
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


def preview_assistant_auto_plan(
    question: str,
    tenant_id: str,
    *,
    query_options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    options = query_options or _extract_query_options(question or "")
    return plan_auto_query(question or "", tenant_id, options)


def _has_explicit_time_expression(question: str) -> bool:
    q = (question or "").strip()
    markers = (
        "今天", "今日", "当天", "实时", "当前", "现在", "正在", "近2小时",
        "最新", "最近一条", "最近一次",
        "近3天", "最近3天", "过去3天", "3天内", "三天内",
        "近7天", "最近7天", "过去7天", "7天内", "一周内", "近一周", "最近一周", "过去一周", "本周", "周内",
        "近30天", "最近30天", "过去30天", "30天内", "一个月内", "近一个月", "最近一个月", "本月",
    )
    return any(x in q for x in markers)


def _has_ambiguous_time_expression(question: str) -> bool:
    q = (question or "").strip()
    return any(x in q for x in ("最近", "近期", "这段时间", "一段时间")) and not _has_explicit_time_expression(q)


def _has_domain_hint(question: str) -> bool:
    q = (question or "").strip()
    return any(x in q for x in ("巡课", "巡查", "到课", "抬头", "前排", "课堂活动", "预警", "告警", "风险"))


def _is_open_status_question(question: str) -> bool:
    q = (question or "").strip()
    return any(x in q for x in ("情况", "怎么样", "有没有问题", "看一下", "看下", "看看", "分析一下", "分析下"))


def _build_boundary_response(
    *,
    question: str,
    bucket: str,
    query_options: dict[str, Any],
) -> dict[str, Any] | None:
    q = (question or "").strip()
    if not q:
        return None
    compact = "".join(q.lower().split())

    boundary_type = ""
    answer = ""
    suggestion = ""

    sensitive_keywords = (
        ".env",
        "env文件",
        "环境变量",
        "api_key",
        "apikey",
        "api key",
        "密钥",
        "token",
        "数据库密码",
        "db密码",
        "连接串",
        "连接字符串",
        "jdbc",
        "dsn",
        "mysql连接",
        "完整连接",
    )
    if any(k in compact for k in sensitive_keywords):
        boundary_type = "sensitive_config"
        answer = (
            "这个请求涉及敏感配置，我不能读取或输出 .env、密钥、token、数据库密码、API Key "
            "或完整数据库连接串。"
        )
        suggestion = "我可以帮你说明配置项用途，或检查代码中是否存在安全输出风险。"

    destructive_keywords = (
        "删除",
        "清空",
        "清库",
        "删库",
        "drop",
        "truncate",
        "deletefrom",
        "update",
        "insert",
        "写入",
        "修改数据",
        "变更数据",
        "修改预警",
        "修改阈值",
        "调整阈值",
        "设置阈值",
        "改阈值",
        "改配置",
        "修改配置",
    )
    if not boundary_type and any(k in compact for k in destructive_keywords):
        boundary_type = "write_or_config_change"
        answer = "我是课堂数据查询和分析助手，不能直接删除、写入、修改业务数据，也不能直接修改生产配置或预警阈值。"
        suggestion = "如需调整配置，请通过有权限的后台或运维流程处理；我可以先帮你查询现状或生成预警推送预览。"

    tenant_or_auth_keywords = (
        "跨租户",
        "其他租户",
        "别的租户",
        "全部租户",
        "所有租户",
        "绕过权限",
        "跳过权限",
        "不走权限",
        "不走鉴权",
        "绕过鉴权",
    )
    if not boundary_type and any(k in compact for k in tenant_or_auth_keywords):
        boundary_type = "tenant_or_auth_boundary"
        answer = "我不能绕过权限或跨租户查询数据，只能在当前授权租户和权限范围内提供课堂数据分析。"
        suggestion = "如需查看其他范围，请先确认平台权限、租户范围和审批流程。"

    free_sql_keywords = ("执行sql", "运行sql", "自由sql", "任意sql", "select*", "selectfrom", "查全表")
    if not boundary_type and any(k in compact for k in free_sql_keywords):
        boundary_type = "free_sql_boundary"
        answer = "我不能执行自由 SQL 或全表查询。当前查询应走白名单模板、受控业务函数或语义规划链路。"
        suggestion = "你可以改问具体业务问题，例如“今日课堂AI预警汇总”或“到课率最低的课堂有哪些”。"

    future_keywords = ("未来", "明天", "后天", "下周", "预测", "预估", "会不会")
    future_metric_keywords = ("预警", "风险", "到课", "巡课", "巡查", "课堂")
    if (
        not boundary_type
        and any(k in q for k in future_keywords)
        and any(k in q for k in future_metric_keywords)
    ):
        boundary_type = "future_prediction_boundary"
        answer = "当前我不能稳定预测未来课堂风险或未来到课情况。"
        suggestion = "可以改查当前实时、今日汇总或近7天趋势，用已有数据辅助判断。"

    deploy_keywords = ("重启服务", "停止服务", "部署服务", "发布生产", "上线生产", "执行部署")
    if not boundary_type and any(k in compact for k in deploy_keywords):
        boundary_type = "ops_boundary"
        answer = "我不能私自执行部署、重启、停止服务等高风险运维操作。"
        suggestion = "如需操作生产环境，请先走运维确认和审批流程；我可以协助整理检查清单。"

    push_action = any(k in q for k in ("推送", "发送", "通知", "发给", "发到"))
    push_preview = any(k in q for k in ("预览", "推送预览", "阈值", "策略", "效果"))
    push_channel = any(
        k in q
        for k in (
            "企业微信",
            "微信",
            "校内消息",
            "短信",
            "辅导员",
            "授课教师",
            "任课教师",
            "任课老师",
            "老师",
            "教师",
            "班主任",
            "学院负责人",
            "负责人",
        )
    )
    real_push_keyword = any(k in q for k in ("真实推送", "直接推送", "正式推送", "立即推送", "马上推送", "现在推送"))
    push_subject = any(k in q for k in ("预警", "告警", "课堂", "消息", "通知"))
    real_push_request = (real_push_keyword and push_subject) or (push_action and push_channel)
    if not boundary_type and real_push_request and not push_preview:
        boundary_type = "real_push_boundary"
        answer = "我不能直接向企业微信、微信或校内消息平台发送真实推送。"
        suggestion = "可以先生成预警推送预览；真实发送需要确认权限、对象、渠道和审批流程。"

    if not boundary_type:
        return None

    return {
        "intent": "clarification",
        "answer": f"{answer}\n{suggestion}",
        "data": {
            "clarification": {
                "missing_fields": ["security_boundary"],
                "detected_bucket": bucket,
                "query_options": query_options,
                "boundary_type": boundary_type,
                "judge": "boundary_rule",
            }
        },
        "source": "boundary_rule",
    }


def _extract_possible_bare_person_name(question: str) -> str | None:
    q = re.sub(r"^(请|帮我|麻烦|查看|看一下|看下|看看|统计|分析|查一下|查下)+", "", (question or "").strip())
    if not q:
        return None
    m = re.match(r"([\u4e00-\u9fa5]{2,4}?)(?=(?:一周|近|最近|过去|本周|周内|最多|最高|最低|风险|预警|的|$))", q)
    if not m:
        return None
    name = m.group(1)
    blocked = {
        "今天", "今日", "当前", "实时", "课堂", "课程", "学院", "教室", "风险", "预警",
        "老师", "教师", "最多", "最高", "最低", "本周", "最近", "过去",
    }
    if name in blocked or any(token in name for token in ("哪个", "哪些", "哪位", "哪门", "多少")):
        return None
    return name


def _question_has_rank_need(question: str) -> bool:
    q = (question or "").lower()
    return any(x in q for x in ("哪个", "哪些", "谁", "最多", "最少", "最高", "最低", "top", "排行", "排名", "分布"))


def _question_has_dimension_hint(question: str) -> bool:
    q = (question or "").strip()
    return any(
        x in q
        for x in (
            "学院", "教师", "老师", "课程", "课堂", "教室", "节次", "风险类型", "预警类型", "告警类型",
            "到课率", "抬头率", "前排满座率", "敏感词",
        )
    )


def _build_clarification_response(
    *,
    question: str,
    bucket: str,
    query_options: dict[str, Any],
) -> dict[str, Any] | None:
    if not settings.assistant_clarification_enabled:
        return None
    q = (question or "").strip()
    if not q:
        return None

    asks: list[str] = []
    suggestions: list[str] = []
    missing_fields: list[str] = []

    bare_name = _extract_possible_bare_person_name(q)
    has_named_filter = any(
        query_options.get(key)
        for key in ("teacher_keyword", "course_keyword", "org_keyword", "classroom_keyword")
    )
    if bare_name and not has_named_filter and any(x in q for x in ("风险", "预警", "到课", "抬头", "课堂")):
        asks.append(f"“{bare_name}”是教师姓名、课程名称，还是其他对象？")
        suggestions.append(f"如果是教师，可以回复：按教师查{bare_name}近7天风险类型Top5。")
        missing_fields.append("entity_role")

    if (
        bucket in {"realtime_patrol", "daily_patrol", "realtime_warning", "daily_warning"}
        and _is_open_status_question(q)
        and not _has_explicit_time_expression(q)
    ):
        if bucket in {"realtime_patrol", "daily_patrol"}:
            asks.append("你想看当前正在上课的实时AI巡课，还是今日已结束课程的AI巡课汇总？")
            suggestions.append("例如回复：当前实时AI巡课，或今日AI巡课汇总。")
        else:
            asks.append("你想看当前实时课堂AI预警，还是今日课堂AI预警汇总？")
            suggestions.append("例如回复：实时课堂AI预警，或今日课堂AI预警汇总。")
        missing_fields.append("time_scope")

    if _has_ambiguous_time_expression(q):
        asks.append("你希望统计哪个时间范围？例如今日、近7天、近30天，还是当前实时？")
        suggestions.append("例如回复：按近7天统计。")
        missing_fields.append("time_scope")
    elif _question_has_rank_need(q) and not _has_explicit_time_expression(q) and bucket not in {"realtime_patrol", "realtime_warning"}:
        asks.append("这个排行需要确认时间范围：按今日、近7天，还是近30天统计？")
        suggestions.append("例如回复：按近7天统计Top5。")
        missing_fields.append("time_scope")

    if _question_has_rank_need(q) and not _question_has_dimension_hint(q):
        asks.append("你想按哪个维度排行？可以按学院、课程、教师、教室、节次或风险类型。")
        suggestions.append("例如回复：按学院排行，或按风险类型排行。")
        missing_fields.append("dimension")

    if bucket == "general" and any(x in q for x in ("情况", "怎么样", "有没有问题", "看一下", "看看", "分析一下")):
        asks.append("你想看AI巡课情况，还是课堂AI预警情况？")
        suggestions.append("例如回复：今日AI巡课汇总，或今日课堂AI预警汇总。")
        missing_fields.append("domain")
    elif bucket == "general" and _question_has_rank_need(q) and not _has_domain_hint(q):
        asks.append("这个排行需要先确认业务范围：你想看AI巡课指标，还是课堂AI预警？")
        suggestions.append("例如回复：按今日课堂AI预警的风险类型排行，或按今日AI巡课的学院排行。")
        missing_fields.append("domain")

    if not asks:
        return None

    unique_asks = list(dict.fromkeys(asks))
    unique_suggestions = list(dict.fromkeys(suggestions))
    ask_text = "\n".join(f"{idx}. {text}" for idx, text in enumerate(unique_asks, start=1))
    suggestion_text = "\n".join(f"- {text}" for text in unique_suggestions[:3])
    return {
        "intent": "clarification",
        "answer": (
            "为了避免按错误口径回答，我需要先确认一下：\n"
            f"{ask_text}\n"
            "确认后我会继续查询并生成分析报告。\n"
            f"你可以这样回复：\n{suggestion_text}"
        ),
        "data": {
            "clarification": {
                "missing_fields": list(dict.fromkeys(missing_fields)),
                "detected_bucket": bucket,
                "query_options": query_options,
                "bare_name": bare_name,
            }
        },
        "source": "clarification",
    }


def _should_prefer_semantic_report(question: str, bucket: str) -> bool:
    if bucket == "general":
        return False
    if not (
        settings.assistant_auto_plan_enabled
        and settings.assistant_auto_plan_template_execute_enabled
        and settings.assistant_semantic_report_enabled
    ):
        return False
    q = (question or "").lower()
    custom_keywords = (
        "哪个",
        "哪些",
        "谁",
        "多少",
        "最多",
        "最少",
        "最高",
        "最低",
        "top",
        "top",
        "排行",
        "排名",
        "分布",
        "趋势",
        "对比",
        "学院",
        "教师",
        "老师",
        "节次",
        "教室",
        "课程",
        "原因",
        "建议",
    )
    report_keywords = ("简报", "汇总", "概览")
    has_custom_need = any(k in q for k in custom_keywords)
    is_plain_report = any(k in q for k in report_keywords) and not has_custom_need
    return has_custom_need and not is_plain_report


def _compose_semantic_report_stream(
    *,
    question: str,
    auto_plan: dict[str, Any],
    semantic_execution: dict[str, Any],
    fallback_answer: str | None,
    stream_callback: StreamCallback,
    trace_id: str | None,
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
    trace_emit(trace_id, "semantic_report_stream_begin", max_tokens=payload["max_tokens"])
    answer = _stream_chat_completion(
        payload,
        stream_callback=stream_callback,
        trace_id=trace_id,
        trace_prefix="semantic_report_llm",
    )
    if answer:
        return answer
    _stream_fixed_answer(stream_callback, fallback)
    return fallback


def _try_semantic_report_answer(
    *,
    question: str,
    tenant_id: str,
    query_options: dict[str, Any],
    fallback_answer: str | None = None,
    trace_id: str | None = None,
    stream_callback: StreamCallback | None = None,
) -> dict[str, Any] | None:
    auto_plan = preview_assistant_auto_plan(question, tenant_id, query_options=query_options)
    plan_meta = auto_plan.get("query_plan") if isinstance(auto_plan.get("query_plan"), dict) else {}
    auto_bucket = str((plan_meta or {}).get("execute_bucket") or "general")
    auto_conf = _safe_float((plan_meta or {}).get("confidence"), 0.0)
    trace_emit(
        trace_id,
        "semantic_report_candidate",
        bucket=auto_bucket,
        confidence=auto_conf,
        plan_intent=(plan_meta or {}).get("intent"),
        templates=",".join((plan_meta or {}).get("template_ids") or []),
    )
    min_conf = float(settings.assistant_auto_plan_min_confidence)
    if auto_bucket == "general" or auto_conf < min_conf:
        trace_emit(
            trace_id,
            "semantic_report_rejected",
            bucket=auto_bucket,
            confidence=auto_conf,
            min_confidence=min_conf,
        )
        return None
    semantic_execution = execute_semantic_plan(
        auto_plan,
        tenant_id=tenant_id,
        continue_on_error=bool(settings.assistant_auto_plan_template_continue_on_error),
    )
    if int(semantic_execution.get("summary", {}).get("success_count") or 0) <= 0:
        trace_emit(trace_id, "semantic_report_no_success", bucket=auto_bucket)
        return None
    if stream_callback:
        answer = _compose_semantic_report_stream(
            question=question,
            auto_plan=auto_plan,
            semantic_execution=semantic_execution,
            fallback_answer=fallback_answer,
            stream_callback=stream_callback,
            trace_id=trace_id,
        )
    else:
        answer = compose_semantic_report(
            question=question,
            auto_plan=auto_plan,
            semantic_execution=semantic_execution,
            fallback_answer=fallback_answer,
            trace_id=trace_id,
        )
    if not answer:
        trace_emit(trace_id, "semantic_report_empty", bucket=auto_bucket)
        return None
    trace_emit(trace_id, "semantic_report_hit", bucket=auto_bucket, confidence=auto_conf)
    return {
        "intent": auto_bucket,
        "answer": answer,
        "data": {
            "semantic_dsl": auto_plan.get("dsl"),
            "semantic_query_plan": plan_meta,
            "semantic_error": auto_plan.get("error"),
            "semantic_execution": semantic_execution,
            "semantic_report_enabled": True,
        },
        "source": "semantic_report",
    }


def route_assistant_query(
    question: str,
    tenant_id: str,
    session_id: str | None = None,
    trace_id: str | None = None,
    stream_callback: StreamCallback | None = None,
) -> dict[str, Any]:
    """本地问答/指标释义优先；业务问题先走规则分桶，再尝试 LLM 意图路由，最后兜底通用回答。"""
    text = (question or "").strip()
    sid = str(session_id or "").strip()[:128]
    if not text:
        trace_emit(trace_id, "branch_empty_question")
        empty_answer = (
            "请输入问题。示例：「当前节次实时AI巡课简报」「今日AI巡课汇总」「实时预警简报」"
            "「今日预警汇总」「预警推送阈值」；其它问题也会尽量简短回答。"
        )
        _stream_fixed_answer(stream_callback, empty_answer)
        return {
            "intent": "",
            "answer": empty_answer,
            "data": {},
            "source": "none",
        }
    boundary = _build_boundary_response(question=text, bucket="general", query_options={})
    if boundary is not None:
        trace_emit(
            trace_id,
            "boundary_required",
            boundary_type=str(boundary.get("data", {}).get("clarification", {}).get("boundary_type") or ""),
        )
        _stream_fixed_answer(stream_callback, str(boundary.get("answer") or ""))
        return boundary
    local_answer = _lookup_local_assistant_answer(text)
    if local_answer:
        trace_emit(trace_id, "local_assistant_qa_hit")
        _stream_fixed_answer(stream_callback, local_answer)
        return {
            "intent": "local_assistant_qa",
            "answer": local_answer,
            "data": {"knowledge_base": "assistant_basic_qa"},
            "source": "local",
        }
    kb_answer = _lookup_metric_kb_answer(text)
    if kb_answer:
        trace_emit(trace_id, "metric_kb_hit")
        _stream_fixed_answer(stream_callback, kb_answer)
        return {
            "intent": "metric_kb",
            "answer": kb_answer,
            "data": {"knowledge_base": "metric_definitions"},
            "source": "kb",
        }
    raw_query_options = _extract_query_options(text)
    trace_emit(trace_id, "query_options_raw", **raw_query_options)
    context = _assistant_context_get(tenant_id, sid, trace_id=trace_id)
    context_bucket = str(context.get("bucket") or "") if context else ""
    context_options = context.get("query_options") if isinstance(context, dict) else None
    followup_refine = _is_followup_refine_question(text, raw_query_options)
    trace_emit(
        trace_id,
        "query_followup_detected",
        is_followup=followup_refine,
        has_session=bool(sid),
        context_bucket=context_bucket or None,
    )
    bucket = simple_assistant_bucket(text)
    trace_emit(trace_id, "simple_bucket", bucket=bucket)
    if bucket != "general":
        inherit_context = _should_inherit_context(
            followup_refine=followup_refine,
            resolved_bucket=bucket,
            context_bucket=context_bucket,
        )
        query_options = _merge_query_options(raw_query_options, context_options, inherit_context=inherit_context)
        trace_emit(
            trace_id,
            "query_options_effective",
            by="rule_bucket",
            inherit_context=inherit_context,
            bucket=bucket,
            summary=_summarize_query_options(query_options, top_n=_normalize_top_n(query_options.get("top_n"))),
        )
        clarification = (
            _build_clarification_response(question=text, bucket=bucket, query_options=query_options)
            or _build_llm_clarification_response(
                question=text,
                bucket=bucket,
                query_options=query_options,
                trace_id=trace_id,
            )
        )
        if clarification is not None:
            trace_emit(
                trace_id,
                "clarification_required",
                bucket=bucket,
                missing=",".join(clarification.get("data", {}).get("clarification", {}).get("missing_fields") or []),
                judge=str(clarification.get("data", {}).get("clarification", {}).get("judge") or "rule"),
            )
            _assistant_context_set(
                tenant_id,
                sid,
                bucket=bucket,
                query_options=query_options,
                trace_id=trace_id,
            )
            _stream_fixed_answer(stream_callback, str(clarification.get("answer") or ""))
            return clarification
        if _should_prefer_semantic_report(text, bucket):
            semantic_hit = _try_semantic_report_answer(
                question=text,
                tenant_id=tenant_id,
                query_options=query_options,
                trace_id=trace_id,
                stream_callback=stream_callback,
            )
            if semantic_hit is not None:
                _assistant_context_set(
                    tenant_id,
                    sid,
                    bucket=str(semantic_hit.get("intent") or bucket),
                    query_options=query_options,
                    trace_id=trace_id,
                )
                return semantic_hit
        hit = _try_simple_bucket_answer(
            tenant_id,
            bucket,
            query_options=query_options,
            stream_callback=stream_callback,
            trace_id=trace_id,
        )
        if hit is not None:
            if hit.get("source") == "patrol_api":
                _assistant_context_set(
                    tenant_id,
                    sid,
                    bucket=bucket,
                    query_options=query_options,
                    trace_id=trace_id,
                )
            trace_emit(trace_id, "patrol_api_hit", source=hit.get("source"), route="rule_bucket")
            return hit

    if bucket == "general" and settings.assistant_auto_plan_enabled:
        clarification = (
            _build_clarification_response(question=text, bucket=bucket, query_options=raw_query_options)
            or _build_llm_clarification_response(
                question=text,
                bucket=bucket,
                query_options=raw_query_options,
                trace_id=trace_id,
            )
        )
        if clarification is not None:
            trace_emit(
                trace_id,
                "clarification_required",
                bucket=bucket,
                missing=",".join(clarification.get("data", {}).get("clarification", {}).get("missing_fields") or []),
                judge=str(clarification.get("data", {}).get("clarification", {}).get("judge") or "rule"),
            )
            _stream_fixed_answer(stream_callback, str(clarification.get("answer") or ""))
            return clarification
        if settings.assistant_auto_plan_template_execute_enabled and settings.assistant_semantic_report_enabled:
            semantic_hit = _try_semantic_report_answer(
                question=text,
                tenant_id=tenant_id,
                query_options=raw_query_options,
                trace_id=trace_id,
                stream_callback=stream_callback,
            )
            if semantic_hit is not None:
                _assistant_context_set(
                    tenant_id,
                    sid,
                    bucket=str(semantic_hit.get("intent") or "general"),
                    query_options=raw_query_options,
                    trace_id=trace_id,
                )
                return semantic_hit
        auto_plan = preview_assistant_auto_plan(text, tenant_id, query_options=raw_query_options)
        plan_meta = auto_plan.get("query_plan") if isinstance(auto_plan, dict) else {}
        auto_bucket = str((plan_meta or {}).get("execute_bucket") or "general")
        auto_conf = _safe_float((plan_meta or {}).get("confidence"), 0.0)
        trace_emit(
            trace_id,
            "auto_plan_candidate",
            bucket=auto_bucket,
            confidence=auto_conf,
            plan_intent=(plan_meta or {}).get("intent"),
            templates=",".join((plan_meta or {}).get("template_ids") or []),
        )
        min_conf = float(settings.assistant_auto_plan_min_confidence)
        if auto_bucket != "general" and auto_conf >= min_conf:
            inherit_context = _should_inherit_context(
                followup_refine=followup_refine,
                resolved_bucket=auto_bucket,
                context_bucket=context_bucket,
            )
            auto_options = _merge_query_options(raw_query_options, context_options, inherit_context=inherit_context)
            effective_auto_plan = preview_assistant_auto_plan(text, tenant_id, query_options=auto_options)
            effective_plan_meta = (
                effective_auto_plan.get("query_plan") if isinstance(effective_auto_plan.get("query_plan"), dict) else {}
            )
            trace_emit(
                trace_id,
                "query_options_effective",
                by="auto_plan",
                inherit_context=inherit_context,
                bucket=auto_bucket,
                summary=_summarize_query_options(auto_options, top_n=_normalize_top_n(auto_options.get("top_n"))),
            )
            auto_stream_callback = None if settings.assistant_auto_plan_template_execute_enabled else stream_callback
            auto_hit = _try_simple_bucket_answer(
                tenant_id,
                auto_bucket,
                query_options=auto_options,
                stream_callback=auto_stream_callback,
                trace_id=trace_id,
            )
            if auto_hit is not None:
                semantic_execution: dict[str, Any] | None = None
                if settings.assistant_auto_plan_template_execute_enabled:
                    semantic_execution = execute_semantic_plan(
                        effective_auto_plan,
                        tenant_id=tenant_id,
                        continue_on_error=bool(settings.assistant_auto_plan_template_continue_on_error),
                    )
                    if stream_callback:
                        semantic_report = _compose_semantic_report_stream(
                            question=text,
                            auto_plan=effective_auto_plan,
                            semantic_execution=semantic_execution,
                            fallback_answer=str(auto_hit.get("answer") or ""),
                            stream_callback=stream_callback,
                            trace_id=trace_id,
                        )
                    else:
                        semantic_report = compose_semantic_report(
                            question=text,
                            auto_plan=effective_auto_plan,
                            semantic_execution=semantic_execution,
                            fallback_answer=str(auto_hit.get("answer") or ""),
                            trace_id=trace_id,
                        )
                    if semantic_report:
                        auto_hit["answer"] = semantic_report
                if isinstance(auto_hit.get("data"), dict):
                    auto_hit["data"]["semantic_dsl"] = effective_auto_plan.get("dsl")
                    auto_hit["data"]["semantic_query_plan"] = effective_plan_meta
                    auto_hit["data"]["semantic_error"] = effective_auto_plan.get("error")
                    if semantic_execution is not None:
                        auto_hit["data"]["semantic_execution"] = semantic_execution
                        auto_hit["data"]["semantic_report_enabled"] = bool(settings.assistant_semantic_report_enabled)
                if auto_hit.get("source") == "patrol_api":
                    _assistant_context_set(
                        tenant_id,
                        sid,
                        bucket=auto_bucket,
                        query_options=auto_options,
                        trace_id=trace_id,
                    )
                trace_emit(
                    trace_id,
                    "patrol_api_hit",
                    source=auto_hit.get("source"),
                    route="auto_plan",
                    bucket=auto_bucket,
                    confidence=auto_conf,
                )
                return auto_hit
        else:
            trace_emit(
                trace_id,
                "auto_plan_rejected",
                bucket=auto_bucket,
                confidence=auto_conf,
                min_confidence=min_conf,
            )

    llm_route = _classify_bucket_with_llm(text, trace_id=trace_id)
    if llm_route:
        llm_bucket = str(llm_route.get("bucket") or "general")
        llm_confidence = _safe_float(llm_route.get("confidence"), 0.0)
        if llm_bucket != "general" and llm_confidence >= float(settings.assistant_intent_llm_min_confidence):
            inherit_context = _should_inherit_context(
                followup_refine=followup_refine,
                resolved_bucket=llm_bucket,
                context_bucket=context_bucket,
            )
            query_options = _merge_query_options(raw_query_options, context_options, inherit_context=inherit_context)
            trace_emit(
                trace_id,
                "query_options_effective",
                by="llm_bucket",
                inherit_context=inherit_context,
                bucket=llm_bucket,
                summary=_summarize_query_options(query_options, top_n=_normalize_top_n(query_options.get("top_n"))),
            )
            llm_hit = _try_simple_bucket_answer(
                tenant_id,
                llm_bucket,
                query_options=query_options,
                stream_callback=stream_callback,
                trace_id=trace_id,
            )
            if llm_hit is not None:
                if isinstance(llm_hit.get("data"), dict):
                    llm_hit["data"]["intent_route"] = llm_route
                if llm_hit.get("source") == "patrol_api":
                    _assistant_context_set(
                        tenant_id,
                        sid,
                        bucket=llm_bucket,
                        query_options=query_options,
                        trace_id=trace_id,
                    )
                trace_emit(
                    trace_id,
                    "patrol_api_hit",
                    source=llm_hit.get("source"),
                    route="llm_intent",
                    bucket=llm_bucket,
                    confidence=llm_confidence,
                )
                return llm_hit
        else:
            trace_emit(
                trace_id,
                "llm_intent_rejected",
                bucket=llm_bucket,
                confidence=llm_confidence,
                min_confidence=float(settings.assistant_intent_llm_min_confidence),
            )
    if followup_refine and context_bucket:
        fallback_options = _merge_query_options(raw_query_options, context_options, inherit_context=True)
        trace_emit(
            trace_id,
            "query_options_effective",
            by="context_fallback",
            inherit_context=True,
            bucket=context_bucket,
            summary=_summarize_query_options(fallback_options, top_n=_normalize_top_n(fallback_options.get("top_n"))),
        )
        ctx_hit = _try_simple_bucket_answer(
            tenant_id,
            context_bucket,
            query_options=fallback_options,
            stream_callback=stream_callback,
            trace_id=trace_id,
        )
        if ctx_hit is not None:
            if isinstance(ctx_hit.get("data"), dict):
                ctx_hit["data"]["intent_route"] = {
                    "bucket": context_bucket,
                    "confidence": 0.51,
                    "reason": "followup_context_fallback",
                }
            if ctx_hit.get("source") == "patrol_api":
                _assistant_context_set(
                    tenant_id,
                    sid,
                    bucket=context_bucket,
                    query_options=fallback_options,
                    trace_id=trace_id,
                )
            trace_emit(trace_id, "patrol_api_hit", source=ctx_hit.get("source"), route="context_fallback")
            return ctx_hit
    trace_emit(trace_id, "llm_general_path")
    trace_emit(trace_id, "llm_blocking_before_urlopen", max_tokens=220)
    general_answer = _general_llm_answer(text, trace_id=trace_id, stream_callback=stream_callback)
    trace_emit(
        trace_id,
        "llm_blocking_after_urlopen",
        has_answer=bool(general_answer),
        answer_chars=len(general_answer or ""),
    )
    if general_answer:
        return {"intent": "general", "answer": general_answer, "data": {}, "source": "llm"}
    _stream_fixed_answer(stream_callback, ASSISTANT_LLM_FAILED_HINT)
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


def _coerce_delta_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        chunks: list[str] = []
        for item in value:
            if isinstance(item, dict):
                chunks.append(str(item.get("text") or item.get("content") or ""))
            elif item is not None:
                chunks.append(str(item))
        return "".join(chunks)
    return str(value)


def _extract_chat_completion_delta(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        choice = choices[0] if isinstance(choices[0], dict) else {}
        delta = choice.get("delta")
        if isinstance(delta, dict):
            text = _coerce_delta_text(delta.get("content"))
            if text:
                return text
        message = choice.get("message")
        if isinstance(message, dict):
            text = _coerce_delta_text(message.get("content"))
            if text:
                return text
        text = _coerce_delta_text(choice.get("text"))
        if text:
            return text
    delta = payload.get("delta")
    if isinstance(delta, dict):
        text = _coerce_delta_text(delta.get("content"))
        if text:
            return text
    return _coerce_delta_text(payload.get("content"))


def _iter_chat_completion_stream(
    payload: dict[str, object],
    *,
    trace_id: str | None,
    trace_prefix: str,
) -> Iterator[str]:
    stream_payload = dict(payload)
    stream_payload["stream"] = True
    req = request.Request(
        f"{settings.llm_base_url.rstrip('/')}/chat/completions",
        data=json.dumps(stream_payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.llm_api_key}",
        },
        method="POST",
    )
    trace_emit(trace_id, f"{trace_prefix}_stream_begin", timeout_sec=settings.llm_timeout_sec)
    with request.urlopen(req, timeout=settings.llm_timeout_sec) as resp:
        trace_emit(trace_id, f"{trace_prefix}_stream_connected", http_status=getattr(resp, "status", None))
        for raw_line in resp:
            if not raw_line:
                continue
            line = raw_line.decode("utf-8", errors="ignore").strip()
            if not line or line.startswith(":") or line.startswith("event:"):
                continue
            if line.startswith("data:"):
                line = line[5:].strip()
            if not line:
                continue
            if line == "[DONE]":
                break
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            delta = _extract_chat_completion_delta(item)
            if delta:
                yield delta


def _stream_chat_completion(
    payload: dict[str, object],
    *,
    stream_callback: StreamCallback,
    trace_id: str | None,
    trace_prefix: str,
) -> str | None:
    parts: list[str] = []
    try:
        for delta in _iter_chat_completion_stream(payload, trace_id=trace_id, trace_prefix=trace_prefix):
            parts.append(delta)
            stream_callback(delta)
    except (error.URLError, TimeoutError, json.JSONDecodeError, ValueError, KeyError, IndexError, TypeError) as exc:
        trace_emit(
            trace_id,
            f"{trace_prefix}_stream_failed",
            error_type=type(exc).__name__,
            partial_chars=len("".join(parts)),
        )
    raw_content = "".join(parts)
    content = raw_content.strip()
    if content:
        trace_emit(trace_id, f"{trace_prefix}_stream_done", content_len=len(content))
        return raw_content
    return None


def _summarize(
    task: str,
    data: dict[str, Any],
    fallback: str,
    *,
    stream_callback: StreamCallback | None = None,
    trace_id: str | None = None,
) -> str:
    prompt = (
        "你是高校AI助教AI巡课助手，请基于给定结构化数据生成简洁专业的中文简报，不要编造不存在的数据。\n"
        f"任务: {task}\n"
        f"数据: {json.dumps(data, ensure_ascii=False, default=str)}\n"
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
    if stream_callback:
        content = _stream_chat_completion(
            payload,
            stream_callback=stream_callback,
            trace_id=trace_id,
            trace_prefix="summarize_llm",
        )
        if content:
            return content
        _stream_fixed_answer(stream_callback, fallback)
        return fallback
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


def _general_llm_answer(
    question: str,
    trace_id: str | None = None,
    *,
    stream_callback: StreamCallback | None = None,
) -> str | None:
    llm_url = f"{settings.llm_base_url.rstrip('/')}/chat/completions"
    payload: dict[str, object] = {
        "model": settings.llm_model,
        "messages": _general_llm_messages(question),
        "temperature": 0.35,
        "max_tokens": 220,
    }
    merge_llm_chat_template_kwargs(payload)
    if stream_callback:
        streamed = _stream_chat_completion(
            payload,
            stream_callback=stream_callback,
            trace_id=trace_id,
            trace_prefix="llm_general",
        )
        if streamed:
            return streamed
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
        if content and stream_callback:
            _stream_fixed_answer(stream_callback, content)
        return content or None
    except (error.URLError, TimeoutError, KeyError, IndexError, ValueError) as ex:
        trace_emit(
            trace_id,
            "llm_urlopen_failed",
            error_type=type(ex).__name__,
            error=redact_sensitive_text(str(ex), max_len=240),
        )
        return None
