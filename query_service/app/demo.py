from __future__ import annotations

from datetime import datetime
import random
from typing import Any


def ask_demo_assistant(question: str) -> dict[str, Any]:
    text = (question or "").strip()
    if not text:
        return {
            "success": False,
            "intent": "invalid",
            "answer": "请输入想查询的内容，例如：查询近两周学情异常课程。",
            "data": [],
            "generated_at": _now(),
        }

    if any(keyword in text for keyword in ("实时课堂", "正在上课", "实时巡查", "实时巡课")):
        return _realtime_patrol_response(text)

    if any(keyword in text for keyword in ("非课表", "今日已经上课", "今日已上课", "今日课堂巡查")):
        return _daily_patrol_response(text)

    if any(keyword in text for keyword in ("实时课堂AI预警", "实时预警", "预警占比", "预警课堂类型")):
        return _realtime_warning_response(text)

    if any(keyword in text for keyword in ("今日课堂AI预警", "今日预警", "已结束上课", "今日已巡查")):
        return _daily_warning_response(text)

    if any(keyword in text for keyword in ("消息推送", "企业微信", "微信", "阈值", "多渠道")):
        return _push_response(text)

    if any(keyword in text for keyword in ("视频打点", "时间戳", "PPT缩略图", "时间轴", "录播")):
        return _video_timeline_response(text)

    if any(keyword in text for keyword in ("评价", "评教", "教师", "老师", "授课")):
        return _evaluation_response(text)

    if any(keyword in text for keyword in ("异常", "预警", "未达标", "风险", "干预")):
        return _anomaly_response(text)

    if any(keyword in text for keyword in ("统计", "对比", "概览", "分布", "占比", "趋势", "课堂数量", "到课率")):
        return _stats_response(text)

    if "top" in text.lower():
        return _anomaly_response(text)

    return {
        "success": True,
        "intent": "guide",
        "answer": (
            "我可以直接给出结论型回答，支持这些方向：\n"
            "1) 课表时间段/非课表时间段智能巡课简报\n"
            "2) 实时课堂与今日课堂AI预警分析\n"
            "3) 预警消息智能推送与阈值策略\n"
            "4) 教师/课程教学评价记录分析\n"
            "5) 录播课堂视频打点与PPT时间轴联动"
        ),
        "data": [],
        "generated_at": _now(),
    }


def _anomaly_response(question: str) -> dict[str, Any]:
    rows = [
        {
            "course_name": "数据结构",
            "college": "计算机学院",
            "teacher": "陈志远",
            "warning_type": "出勤率连续下降",
            "warning_score": 91,
        },
        {
            "course_name": "高等数学A",
            "college": "信息工程学院",
            "teacher": "刘思涵",
            "warning_type": "过程考核参与率偏低",
            "warning_score": 87,
        },
        {
            "course_name": "大学英语II",
            "college": "外国语学院",
            "teacher": "赵明哲",
            "warning_type": "课堂互动显著下降",
            "warning_score": 84,
        },
    ]
    high_risk = sorted(rows, key=lambda item: item["warning_score"], reverse=True)
    top = high_risk[0]
    second_focus = "、".join(item["course_name"] for item in high_risk[1:])
    issue_mix = "，".join(item["warning_type"] for item in high_risk)
    org_hint = _extract_org_hint(question)
    org_prefix = f"结合{org_hint}的查询口径，" if org_hint else ""
    tone_variants = [
        (
            "建议先做分层处置：高风险课程本周内完成师生访谈与个性化学业帮扶，中风险课程按周追踪出勤和课堂互动曲线，"
            "并在下周教务例会上回看干预效果。"
        ),
        (
            "建议按“课程-教师-班级”三级联动推进：先锁定高风险课程，再由任课教师与辅导员协同复盘，"
            "用一周时间观察预警指标是否回落。"
        ),
    ]

    return {
        "success": True,
        "intent": "学情异常课程查询",
        "answer": (
            f"已完成“{question}”的分析，{org_prefix}当前识别到 3 门需要优先跟进的课程。\n"
            f"从风险强度看，{top['college']}《{top['course_name']}》最值得先处理（预警分值 {top['warning_score']}），"
            f"其余重点课程为 {second_focus}。\n"
            f"异常信号主要来自：{issue_mix}。这类组合通常意味着学习投入与课堂参与同步下滑。\n"
            f"{random.choice(tone_variants)}"
        ),
        "data": rows,
        "generated_at": _now(),
    }


