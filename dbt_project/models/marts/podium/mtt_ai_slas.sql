{{ config(
    materialized='incremental',
    unique_key=['tenant_id'],
    properties=trino_s3_properties('mtt_ai_slas')
) }}

select
    tenant_id,
    {{ date_from_timestamp('min(timestamp)') }} as date_day,
    max(timestamp) as latest_timestamp,
    count(*) as telemetry_count,
    sum(prompt_tokens) as total_prompt_tokens,
    sum(completion_tokens) as total_completion_tokens,
    sum(total_tokens) as total_tokens_consumed,
    avg(latency_ms) as avg_latency_ms,
    {{ percentile_value('latency_ms', 0.5) }} as p50_latency,
    {{ percentile_value('latency_ms', 0.95) }} as p95_latency,
    {{ percentile_value('latency_ms', 0.99) }} as p99_latency,
    count(*) filter (where sla_status = 'met') as sla_met_count,
    count(*) filter (where sla_status = 'warning') as sla_warning_count,
    count(*) filter (where sla_status = 'breached') as sla_breached_count,
    {{ as_double("count(*) filter (where sla_status = 'met')") }}
        / nullif(count(*), 0) as sla_compliance_rate
from {{ ref('stg_ai_telemetry') }}
{% if is_incremental() %}
where timestamp >= (select coalesce(max(latest_timestamp), {{ timestamp_literal('1970-01-01') }}) from {{ this }})
{% endif %}
group by tenant_id
