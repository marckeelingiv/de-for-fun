{{ config(
    materialized='incremental',
    unique_key=['tenant_id', 'vendor_id', 'item_id', 'hour', 'date_day'],
    properties=trino_s3_properties('mtt_dynamic_pricing')
) }}

with aggregated as (
    select
        tenant_id,
        vendor_id,
        item_id,
        hour,
        {{ date_from_timestamp('min(timestamp)') }} as date_day,
        max(timestamp) as latest_timestamp,
        count(*) as transaction_count,
        sum(amount) as total_revenue,
        avg(amount) as avg_price,
        min(amount) as min_price,
        max(amount) as max_price
    from {{ ref('stg_pos_transactions') }}
    {% if is_incremental() %}
    where timestamp >= (select coalesce(max(latest_timestamp), {{ timestamp_literal('1970-01-01') }}) from {{ this }})
    {% endif %}
    group by 1, 2, 3, 4
)

select
    tenant_id,
    vendor_id,
    item_id,
    hour,
    date_day,
    transaction_count,
    total_revenue,
    avg_price,
    min_price,
    max_price,
    transaction_count * 1.0 / nullif(avg(transaction_count) over (), 0) as demand_index,
    hour in (18, 21) as is_peak_window,
    rank() over (partition by tenant_id, vendor_id order by total_revenue desc) as revenue_rank,
    latest_timestamp
from aggregated
