{{ config(
    materialized='incremental',
    unique_key=['tenant_id', 'zone', 'beacon_id', 'hour', 'date_day'],
    properties=trino_s3_properties('mtt_arena_bottlenecks')
) }}

with aggregated as (
    select
        tenant_id,
        zone,
        beacon_id,
        hour,
        {{ date_from_timestamp('min(timestamp)') }} as date_day,
        max(timestamp) as latest_timestamp,
        count(*) as ping_count,
        count(distinct device_id) as unique_devices,
        avg(estimated_dwell_time) as avg_dwell_time,
        max(estimated_dwell_time) as max_dwell_time,
        sum(case when is_high_dwell then 1 else 0 end) as high_dwell_count
    from {{ ref('stg_fan_pings') }}
    {% if is_incremental() %}
    where timestamp >= (select coalesce(max(latest_timestamp), {{ timestamp_literal('1970-01-01') }}) from {{ this }})
    {% endif %}
    group by 1, 2, 3, 4
)

select
    tenant_id,
    zone,
    beacon_id,
    hour,
    date_day,
    ping_count,
    unique_devices,
    avg_dwell_time,
    max_dwell_time,
    high_dwell_count,
    {{ as_double('high_dwell_count') }} / ping_count as bottleneck_ratio,
    case
        when {{ as_double('high_dwell_count') }} / ping_count >= 0.5 then 'critical'
        when {{ as_double('high_dwell_count') }} / ping_count >= 0.3 then 'high'
        when {{ as_double('high_dwell_count') }} / ping_count >= 0.15 then 'moderate'
        else 'low'
    end as congestion_level,
    latest_timestamp
from aggregated