def _stats_response(question: str) -> dict[str, Any]:
    rows = [
        {"scope": "本科课程", "course_count": 428, "warning_rate": "12.6%", "avg_completion_rate": "89.1%"},
        {"scope": "研究生课程", "course_count": 167, "warning_rate": "8.9%", "avg_completion_rate": "93.4%"},
    ]
    undergrad = rows[0]
    graduate = rows[1]
    warn_gap = round(float(undergrad["warning_rate"].rstrip("%")) - float(graduate["warning_rate"].rstrip("%")), 1)
    completion_gap = round(
        float(graduate["avg_completion_rate"].rstrip("%")) - float(undergrad["avg_completion_rate"].rstrip("%")), 1
    )
    org_hint = _extract_org_hint(question)
    org_prefix = f"按{org_hint}口径看，" if org_hint else ""

    strategy_variants = [
        "建议将治理动作拆成两条线：一条做预警课程周跟踪，另一条做学院层面的过程指标复盘（出勤、过程考核、互动），用 2-3 周观察预警率是否回落。",
        "建议先聚焦本科基础课高风险班级，按周看预警率和课堂参与度，再按学院维度复盘教学组织策略。",
    ]
    return {
        "success": True,
        "intent": "学情统计分析",
        "answer": (
            f"“{question}”已完成统计归因分析。\n"
            f"{org_prefix}本科课程预警率为 {undergrad['warning_rate']}，比研究生高 {warn_gap} 个百分点；"
            f"研究生平均完成率比本科高 {completion_gap} 个百分点。\n"
            "这说明当前波动主要集中在本科阶段，尤其是基础课和大班课场景，问题不在单门课程而在教学组织与学习节奏匹配。\n"
            f"{random.choice(strategy_variants)}"
        ),
        "data": rows,
        "generated_at": _now(),
    }


def _realtime_patrol_response(question: str) -> dict[str, Any]:
    section = "第3节"
    classroom_count = 36
    round_no = random.randint(4, 7)
    attend = round(random.uniform(92.4, 95.8), 1)
    front_row = round(random.uniform(74.2, 81.3), 1)
    look_up = round(random.uniform(68.0, 76.5), 1)
    focus_count = random.randint(4, 8)
    high_vitality = random.randint(11, 16)
    answer = (
        f"已生成实时AI巡查简报（问题：{question}）。\n"
        f"当前节次：{section}，正在上课课堂数量：{classroom_count}，AI巡查轮次：第 {round_no} 轮。\n"
        f"课堂状态均值：平均到课率 {attend}%，平均前排满座率 {front_row}%，平均抬头率 {look_up}%。\n"
        f"需重点关注课堂数量：{focus_count}，活力值较高课堂数量：{high_vitality}。\n"
        "结论：整体课堂运行稳定，但个别课程存在参与度波动，建议对重点关注课堂启动高频复查。"
    )
    return {"success": True, "intent": "课表时间段智能巡课", "answer": answer, "data": [], "generated_at": _now()}


def _daily_patrol_response(question: str) -> dict[str, Any]:
    attend = round(random.uniform(90.8, 93.9), 1)
    front_row = round(random.uniform(70.5, 77.4), 1)
    look_up = round(random.uniform(65.2, 73.8), 1)
    activity = random.randint(820, 980)
    focus_count = random.randint(12, 18)
    high_vitality = random.randint(28, 36)
    answer = (
        f"已完成今日非课表时段AI巡课汇总（问题：{question}）。\n"
        f"今日课堂平均到课率 {attend}%，平均前排满座率 {front_row}%，平均抬头率 {look_up}%。\n"
        f"课堂活动数据累计 {activity} 次（提问、互动、随堂反馈等），需重点关注课堂 {focus_count} 个，活力值较高课堂 {high_vitality} 个。\n"
        "结论：今日课堂活跃度总体良好，但基础课大班场景波动更明显，建议在次日排课时优先安排教务回访。"
    )
    return {"success": True, "intent": "非课表时间段智能巡课", "answer": answer, "data": [], "generated_at": _now()}


def _realtime_warning_response(question: str) -> dict[str, Any]:
    round_progress = f"{random.randint(58, 86)}%"
    section = random.choice(("第2节", "第3节", "第4节"))
    class_count = random.randint(30, 42)
    warning_count = random.randint(4, 9)
    warning_ratio = round(warning_count * 100 / class_count, 1)
    risk = random.choice(("中", "中高"))
    warning_types = random.choice(("到课率偏低、互动不足", "抬头率下降、课堂活力偏弱", "前排空置率高、参与波动"))
    answer = (
        f"实时课堂AI预警已生成（问题：{question}）。\n"
        f"实时巡查轮次进度：{round_progress}，上课节次：{section}，当前上课课堂：{class_count} 个。\n"
        f"预警课堂：{warning_count} 个，占比 {warning_ratio}% ，整体预警风险等级：{risk}。\n"
        f"预警课堂类型：{warning_types}。\n"
        "结论：当前风险可控但有上行迹象，建议先对风险课堂做即时提醒并加密下一轮巡查。"
    )
    return {"success": True, "intent": "实时课堂AI预警", "answer": answer, "data": [], "generated_at": _now()}


def _daily_warning_response(question: str) -> dict[str, Any]:
    inspected = random.randint(150, 210)
    warning = random.randint(18, 28)
    ratio = round(warning * 100 / inspected, 1)
    risk = random.choice(("中", "中高"))
    types = random.choice(("到课率偏低、课堂互动不足", "前排满座率下降、抬头率偏低", "连续两轮活力值下滑"))
    answer = (
        f"今日课堂AI预警汇总已完成（问题：{question}）。\n"
        f"今日已巡查课堂：{inspected} 个，预警课堂：{warning} 个，占比 {ratio}% 。\n"
        f"整体预警风险等级：{risk}，主要预警类型：{types}。\n"
        "结论：今日风险课堂主要集中在大班基础课，建议将预警清单同步至学院教学秘书与辅导员，形成日闭环。"
    )
    return {"success": True, "intent": "今日课堂AI预警", "answer": answer, "data": [], "generated_at": _now()}


