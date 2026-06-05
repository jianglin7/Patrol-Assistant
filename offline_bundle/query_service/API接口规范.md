# Query Service API 接口规范

## 1. 接口目标

`query-service` 只做受控查询，不提供自由 SQL 执行能力。

调用方只需要传：

- `template_id`
- `tenant_id`
- `user_id`
- `params`

服务内部完成：

- 参数默认值补齐
- 参数类型校验
- `tenant_id` 注入
- 模板查询
- 审计日志

## 2. 健康检查

### 请求

```http
GET /health
```

### 响应

```json
{
  "status": "ok",
  "service": "patrol-assistant"
}
```

## 3. 执行模板查询

### 请求

```http
POST /api/query/execute
Content-Type: application/json
```

### 请求体

```json
{
  "request_id": "optional-request-id",
  "user_id": "u001",
  "tenant_id": "tenant_a",
  "template_id": "T06",
  "params": {
    "today": "2026-04-21",
    "now_time": "2026-04-21 18:00:00"
  }
}
```

### 字段说明

| 字段 | 必填 | 说明 |
|---|---|---|
| `request_id` | 否 | 外部请求唯一标识，不传则服务自动生成 |
| `user_id` | 否 | 当前查询用户，用于审计 |
| `tenant_id` | 是 | 租户编号 |
| `template_id` | 是 | 模板编号，例如 `T01` |
| `params` | 否 | 模板运行参数 |

## 4. 成功响应

```json
{
  "request_id": "7e4c4dbac2974f0a9e6d5e4f9121d1ff",
  "success": true,
  "template_id": "T06",
  "template_name": "今日已结束课程核心均值",
  "data": [
    {
      "finished_course_count": 86,
      "today_avg_att_percent": 92.15,
      "today_avg_front_full_percent": 68.30,
      "today_avg_rise_percent": 79.55
    }
  ],
  "meta": {
    "row_count": 1,
    "executed_at": "2026-04-21T18:12:31",
    "normalized_params": {
      "tenant_id": "tenant_a",
      "today": "2026-04-21",
      "now_time": "2026-04-21 18:00:00"
    },
    "result_schema": {
      "finished_course_count": "integer",
      "today_avg_att_percent": "number",
      "today_avg_front_full_percent": "number",
      "today_avg_rise_percent": "number"
    }
  }
}
```

## 5. 失败响应

### 参数错误

```json
{
  "detail": {
    "request_id": "1d4f5b25d3aa4b0ca1de7f5ddf43a5d4",
    "success": false,
    "error_code": "INVALID_PARAM",
    "error_msg": "param `today` must be in YYYY-MM-DD format"
  }
}
```

### 模板不存在

```json
{
  "detail": {
    "request_id": "79b7595f39974331b392ec6ae93228b3",
    "success": false,
    "error_code": "TEMPLATE_NOT_FOUND",
    "error_msg": "template `T99` is not enabled for tenant `tenant_a`"
  }
}
```

## 6. 推荐模板映射

| 模板ID | 说明 | 常见问题 |
|---|---|---|
| `T01` | 当前节次 | 现在第几节？ |
| `T02` | 当前在课课堂数 | 现在有多少教室在上课？ |
| `T03` | 当前核心三率 | 当前平均到课率是多少？ |
| `T04` | 当前重点关注课堂数 | 当前重点关注课堂有多少？ |
| `T06` | 今日已结束课程核心均值 | 今天课堂平均到课率是多少？ |
| `T08` | 今日重点关注占比 | 今日重点关注课堂占比多少？ |
| `T09` | 实时预警课堂占比 | 当前预警课堂占比多少？ |
| `T10` | 实时整体风险等级 | 当前整体风险等级是什么？ |
| `T11` | 实时预警类型分布 | 当前主要是什么预警？ |
| `T13` | 今日预警占比与风险 | 今日风险整体怎么样？ |
