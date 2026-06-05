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
    llm_base_url: str = "http://10.80.5.197:8855/v1"
    llm_model: str = "qwen3-8b"
    llm_api_key: str = "EMPTY"
    llm_timeout_sec: int = 20
    # Qwen3 / vLLM 等：False 时在请求里带 chat_template_kwargs 关闭思考（由推理侧不生成思考，非客户端剥除）
    llm_enable_thinking: bool = False
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
