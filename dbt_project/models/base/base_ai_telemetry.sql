select
    cast(timestamp as timestamp) as timestamp,
    cast(interaction_id as varchar) as interaction_id,
    cast(prompt_tokens as integer) as prompt_tokens,
    cast(completion_tokens as integer) as completion_tokens,
    cast(sentiment_score as double) as sentiment_score,
    cast(latency_ms as integer) as latency_ms,
    cast(tenant_id as varchar) as tenant_id,
    cast(year as integer) as year,
    cast(month as integer) as month
from {{ source('raw_podium', 'ai_telemetry') }}
