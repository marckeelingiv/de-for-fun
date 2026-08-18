{{ config(properties=trino_s3_properties('time_spine_daily')) }}

{% if target.type == 'trino' %}
select date_day
from unnest(sequence(date '2025-01-01', date '2025-12-31', interval '1' day)) as t(date_day)
{% else %}
select
    {{ date_from_timestamp('generate_series') }} as date_day
from generate_series(date '2025-01-01', date '2025-12-31', interval '1 day')
{% endif %}
