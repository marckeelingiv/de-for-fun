select
    cast(timestamp as timestamp) as timestamp,
    cast(device_id as varchar) as device_id,
    cast(beacon_id as varchar) as beacon_id,
    cast(x_coord as double) as x_coord,
    cast(y_coord as double) as y_coord,
    cast(estimated_dwell_time as integer) as estimated_dwell_time,
    cast(tenant_id as varchar) as tenant_id,
    cast(year as integer) as year,
    cast(month as integer) as month
from {{ source('raw_arena', 'fan_pings') }}