def _push_response(question: str) -> dict[str, Any]:
    threshold = random.choice(("抬头率低于 62%", "到课率低于 88%", "活力值连续两轮下降"))
    channels = "企业微信、微信、校内消息平台"
    answer = (
        f"AI预警消息推送策略已匹配（问题：{question}）。\n"
        f"当前触发阈值策略：{threshold}；命中后自动向授课教师与辅导员发送即时提醒。\n"
        f"消息分发渠道：{channels}，并支持按学院/课程类型自定义阈值。\n"
        "结论：该机制可以把“发现风险”到“责任人响应”压缩到分钟级，适合持续运行的精准预警管理。"
    )
    return {"success": True, "intent": "AI预警消息智能推送", "answer": answer, "data": [], "generated_at": _now()}


def _video_timeline_response(question: str) -> dict[str, Any]:
    points = random.randint(22, 36)
    cover = random.randint(44, 58)
    answer = (
        f"视频打点分析已生成（问题：{question}）。\n"
        f"本次录播课堂自动识别关键讲解节点 {points} 个，并生成对应时间戳与PPT缩略图时间轴。\n"
        f"每个缩略图同步展示该页核心要点，点击后可直接跳转至对应讲解时间点，实现PPT与视频精准对齐。\n"
        f"当前已覆盖 {cover} 页课件内容，支持快速回看重点知识段落与课堂讲解结构。\n"
        "结论：该功能可显著提升教学复盘效率，尤其适用于督导抽检与学生课后复习。"
    )
    return {"success": True, "intent": "视频打点", "answer": answer, "data": [], "generated_at": _now()}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _evaluation_response(question: str) -> dict[str, Any]:
    teacher_records = {
        "陈志远": {"course": "数据结构", "score": 4.7, "positive": "课堂组织清晰、案例讲解到位", "risk": "后半程互动下降"},
        "刘思涵": {"course": "高等数学A", "score": 4.5, "positive": "板书规范、知识点拆解细致", "risk": "部分班级跟进节奏偏慢"},
        "赵明哲": {"course": "大学英语II", "score": 4.6, "positive": "课堂氛围好、任务引导明确", "risk": "个别班级参与度波动"},
    }
    course_records = {
        "数据结构": {"avg": 4.7, "trend": "近3周稳定", "highlight": "实践环节认可度高", "risk": "到课率小幅下滑"},
        "高等数学A": {"avg": 4.4, "trend": "近2周回升", "highlight": "教学节奏优化后满意度提升", "risk": "基础薄弱学生反馈压力偏大"},
        "大学英语II": {"avg": 4.6, "trend": "整体平稳", "highlight": "互动式教学评价较高", "risk": "晚间班次专注度下降"},
    }

    target_teacher = next((name for name in teacher_records if name in question), "")
    target_course = next((name for name in course_records if name in question), "")

    if target_teacher:
        item = teacher_records[target_teacher]
        answer = (
            f"已检索到 {target_teacher} 的教学评价记录。\n"
            f"该教师当前主讲《{item['course']}》，综合评价均分 {item['score']}（5分制），总体处于学院前列。\n"
            f"正向反馈主要集中在：{item['positive']}；需要关注的点是：{item['risk']}。\n"
            "建议继续保持优势教学方式，同时在课堂后半段增加点名互动或随堂测验，稳定学生参与质量。"
        )
    elif target_course:
        item = course_records[target_course]
        answer = (
            f"已完成《{target_course}》教学评价记录分析。\n"
            f"当前课程综合评价均分 {item['avg']}，评价趋势为：{item['trend']}。\n"
            f"主要亮点：{item['highlight']}；当前风险信号：{item['risk']}。\n"
            "建议按班级分层复盘课堂节奏，并与学情预警数据联动，优先干预参与度连续下滑的班级。"
        )
    else:
        fallback_teacher = random.choice(list(teacher_records.keys()))
        item = teacher_records[fallback_teacher]
        answer = (
            f"“{question}”已完成评价维度分析。\n"
            f"当前可直接输出教师与课程评价结论，例如：{fallback_teacher}《{item['course']}》综合评价 {item['score']}，"
            f"优势为“{item['positive']}”，需关注“{item['risk']}”。\n"
            "如果你指定教师姓名或课程名，我可以进一步给出该对象的阶段趋势和改进建议。"
        )

    return {
        "success": True,
        "intent": "教学评价记录分析",
        "answer": answer,
        "data": [],
        "generated_at": _now(),
    }


def _extract_org_hint(question: str) -> str:
    org_keywords = ("学院", "本科", "研究生", "大一", "大二", "大三", "计算机", "信息工程", "外国语")
    for key in org_keywords:
        if key in question:
            return key
    return ""
