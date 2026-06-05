sequenceDiagram
    participant U as 用户/前端(/assistant)
    participant M as main.py
    participant P as patrol_api.py
    participant DB as MySQL
    participant L as LLM(/chat/completions)

    U->>M: POST /api/assistant/ask-stream {question, tenant_id}
    M->>M: assistant_ask_stream()
    M->>U: NDJSON meta
    M->>P: asyncio.to_thread(route_assistant_query)

    P->>P: route_assistant_query(question, tenant_id)

    alt 空问题
        P-->>M: {intent:"", source:"none", answer:引导文案}
    else 指标释义命中
        P->>P: _lookup_metric_kb_answer()
        P-->>M: {intent:"metric_kb", source:"kb", answer:指标释义}
    else 关键词命中业务桶
        P->>P: simple_assistant_bucket()
        P->>P: _try_simple_bucket_answer(bucket)

        alt realtime_patrol
            P->>P: get_realtime_patrol_brief(synthesize=True)
            P->>DB: 查询 t_tias_course 等
            DB-->>P: 聚合数据
            P->>P: _summarize(task,data,fallback)
            P->>L: chat/completions
            L-->>P: 简报文本(失败则fallback)
        else daily_patrol/realtime_warning/daily_warning/push_preview/...
            P->>P: get_*_brief(synthesize=True)
            P->>DB: 对应 SQL 聚合
            DB-->>P: 结构化数据
            P->>P: _summarize()
            P->>L: chat/completions
            L-->>P: 简报文本(失败则fallback)
        end

        P-->>M: {intent:bucket, source:"patrol_api", data, answer}
    else 通用问答
        P->>P: _general_llm_answer()
        P->>L: chat/completions
        L-->>P: 通用回答(失败返回兜底提示)
        P-->>M: {intent:"general", source:"llm", answer}
    end

    M->>M: 按字符切分 answer
    loop delta streaming
        M-->>U: NDJSON delta
    end
    M-->>U: NDJSON done
