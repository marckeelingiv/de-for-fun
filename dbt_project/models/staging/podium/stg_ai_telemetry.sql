select
    timestamp,
    interaction_id,
    prompt_tokens,
    completion_tokens,
    sentiment_score,
    latency_ms,
    tenant_id,
    year,
    month,
    prompt_tokens + completion_tokens as total_tokens,
    case
        when latency_ms <= 500 then 'met'
        when latency_ms <= 2000 then 'warning'
        else 'breached'
    end as sla_status,
    case
        when sentiment_score >= 0.5 then 'positive'
        when sentiment_score >= 0.0 then 'neutral'
        when sentiment_score >= -0.5 then 'negative'
        else 'very_negative'
    end as sentiment_category,
    extract(hour from timestamp) as hour,
    extract(dow from timestamp) as day_of_week
from {{ ref('base_ai_telemetry') }}
