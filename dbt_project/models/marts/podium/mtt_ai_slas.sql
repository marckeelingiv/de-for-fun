{{ config(
    materialized='incremental',
    unique_key=['tenant_id']
) }}

select
    tenant_id,
    min(timestamp)::date as date_day,
    max(timestamp) as latest_timestamp,
    count(*) as telemetry_count,
    sum(prompt_tokens) as total_prompt_tokens,
    sum(completion_tokens) as total_completion_tokens,
    sum(total_tokens) as total_tokens_consumed,
    avg(latency_ms) as avg_latency_ms,
    median(latency_ms) as p50_latency,
    quantile_cont(latency_ms, 0.95) as p95_latency,
    quantile_cont(latency_ms, 0.99) as p99_latency,
    count(*) filter (where sla_status = 'met') as sla_met_count,
    count(*) filter (where sla_status = 'warning') as sla_warning_count,
    count(*) filter (where sla_status = 'breached') as sla_breached_count,
    count(*) filter (where sla_status = 'met')::double
        / nullif(count(*), 0) as sla_compliance_rate
from {{ ref('stg_ai_telemetry') }}
{% if is_incremental() %}
where timestamp >= (select coalesce(max(latest_timestamp), '1970-01-01'::timestamp) from {{ this }})
{% endif %}
group by tenant_id
