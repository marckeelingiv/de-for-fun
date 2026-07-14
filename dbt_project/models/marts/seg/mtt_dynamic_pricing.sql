with aggregated as (
    select
        tenant_id,
        vendor_id,
        item_id,
        hour,
        min(timestamp)::date as date_day,
        count(*) as transaction_count,
        sum(amount) as total_revenue,
        avg(amount) as avg_price,
        min(amount) as min_price,
        max(amount) as max_price
    from {{ ref('stg_pos_transactions') }}
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
    rank() over (partition by tenant_id, vendor_id order by total_revenue desc) as revenue_rank
from aggregated
