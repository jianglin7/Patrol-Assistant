from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_name: str = "patrol-assistant"
    app_env: str = "dev"
    app_port: int = 8000
    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_database: str = "jy_application_digital_patrol"
    mysql_charset: str = "utf8mb4"
    # 课表库（如 jy_course_he）连接；不填则复用业务库配置，建议使用只读账号
    schedule_mysql_host: str | None = None
    schedule_mysql_port: int | None = None
    schedule_mysql_user: str | None = None
    schedule_mysql_password: str | None = None
    schedule_mysql_database: str | None = None
    schedule_mysql_charset: str | None = None
    # 课表库租户编码映射：可配置固定 tenant_org_code，留空则默认使用 tenant_id
    schedule_tenant_org_code: str | None = None
    # 控制库（模板注册/审计日志）连接；留空时默认复用业务库配置
    control_mysql_host: str | None = None
    control_mysql_port: int | None = None
    control_mysql_user: str | None = None
    control_mysql_password: str | None = None
    control_mysql_database: str | None = None
    control_mysql_charset: str | None = None
    # true 时启用数据库只读保护：仅允许执行只读 SQL，并且不写审计日志
    db_readonly: bool = False
    # AI巡课阈值（可按租户运营规则调整）
    patrol_focus_attendance_lt: float = 90
    patrol_focus_front_full_lt: float = 65
    patrol_focus_rise_lt: float = 65
    patrol_vitality_attendance_gte: float = 95
    patrol_vitality_front_full_gte: float = 80
    patrol_vitality_rise_gte: float = 75
    llm_base_url: str = "http://10.80.5.197:8855/v1"
    llm_model: str = "qwen3-8b"
    llm_api_key: str = "EMPTY"
    llm_timeout_sec: int = 20
    # Qwen3 / vLLM 等：False 时在请求里带 chat_template_kwargs 关闭思考（由推理侧不生成思考，非客户端剥除）
    llm_enable_thinking: bool = False
    # 助手路由增强：先用 LLM 做意图分类（JSON），再决定是否走业务数据简报
    assistant_intent_llm_enabled: bool = True
    assistant_intent_llm_min_confidence: float = 0.55
    # 助手查询参数：TopN 默认与上限
    assistant_default_top_n: int = 5
    assistant_max_top_n: int = 20
    # 追问上下文：按会话缓存上一次业务查询条件（TopN/学院/节次/学段）用于“改成Top3”这类追问
    assistant_context_enabled: bool = True
    assistant_context_ttl_sec: int = 1800
    assistant_context_max_entries: int = 500
    # 自动化取数规划器：配置驱动的 DSL/QueryPlan 分支
    assistant_auto_plan_enabled: bool = True
    assistant_auto_plan_min_confidence: float = 0.45
    assistant_auto_plan_resource_dir: str = "resources/assistant_semantic"
    assistant_auto_plan_template_execute_enabled: bool = False
    assistant_auto_plan_template_continue_on_error: bool = True
    # 控制库未注册语义模板时，使用代码内置只读白名单模板兜底
    assistant_builtin_template_fallback_enabled: bool = True
    # 语义取数结果报告生成：把 QueryPlan 执行结果交给 LLM 组织成差异化回答
    assistant_semantic_report_enabled: bool = True
    assistant_semantic_report_max_steps: int = 6
    assistant_semantic_report_max_rows_per_step: int = 5
    assistant_semantic_report_max_tokens: int = 900
    # 信息不足或实体角色不明确时，优先追问确认，避免按错误口径硬答
    assistant_clarification_enabled: bool = True
    assistant_clarification_llm_enabled: bool = True
    assistant_clarification_llm_min_confidence: float = 0.62
    assistant_clarification_llm_max_tokens: int = 420
    assistant_clarification_llm_timeout_sec: float = 5
    # 业务简报结果短缓存（减少同口径重复查询压力）
    assistant_result_cache_enabled: bool = True
    assistant_result_cache_ttl_sec: int = 20
    assistant_result_cache_max_entries: int = 1000
    # 流式体验可调（生产可下调，减少“逐字慢输出”）
    assistant_stream_thinking_delay_sec: float = 0.45
    assistant_stream_char_delay_sec: float = 0.002
    assistant_stream_preset_thinking_delay_sec: float = 0.9
    assistant_stream_preset_char_delay_sec: float = 0.002
    assistant_stream_chunk_size: int = 16
    assistant_stream_preset_chunk_size: int = 18
    # 逗号分隔的浏览器 Origin，用于第三方页面用 fetch 直连本服务 API；留空则不启用 CORS。开发可填 `*`
    cors_allow_origins: str = ""
    # 未传 tenant_id 时AI巡课/助手接口使用的租户（仅服务端与可选 URL 参数，页面默认不在地址栏写死）
    assistant_default_tenant_id: str = "demo"
    # 为 true 时记录助手提问各阶段耗时（内存环形缓冲），供 GET /api/debug/assistant-traces 查询；生产建议关闭
    assistant_trace_enabled: bool = False
    assistant_trace_max_entries: int = 200

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()


def merge_llm_chat_template_kwargs(body: dict[str, object]) -> dict[str, object]:
    """合并 vLLM/OpenAI 兼容接口的 chat 模板参数（就地修改并返回 body）。"""
    body["chat_template_kwargs"] = {"enable_thinking": settings.llm_enable_thinking}
    return body
