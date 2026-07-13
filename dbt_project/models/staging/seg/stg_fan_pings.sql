select
    timestamp,
    device_id,
    beacon_id,
    x_coord,
    y_coord,
    estimated_dwell_time,
    tenant_id,
    year,
    month,
    extract(hour from timestamp) as hour,
    extract(dow from timestamp) as day_of_week,
    case
        when beacon_id like 'food_court%' then 'food_court'
        when beacon_id like 'entrance%' then 'entrance'
        when beacon_id like 'section%' then 'section'
        when beacon_id like 'vip%' then 'vip'
        when beacon_id like 'merch%' then 'merch'
        when beacon_id like 'concourse%' then 'concourse'
        else 'unknown'
    end as zone,
    estimated_dwell_time >= 300 as is_high_dwell
from {{ ref('base_fan_pings') }}
