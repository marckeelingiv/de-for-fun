{{ config(properties=trino_s3_properties('base_fan_pings')) }}

select
    cast(timestamp as timestamp) as timestamp,
    cast(device_id as varchar) as device_id,
    cast(beacon_id as varchar) as beacon_id,
    cast(x_coord as double) as x_coord,
    cast(y_coord as double) as y_coord,
    cast(estimated_dwell_time as integer) as estimated_dwell_time,
    cast(tenant_id as varchar) as tenant_id,
    cast(extract(year from timestamp) as integer) as year,
    cast(extract(month from timestamp) as integer) as month,
    cast(generated_at as timestamp) as generated_at
from {{ source('raw_arena', 'fan_pings') }}
