select
    timestamp,
    transaction_id,
    vendor_id,
    item_id,
    amount,
    payment_method,
    tenant_id,
    year,
    month,
    extract(hour from timestamp) as hour,
    extract(dow from timestamp) as day_of_week,
    case
        when amount < 10 then 'budget'
        when amount < 30 then 'standard'
        when amount < 60 then 'premium'
        else 'luxury'
    end as price_tier,
    extract(hour from timestamp) in (18, 21) as is_peak_window
from {{ ref('base_pos_transactions') }}
