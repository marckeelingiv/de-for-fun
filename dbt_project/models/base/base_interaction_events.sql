select
    cast(timestamp as timestamp) as timestamp,
    cast(merchant_id as varchar) as merchant_id,
    cast(customer_id as varchar) as customer_id,
    cast(channel as varchar) as channel,
    cast(direction as varchar) as direction,
    cast(tenant_id as varchar) as tenant_id,
    cast(year as integer) as year,
    cast(month as integer) as month
from {{ source('raw_podium', 'interaction_events') }}
