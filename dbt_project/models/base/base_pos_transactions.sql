select
    cast(timestamp as timestamp) as timestamp,
    cast(transaction_id as varchar) as transaction_id,
    cast(vendor_id as varchar) as vendor_id,
    cast(item_id as varchar) as item_id,
    cast(amount as double) as amount,
    cast(payment_method as varchar) as payment_method,
    cast(tenant_id as varchar) as tenant_id,
    cast(year as integer) as year,
    cast(month as integer) as month
from {{ source('raw_arena', 'pos_transactions') }}
