{{ config(properties=trino_s3_properties('base_pos_transactions')) }}

select
    cast(timestamp as timestamp) as timestamp,
    cast(transaction_id as varchar) as transaction_id,
    cast(vendor_id as varchar) as vendor_id,
    cast(item_id as varchar) as item_id,
    cast(amount as double) as amount,
    cast(payment_method as varchar) as payment_method,
    cast(tenant_id as varchar) as tenant_id,
    cast(extract(year from timestamp) as integer) as year,
    cast(extract(month from timestamp) as integer) as month,
    cast(generated_at as timestamp) as generated_at
from {{ source('raw_arena', 'pos_transactions') }}
