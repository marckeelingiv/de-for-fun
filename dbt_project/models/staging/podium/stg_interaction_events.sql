select
    timestamp,
    interaction_id,
    merchant_id,
    customer_id,
    channel,
    direction,
    tenant_id,
    year,
    month,
    extract(hour from timestamp) as hour,
    extract(dow from timestamp) as day_of_week,
    extract(hour from timestamp) between 9 and 17 as is_business_hours,
    direction = 'Inbound' as is_inbound,
    channel = 'SMS' as is_sms
from {{ ref('base_interaction_events') }}
