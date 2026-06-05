from typing import Any

from pydantic import BaseModel, Field


class ExecuteRequest(BaseModel):
    request_id: str | None = Field(default=None, description="外部请求ID")
    user_id: str | None = Field(default=None, description="当前用户ID")
    tenant_id: str = Field(description="租户编号")
    template_id: str = Field(description="查询模板ID")
    params: dict[str, Any] = Field(default_factory=dict, description="模板参数")


class ExecuteMeta(BaseModel):
    row_count: int
    executed_at: str
    normalized_params: dict[str, Any]
    result_schema: dict[str, Any] | None = None


class ExecuteResponse(BaseModel):
    request_id: str
    success: bool
    template_id: str
    template_name: str
    data: list[dict[str, Any]]
    meta: ExecuteMeta
