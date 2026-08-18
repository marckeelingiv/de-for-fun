{{ config(
    materialized='incremental',
    unique_key=['tenant_id', 'merchant_id'],
    properties=trino_s3_properties('mtt_merchant_sentiment')
) }}

with joined as (
    select
        i.tenant_id,
        i.merchant_id,
        i.interaction_id,
        i.timestamp,
        i.is_inbound,
        i.is_sms,
        t.sentiment_score
    from {{ ref('stg_interaction_events') }} i
    left join {{ ref('stg_ai_telemetry') }} t
        on i.interaction_id = t.interaction_id
    {% if is_incremental() %}
    where i.timestamp >= (select coalesce(max(latest_timestamp), {{ timestamp_literal('1970-01-01') }}) from {{ this }})
    {% endif %}
)

select
    tenant_id,
    merchant_id,
    {{ date_from_timestamp('min(timestamp)') }} as date_day,
    max(timestamp) as latest_timestamp,
    count(*) as interaction_count,
    count(sentiment_score) as ai_interaction_count,
    avg(sentiment_score) as avg_sentiment,
    count(*) filter (where sentiment_score >= 0.5) as positive_sentiment_count,
    count(*) filter (where sentiment_score < 0.0) as negative_sentiment_count,
    coalesce(round(avg(sentiment_score), 2), 0.0) as sentiment_score,
    {{ as_double('count(*) filter (where sentiment_score >= 0.5)') }}
        / nullif(count(sentiment_score), 0) as sentiment_ratio,
    {{ as_double('count(*) filter (where is_inbound)') }}
        / nullif(count(*), 0) as inbound_ratio,
    {{ as_double('count(*) filter (where is_sms)') }}
        / nullif(count(*), 0) as sms_ratio
from joined
group by tenant_id, merchant_id
