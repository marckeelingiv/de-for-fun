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
)

select
    tenant_id,
    merchant_id,
    min(timestamp)::date as date_day,
    count(*) as interaction_count,
    count(sentiment_score) as ai_interaction_count,
    avg(sentiment_score) as avg_sentiment,
    count(*) filter (where sentiment_score >= 0.5) as positive_sentiment_count,
    count(*) filter (where sentiment_score < 0.0) as negative_sentiment_count,
    coalesce(round(avg(sentiment_score), 2), 0.0) as sentiment_score,
    count(*) filter (where sentiment_score >= 0.5)::double
        / nullif(count(sentiment_score), 0) as sentiment_ratio,
    count(*) filter (where is_inbound)::double
        / nullif(count(*), 0) as inbound_ratio,
    count(*) filter (where is_sms)::double
        / nullif(count(*), 0) as sms_ratio
from joined
group by tenant_id, merchant_id
