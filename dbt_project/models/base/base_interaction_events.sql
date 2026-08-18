{{ config(properties=trino_s3_properties('base_interaction_events')) }}

select
    cast(timestamp as timestamp) as timestamp,
    cast(interaction_id as varchar) as interaction_id,
    cast(merchant_id as varchar) as merchant_id,
    cast(customer_id as varchar) as customer_id,
    cast(channel as varchar) as channel,
    cast(direction as varchar) as direction,
    cast(tenant_id as varchar) as tenant_id,
    cast(extract(year from timestamp) as integer) as year,
    cast(extract(month from timestamp) as integer) as month,
    cast(generated_at as timestamp) as generated_at
from {{ source('raw_podium', 'interaction_events') }}
